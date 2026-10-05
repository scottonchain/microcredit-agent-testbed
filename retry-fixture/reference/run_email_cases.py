#!/usr/bin/env python3
"""Executable checks for the email cases of retry-fixture/cases.json, run against the reference model in model.py.

For every email case there is one check written from the case's `setup` and `expected` text. Each check runs twice:
  reference  -> must PASS  (our model of the stated rule produces the stated expected state)
  mutant     -> must FAIL  (the same model with exactly the rule that case states flipped does NOT; so the check
                            discriminates and is not vacuous)
Exit 0 only if every reference run passes and every mutant run fails. Stdlib only; deterministic; simulated clock.

This does not change the status of any case in cases.json: they stay `proposed / not-run` with respect to the systems
of the agents whose words the expected states are (merktop, forgeloop). What it adds is a third field of evidence per
case: `reference_model_check` (which check, what it asserts, mutant that fails it), so a reader can run the words.
Usage: python3 run_email_cases.py [--json]
"""
import json, sys
from model import Clock, Provider, Reconciler, REFERENCE


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
