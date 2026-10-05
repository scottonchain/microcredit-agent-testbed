#!/usr/bin/env python3
"""Executable checks for the off-chain cases (email-N, api-N) of retry-fixture/cases.json, run against the reference model
in model.py (email cases) and comment_api.py (api cases).

For every off-chain case there is one check written from the case's `setup` and `expected` text. Each check runs twice:
  reference  -> must PASS  (our model of the stated rule produces the stated expected state)
  mutant     -> must FAIL  (the same model with exactly the rule that case states flipped does NOT; so the check
                            discriminates and is not vacuous)
Exit 0 only if every reference run passes and every mutant run fails. Stdlib only; deterministic; simulated clock.

This does not change the status of any case in cases.json: they stay `proposed / not-run` with respect to the systems
of the agents whose words the expected states are (merktop, forgeloop, pyclaw001, mundo). What it adds is a third field of evidence per
case: `reference_model_check` (which check, what it asserts, mutant that fails it), so a reader can run the words.
Usage: python3 run_email_cases.py [--json]
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Clock, Provider, Reconciler, REFERENCE
from comment_api import CommentAPI, Poster


def scenario(policy, index_latency=0):
    clk = Clock()
    p = Provider(clk, index_latency=index_latency)
    r = Reconciler(p, clk, policy)
    return clk, p, r


class Check:
    def __init__(self, cid, asserts, mutant, fn):
        self.cid, self.asserts, self.mutant, self.fn = cid, asserts, mutant, fn


def email_1(policy):
    """send accepted by provider, then client timed out after the server committed -> an idempotent retry must find
    the original before sending (exactly one message at the provider)."""
    clk, p, r = scenario(policy, index_latency=0)
    p.send_behaviour = "accept_then_timeout"
    r.submit("k1", ["a@x"], "body")
    p.send_behaviour = "accepted"
    res = r.idempotent_retry("k1")
    return p.send_calls == 1 and len(p.msgs) == 1 and r.rows["k1"]["submission"] == "confirmed" and res["action"] == "no_send", \
        {"provider_sends": p.send_calls, "messages_at_provider": len(p.msgs), "row": r.rows["k1"]["submission"], "retry": res}


def email_2(policy):
    """accepted copy only searchable ~10 s later -> the read tolerates late indexing with timed retries AND every
    absence verdict names the index's as-of time; 'not found at index-as-of-T' is not 'never sent'."""
    clk, p, r = scenario(policy, index_latency=10)
    p.send_behaviour = "accept_then_timeout"
    r.submit("k2", ["a@x"], "body")          # committed at t=0, searchable from t=10
    p.send_behaviour = "accepted"
    res = r.idempotent_retry("k2")           # reads at t=0 (as-of -10), t=8 (as-of -2), t=16 (as-of 6 >= 0: hit)
    absences = [v for v in r.rows["k2"]["verdicts"] if v["kind"] == "absence"]
    named = all(v.get("as_of") is not None and "never sent" in v.get("meaning", "") for v in absences)
    ok = (r.rows["k2"]["submission"] == "confirmed" and p.send_calls == 1 and len(absences) == 2 and named
          and all(v["index_current_past_dispatch"] is False for v in absences))
    return ok, {"row": r.rows["k2"]["submission"], "provider_sends": p.send_calls, "absence_verdicts": absences, "clock": clk.now}


def email_3(policy):
    """the dedup query's template phrase silently changed so the match misses -> a phrase-free fallback still matches."""
    clk, p, r = scenario(policy, index_latency=0)
    p.send_behaviour = "accept_then_timeout"
    r.submit("k3", ["a@x"], "body")          # sent with template-v1
    r.template_phrase = "template-v2"        # drift after the send: phrase queries now miss
    p.send_behaviour = "accepted"
    res = r.idempotent_retry("k3")
    ev = r.rows["k3"]["submission_evidence"] or {}
    return r.rows["k3"]["submission"] == "confirmed" and ev.get("fallback") is True and p.send_calls == 1, \
        {"row": r.rows["k3"]["submission"], "evidence": ev, "provider_sends": p.send_calls}


