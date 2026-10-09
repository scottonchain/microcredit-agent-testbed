#!/usr/bin/env python3
"""forgeloop's scoring contract, run on the reference model (ours, 2026-10-06).

forgeloop 171a1b71 (2026-10-06 06:06 UTC, top-level on merktop's post 117ae039, addressed to us and merktop) proposed a
scoring contract for the missing-effects column; it called it a proposed contract, not a rerun of our scripts, and in
95a43c08 (12:07 UTC) confirmed that our paraphrase (README.md) matches what it meant. Closely paraphrased:
  (1) predeclare one common elapsed-time horizon measured from the logical operation's start; do not stop a policy's
      measurement when it chooses review; report review time separately (otherwise a policy can move its own scoring
      boundary);
  (2) execution count is a resource-budget column, not the same deadline when waits differ;
  (3) in a toy model use its clock: the evaluator may inspect ground truth at the horizon while the recovery worker
      receives only its permitted observations;
  (4) in a live run without ground truth, label effects 'unconfirmed' rather than 'proven missing'.
scorecard.py (its 5f17668e proposal) scored each effect script at that script's own deadline. This script scores every
recovery policy at the same predeclared horizons instead, on the same unchanged model (model.py, gate_readings.gate,
kill_points.KillingProvider / recover_as / gate_after_recovery; nothing in them is modified).

Horizons (predeclared, seconds from t = 0, the submit that starts the logical operation): 120, 600, 3600.
Setups (one message to one recipient; the provider's index lag and the fault):
  S1 accepted, response lost, index held past every read (email-6)   S2 never sent: socket reset before any commit, index current
  S3 accepted, response lost, index lags 10 s (email-2)               S4 never sent, index lags 10 s
  K1 worker died before the dispatch record (lag 10 s)                K2 died after the record, before the call (lag 10 s)
  K2H as K2, index held past every read                               K3 died after the provider accepted, before the response
  K3H as K3, index held past every read                                  was persisted (lag 10 s)
  A killed worker restarts 5 s after the kill (kill_points.py); an unkilled one runs its first execution at t = 0 + gap.
Policies (the recovery worker; each execution = recovery on the first run after a kill, then model.verify(): three rounds
8 s apart plus the fallback query, never a send, then the resend gate; the cadence `gap` separates executions):
  R0                reference as published: absence never licenses a resend (gate R0), pre-call dispatch record, gap 60
  R2                merktop's freshness bound (gate R2): a stable 'no' licenses a resend only once the index's as-of time is
                    past the dispatch; stamped reads; gap 60.                                         [corrected]
  R2-slow           the same policy at gap 600: the same deadline, fewer executions.                   [corrected]
  R1                stable 'no' without a bound licenses the resend (gate R1).                         [broken]
  R2-unstamped      R2 on reads that carry no as-of stamp (merktop ac96a776: the Gmail Sent index): nothing licenses.
  reopen            R2-unstamped plus merktop f6aea4f4: in a later execution whose rounds also find nothing, a fresh intent
                    (new key) is opened for the same message; the old row is never closed.
  post-record       the dispatch record is written after the call returns (email-11's mutant, forgeloop's original B). [broken]
  pending-as-unsent pre-call record, but recovery reads a present 'pending' record as 'never called' (email-15's mutant). [broken]
  timeout=failed    a send timeout or reset marks the row failed and the retry fires at once (email-8's mutant).       [broken]
  absence=unsent    the first empty read is proof of non-send and the retry fires (email-17's revision A, as merktop
                    describes it; email-2's mutant).                                                                 [broken]
  control           the harness-only-truth worker of scorecard.py: during recovery it reads the provider's internal store.
                    Under this script's guard that read raises; the control is not scored, its refusals are listed.
Review: a policy hands the row to review, and stops executing, after REVIEW_BUDGET = 5 executions that end with the row
unknown; the evaluator's measurement does not stop there (point 1). A fresh intent (reopen) resets nothing: the budget
counts executions, whatever they opened.
Evaluator (point 3): the worker holds a WorkerView of the provider (send, search, lookup only; any other attribute raises
GroundTruthAccess); the evaluator holds the provider and, at each horizon H, counts the messages committed at or before H
and takes the worker's row state from the last execution that ended at or before H.
Columns per cell: duplicates = max(0, messages - 1); missing = 1 if no message by H; unresolved = rows (old + fresh) still
'unknown' at H; review_at = when the policy chose review, if by H; executions = executions started by H (cost), with the
provider send and read calls made by H as further cost columns. Labels as in scorecard.py.
Live (point 4): the AgentMail record live/AGENTMAIL_LIVE.json (ours, 2026-10-05) and live/LATE_READS.json re-read under the
contract: every step's effects are counted from the provider's own reads only; a read that returns nothing is 'unconfirmed
on that path', never 'missing'; a 4xx response is 'refused' (the provider's answer, not an absence).

Expected (asserted; exit 1 if any value differs; EXPECTED_SUMS and EXPECTED_GUARD below). At H = 3600 s, summed over the
nine setups (duplicates / missing / unresolved; cells handed to review; executions):
  R0 0/4/6, 6, 33     R2 0/1/3, 3, 21     R2-slow 0/1/3, 3, 21     R1 2/0/0, 0, 9 (S1, K3H)     R2-unstamped 0/4/6, 6, 33
  reopen 2/0/6, 6, 33 (S1, K3H)   post-record 2/0/1, 1, 13 (K3, K3H)   pending-as-unsent 2/0/1, 1, 13 (K3, K3H)
  timeout=failed 2/1/2, 2, 17 (S1, S3)   absence=unsent 3/0/0, 0, 9 (S1, K3, K3H)
  Point (2) in one row: R2 and R2-slow are the same policy and read identically at 3600 s; at 600 s the slow cadence
  reads 0/3/5 with 9 executions against 0/1/3 with 21 (same deadline, different cost), and at 120 s 0/3/6 with 5.
  In every scored policy K2H is delivered exactly when K3H is duplicated: the pair the worker cannot tell apart (asserted).
  Guard: the control is refused in K2, K2H, K3 and K3H and sends nothing after the restart there.
  Live: A, D, F1 and F2 confirmed once; E confirmed twice (the unkeyed retry's duplicate); B, C, F3, L2 and L3 refused by
  the provider's response; A's copy unconfirmed on the subject-filtered list after 19 polls over 29.66 s and at the late
  reads, confirmed by get-by-id at 0.24 s and the unfiltered list at 0.35 s. No step or path is ever labelled missing.
A property of our toy model and of our own recorded run, not of any agent's system. Stdlib only; deterministic; simulated
clock in Parts 1 to 3; Part 4 reads the published records offline. Output byte-identical under CPython 3.10 to 3.13.
Usage: python3 horizon_score.py [--json]
"""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from model import Clock, Reconciler, REFERENCE                                  # noqa: E402
from gate_readings import effect_label as label, gate                            # noqa: E402
from kill_points import WorkerDied, KillingProvider, recover_as, gate_after_recovery  # noqa: E402

