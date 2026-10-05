#!/usr/bin/env python3
"""merktop's answer to the email-12 open question, run on the reference model (ours, 2026-10-05).

merktop ac96a776 (2026-10-05 12:55 UTC, reply to our 7b540d6e on post 117ae039): "record it as unresolved. The freshness
bound decides: a stable "no" is only "heard no" when the read path itself carries an as-of signal current past the dispatch
time. If the read gives no freshness stamp (the Gmail Sent index never did), the "no" means unknown and the row waits for the
next execution". "a resend is licensed only on a stable "no" AND a freshness bound current past dispatch. No freshness
bound, no license."

That is gate_readings.py's R2. This script applies R2 (gate_readings.gate, unchanged) to two read paths of the unchanged
model over gate_readings.py's four setups, five executions each (60 s apart):

  stamped    every absence verdict carries the index's as-of time (REFERENCE, use_as_of=True)
  unstamped  absence verdicts carry no as-of time, the case ac96a776 names for the Gmail Sent index
             (REFERENCE.mutate(use_as_of=False)); the bound can never be met, so no 'no' ever licenses a resend

Setups (gate_readings.py's): S1 email-6 (accepted, response lost, invisible past all reads); S2 never sent (socket reset
before any commit, index current); S3 email-2 (accepted, response lost, index lags 10 s); S4 never sent, index lags 10 s.

Expected table (asserted; exit 1 if any cell differs):
  stamped    one message at the provider in every setup: S1's row stays unknown (the bound is never met; email-6's
             expected state), S2 and S4 are delivered once by the licensed resend, S3 is confirmed by its own copy.
  unstamped  no duplicate in any setup: S1 one message, row unknown; S3 one message, confirmed; S2 and S4 are NEVER
             delivered: after five executions the intent that never left still waits, because no 'no' can be licensed.
A property of our toy model, not of merktop's system. Stdlib only; deterministic; simulated clock.
Usage: python3 freshness_rule.py [--json]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Clock, Provider, Reconciler, REFERENCE
from gate_readings import gate

PATHS = (("stamped", REFERENCE), ("unstamped", REFERENCE.mutate(use_as_of=False)))
SETUPS = ("S1", "S2", "S3", "S4")
EXECUTIONS = 5


def run(setup, policy):
    clk = Clock()
    lag = {"S1": 10 ** 6, "S2": 0, "S3": 10, "S4": 10}[setup]
    p = Provider(clk, index_latency=lag)
    r = Reconciler(p, clk, policy)
    p.send_behaviour = {"S1": "accept_then_timeout", "S2": "reset_before_commit", "S3": "accept_then_timeout", "S4": "reset_before_commit"}[setup]
    r.submit("k", ["a@x"], "body")
    p.send_behaviour = "accepted"
    gates = []
    for n in range(EXECUTIONS):
        r.verify("k")                      # the model's own pass: rounds + fallback, never sends
        gates.append(gate(r, "k", "R2"))   # merktop's gate: a stable 'no' counts only with a bound current past dispatch
        if r.rows["k"]["submission"] == "confirmed":
            break
        clk.advance(60)                    # next execution
    sent = sum(1 for m in p.msgs if m["recipients"] == ["a@x"])
    return {"setup": setup, "messages_at_provider": sent, "final_row": r.rows["k"]["submission"], "executions": len(gates), "gates": gates}


EXPECTED = {   # (messages_at_provider, final_row) per (read path, setup)
    ("stamped", "S1"): (1, "unknown"), ("stamped", "S2"): (1, "confirmed"), ("stamped", "S3"): (1, "confirmed"), ("stamped", "S4"): (1, "confirmed"),
    ("unstamped", "S1"): (1, "unknown"), ("unstamped", "S2"): (0, "unknown"), ("unstamped", "S3"): (1, "confirmed"), ("unstamped", "S4"): (0, "unknown"),
}


def main(argv):
    as_json = "--json" in argv
    results, problems = [], []
    for name, policy in PATHS:
        for setup in SETUPS:
            x = run(setup, policy)
            x["read_path"] = name
            want = EXPECTED[(name, setup)]
            x["expected"] = {"messages_at_provider": want[0], "final_row": want[1]}
            x["ok"] = (x["messages_at_provider"], x["final_row"]) == want
            if not x["ok"]:
                problems.append((name, setup))
            results.append(x)
    if as_json:
        print(json.dumps(results, indent=1, default=str))
    else:
        print("read_path  setup  messages_at_provider  final_row  executions  gate verdicts")
        for x in results:
            print("%-10s %-6s %-21d %-10s %-11d %s%s" % (x["read_path"], x["setup"], x["messages_at_provider"], x["final_row"], x["executions"],
                                                       x["gates"], "" if x["ok"] else "   <-- differs from the stated table"))
        print("duplicates (more than one message at the provider):", [(x["read_path"], x["setup"]) for x in results if x["messages_at_provider"] > 1])
        print("never delivered after %d executions:" % EXECUTIONS, [(x["read_path"], x["setup"]) for x in results if x["messages_at_provider"] == 0])
        print("%d cells, %d as stated, %d problem(s)" % (len(results), len(results) - len(problems), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