def email_4(policy):
    """clean send (control) -> exactly one send, and a replay of the same intent sends nothing."""
    clk, p, r = scenario(policy)
    r.submit("k4", ["a@x"], "body")
    again = r.submit("k4", ["a@x"], "body")
    return p.send_calls == 1 and r.rows["k4"]["submission"] == "confirmed" and again["action"] == "blocked", \
        {"provider_sends": p.send_calls, "row": r.rows["k4"]["submission"], "replay": again}


def email_5(policy):
    """one submission to two recipients; delivered to A; permanent DSN for B -> submission stays 'submitted' (never
    'never sent'); replaying the whole list stays blocked; only delivery-B flips to failed; a resend to B is a new
    intent with its own key and recipient scope."""
    clk, p, r = scenario(policy)
    r.submit("k5", ["a@x", "b@y"], "body")
    r.delivery_evidence("k5", "a@x", "delivery_receipt", "rcpt-a")
    r.delivery_evidence("k5", "b@y", "dsn_permanent", "dsn-b")
    replay = r.submit("k5", ["a@x", "b@y"], "body")
    resend_all = r.resend("k5")
    new = r.new_intent_for_recipient("k5", "b@y")
    new_a = r.new_intent_for_recipient("k5", "a@x")
    ok = (r.rows["k5"]["submission"] == "confirmed" and replay["action"] == "blocked" and resend_all["action"] == "blocked"
          and r.rows["k5"]["recipients"]["b@y"]["outcome"] == "failed" and r.rows["k5"]["recipients"]["a@x"]["outcome"] == "confirmed"
          and new == {"key": "k5/b@y/1", "recipients": ["b@y"]} and new_a is None and p.send_calls == 1)
    return ok, {"submission": r.rows["k5"]["submission"], "replay": replay, "resend_all": resend_all,
                "recipients": r.rows["k5"]["recipients"], "new_intent_for_B": new, "provider_sends": p.send_calls}


def email_6(policy):
    """accepted message, response lost, search visibility held past all three reads -> row stays unknown; auto-resend
    blocked; a sweeper may write 'unresolved' but never 'failed' without provider-side negative proof; reads promote,
    never demote."""
    clk, p, r = scenario(policy, index_latency=10 ** 6)   # never searchable within the run
    p.send_behaviour = "accept_then_timeout"
    r.submit("k6", ["a@x"], "body")
    p.send_behaviour = "accepted"
    res = r.idempotent_retry("k6")
    sw_unres = r.sweeper_mark("k6", "unresolved")
    sw_fail = r.sweeper_mark("k6", "failed")                                   # no proof: must be refused
    sw_fail_proof = r.sweeper_mark("k6", "failed", provider_negative_proof=None)
    row = r.rows["k6"]
    still_unknown = row["submission"] == "unknown"
    # reads promote, never demote: make the message visible, read (promotes), then a miss must not demote
    p.index_latency = 0
    after_hit = r.reread("k6")
    p.expire("k6")
    after_miss = r.reread("k6")
    ok = (res["action"] == "no_send" and p.send_calls == 1 and still_unknown and sw_unres == "written"
          and sw_fail.startswith("refused") and sw_fail_proof.startswith("refused") and after_hit == "confirmed" and after_miss == "confirmed")
    return ok, {"retry": res, "provider_sends": p.send_calls, "row_after_reads": still_unknown and "unknown", "sweeper_unresolved": sw_unres,
                "sweeper_failed_no_proof": sw_fail, "after_hit": after_hit, "after_miss": after_miss, "verdicts": len(row["verdicts"])}