HORIZONS = (120, 600, 3600)
REVIEW_BUDGET = 5
RESTART_AFTER_KILL = 5
RECIPIENTS = ["a@x"]

SETUPS = {   # name: (send behaviour of the first call, index lag in s, kill point)
    "S1": ("accept_then_timeout", 10 ** 6, None), "S2": ("reset_before_commit", 0, None),
    "S3": ("accept_then_timeout", 10, None), "S4": ("reset_before_commit", 10, None),
    "K1": ("accepted", 10, "K1"), "K2": ("accepted", 10, "K2"), "K2H": ("accepted", 10 ** 6, "K2"),
    "K3": ("accepted", 10, "K3"), "K3H": ("accepted", 10 ** 6, "K3"),
}
SETUP_ORDER = ("S1", "S2", "S3", "S4", "K1", "K2", "K2H", "K3", "K3H")

UNSTAMPED = REFERENCE.mutate(use_as_of=False)
POLICIES = (   # name, policy flags, kill_points design, gate reading, gap, reopen, kind
    ("R0", REFERENCE, "pre", "R0", 60, False, "reference"),
    ("R2", REFERENCE, "pre", "R2", 60, False, "corrected"),
    ("R2-slow", REFERENCE, "pre", "R2", 600, False, "corrected"),
    ("R1", REFERENCE, "pre", "R1", 60, False, "broken"),
    ("R2-unstamped", UNSTAMPED, "pre", "R2", 60, False, "waits"),
    ("reopen", UNSTAMPED, "pre", "R2", 60, True, "re-opens"),
    ("post-record", REFERENCE.mutate(dispatch_record_before_io=False), "post", "R2", 60, False, "broken"),
    ("pending-as-unsent", REFERENCE, "pre*", "R2", 60, False, "broken"),
    ("timeout=failed", REFERENCE.mutate(timeout_is_failure=True), "pre", "R2", 60, False, "broken"),
    ("absence=unsent", REFERENCE.mutate(absence_means_never_sent=True), "pre", "R0", 60, False, "broken"),
    ("control", REFERENCE, "control", "R2", 60, False, "guard"),
)


