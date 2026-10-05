#!/usr/bin/env python3
"""Reference model for the email cases of retry-fixture/cases.json (stdlib only, deterministic, simulated clock).

What this is: a toy provider (accepts sends, has a search index with latency, can time out, can emit DSNs) and a
reconciler that implements the rules the fixture states, written by us from the case text, so the email cases can be
executed as checks instead of only read. What it is not: merktop's system, forgeloop's system or any real provider.
A pass here means our model of the stated rule is self-consistent and the check is discriminating (a mutant policy
with that one rule flipped fails it); it says nothing about how the source agents' systems behave.

Policy flags (REFERENCE = the fixture's rules; each case's mutant flips exactly the rule that case states):
  timeout_is_failure              send timeout / connection reset marks the row failed and retries at once
  absence_means_never_sent        an absence verdict (not found) is read as 'never sent' and demotes the row
  use_as_of                       every absence verdict names the index's own as-of time
  rounds, wait                    timed verification reads (merktop: 3 rounds, 8 s)
  fallback_query                  after the phrase reads miss, one phrase-free read
  verification_timeout_is_absence a verification read that times out counts as 'not found'
  sweeper_failed_needs_proof      an external sweeper may write 'failed' only with provider-side negative proof
  miss_demotes                    a later read that misses demotes a confirmed row (reads should promote, never demote)
  recipient_enum                  per-recipient outcome enum + evidence reference (vs two booleans per recipient)
  replay_check                    a second submit under an existing idempotency key is blocked
  dsn_fails_submission            a permanent DSN for one recipient is read as a failed send of the whole list (resend to all)
  dispatch_record_before_io       the dispatch record is committed BEFORE the provider call (outcome 'pending', completed after
                                  the response), so 'intent row + no dispatch record' can only mean the call was never permitted;
                                  False = the ordering published at d563e39 (record written after the call returned), under which
                                  a worker that dies between provider accept and the record write looks proven-unsent (email-11)
  byte_match_required             a listing hit confirms only if its bytes match the intent's payload digest; a mismatched hit is
                                  absent AND evidence of corruption (quarantine, no blind retry) (email-10)
  two_authorities                 a create with a single-shot verifier: retry permitted iff the verifier allows a new attempt AND a
                                  fresh canonical-listing read shows the object absent; neither authority stands in for the other,
                                  and the create response's own claim is never trusted (api-1; see comment_api.py)
"""
import hashlib


class Clock:
    def __init__(self):
        self.now = 0

    def advance(self, seconds):
        self.now += int(seconds)


class Provider:
    """Email provider as the client sees it. A message is committed at accept time and becomes searchable
    index_latency seconds later; the index's as-of time is now - index_latency."""

    def __init__(self, clock, index_latency=0):
        self.clock = clock
        self.index_latency = int(index_latency)
        self.msgs = []
        self.send_calls = 0
        self.search_calls = 0
        self.send_behaviour = "accepted"      # accepted | accept_then_timeout | reject_5xx | reset_before_commit
        self.search_timeouts_pending = 0      # the next N search calls time out on the client side

    def send(self, key, recipients, phrase, payload_hash=None):
        self.send_calls += 1
        b = self.send_behaviour
        if b == "reject_5xx":
            return {"outcome": "5xx", "code": 550}
        if b == "reset_before_commit":
            return {"outcome": "connection_reset"}
        mid = "msg-%d" % (len(self.msgs) + 1)
        self.msgs.append({"id": mid, "key": key, "recipients": list(recipients), "phrase": phrase, "committed_at": self.clock.now,
                          "payload_hash": payload_hash})
        if b == "accept_then_timeout":
            return {"outcome": "timeout"}     # the server committed; the client never saw the response
        return {"outcome": "accepted", "message_id": mid}

    def search(self, key, phrase=None):
        self.search_calls += 1
        if self.search_timeouts_pending > 0:
            self.search_timeouts_pending -= 1
            return {"outcome": "timeout"}
        as_of = self.clock.now - self.index_latency
        hits = [m for m in self.msgs if m["committed_at"] <= as_of and m["key"] == key and (phrase is None or m["phrase"] == phrase)]
        return {"outcome": "ok", "as_of": as_of, "hits": hits}

    def inject_artifact(self, key, message_id):
        """A provider-side artifact for the key appears later (used to falsify a 'never left' attestation)."""
        self.msgs.append({"id": message_id, "key": key, "recipients": [], "phrase": "", "committed_at": self.clock.now, "payload_hash": None})

    def corrupt(self, key, payload_hash):
        """The copy the listing returns for the key no longer carries the bytes that were sent (corrupted receiver state,
        or a different message filed under the same key)."""
        for m in self.msgs:
            if m["key"] == key:
                m["payload_hash"] = payload_hash

    def expire(self, key):
        """Retention: the provider no longer returns the message (a later read misses)."""
        self.msgs = [m for m in self.msgs if m["key"] != key]