def email_7(policy):
    """two recipients; Sent observation held fixed; B has no delivery evidence yet; then a permanent DSN for B ->
    before: B = delivery-unknown (a Sent match is not receiver-side evidence); after: B = delivery-failed; A unchanged
    throughout; the two B states must be distinguishable (needs an outcome enum + evidence reference)."""
    clk, p, r = scenario(policy)
    r.submit("k7", ["a@x", "b@y"], "body")                 # accepted: submission confirmed (sender-side Sent evidence)
    r.delivery_evidence("k7", "a@x", "delivery_receipt", "rcpt-a")
    before = r.recipient_state("k7", "b@y")
    a_before = r.recipient_state("k7", "a@x")
    r.delivery_evidence("k7", "b@y", "dsn_permanent", "dsn-b")
    after = r.recipient_state("k7", "b@y")
    a_after = r.recipient_state("k7", "a@x")
    distinguishable = before != after
    b_unknown_before = (before[0] == "unknown") if policy.recipient_enum else (before == (True, False))
    b_failed_after = (after[0] == "failed" and after[1] == ("dsn_permanent", "dsn-b")) if policy.recipient_enum else False
    ok = distinguishable and b_unknown_before and b_failed_after and a_before == a_after and r.rows["k7"]["submission"] == "confirmed"
    return ok, {"B_before_DSN": before, "B_after_DSN": after, "A_before": a_before, "A_after": a_after,
                "distinguishable": distinguishable, "submission": r.rows["k7"]["submission"]}


def email_8(policy):
    """writer observed no provider call and no dispatch record was written (process death) -> the one allowed 'failed'
    without a provider 5xx; checkable = falsifiable: a later provider artifact for the key proves it wrong; a timeout
    or reset with no 5xx stays unknown."""
    clk, p, r = scenario(policy)
    r.submit("k8", ["a@x"], "body", crash_before_dispatch=True)
    state = r.recover("k8")
    dl = r.dead_letters[-1] if r.dead_letters else None
    checkable = (dl is not None and dl["intent_key"] == "k8" and "k8" in r.intents and not r.dispatches.get("k8")
                 and dl["process_id"] == r.process_id and "stop_point" in dl)
    # falsification: a provider artifact appears later -> alert, row promoted
    p.inject_artifact("k8", "msg-late")
    alert = r.provider_artifact_appeared("k8", "msg-late")
    # contrast: timeout / connection reset with no 5xx must NOT be 'failed'
    p.send_behaviour = "reset_before_commit"
    r.submit("k8b", ["a@x"], "body")
    p.send_behaviour = "accept_then_timeout"
    r.submit("k8c", ["a@x"], "body")
    ok = (state == "failed_by_our_own_hand" and checkable and alert == "alert" and r.rows["k8"]["submission"] == "confirmed"
          and r.rows["k8b"]["submission"] == "unknown" and r.rows["k8c"]["submission"] == "unknown")
    return ok, {"recover": state, "dead_letter": dl, "checkable": checkable, "falsification": alert,
                "reset_no_5xx": r.rows["k8b"]["submission"], "timeout_no_5xx": r.rows["k8c"]["submission"]}


def email_9(policy):
    """send outcome unknown; the verification read itself times out -> neither confirmation nor absence: no retry;
    row goes to 'pending verification'; the next run re-checks before any action."""
    clk, p, r = scenario(policy, index_latency=0)
    p.send_behaviour = "accept_then_timeout"
    r.submit("k9", ["a@x"], "body")          # committed; client saw a timeout
    p.send_behaviour = "accepted"
    p.search_timeouts_pending = 1            # the first verification read times out
    res1 = r.idempotent_retry("k9")
    row = r.rows["k9"]
    snap = {"submission": row["submission"], "status": row["status"], "sends": p.send_calls,
            "last_verdict": row["verdicts"][-1]["kind"] if row["verdicts"] else None, "retry": res1}
    first = (snap["submission"] == "unknown" and snap["status"] == "pending_verification" and res1["action"] == "no_send"
             and snap["last_verdict"] == "verification_timeout" and snap["sends"] == 1)
    clk.advance(60)
    res2 = r.idempotent_retry("k9")          # next run: the read works, the original is found, nothing sent
    ok = first and row["submission"] == "confirmed" and res2["action"] == "no_send" and p.send_calls == 1
    return ok, {"after_timed_out_read": snap, "next_run": {"submission": row["submission"], "retry": res2}, "provider_sends": p.send_calls}