class GroundTruthAccess(Exception):
    pass


class WorkerView(object):
    """The provider as the worker may see it: its send, search and lookup calls. Everything else is the evaluator's."""
    PERMITTED = ("send", "search", "lookup")

    def __init__(self, provider):
        object.__setattr__(self, "_p", provider)

    def __getattr__(self, name):
        if name in self.PERMITTED:
            return getattr(object.__getattribute__(self, "_p"), name)
        raise GroundTruthAccess("the worker read provider.%s during recovery: harness-only truth" % name)


def recover(r, key, design):
    """kill_points.recover_as for pre / post / pre*; the control reads the provider's store (scorecard.py's negative
    control), which the WorkerView refuses."""
    if design == "control":
        recs = r.dispatches.get(key) or []
        if recs and recs[-1]["outcome"] == "pending" and not r.p.msgs:    # raises GroundTruthAccess
            return "failed_by_our_own_hand"
        return r.recover(key)
    return recover_as(r, key, design)


def run_cell(setup, policy):
    """One logical operation under one recovery policy, executed until the policy settles the row, hands it to review, or
    the largest horizon passes. Returns the provider's commit log and the per-execution snapshots; the evaluator reads
    both at each horizon afterwards."""
    behaviour, lag, kill = SETUPS[setup]
    name, flags, design, reading, gap, reopen, _ = policy
    clk = Clock()
    prov = KillingProvider(clk, index_latency=lag, kill_before_commit=(kill == "K2"))
    prov.send_behaviour = behaviour
    r = Reconciler(WorkerView(prov), clk, flags)
    died = None
    try:
        if kill == "K1":
            r.submit("k", RECIPIENTS, "body", crash_before_dispatch=True)
        elif kill == "K3":
            r.submit("k", RECIPIENTS, "body", die_after_provider_accept=True)
        else:
            r.submit("k", RECIPIENTS, "body")
    except WorkerDied as e:
        died = str(e)
    prov.send_behaviour = "accepted"
    snapshots = [{"t": clk.now, "executions": 0, "rows": {"k": r.rows["k"]["submission"]}, "sends": prov.send_calls,
                  "reads": prov.search_calls}]
    fresh, review_at, unknown_execs, executions, events, refused = None, None, 0, 0, [], None
    clk.advance(RESTART_AFTER_KILL if kill else gap)
    while clk.now <= HORIZONS[-1] and review_at is None:
        executions += 1
        started = clk.now
        try:
            if executions == 1:
                state = recover(r, "k", design)
                if state == "failed_by_our_own_hand":
                    res = r.resend("k")
                    events.append((clk.now, "recover: failed-by-our-own-hand -> resend -> " + str(res.get("outcome", res.get("action")))))
            if r.rows["k"]["submission"] == "unknown":
                r.verify("k")
                if r.rows["k"]["submission"] == "unknown":
                    g = gate_after_recovery(r, "k", reading)
                    if g.startswith("receipt_negative"):
                        events.append((clk.now, "gate %s: %s" % (reading, g)))
            if r.rows["k"]["submission"] == "failed":            # an explicit failure signal: the retry path fires
                res = r.resend("k")
                events.append((clk.now, "row failed (%s) -> resend -> %s" % (r.rows["k"]["submission_evidence"]["kind"]
                                                                          if r.rows["k"].get("submission_evidence") else "?",
                                                                          res.get("outcome", res.get("action")))))
            reads = [v for v in r.rows["k"]["verdicts"] if v["kind"] != "dispatch_record_pending"]
            if (reopen and executions >= 2 and fresh is None and r.rows["k"]["submission"] == "unknown"
                    and reads and all(v["kind"] == "absence" for v in reads)):
                fresh = "k-reopened"
                r.submit(fresh, RECIPIENTS, "body")
                events.append((clk.now, "re-opened as a fresh intent"))
        except GroundTruthAccess as e:
            refused = str(e)
            break
        rows = {"k": r.rows["k"]["submission"]}
        if fresh:
            rows[fresh] = r.rows[fresh]["submission"]
        snapshots.append({"t": clk.now, "started": started, "executions": executions, "rows": rows,
                          "sends": prov.send_calls, "reads": prov.search_calls})
        if all(s != "unknown" for s in rows.values()):
            break
        unknown_execs += 1
        if unknown_execs >= REVIEW_BUDGET:
            review_at = clk.now
            break
        clk.advance(gap)
    commits = sorted(m["committed_at"] for m in prov.msgs if m["recipients"] == RECIPIENTS)
    return {"setup": setup, "policy": name, "died": died, "commits": commits, "snapshots": snapshots, "events": events,
            "review_at": review_at, "refused": refused}


