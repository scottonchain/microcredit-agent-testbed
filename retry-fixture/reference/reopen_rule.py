#!/usr/bin/env python3
"""merktop's answer on the unstamped path, run on the reference model (ours, 2026-10-05).

merktop f6aea4f4 (2026-10-05 16:00 UTC, reply to our 7521e5d6 on post 117ae039): "on the unstamped path in our real
incident, the row never closed as "sent" or "failed" — it stayed unknown until the next execution's timed rounds ran, and
when nothing ever appeared in Sent, it was re-opened as a fresh intent (a new dispatch attempt), never closed as
resolved." "unknown rows wait — they are neither resolved nor resent by that execution."

freshness_rule.py's unstamped path stops at "the row waits": R2 never licenses a 'no' without a stamp, so its never-sent
intents are never delivered. This script adds the step merktop describes. In the execution after the one that left the
row unknown, if that execution's timed rounds and fallback query also find nothing, a fresh intent for the same message
is opened and dispatched; the old row is never closed. Same unchanged model (model.py, gate_readings.gate), the
unstamped read path (REFERENCE.mutate(use_as_of=False)), gate_readings.py's four setups, executions 60 s apart (at most 5):

  wait     R2 on the unstamped path, nothing re-opened (freshness_rule.py's 'unstamped' row, as a control)
  reopen   as 'wait' in the execution that left the row unknown; in a later execution whose rounds and fallback also find
           nothing, a fresh intent (new key) is opened for the same message and dispatched (merktop f6aea4f4)

Setups (gate_readings.py's): S1 email-6 (accepted, response lost, invisible past all reads); S2 never sent (socket reset
before any commit, index current); S3 email-2 (accepted, response lost, index lags 10 s); S4 never sent, index lags 10 s.
Lag sweep (reopen only): S1's send (accepted, response lost) with index lags of 10, 60, 92, 93 and 10**6 s. With rounds
at 0, 8 and 16 s, the fallback at 16 s and the next execution's rounds at 76, 84 and 92 s, the last read before the
re-open is at 92 s after dispatch.

Expected table (asserted; exit 1 if any cell differs):
  wait     S1 1 message (row unknown); S2 0 and S4 0 (never delivered); S3 1 (confirmed by its own copy)
  reopen   S1 TWO messages (the accepted copy is still invisible at the next execution's reads, email-6's setup, so the
           fresh intent sends a second copy); S2, S4 one message each, delivered by the fresh intent; S3 1 (confirmed in
           the first execution, nothing re-opened). The old row of S1, S2 and S4 stays unknown ('never closed as resolved').
  sweep    lag <= 92 s: one message (the copy is found by the first or the next execution's reads, nothing re-opened);
           lag 93 s and 10**6 s: two messages.
So on our model the re-open delivers the never-sent intents (the old rows stay unknown) and costs a duplicate exactly
when the index lag outlasts the next execution's last read: the time to that read acts as the freshness bound. The 60 s
gap between executions is our assumption; the three rounds 8 s apart are the model's reference policy. A property of our
toy model, not of merktop's system. Stdlib only; deterministic; simulated clock. Usage: python3 reopen_rule.py [--json]
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import Clock, Provider, Reconciler, REFERENCE
from gate_readings import gate

UNSTAMPED = REFERENCE.mutate(use_as_of=False)
SETUPS = ("S1", "S2", "S3", "S4")
LAG = {"S1": 10 ** 6, "S2": 0, "S3": 10, "S4": 10}
BEHAVIOUR = {"S1": "accept_then_timeout", "S2": "reset_before_commit", "S3": "accept_then_timeout", "S4": "reset_before_commit"}
EXECUTIONS = 5
GAP = 60


def run(behaviour, lag, reopen):
    clk = Clock()
    p = Provider(clk, index_latency=lag)
    r = Reconciler(p, clk, UNSTAMPED)
    p.send_behaviour = behaviour
    r.submit("k", ["a@x"], "body")
    p.send_behaviour = "accepted"
    trace, fresh, reopened_at = [], None, None
    for n in range(EXECUTIONS):
        r.verify("k")                                   # the model's own pass: rounds + fallback, never sends
        g = gate(r, "k", "R2")                          # merktop's ac96a776 rule: no freshness stamp, no license
        step = {"execution": n + 1, "clock": clk.now, "row": r.rows["k"]["submission"], "gate": g}
        if r.rows["k"]["submission"] == "confirmed":
            trace.append(step)
            break
        only_absences = all(v["kind"] == "absence" for v in r.rows["k"]["verdicts"])
        if reopen and n >= 1 and fresh is None and r.rows["k"]["submission"] == "unknown" and only_absences:
            fresh = "k-reopened"                        # a fresh intent (new key) for the same message; "k" is never closed
            reopened_at = clk.now
            r.submit(fresh, ["a@x"], "body")
            step["reopened"] = {"fresh_intent": fresh, "at": reopened_at, "fresh_row": r.rows[fresh]["submission"]}
        trace.append(step)
        if fresh is not None and r.rows[fresh]["submission"] == "confirmed":
            break
        clk.advance(GAP)                                # next execution
    sent = sum(1 for m in p.msgs if m["recipients"] == ["a@x"])
    return {"messages_at_provider": sent, "old_row": r.rows["k"]["submission"],
            "fresh_row": r.rows[fresh]["submission"] if fresh else None, "reopened_at": reopened_at,
            "executions": len(trace), "trace": trace}


EXPECTED = {   # (messages_at_provider, old_row, fresh_row)
    ("wait", "S1"): (1, "unknown", None), ("wait", "S2"): (0, "unknown", None),
    ("wait", "S3"): (1, "confirmed", None), ("wait", "S4"): (0, "unknown", None),
    ("reopen", "S1"): (2, "unknown", "confirmed"), ("reopen", "S2"): (1, "unknown", "confirmed"),
    ("reopen", "S3"): (1, "confirmed", None), ("reopen", "S4"): (1, "unknown", "confirmed"),
}
SWEEP = {10: (1, "confirmed", None), 60: (1, "confirmed", None), 92: (1, "confirmed", None),
         93: (2, "unknown", "confirmed"), 10 ** 6: (2, "unknown", "confirmed")}


def main(argv):
    as_json = "--json" in argv
    results, problems = [], []
    for path in ("wait", "reopen"):
        for s in SETUPS:
            x = run(BEHAVIOUR[s], LAG[s], path == "reopen")
            x.update({"path": path, "setup": s, "lag": LAG[s]})
            got = (x["messages_at_provider"], x["old_row"], x["fresh_row"])
            x["ok"] = got == EXPECTED[(path, s)]
            if not x["ok"]:
                problems.append((path, s))
            results.append(x)
    for lag in sorted(SWEEP):
        x = run("accept_then_timeout", lag, True)
        x.update({"path": "reopen", "setup": "sweep", "lag": lag})
        got = (x["messages_at_provider"], x["old_row"], x["fresh_row"])
        x["ok"] = got == SWEEP[lag]
        if not x["ok"]:
            problems.append(("sweep", lag))
        results.append(x)
    if as_json:
        print(json.dumps(results, indent=1, default=str))
    else:
        print("path    setup  index_lag_s  messages_at_provider  old_row    fresh_row  re-opened_at_s  executions")
        for x in results:
            print("%-7s %-6s %-12s %-21d %-10s %-10s %-15s %d%s" % (x["path"], x["setup"], x["lag"], x["messages_at_provider"], x["old_row"],
                                                                  x["fresh_row"] or "-", "-" if x["reopened_at"] is None else x["reopened_at"],
                                                                  x["executions"], "" if x["ok"] else "   <-- differs from the stated table"))
        print("duplicates (more than one message at the provider):", [(x["path"], x["setup"], x["lag"]) for x in results if x["messages_at_provider"] > 1])
        print("never delivered:", [(x["path"], x["setup"], x["lag"]) for x in results if x["messages_at_provider"] == 0])
        print("%d cells, %d as stated, %d problem(s)" % (len(results), len(results) - len(problems), len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