def email_11(policy):
    """forgeloop's paired fixture (comment 9ad72438, 2026-10-05): A stops at a controlled barrier before dispatch; B reaches
    a fake provider that records acceptance, then the worker dies before persisting its dispatch record or response.
    Expected: A may qualify as proven-unsent; B must remain outcome-unknown on the recovery path and must not auto-resend;
    the harness keeps the provider receipt as ground truth. The mutant is the ordering published at d563e39 (dispatch
    record written after the call returned): under it B looks exactly like A and a second message is sent."""
    clk, p, r = scenario(policy, index_latency=0)
    r.submit("kA", ["a@x"], "body", crash_before_dispatch=True)
    state_a = r.recover("kA")
    retry_a, _ = r.retry_allowed("kA")
    r.submit("kB", ["a@x"], "body", die_after_provider_accept=True)   # the provider committed one message; no response persisted
    msgs_after_b = len(p.msgs)
    recs_b = list(r.dispatches.get("kB") or [])
    state_b = r.recover("kB")
    retry_b, why_b = r.retry_allowed("kB")
    res_b = r.idempotent_retry("kB")      # recovery path: reconcile first; the provider's receipt is the ground truth
    ok = (state_a == "failed_by_our_own_hand" and retry_a
          and msgs_after_b == 1 and state_b == "unknown" and not retry_b and res_b["action"] == "no_send"
          and len(p.msgs) == 1 and r.rows["kB"]["submission"] == "confirmed")
    return ok, {"A": {"recover": state_a, "retry_allowed": retry_a},
                "B": {"dispatch_records_surviving_the_crash": recs_b, "recover": state_b, "retry_allowed": retry_b, "why": why_b,
                      "recovery_path": res_b, "messages_at_provider": len(p.msgs), "row": r.rows["kB"]["submission"]}}


def email_10(policy):
    """the verification read returns a listing hit for the intent's key whose bytes are not the bytes that were sent ->
    treated as absent AND as evidence of corruption: quarantine, no blind retry; a hit with matching bytes confirms."""
    clk, p, r = scenario(policy, index_latency=0)
    p.send_behaviour = "accept_then_timeout"
    r.submit("k10", ["a@x"], "body")          # committed with the intent's payload digest; the client saw a timeout
    p.send_behaviour = "accepted"
    p.corrupt("k10", "not-the-sent-bytes")    # the copy the listing returns for the key no longer matches the sent bytes
    res = r.idempotent_retry("k10")
    row = r.rows["k10"]
    retry_ok, why = r.retry_allowed("k10")
    resend = r.resend("k10")
    second_pass = r.idempotent_retry("k10")   # a later run must not undo the quarantine by re-reading the same hit
    # control under the same policy: a listing hit whose bytes match the sent payload confirms the row
    clk2, p2, r2 = scenario(policy, index_latency=0)
    p2.send_behaviour = "accept_then_timeout"
    r2.submit("k10c", ["a@x"], "body")
    p2.send_behaviour = "accepted"
    res_c = r2.idempotent_retry("k10c")
    ev_c = r2.rows["k10c"]["submission_evidence"] or {}
    ok = (row["submission"] == "unknown" and row["status"] == "quarantined"
          and (row.get("corruption_evidence") or {}).get("kind") == "listing_hit_mismatched_bytes"
          and res["action"] == "no_send" and not retry_ok and resend["action"] == "blocked" and second_pass["action"] == "no_send"
          and p.send_calls == 1 and len(r.alerts) == 1
          and r2.rows["k10c"]["submission"] == "confirmed" and ev_c.get("bytes_match") is True and res_c["action"] == "no_send" and p2.send_calls == 1)
    return ok, {"mismatch": {"submission": row["submission"], "status": row["status"], "corruption_evidence": row.get("corruption_evidence"),
                             "retry_allowed": [retry_ok, why], "resend": resend, "second_pass": second_pass, "provider_sends": p.send_calls,
                             "alerts": r.alerts},
                "control_match": {"submission": r2.rows["k10c"]["submission"], "evidence": ev_c, "provider_sends": p2.send_calls}}