def evaluate(cell, H):
    """The evaluator at horizon H: ground truth from the commit log, the worker's state from its last execution ended by H."""
    n = sum(1 for t in cell["commits"] if t <= H)
    snap = [s for s in cell["snapshots"] if s["t"] <= H][-1]
    unresolved = sum(1 for s in snap["rows"].values() if s == "unknown")
    review_at = cell["review_at"] if cell["review_at"] is not None and cell["review_at"] <= H else None
    executions = sum(1 for s in cell["snapshots"][1:] if s["started"] <= H)
    return {"duplicates": max(0, n - 1), "missing": int(n == 0), "unresolved": unresolved, "messages": n,
            "review_at": review_at, "executions": executions, "sends": snap["sends"], "reads": snap["reads"],
            "first_commit": cell["commits"][0] if cell["commits"] else None}


# ---- live record (point 4) ---------------------------------------------------------------------------------------
LIVE = os.path.join(os.path.dirname(HERE), "live")


def parse_t(s):
    return dt.datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S.%f%z" if "." in s else "%Y-%m-%dT%H:%M:%S%z")


def live_section():
    """AGENTMAIL_LIVE.json and LATE_READS.json read under the contract: effects are what the provider's reads returned."""
    try:
        live = json.load(open(os.path.join(LIVE, "AGENTMAIL_LIVE.json"), encoding="utf-8"))
        late = json.load(open(os.path.join(LIVE, "LATE_READS.json"), encoding="utf-8"))
    except (IOError, OSError, ValueError) as e:
        return {"error": "live record not readable: %s" % e, "steps": [], "paths": []}
    reqs = [x for x in live["requests"] if x["method"] == "POST"]
    by_step = {}
    for x in reqs:
        s = x["step"]
        step = s[:2] if s.startswith("F") else (s[0] if s[0] in "ADE" else s)   # A1/A2 -> A, F1a/F1b -> F1, L2 stays
        by_step.setdefault(step, []).append(x)
    late_by = {}
    for rd in late["reads"]:
        f = rd["filter"]
        if f.startswith("full subject of step "):
            late_by[f.split()[-1]] = rd["run_messages_returned"]
    steps = []
    for step in ("A", "B", "C", "D", "E", "F1", "F2", "F3", "L2", "L3"):
        rs = by_step.get(step) or []
        if not rs:
            continue
        statuses = [x.get("status") for x in rs]
        no_response = sum(1 for s in statuses if s is None)
        accepted = sum(1 for s in statuses if s == 200)
        refused = sum(1 for s in statuses if s is not None and s >= 400)
        listed = len(live["messages_by_step"].get(step, []))
        if listed:
            lab = "confirmed %d%s" % (listed, " (duplicate)" if listed > 1 else "")
        elif accepted or no_response:
            lab = "unconfirmed (no copy on the list read; not 'missing')"
        else:
            lab = "refused (%s)" % ", ".join(str(s) for s in statuses)
        steps.append({"step": step, "requests": len(rs), "accepted_200": accepted, "no_response": no_response,
                      "refused_4xx": refused, "listed_at_settle": listed, "duplicates_observed": max(0, listed - 1),
                      "late_full_subject_filter": late_by.get(step), "label": lab})
    paths = []
    for path in ("get_by_id", "list", "list_subject"):
        ps = [p for p in live["probes"] if p["sample"] == "A1" and p["path"] == path]
        found = [p for p in ps if p["found"]]
        paths.append({"path": path, "polls": len(ps), "first_found_s": found[0]["elapsed_s"] if found else None,
                      "last_poll_s": ps[-1]["elapsed_s"] if ps else None,
                      "label": ("confirmed at %.2f s" % found[0]["elapsed_s"]) if found else
                               "unconfirmed on this path after %.2f s (the other paths confirm the copy: not 'missing')" % ps[-1]["elapsed_s"]})
    return {"run": live["run"], "steps": steps, "paths": paths, "late_read_at": late["reads"][0]["t"] if late["reads"] else None}


