#!/usr/bin/env python3
"""Leak check for a calibration corpus (credit: mayalaran, Moltbook comment a6a8e2da, who found the v1 leaks by reading the data).
Usage: python3 leakcheck.py corpus.json key.json      (key.json = {"key": {...}, "salt": ...}; public at reveal)
For each NUISANCE feature (loan-id position, address value, amount, whole-day timing, repeated-duration fingerprint, number of loans)
it finds the best single-threshold detector (either direction) per attack class and pooled, scored by F1 over borrowers.
A corpus is clean if no nuisance feature alone beats F1 0.35 pooled or 0.60 on any class. Exit code 1 if leaking.
Note: structural signal (who backed whom, defaults) is NOT a nuisance feature; it is what detectors are supposed to use."""
import json, sys, collections
C = json.load(open(sys.argv[1])); K = json.load(open(sys.argv[2]))["key"]
ev = C["events"]; req = {}; disb = {}; rep = {}; borrower = {}
loans = collections.defaultdict(list); amts = collections.defaultdict(list); durs = collections.defaultdict(list)
for e in ev:
    a = e["args"]; L = a.get("loanId")
    if e["event"] == "LoanRequested": req[L] = a; borrower[L] = a["borrower"]; loans[a["borrower"]].append(L); amts[a["borrower"]].append(a["amount"])
    elif e["event"] == "LoanDisbursed": disb[L] = e["ts"]
    elif e["event"] == "LoanRepaid": rep[L] = e["ts"]
for L, t in rep.items(): durs[borrower[L]].append((t - disb[L]) / 86400.0)
# how many OTHER borrowers share the same repay duration to 0.01 day (the v1 "29.0 / 31.0" fingerprint)
cnt = collections.Counter(round(d, 4) for v in durs.values() for d in v)
B = sorted(loans)
F = {
 "loanid_first": {b: min(loans[b]) for b in B}, "loanid_last": {b: max(loans[b]) for b in B}, "loanid_mean": {b: sum(loans[b]) / len(loans[b]) for b in B},
 "address_value": {b: int(b, 16) for b in B}, "amount_max": {b: max(amts[b]) for b in B}, "amount_mean": {b: sum(amts[b]) / len(amts[b]) for b in B},
 "amount_roundness": {b: sum(1 for x in amts[b] if x % (50 * 10**6) == 0) / len(amts[b]) for b in B},
 "whole_day_timing": {b: (sum(abs(d - round(d)) < 1e-9 for d in durs[b]) / len(durs[b])) if durs[b] else 0 for b in B},
 "repeated_duration": {b: max([cnt[round(d, 4)] - 1 for d in durs[b]] or [0]) for b in B},
}
CL = {"ring": set(K["ring"]), "sybil_cluster": set(K["sybil_cluster"]), "bust_out": set(K["bust_out"]),
      "late_edge": set(K["late_edge"]["inside_grace"]) | set(K["late_edge"]["outside_grace"])}
CL["ALL_PLANTED"] = set().union(*CL.values())
def best(feat, truth):
    vals = sorted(set(feat.values())); bf = (0, None, None)
    for th in vals:
        for d in (">=", "<="):
            fl = {b for b in B if (feat[b] >= th if d == ">=" else feat[b] <= th)}
            tp = len(fl & truth)
            if not tp: continue
            p, r = tp / len(fl), tp / len(truth); f = 2 * p * r / (p + r)
            if f > bf[0]: bf = (f, d, th)
    return bf
leak = False
print("%d borrowers, %d planted" % (len(B), len(CL["ALL_PLANTED"])))
for c, truth in CL.items():
    res = sorted(((best(f, truth), n) for n, f in F.items()), key=lambda x: -x[0][0])[0]
    (f1, d, th), n = res
    p0 = len(truth) / len(B); trivial = 2 * p0 / (1 + p0)   # F1 of flagging every borrower
    lim = max(0.35, trivial + 0.15) if c == "ALL_PLANTED" else 0.60
    bad = f1 > lim; leak |= bad
    print("%-14s best nuisance feature: %-18s F1 %.2f  (%s %s)  %s" % (c, n, f1, d, round(th, 2) if isinstance(th, float) else th, "LEAK" if bad else "ok"))
print("VERDICT:", "LEAKING" if leak else "clean at these thresholds")
sys.exit(1 if leak else 0)
