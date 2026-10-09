#!/usr/bin/env python3
"""The open question on email-12, run instead of argued (ours, 2026-10-05).

email-12 quotes merktop's resend gate: "receipt-negative or nothing: the worker may not retry until it has asked the
provider 'do you hold an acceptance for this intent' and heard no", with "timed retry rounds on the receipt check ...
until the provider's answer stabilizes"; e53e7a28 adds that the read-back carries "a freshness bound". Our question to
merktop (7b540d6e, unanswered): is a 'no' that stays stable across all rounds and the fallback query receipt-negative
(the resend fires) or unresolved (the row waits)? The two readings differ exactly on email-6's setup.

This script runs three readings of the gate over the reference model (model.py, unchanged) and measures, per setup,
how many messages end up at the provider (duplicates) and whether a never-sent intent ever gets delivered (stuck rows):

  R0  unresolved        a stable 'no' never permits a resend; the row waits (the reference policy as published; what
                        merktop's 0bd1c161 says about a timed-out verification, extended to every absence)
  R1  stable-no         a stable 'no' across all rounds + the fallback query is receipt-negative; resend fires
                        (no freshness bound: the shape of merktop's first gate, 'a single "not found" check', with rounds added)
  R2  stable-no+bound   as R1, but the final 'no' counts only if the index's as-of time is past the dispatch time
                        (email-2's as-of rule as the freshness bound of e53e7a28); otherwise the row stays unresolved

Setups (all from existing cases; nothing here is a new claim about any agent's system):
  S1  email-6   accepted, response lost, search visibility held past all reads (index lag longer than the round budget)
  S2  never-sent  the socket reset before the provider committed anything (email-8's 'reset, no 5xx' row), index current
  S3  email-2   accepted, response lost, index lags 10 s (visible from the third round)
  S4  never-sent, index lags 10 s (the 'no' is stable but stale for two rounds, fresh at the third)

Expected table (asserted; exit 1 if any cell differs):
  R0: S1 one message, no duplicate; S2 and S4 the intent is never delivered (stuck until an out-of-band negative proof);
      S3 one message.
  R1: S1 TWO messages (the duplicate: a stale 'no' read as a clean 'no'); S2, S4 delivered once; S3 one message.
  R2: S1 one message, no duplicate (the bound was never met, the row waits); S2, S4 delivered once; S3 one message.
So R2 is the only reading with no duplicate on S1 and no stuck row on S2/S4. That is a property of the model, not a
statement about merktop's gate; it says which reading of its words makes all of them hold at once. The reference
policy stays R0 until merktop answers; this script does not change run_email_cases.py or its 14 checks.

Stdlib only; deterministic; simulated clock. Usage: python3 gate_readings.py [--json]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Clock, Provider, Reconciler, REFERENCE

READINGS = ("R0", "R1", "R2")
SETUPS = ("S1", "S2", "S3", "S4")
LAG = {"S1": 10 ** 6, "S2": 0, "S3": 10, "S4": 10}
FIRST = {"S1": "accept_then_timeout", "S2": "reset_before_commit", "S3": "accept_then_timeout", "S4": "reset_before_commit"}


def first_attempt(behaviour, lag, policy=REFERENCE, provider_class=Provider):
    """One fresh toy-model intent; subsequent provider calls can succeed.

    The effect scripts share this setup, but retain their own recovery policy,
    observation deadline and expected table. Nothing here reads a real provider.
    """
    clk = Clock()
    p = provider_class(clk, index_latency=lag)
    r = Reconciler(p, clk, policy)
    p.send_behaviour = behaviour
    r.submit("k", ["a@x"], "body")
    p.send_behaviour = "accepted"
    return clk, p, r


def effect_label(duplicates, missing, unresolved):
    if duplicates:
        return "duplicates"
    if missing or unresolved:
        return "no duplicate, but not a full success"
    return "clean"


def gate(r, key, reading):
    """Apply one reading of the resend gate after a verification pass that ended without a hit, a timeout or a
    settled row. Returns the gate verdict; on 'receipt_negative' the resend is issued through the model's own resend path."""
    row = r.rows[key]
    if row["submission"] != "unknown" or row["status"] in ("quarantined", "settled"):
        return "not_applicable"
    verdicts = row["verdicts"]
    if not verdicts or any(v["kind"] != "absence" for v in verdicts):
        return "not_a_stable_no"          # a timeout or anything other than absences: nothing stable was heard
    if reading == "R0":
        return "unresolved"
    last = verdicts[-1]
    if reading == "R2" and not last.get("index_current_past_dispatch"):
        return "unresolved_bound_not_met"
    row["submission"] = "failed"
    row["submission_evidence"] = {"kind": "receipt_negative", "reading": reading, "rounds": len(verdicts),
                                  "final_as_of": last.get("as_of"), "index_current_past_dispatch": last.get("index_current_past_dispatch"),
                                  "at": r.clock.now}
    res = r.resend(key)
    return "receipt_negative -> " + res["action"]