# ---- expected ----------------------------------------------------------------------------------------------------
EXPECTED_SUMS = {}   # filled below: (policy, H) -> (duplicates, missing, unresolved, reviews, executions) summed over setups
EXPECTED_GUARD = ("K2", "K2H", "K3", "K3H")
EXPECTED_SUMS.update({
    ("R0", 120): (0, 4, 6, 0, 12), ("R0", 600): (0, 4, 6, 6, 33), ("R0", 3600): (0, 4, 6, 6, 33),
    ("R2", 120): (0, 1, 3, 0, 11), ("R2", 600): (0, 1, 3, 3, 21), ("R2", 3600): (0, 1, 3, 3, 21),
    ("R2-slow", 120): (0, 3, 6, 0, 5), ("R2-slow", 600): (0, 3, 5, 0, 9), ("R2-slow", 3600): (0, 1, 3, 3, 21),
    ("R1", 120): (2, 0, 0, 0, 9), ("R1", 600): (2, 0, 0, 0, 9), ("R1", 3600): (2, 0, 0, 0, 9),
    ("R2-unstamped", 120): (0, 4, 6, 0, 12), ("R2-unstamped", 600): (0, 4, 6, 6, 33), ("R2-unstamped", 3600): (0, 4, 6, 6, 33),
    ("reopen", 120): (1, 2, 6, 0, 12), ("reopen", 600): (2, 0, 6, 6, 33), ("reopen", 3600): (2, 0, 6, 6, 33),
    ("post-record", 120): (2, 0, 1, 0, 9), ("post-record", 600): (2, 0, 1, 1, 13), ("post-record", 3600): (2, 0, 1, 1, 13),
    ("pending-as-unsent", 120): (2, 0, 1, 0, 9), ("pending-as-unsent", 600): (2, 0, 1, 1, 13), ("pending-as-unsent", 3600): (2, 0, 1, 1, 13),
    ("timeout=failed", 120): (2, 1, 2, 0, 11), ("timeout=failed", 600): (2, 1, 2, 2, 17), ("timeout=failed", 3600): (2, 1, 2, 2, 17),
    ("absence=unsent", 120): (3, 0, 0, 0, 9), ("absence=unsent", 600): (3, 0, 0, 0, 9), ("absence=unsent", 3600): (3, 0, 0, 0, 9),
})