def email_12(policy):
    """merktop's resend gate and keyed receipt (comments d6effd5a / db054646 / fe341d24, 2026-10-05, addressed to forgeloop and
    deepdonorbot): the dispatch record is committed pre-network as claimed-sent and 'the record alone can never authorize a
    retry'; only a provider receipt promotes it; receipts are matched to intents 'via a request id generated before the first
    byte goes out', so 'an unkeyed receipt is just another blob you cannot safely attribute'. Two intents with identical bytes
    are in flight; the provider commits only the first (its response is lost); the second dies at the socket before any commit.
    Reference: the first is confirmed by its own keyed receipt, the second is confirmed by nothing, one message at the provider,
    and neither present dispatch record authorizes a retry. Mutant receipt_key_required=False: the second intent's unkeyed read
    attributes the first intent's receipt to itself (same bytes, no key) and confirms a message that never went out.
    NOT checked here: whether a 'no' that stays stable across all rounds is receipt-negative (resend fires) or unresolved (the
    row waits for the next run); merktop's words allow both readings, the question is on the case (open_question)."""
    clk, p, r = scenario(policy, index_latency=0)
    p.send_behaviour = "accept_then_timeout"
    r.submit("k12a", ["a@x"], "same template body")      # committed at the provider; the client saw a timeout
    p.send_behaviour = "reset_before_commit"
    r.submit("k12b", ["b@y"], "same template body")      # the socket reset before the provider committed anything
    p.send_behaviour = "accepted"
    rec_a, rec_b = r.dispatches["k12a"][-1], r.dispatches["k12b"][-1]
    retry_a, why_a = r.retry_allowed("k12a")
    retry_b, why_b = r.retry_allowed("k12b")
    res_a = r.idempotent_retry("k12a")                    # keyed receipt for k12a exists -> confirmed, nothing sent
    res_b = r.idempotent_retry("k12b")                    # no receipt carries k12b's key -> must not be confirmed by k12a's
    ev_a = r.rows["k12a"]["submission_evidence"] or {}
    ok = (rec_a["committed"] == "before the provider call" and rec_b["committed"] == "before the provider call"
          and not retry_a and not retry_b
          and r.rows["k12a"]["submission"] == "confirmed" and res_a["action"] == "no_send" and ev_a.get("ref") == "msg-1"
          and r.rows["k12b"]["submission"] != "confirmed"
          and len(p.msgs) == 1)
    return ok, {"records_before_io": [rec_a["committed"], rec_b["committed"]], "retry_allowed_on_record_alone": [retry_a, retry_b],
                "why": [why_a, why_b], "k12a": {"submission": r.rows["k12a"]["submission"], "evidence": ev_a, "retry": res_a},
                "k12b": {"submission": r.rows["k12b"]["submission"], "evidence": r.rows["k12b"]["submission_evidence"], "retry": res_b,
                         "status": r.rows["k12b"]["status"]},
                "messages_at_provider": len(p.msgs), "provider_sends": p.send_calls}


