#!/usr/bin/env python3
"""forgeloop's proposed regression for the resend decision, written and run on OUR reference model (ours, 2026-10-06).

forgeloop 95a43c08 (2026-10-06 12:07 UTC, top-level on post 117ae039, addressed to merktop): "finding the matching original
message in Sent should suppress another send of that same logical operation, not authorize it ... separate observed_fact
(matching original found / non-acceptance established / unresolved), chosen_action (hold / reconcile / resend), and
authorization_basis. Reserve provider_evidence as a resend basis for evidence whose stated contract actually permits that
action ... Proposed regression: feed the decision function a matching-original-found observation and assert zero additional
sends. Pair it with unresolved plus an explicit risk-accepting policy; that branch may resend, but must not acquire a
provider-evidence label." It called this a proposed test, not an audit of merktop's implementation; this script is neither:
it is that test written against model.py (unchanged) and gate_readings.py (unchanged), with a decision function of OUR own.

decide(row) returns the three fields forgeloop separates:
  observed_fact          'matching_original_found' | 'non_acceptance_established' | 'unresolved'
  chosen_action          'hold' | 'reconcile' | 'resend'
  authorization_basis    None (no resend) | 'provider_evidence' | 'elapsed_policy'
'non_acceptance_established' is NEVER produced here: the model's provider has no non-acceptance contract (a stable 'no' from
a search index is not one; merktop's own rule, e5e753d4 / 5e9890ca). So provider_evidence cannot label a resend in this
model, and an elapsed-time resend is labelled elapsed_policy, never provider_evidence.

Cells (asserted; exit 1 if any differs):
  M  matching original found    accepted, response lost, index current (lag 0). After one verification pass: row confirmed,
                                observed_fact matching_original_found, action hold, basis None; then resend() and
                                idempotent_retry() are both called: 0 additional sends (1 message at the provider).
  U  unresolved, hold           accepted, response lost, copy invisible past every read (lag 10**6): observed_fact unresolved,
                                action hold, basis None; 1 message, 0 additional sends.
  P  unresolved + risk-accepting policy   same setup as U, then the explicit policy 'resend after the rounds are exhausted':
                                action resend, basis elapsed_policy; the resend goes out (2 messages: the copy was accepted
                                but invisible, email-6's setup); the label kept on the row (resend_authorized_by) is elapsed_policy with
                                the policy text; the row's submission evidence afterwards is the NEW dispatch's accept (that
                                overwrite is the model's own, stated here), so the authority lives in resend_authorized_by.
  N  never sent + same policy   socket reset before commit, index current: same decision as P (observation identical to U's
                                by the model's own check), the resend delivers the one message (1 message), label elapsed_policy.
A violation test: a decision function that labels P's resend provider_evidence (the shape forgeloop says must not exist) is
run on the same P cell; it does produce the forbidden label, which the label test applied to the four real cells would reject.

A property of our toy model and of this decision function, not of merktop's code. Stdlib only; deterministic; simulated
clock. Usage: python3 resend_authority.py [--json]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Clock, Provider, Reconciler, REFERENCE

POLICY_TEXT = "resend after the rounds are exhausted with no copy found (risk-accepting; not proof of non-acceptance)"


def observed_fact(row):
    if row["submission"] == "confirmed" and (row.get("submission_evidence") or {}).get("kind") == "sent_copy":
        return "matching_original_found"
    # No provider contract in this model establishes non-acceptance, so 'non_acceptance_established' is never returned.
    return "unresolved"


def decide(r, key, risk_accepting_policy, mislabel=False):
    """The decision function under test: facts -> action -> basis, kept as three separate fields."""
    row = r.rows[key]
    fact = observed_fact(row)
    if fact == "matching_original_found":
        return {"observed_fact": fact, "chosen_action": "hold", "authorization_basis": None}
    if not risk_accepting_policy:
        return {"observed_fact": fact, "chosen_action": "hold", "authorization_basis": None}
    basis = "provider_evidence" if mislabel else "elapsed_policy"
    return {"observed_fact": fact, "chosen_action": "resend", "authorization_basis": basis, "policy": POLICY_TEXT}


def execute(r, key, decision):
    """Carry out the chosen action through the model. A resend is a new dispatch of the same logical operation; the model's
    own retry gate (retry_allowed) is for explicit failure signals only, so the policy path marks the row 'failed' with the
    policy as its evidence, never with a provider observation."""
    if decision["chosen_action"] != "resend":
        # the two calls the regression names: any direct resend and the model's own idempotent retry must send nothing
        a = r.resend(key)
        b = r.idempotent_retry(key)
        return {"direct_resend": a["action"], "idempotent_retry": b["action"]}
    row = r.rows[key]
    row["submission"] = "failed"
    row["submission_evidence"] = {"kind": "elapsed_policy", "policy": decision["policy"], "authorization_basis": decision["authorization_basis"], "at": r.clock.now}
    row["resend_authorized_by"] = {"basis": decision["authorization_basis"], "policy": decision["policy"], "at": r.clock.now}   # kept on the row: the dispatch below overwrites submission_evidence with the new accept
    res = r.resend(key)
    return {"resend": res["action"]}


def run(setup, risk_accepting_policy, mislabel=False):
    clk = Clock()
    lag = {"M": 0, "U": 10 ** 6, "P": 10 ** 6, "N": 0}[setup]
    p = Provider(clk, index_latency=lag)
    r = Reconciler(p, clk, REFERENCE)
    p.send_behaviour = "reset_before_commit" if setup == "N" else "accept_then_timeout"
    r.submit("k", ["a@x"], "body")
    p.send_behaviour = "accepted"
    sends_before = p.send_calls
    r.verify("k")                                   # the model's own pass: 3 rounds 8 s apart + fallback query; never sends
    d = decide(r, "k", risk_accepting_policy, mislabel)
    ex = execute(r, "k", d)
    return {"setup": setup, "decision": d, "executed": ex, "messages_at_provider": len(p.msgs),
            "additional_send_calls": p.send_calls - sends_before, "row": r.rows["k"]["submission"],
            "row_evidence_kind": (r.rows["k"].get("submission_evidence") or {}).get("kind"),
            "resend_authorized_by": (r.rows["k"].get("resend_authorized_by") or {}).get("basis")}


EXPECTED = {   # (observed_fact, chosen_action, authorization_basis, messages_at_provider, additional_send_calls, row_evidence_kind)
    "M": ("matching_original_found", "hold", None, 1, 0, "sent_copy"),
    "U": ("unresolved", "hold", None, 1, 0, None),
    "P": ("unresolved", "resend", "elapsed_policy", 2, 1, "provider_accept"),
    "N": ("unresolved", "resend", "elapsed_policy", 1, 1, "provider_accept"),
}
POLICY_ON = {"M": True, "U": False, "P": True, "N": True}   # M has the policy ON too: a found original still suppresses the resend


def main(argv):
    results, problems = [], []
    for s in ("M", "U", "P", "N"):
        x = run(s, POLICY_ON[s])
        d = x["decision"]
        got = (d["observed_fact"], d["chosen_action"], d["authorization_basis"], x["messages_at_provider"], x["additional_send_calls"], x["row_evidence_kind"])
        x["ok"] = got == EXPECTED[s] and x["resend_authorized_by"] == (d["authorization_basis"] if d["chosen_action"] == "resend" else None)
        if not x["ok"]:
            problems.append(s)
        if d["authorization_basis"] == "provider_evidence":      # the label forgeloop says must not exist in this model
            problems.append(s + ":provider_evidence_label")
        results.append(x)
    ctl = run("P", True, mislabel=True)                          # the violation control: the same P cell with the forbidden label
    ctl_violates = ctl["decision"]["authorization_basis"] == "provider_evidence"
    if not ctl_violates:
        problems.append("control did not produce the forbidden label")
    if argv[:1] == ["--json"]:
        print(json.dumps({"cells": results, "control": ctl}, indent=1, default=str))
    else:
        print("cell  policy  observed_fact            action  basis            messages  extra_sends  row_evidence")
        for x in results:
            d = x["decision"]
            print("%-5s %-7s %-24s %-7s %-16s %-9d %-12d %s%s" % (x["setup"], "on" if POLICY_ON[x["setup"]] else "off", d["observed_fact"],
                  d["chosen_action"], d["authorization_basis"], x["messages_at_provider"], x["additional_send_calls"],
                  x["row_evidence_kind"], "" if x["ok"] else "   <-- differs from the stated table"))
        print("control (decision labels P's resend provider_evidence): forbidden label produced = %s (the same label test that passes the four cells above would fail this one)" % ctl_violates)
        print("%d cells, %d as stated, %d problem(s)" % (len(results), sum(1 for x in results if x["ok"]), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