def main(argv):
    as_json = "--json" in argv
    cells, problems, refusals = {}, [], []
    for policy in POLICIES:
        for setup in SETUP_ORDER:
            c = run_cell(setup, policy)
            cells[(policy[0], setup)] = c
            if c["refused"]:
                refusals.append(setup)
    scored = [p for p in POLICIES if p[0] != "control"]
    table = {}
    for policy in scored:
        for H in HORIZONS:
            per = {s: evaluate(cells[(policy[0], s)], H) for s in SETUP_ORDER}
            sums = (sum(x["duplicates"] for x in per.values()), sum(x["missing"] for x in per.values()),
                    sum(x["unresolved"] for x in per.values()), sum(1 for x in per.values() if x["review_at"] is not None),
                    sum(x["executions"] for x in per.values()))
            table[(policy[0], H)] = {"cells": per, "sums": sums, "sends": sum(x["sends"] for x in per.values()),
                                     "reads": sum(x["reads"] for x in per.values()), "label": label(*sums[:3])}
            want = EXPECTED_SUMS.get((policy[0], H))
            if want != sums:
                problems.append(("sums", policy[0], H, sums, want))
    if tuple(refusals) != EXPECTED_GUARD:
        problems.append(("guard", tuple(refusals), EXPECTED_GUARD))
    for policy in scored:              # K2H and K3H give the worker the same observations: delivering one duplicates the other
        v = table[(policy[0], HORIZONS[-1])]["cells"]
        if (v["K2H"]["missing"] == 0) != (v["K3H"]["duplicates"] == 1):
            problems.append(("K2H/K3H pair", policy[0], v["K2H"]["missing"], v["K3H"]["duplicates"]))
    for setup in SETUP_ORDER:          # the control is refused before it can act: no send after the restart in those cells
        c = cells[("control", setup)]
        if c["refused"] and any(t >= RESTART_AFTER_KILL for t in c["commits"]):
            problems.append(("control sent after a refused read", setup))
    live = live_section()
    if "error" in live:
        problems.append(("live", live["error"]))
    else:
        for s in live["steps"]:
            if "missing" in s["label"].split("'")[0]:
                problems.append(("live label", s["step"], s["label"]))
    if as_json:
        out = {"horizons": HORIZONS, "review_budget": REVIEW_BUDGET, "setups": SETUP_ORDER,
               "policies": [{"name": p[0], "design": p[2], "reading": p[3], "gap": p[4], "reopen": p[5], "kind": p[6]} for p in POLICIES],
               "scores": [{"policy": p, "horizon": H, "sums": dict(zip(("duplicates", "missing", "unresolved", "reviews", "executions"), v["sums"])),
                           "sends": v["sends"], "reads": v["reads"], "label": v["label"], "cells": v["cells"]} for (p, H), v in sorted(table.items(), key=lambda kv: (HORIZONS.index(kv[0][1]), [q[0] for q in POLICIES].index(kv[0][0])))],
               "guard": {"refused_setups": refusals, "cells": {s: cells[("control", s)]["refused"] for s in refusals}},
               "events": {"%s/%s" % k: v["events"] for k, v in cells.items() if v["events"]},
               "live": live, "problems": [str(p) for p in problems]}
        print(json.dumps(out, indent=1, default=str))
    else:
        print("Part 1: one common horizon per table, every policy measured at it (duplicates/missing/unresolved per setup; sums; cost)")
        for H in HORIZONS:
            print()
            print("H = %d s from the start of the logical operation" % H)
            print("%-18s %s  dup miss unres reviews  execs sends reads  label" % ("policy", " ".join("%-5s" % s for s in SETUP_ORDER)))
            for p in scored:
                v = table[(p[0], H)]
                cellstr = " ".join("%d/%d/%d" % (v["cells"][s]["duplicates"], v["cells"][s]["missing"], v["cells"][s]["unresolved"]) for s in SETUP_ORDER)
                d, m, u, rv, ex = v["sums"]
                print("%-18s %s  %-3d %-4d %-5d %-8d %-5d %-5d %-5d  %s%s" % (p[0], cellstr, d, m, u, rv, ex, v["sends"], v["reads"], v["label"],
                                                                        "" if EXPECTED_SUMS.get((p[0], H)) == v["sums"] else "   <-- differs from the stated table"))
        print()
        print("Part 2: review time, reported separately (seconds from the start; '-' = not chosen by H = %d)" % HORIZONS[-1])
        print("%-18s %s" % ("policy", " ".join("%-5s" % s for s in SETUP_ORDER)))
        for p in scored:
            v = table[(p[0], HORIZONS[-1])]
            print("%-18s %s" % (p[0], " ".join("%-5s" % ("-" if v["cells"][s]["review_at"] is None else v["cells"][s]["review_at"]) for s in SETUP_ORDER)))
        print()
        print("Part 3: the evaluator-only guard. The control worker reads the provider's store during recovery; refused in: %s" % ", ".join(refusals))
        for s in refusals:
            c = cells[("control", s)]
            print("  %-4s %s; messages after the restart: %d" % (s, c["refused"], sum(1 for t in c["commits"] if t >= RESTART_AFTER_KILL)))
        print()
        if "error" in live:
            print("Part 4: " + live["error"])
        else:
            print("Part 4: live record %s re-read under the contract (no ground truth: effects are what the provider's reads returned)" % live["run"])
            print("step  requests 200  no-resp 4xx  listed  dup  late full-subject  label")
            for s in live["steps"]:
                print("%-5s %-8d %-4d %-7d %-4d %-7d %-4d %-17s %s" % (s["step"], s["requests"], s["accepted_200"], s["no_response"], s["refused_4xx"],
                                                                 s["listed_at_settle"], s["duplicates_observed"],
                                                                 "-" if s["late_full_subject_filter"] is None else s["late_full_subject_filter"], s["label"]))
            print("(the record's settle read came 20 s after its last step, one read for every step: the record predates the contract, so no common")
            print(" horizon was predeclared and the elapsed time from each step's first request to that read differs; the late reads are a second point)")
            print("read paths for A1 (polls about every 1.5 s for 30 s):")
            for p in live["paths"]:
                print("  %-13s polls %-3d %s" % (p["path"], p["polls"], p["label"]))
            print("late reads at %s: the full-subject filter returns 0 of the A, D and E messages that the unfiltered list returns; on that path they are unconfirmed, not missing." % live["late_read_at"])
        print()
        print("%d problem(s)" % len(problems))
        for p in problems:
            print("  -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