def email_13(policy):
    """mundo 473e4717 (top-level on 117ae039, 07:06 UTC) and merktop 346f92fe (its reply, 09:53 UTC, 'I agree completely'):
    the dedup key has to be born with the message, not derived after the fact from a response; merktop's shape: key minted at
    enqueue time, never regenerated on retry, carried in the send payload, the resend gate queries by it with timed rounds; the
    one post-hoc check that earns its keep is a probe after a quiet period for keys that leaked before the envelope existed.
    Reference (key_born_at_enqueue=True): (a) accept-then-timeout with a lagging index: the gate queries by the enqueue-born key
    and confirms the original, one message, no resend; the provider's record carries that key. (b) a 5xx then a resend: every
    dispatch record carries the same key (never regenerated). (c) an intent with no dispatch record whose acceptance leaked to
    the provider anyway: the probe by key after the quiet period finds it and raises the email-8 alert; a control intent that
    never leaked stays a dead letter after an absent probe. Mutant key_born_at_enqueue=False (the identity is the provider's
    message id from the response): in (a) the response was lost, so there is nothing to query by and the row can never be
    settled by a post-hoc check; in (c) the leaked acceptance cannot be found by this intent."""
    out = {}
    # (a) at-least-once delivery, response lost, index lags 10 s: the gate queries by the enqueue-born key
    clk, p, r = scenario(policy, index_latency=10)
    p.send_behaviour = "accept_then_timeout"
    r.submit("k13a", ["a@x"], "body")
    p.send_behaviour = "accepted"
    res_a = r.idempotent_retry("k13a")
    row_a = r.rows["k13a"]
    out["a"] = {"row": row_a["submission"], "retry": res_a, "provider_sends": p.send_calls, "messages_at_provider": len(p.msgs),
                "provider_record_key": p.msgs[0]["key"] if p.msgs else None, "payload_key_on_record": r.dispatches["k13a"][-1].get("payload_key"),
                "verdicts": [v["kind"] for v in row_a["verdicts"]]}
    ok_a = (row_a["submission"] == "confirmed" and res_a["action"] == "no_send" and p.send_calls == 1 and len(p.msgs) == 1
            and p.msgs[0]["key"] == "k13a" and r.dispatches["k13a"][-1].get("payload_key") == "k13a")
    # (b) explicit 5xx, then the resend: the key is the same on every dispatch record and on the provider's record
    clk, p, r = scenario(policy, index_latency=0)
    p.send_behaviour = "reject_5xx"
    r.submit("k13b", ["b@y"], "body")
    p.send_behaviour = "accepted"
    res_b = r.idempotent_retry("k13b")
    keys_b = [d.get("payload_key") for d in r.dispatches["k13b"]]
    out["b"] = {"retry": res_b, "dispatch_record_keys": keys_b, "provider_record_keys": [m["key"] for m in p.msgs], "row": r.rows["k13b"]["submission"]}
    ok_b = (len(keys_b) == 2 and keys_b == ["k13b", "k13b"] and [m["key"] for m in p.msgs] == ["k13b"] and r.rows["k13b"]["submission"] == "confirmed")
    # (c) the probe: intent row, no dispatch record (dead letter) but the acceptance leaked to the provider under the key;
    #     a control intent with the same shape and no leak
    clk, p, r = scenario(policy, index_latency=0)
    r.submit("k13c", ["c@z"], "leaked body", crash_before_dispatch=True)
    r.submit("k13d", ["d@w"], "control body", crash_before_dispatch=True)
    st_c, st_d = r.recover("k13c"), r.recover("k13d")
    payload_key_c = "k13c" if policy.key_born_at_enqueue else None     # what the leaked send carried, under each policy
    p.send(payload_key_c, ["c@z"], r.template_phrase, r.intents["k13c"]["payload_hash"])   # the leak: a send outside the record
    clk.advance(60)
    early = r.probe_leaked("k13c", quiet_period=120)
    clk.advance(60)
    probe_c, probe_d = r.probe_leaked("k13c", quiet_period=120), r.probe_leaked("k13d", quiet_period=120)
    out["c"] = {"recover": [st_c, st_d], "probe_before_quiet_period": early, "probe": [probe_c, probe_d],
                "k13c": {"submission": r.rows["k13c"]["submission"], "evidence": r.rows["k13c"]["submission_evidence"]},
                "k13d": {"submission": r.rows["k13d"]["submission"], "status": r.rows["k13d"]["status"]},
                "alerts": r.alerts, "dead_letters": [d["intent_key"] for d in r.dead_letters]}
    ok_c = (st_c == "failed_by_our_own_hand" and st_d == "failed_by_our_own_hand" and early == "refused: quiet period not over"
            and probe_c == "alert" and r.rows["k13c"]["submission"] == "confirmed" and (r.rows["k13c"]["submission_evidence"] or {}).get("after_failed_mark") is True
            and probe_d == "absent" and r.rows["k13d"]["submission"] == "failed" and r.rows["k13d"]["status"] == "dead_letter"
            and len(r.alerts) == 1)
    return ok_a and ok_b and ok_c, out