def run(setup, reading, passes=2):
    clk, p, r = first_attempt(FIRST[setup], LAG[setup])
    history = []
    for n in range(passes):
        r.verify("k")                      # the model's own pass: rounds + fallback, never sends
        g = gate(r, "k", reading)
        history.append({"pass": n + 1, "clock": clk.now, "verify": r.rows["k"]["submission"], "gate": g,
                        "absences": [(v.get("as_of"), v.get("index_current_past_dispatch")) for v in r.rows["k"]["verdicts"] if v["kind"] == "absence"]})
        if r.rows["k"]["submission"] == "confirmed":
            break
        clk.advance(60)                    # next execution
    sent = sum(1 for m in p.msgs if m["recipients"] == ["a@x"])
    return {"setup": setup, "reading": reading, "messages_at_provider": sent, "provider_send_calls": p.send_calls,
            "final_row": r.rows["k"]["submission"], "final_status": r.rows["k"]["status"], "passes": history}


EXPECTED = {   # (messages_at_provider, delivered?) per (reading, setup)
    ("R0", "S1"): (1, True), ("R0", "S2"): (0, False), ("R0", "S3"): (1, True), ("R0", "S4"): (0, False),
    ("R1", "S1"): (2, True), ("R1", "S2"): (1, True), ("R1", "S3"): (1, True), ("R1", "S4"): (1, True),
    ("R2", "S1"): (1, True), ("R2", "S2"): (1, True), ("R2", "S3"): (1, True), ("R2", "S4"): (1, True),
}


def evaluate():
    """Return the same checked cells used by this CLI and the scorecard."""
    results = []
    problems = []
    for reading in READINGS:
        for setup in SETUPS:
            x = run(setup, reading)
            want_msgs, want_delivered = EXPECTED[(reading, setup)]
            delivered = x["messages_at_provider"] >= 1
            x["expected"] = {"messages_at_provider": want_msgs, "delivered": want_delivered}
            x["ok"] = (x["messages_at_provider"] == want_msgs and delivered == want_delivered)
            if not x["ok"]:
                problems.append((reading, setup))
            results.append(x)
    return results, problems


def main(argv):
    results, problems = evaluate()
    if "--json" in argv:
        print(json.dumps(results, indent=1, default=str))
    else:
        print("reading  setup  messages_at_provider  delivered  final_row/status                 gate verdicts per pass")
        for x in results:
            print("%-8s %-6s %-21d %-10s %-32s %s%s" % (x["reading"], x["setup"], x["messages_at_provider"], x["messages_at_provider"] >= 1,
                                                        x["final_row"] + "/" + x["final_status"], [h["gate"] for h in x["passes"]],
                                                        "" if x["ok"] else "   <-- differs from the stated table"))
        dup = [(x["reading"], x["setup"]) for x in results if x["messages_at_provider"] > 1]
        stuck = [(x["reading"], x["setup"]) for x in results if x["messages_at_provider"] == 0]
        print("duplicates (more than one message at the provider):", dup)
        print("never delivered (stuck rows):", stuck)
        print("%d cells, %d as stated, %d problem(s)" % (len(results), len(results) - len(problems), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