class Policy:
    FIELDS = ("timeout_is_failure", "absence_means_never_sent", "use_as_of", "rounds", "wait", "fallback_query",
              "verification_timeout_is_absence", "sweeper_failed_needs_proof", "miss_demotes", "recipient_enum", "replay_check",
              "dsn_fails_submission", "dispatch_record_before_io", "byte_match_required", "two_authorities")

    def __init__(self, name, **kw):
        self.name = name
        for f in self.FIELDS:
            setattr(self, f, kw[f])

    def mutate(self, **changes):
        kw = {f: getattr(self, f) for f in self.FIELDS}
        kw.update(changes)
        return Policy("mutant(" + ", ".join("%s=%s" % kv for kv in sorted(changes.items())) + ")", **kw)


REFERENCE = Policy("reference", timeout_is_failure=False, absence_means_never_sent=False, use_as_of=True, rounds=3, wait=8,
                   fallback_query=True, verification_timeout_is_absence=False, sweeper_failed_needs_proof=True,
                   miss_demotes=False, recipient_enum=True, replay_check=True, dsn_fails_submission=False,
                   dispatch_record_before_io=True, byte_match_required=True, two_authorities=True)


class Reconciler:
    def __init__(self, provider, clock, policy, process_id="worker-1", template_phrase="template-v1"):
        self.p = provider
        self.clock = clock
        self.policy = policy
        self.process_id = process_id
        self.template_phrase = template_phrase   # the phrase the dedup query uses NOW (it can drift after the send)
        self.intents = {}       # key -> intent row, written before any provider call
        self.dispatches = {}    # key -> [dispatch records], one per provider call
        self.rows = {}          # key -> reconciliation row
        self.dead_letters = []
        self.alerts = []
        self.log = []

    # ---- intent + dispatch -------------------------------------------------------------------------------------
    def submit(self, key, recipients, body, crash_before_dispatch=False, die_after_provider_accept=False):
        if key in self.intents and self.policy.replay_check:
            self.log.append((self.clock.now, key, "replay blocked: intent exists; reconcile, do not resend"))
            return {"action": "blocked", "reason": "intent exists"}
        if key not in self.intents:
            self.intents[key] = {"key": key, "recipients": list(recipients), "payload_hash": hashlib.sha256(body.encode()).hexdigest(),
                                 "phrase": self.template_phrase, "created_at": self.clock.now}
            self.rows[key] = {"submission": "unknown", "submission_evidence": None, "status": "open", "verdicts": [],
                              "recipients": {r: {"outcome": "unknown", "evidence": None} for r in recipients}}
        if crash_before_dispatch:
            self.log.append((self.clock.now, key, "process died before the provider call"))
            return {"action": "crashed_before_dispatch"}
        return self._dispatch(key, die_after_provider_accept=die_after_provider_accept)

    def _dispatch(self, key, die_after_provider_accept=False):
        intent = self.intents[key]
        rec = None
        if self.policy.dispatch_record_before_io:
            # committed before any network I/O: a present record means dispatch was permitted or intended, not performed
            rec = {"at": self.clock.now, "outcome": "pending", "provider_ref": None, "code": None,
                   "committed": "before the provider call"}
            self.dispatches.setdefault(key, []).append(rec)
        res = self.p.send(key, intent["recipients"], intent["phrase"], intent["payload_hash"])
        if die_after_provider_accept:
            # forgeloop's case B: the provider has committed the message; the worker dies before persisting the dispatch
            # record (if it is written after the call) or the response. Only what was committed before the call survives.
            self.log.append((self.clock.now, key, "process died after the provider call, before the response was persisted"))
            return {"action": "crashed_after_provider_call"}
        if rec is None:
            rec = {"at": self.clock.now, "outcome": None, "provider_ref": None, "code": None, "committed": "after the provider call"}
            self.dispatches.setdefault(key, []).append(rec)
        rec.update({"outcome": res["outcome"], "provider_ref": res.get("message_id"), "code": res.get("code")})
        row = self.rows[key]
        if res["outcome"] == "accepted":
            self._promote(key, {"kind": "provider_accept", "ref": res["message_id"], "at": self.clock.now})
        elif res["outcome"] == "5xx":
            row["submission"] = "failed"
            row["submission_evidence"] = {"kind": "provider_5xx", "code": res["code"], "at": self.clock.now}
            row["status"] = "settled"
        elif self.policy.timeout_is_failure:          # timeout / reset: no provider verdict of any kind
            row["submission"] = "failed"
            row["submission_evidence"] = {"kind": "client_timeout_treated_as_failure", "at": self.clock.now}
            row["status"] = "settled"
        else:
            row["submission"] = "unknown"
            row["status"] = "pending_verification"
        return {"action": "dispatched", "outcome": res["outcome"]}

    def recover(self, key):
        """Restart path. Intent row with no dispatch record = no provider call was ever permitted -> failed-by-our-own-hand
        (sound only because the record is committed before the call; see dispatch_record_before_io). A dispatch record
        whose outcome is still 'pending' = the call may have happened and the response was lost -> unknown; the row goes to
        pending_verification and auto-resend stays blocked (forgeloop's case B, email-11)."""
        row = self.rows[key]
        recs = self.dispatches.get(key) or []
        if recs and recs[-1]["outcome"] == "pending":
            row["submission"] = "unknown"
            row["status"] = "pending_verification"
            row["verdicts"].append({"kind": "dispatch_record_pending", "at": self.clock.now,
                                    "meaning": "dispatch was permitted before the call and no response was persisted: neither "
                                               "confirmation nor absence; reconcile against the provider, never resend on this"})
            return "unknown"
        if key in self.intents and not recs:
            row["submission"] = "failed"
            row["submission_evidence"] = {"kind": "failed_by_our_own_hand", "stop_point": "process death before the provider call",
                                          "evidence": "intent row present, no dispatch record under this key", "at": self.clock.now}
            row["status"] = "dead_letter"
            self.dead_letters.append({"intent_key": key, "stop_point": "process death before the provider call",
                                      "process_id": self.process_id, "at": self.clock.now})
            return "failed_by_our_own_hand"
        return row["submission"]

    # ---- verification ------------------------------------------------------------------------------------------
    def _absence(self, key, r, extra=None):
        row = self.rows[key]
        dispatch_at = self.dispatches[key][-1]["at"]
        v = {"kind": "absence", "at": self.clock.now}
        if extra:
            v.update(extra)
        if self.policy.use_as_of and r.get("as_of") is not None:
            v["as_of"] = r["as_of"]
            v["index_current_past_dispatch"] = r["as_of"] >= dispatch_at
            v["meaning"] = "not found at index-as-of-%d; not 'never sent'; unknown until the index is current past %d" % (r["as_of"], dispatch_at)
        else:
            v["as_of"] = None
            v["meaning"] = "not found"
        row["verdicts"].append(v)
        if self.policy.absence_means_never_sent:
            row["submission"] = "failed"
            row["submission_evidence"] = {"kind": "absence_verdict_read_as_never_sent", "at": self.clock.now}
            row["status"] = "settled"
            return True
        return False

    def _timeout(self, key, extra=None):
        row = self.rows[key]
        if self.policy.verification_timeout_is_absence:
            return self._absence(key, {"as_of": None}, dict(extra or {}, timed_out_read=True))
        v = {"kind": "verification_timeout", "at": self.clock.now, "meaning": "neither confirmation nor absence; no retry; re-check next run"}
        if extra:
            v.update(extra)
        row["verdicts"].append(v)
        row["status"] = "pending_verification"
        return True

    def _hit(self, key, r, extra=None):
        """A listing hit for the key. Reference: it confirms only if its bytes match the intent's payload digest; a hit whose
        bytes mismatch is absent AND evidence of corruption (quarantine, no blind retry). Mutant byte_match_required=False:
        the id-only check most send loops run (any hit for the key confirms). Returns True when the row was settled here."""
        row = self.rows[key]
        want = self.intents[key]["payload_hash"]
        match = [m for m in r["hits"] if m.get("payload_hash") == want]
        if match or not self.policy.byte_match_required:
            ev = {"kind": "sent_copy", "ref": (match or r["hits"])[0]["id"], "index_as_of": r["as_of"], "at": self.clock.now,
                  "bytes_match": bool(match)}
            if extra:
                ev.update(extra)
            self._promote(key, ev)
            return True
        found = sorted(set(str(m.get("payload_hash")) for m in r["hits"]))
        row["status"] = "quarantined"                      # submission stays unknown: the hit is not the original
        row["corruption_evidence"] = {"kind": "listing_hit_mismatched_bytes", "refs": [m["id"] for m in r["hits"]],
                                      "expected_digest": want, "found_digests": found, "index_as_of": r["as_of"], "at": self.clock.now}
        v = {"kind": "absence_with_corruption", "at": self.clock.now, "as_of": r["as_of"],
             "meaning": "listing hit for the key but the bytes are not what was sent: absent AND corrupted receiver state; quarantine, no blind retry"}
        if extra:
            v.update(extra)
        row["verdicts"].append(v)
        self.alerts.append({"key": key, "at": self.clock.now, "alert": "quarantine: listing copy for the key does not match the sent bytes"})
        return True

    def verify(self, key):
        """One reconcile pass for an unknown-outcome row. Never sends."""
        row = self.rows[key]
        if row["submission"] != "unknown" or row["status"] == "quarantined":
            return row["submission"]
        for i in range(self.policy.rounds):
            r = self.p.search(key, phrase=self.template_phrase)
            if r["outcome"] == "timeout":
                self._timeout(key)
                return row["submission"]
            if r["hits"]:
                self._hit(key, r)
                return row["submission"]
            if self._absence(key, r):
                return row["submission"]
            if i < self.policy.rounds - 1:
                self.clock.advance(self.policy.wait)
        if self.policy.fallback_query:
            r = self.p.search(key, phrase=None)
            if r["outcome"] == "timeout":
                self._timeout(key, {"fallback": True})
                return row["submission"]
            if r["hits"]:
                self._hit(key, r, {"fallback": True})
                return row["submission"]
            if self._absence(key, r, {"fallback": True}):
                return row["submission"]
        row["status"] = "pending_verification"
        row["note"] = "unresolved this run; the row waits for the next execution"
        return "unknown"

    def _promote(self, key, evidence):
        row = self.rows[key]
        row["submission"] = "confirmed"
        row["submission_evidence"] = evidence     # submission evidence only; per-recipient outcomes untouched
        row["status"] = "settled"

    def reread(self, key):
        """A later read with no action attached. A hit promotes; a miss changes nothing unless miss_demotes."""
        row = self.rows[key]
        r = self.p.search(key, phrase=None)
        if r["outcome"] == "ok" and r["hits"]:
            if row["submission"] != "confirmed":
                self._promote(key, {"kind": "sent_copy", "ref": r["hits"][0]["id"], "index_as_of": r["as_of"], "at": self.clock.now})
        elif r["outcome"] == "ok" and self.policy.miss_demotes and row["submission"] == "confirmed":
            row["submission"] = "unknown"
            row["submission_evidence"] = None
            row["status"] = "pending_verification"
        return row["submission"]

    # ---- retries -----------------------------------------------------------------------------------------------
    def retry_allowed(self, key):
        row = self.rows[key]
        if row["status"] == "quarantined":
            return False, "quarantined: the listing copy for this key does not match the sent bytes; review, no blind retry"
        if row["submission"] == "failed":
            return True, row["submission_evidence"]["kind"]
        return False, "submission is %s; retries fire only on explicit failure signals" % row["submission"]

    def resend(self, key):
        ok, why = self.retry_allowed(key)
        if not ok:
            self.log.append((self.clock.now, key, "resend blocked: " + why))
            return {"action": "blocked", "reason": why}
        self.rows[key]["submission"] = "unknown"
        return self._dispatch(key)

    def idempotent_retry(self, key):
        """The retry path: reconcile first, send only on an explicit failure."""
        state = self.verify(key)
        if state == "failed":
            return self.resend(key)
        return {"action": "no_send", "state": state}

    # ---- sweeper (external process with its own clock) -------------------------------------------------------
    def sweeper_mark(self, key, state, provider_negative_proof=None):
        row = self.rows[key]
        if state == "unresolved":
            row["status"] = "unresolved"
            return "written"
        if state == "failed":
            if provider_negative_proof in ("provider_5xx", "explicit_not_sent_for_key") or not self.policy.sweeper_failed_needs_proof:
                row["submission"] = "failed"
                row["submission_evidence"] = {"kind": provider_negative_proof or "sweeper_clock_expiry", "at": self.clock.now}
                return "written"
            return "refused: 'failed' needs provider-side negative proof"
        return "refused: unknown state"

    # ---- per-recipient delivery evidence --------------------------------------------------------------------------
    def delivery_evidence(self, key, recipient, kind, ref):
        """kind: delivery_receipt (receiver-side positive) | dsn_permanent (RFC 3464 permanent failure)."""
        row = self.rows[key]
        rec = row["recipients"][recipient]
        rec["outcome"] = {"dsn_permanent": "failed", "delivery_receipt": "confirmed"}[kind]
        rec["evidence"] = {"kind": kind, "ref": ref, "at": self.clock.now}
        if kind == "dsn_permanent" and self.policy.dsn_fails_submission:   # the behaviour email-5 warns about: a bounce for one
            row["submission"] = "failed"                                     # recipient read as a failed send of the whole list
            row["submission_evidence"] = {"kind": "dsn_read_as_submission_failure", "ref": ref, "at": self.clock.now}

    def recipient_state(self, key, recipient):
        """What the store can say about one recipient: enum + evidence reference, or two booleans."""
        row = self.rows[key]
        rec = row["recipients"][recipient]
        if self.policy.recipient_enum:
            return (rec["outcome"], None if rec["evidence"] is None else (rec["evidence"]["kind"], rec["evidence"]["ref"]))
        return (row["submission"] == "confirmed", rec["outcome"] == "confirmed")   # submission_confirmed, delivery_confirmed

    def new_intent_for_recipient(self, old_key, recipient):
        """A resend to one failed recipient is a new intent with its own idempotency key and recipient scope."""
        rec = self.rows[old_key]["recipients"][recipient]
        if rec["outcome"] != "failed":
            return None
        n = 1 + sum(1 for k in self.intents if k.startswith(old_key + "/" + recipient + "/"))
        return {"key": "%s/%s/%d" % (old_key, recipient, n), "recipients": [recipient]}

    # ---- falsification -------------------------------------------------------------------------------------------
    def provider_artifact_appeared(self, key, message_id):
        row = self.rows[key]
        ev = row.get("submission_evidence") or {}
        if row["submission"] == "failed" and ev.get("kind") in ("failed_by_our_own_hand", "client_timeout_treated_as_failure",
                                                                "absence_verdict_read_as_never_sent", "sweeper_clock_expiry"):
            self.alerts.append({"key": key, "at": self.clock.now, "alert": "provider artifact %s appeared for a row marked failed (%s): "
                                "the 'never left' attestation is provably wrong" % (message_id, ev.get("kind"))})
            self._promote(key, {"kind": "sent_copy", "ref": message_id, "at": self.clock.now, "after_failed_mark": True})
            return "alert"
        return "no_alert"