def api_1(policy):
    """a create endpoint with a single-shot verifier (wrong answer burns the code: 400; a consumed code: 409) whose state
    and the object's published state come from authorities that do not see each other -> retry permitted iff the verifier
    allows a new attempt AND a fresh canonical-listing read shows the object absent; verifier success without a listing hit
    is reconciliation, not delivery; the create response's own 'existing' claim is never trusted without a listing read.
    Three sub-scenarios, all from public incident reports: (a) verifier failed but the object is readable (pyclaw001);
    (b) create says 'existing' but the object is failed and unpublished (merktop); (c) verifier 200 but the object is
    absent, the lost receipt (merktop's converse hazard)."""
    two = policy.two_authorities
    out = {}
    # (a) verifier says failed (wrong answer), the object is published anyway: stop, no blind re-create
    api = CommentAPI(); api.publish_despite_failed = True
    po = Poster(api, two_authorities=two)
    disp_a = po.post_once("hello", answers=(False, True))
    burned = api.verify("code-1", True)         # reuse of the consumed code is impermissible whatever the policy (model fact)
    out["a"] = {"disposition": disp_a, "creates": api.creates, "published": api.listing(), "reuse_of_consumed_code": burned, "log": po.log}
    ok_a = disp_a == "stop: object present despite verifier 400" and api.creates == 1 and api.listing() == ["c1"] and burned == 409
    # (b) a crashed-then-restarted client re-creates the same content; the dedup layer answers 'existing' for an object whose
    #     verification failed and which the listing does not show: the listing decides, so the object is rewritten under a new identity
    api = CommentAPI()
    po = Poster(api, two_authorities=two)
    first = po.post_once("hello", answers=(False,), max_creates=1)       # wrong answer: failed, unpublished
    po2 = Poster(api, two_authorities=two)
    disp_b = po2.post_once("hello", answers=(True,))                     # restart: create -> 'existing' (status failed)
    out["b"] = {"first": first, "disposition": disp_b, "creates": api.creates, "published": api.listing(), "log": po2.log}
    ok_b = disp_b == "delivered" and api.listing_has("hello ") and len(api.listing()) == 1 and api.creates == 3
    # (c) verifier 200 but the object never becomes readable (lost receipt): reconcile, never claim delivery
    api = CommentAPI(); api.lose_receipt = True
    po = Poster(api, two_authorities=two)
    disp_c = po.post_once("hello", answers=(True,))
    out["c"] = {"disposition": disp_c, "creates": api.creates, "published": api.listing(), "log": po.log}
    ok_c = disp_c == "reconcile: verifier success, object absent" and api.creates == 1 and api.listing() == []
    return ok_a and ok_b and ok_c, out


CHECKS = [
    Check("email-1", "one provider send; the retry reconciles and finds the original; row confirmed",
          REFERENCE.mutate(timeout_is_failure=True), email_1),
    Check("email-2", "two absence verdicts, each naming index-as-of and 'not never sent'; third read hits; one send",
          REFERENCE.mutate(absence_means_never_sent=True), email_2),
    Check("email-3", "phrase reads miss after template drift; the phrase-free fallback confirms; one send",
          REFERENCE.mutate(fallback_query=False), email_3),
    Check("email-4", "exactly one send; a replay under the same key is blocked",
          REFERENCE.mutate(replay_check=False), email_4),
    Check("email-5", "submission stays confirmed; whole-list replay and resend blocked; only B failed; B resend = new intent key",
          REFERENCE.mutate(dsn_fails_submission=True), email_5),
    Check("email-6", "row unknown past all reads; no send; sweeper 'unresolved' ok, 'failed' refused without proof; hit promotes, miss never demotes",
          REFERENCE.mutate(sweeper_failed_needs_proof=False), email_6),
    Check("email-7", "B unknown-with-no-evidence before the DSN, failed-with-DSN-reference after; A unchanged; the two B states differ",
          REFERENCE.mutate(recipient_enum=False), email_7),
    Check("email-8", "intent row + no dispatch record -> failed-by-our-own-hand in a dead letter; a later provider artifact raises an alert; reset/timeout stay unknown",
          REFERENCE.mutate(timeout_is_failure=True), email_8),
    Check("email-9", "a timed-out verification read leaves the row pending verification with no send; the next run confirms; one send",
          REFERENCE.mutate(verification_timeout_is_absence=True), email_9),
    Check("email-11", "A (barrier before dispatch) -> proven-unsent; B (provider accepted, response never persisted) -> unknown, "
          "auto-resend blocked, reconciled from the provider receipt: one message at the provider",
          REFERENCE.mutate(dispatch_record_before_io=False), email_11),
    Check("email-10", "a listing hit with mismatched bytes leaves the row unknown + quarantined with corruption evidence; retry and resend blocked; a matching hit confirms; one send each",
          REFERENCE.mutate(byte_match_required=False), email_10),
    Check("email-12", "neither present dispatch record authorizes a retry; the committed intent is confirmed by its own keyed receipt; the intent that never left is not confirmed by another intent's receipt (same bytes, other key); one message at the provider",
          REFERENCE.mutate(receipt_key_required=False), email_12),
    Check("email-13", "(a) response lost, index lagging: the gate queries by the enqueue-born key, confirms the original, one message, no resend; (b) after a 5xx the resend carries the same key; (c) a leaked acceptance for an intent with no dispatch record is found by the probe after the quiet period (alert), a control stays a dead letter",
          REFERENCE.mutate(key_born_at_enqueue=False), email_13),
    Check("api-1", "(a) verifier 400 + object readable: stop, one create; (b) create says existing + object unpublished: rewrite, delivered once; (c) verifier 200 + object absent: reconcile, no delivery claim",
          REFERENCE.mutate(two_authorities=False), api_1),
]


def main(argv):
    as_json = "--json" in argv
    results = []
    all_ok = True
    for ch in CHECKS:
        ref_ok, ref_detail = ch.fn(REFERENCE)
        mut_ok, mut_detail = ch.fn(ch.mutant)
        good = ref_ok and not mut_ok
        all_ok = all_ok and good
        results.append({"case": ch.cid, "asserts": ch.asserts, "reference": "PASS" if ref_ok else "FAIL",
                        "mutant": ch.mutant.name, "mutant_result": "FAIL (expected)" if not mut_ok else "PASS (check is vacuous)",
                        "ok": good, "reference_detail": ref_detail, "mutant_detail": mut_detail})
    if as_json:
        print(json.dumps(results, indent=1, default=str))
    else:
        for x in results:
            print("%-8s reference %s | %s -> %s | %s" % (x["case"], x["reference"], x["mutant"], x["mutant_result"], "ok" if x["ok"] else "PROBLEM"))
            print("         asserts: " + x["asserts"])
        n_ok = sum(1 for x in results if x["ok"])
        print("%d checks, %d ok, %d problem(s)" % (len(results), n_ok, len(results) - n_ok))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
