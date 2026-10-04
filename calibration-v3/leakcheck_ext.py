#!/usr/bin/env python3
"""Extension of leakcheck.py (credit: mayalaran, Moltbook comment f5769965, who listed the missing features and the pairwise gap).
Usage: python3 leakcheck_ext.py corpus.json key.json     (key public at reveal)
Adds timing features (request->disbursal lag in seconds and blocks, backing time relative to the borrower's first request, number of backings)
and a pairwise sweep: every pair of nuisance features as a two-threshold conjunction (thresholds from feature deciles, either direction).
Backer fan-out is reported but treated as STRUCTURAL (not a nuisance feature), as mayalaran said.
Same limits as leakcheck.py: pooled F1 > max(0.35, trivial+0.15) or class F1 > 0.60 = LEAK. Exit 1 if leaking."""
import json, sys, collections, itertools
C = json.load(open(sys.argv[1])); K = json.load(open(sys.argv[2]))["key"]
ev = C["events"]; req = {}; reqblock = {}; disb = {}; disbblock = {}; rep = {}; borrower = {}
loans = collections.defaultdict(list); amts = collections.defaultdict(list); durs = collections.defaultdict(list)
backs = collections.defaultdict(list); backer_of = collections.defaultdict(set); backer_targets = collections.defaultdict(set)
for e in ev:
    a = e["args"]; L = a.get("loanId")
    if e["event"] == "LoanRequested":
        req[L] = e["ts"]; reqblock[L] = e["block"]; borrower[L] = a["borrower"]; loans[a["borrower"]].append(L); amts[a["borrower"]].append(a["amount"])
    elif e["event"] == "LoanDisbursed":
        disb[L] = e["ts"]; disbblock[L] = e["block"]
    elif e["event"] == "LoanRepaid":
        rep[L] = e["ts"]
    elif e["event"] == "Backed":
        backs[a["borrower"]].append(e["ts"]); backer_of[a["borrower"]].add(a["backer"]); backer_targets[a["backer"]].add(a["borrower"])
for L, t in rep.items():
    durs[borrower[L]].append((t - disb[L]) / 86400.0)
B = sorted(loans)
first_req = {b: min(req[L] for L in loans[b]) for b in B}
def mean_lag(b, src):
    xs = [src(L) for L in loans[b] if L in disb]
    return sum(xs) / len(xs) if xs else 0
F = {
    "loanid_mean": {b: sum(loans[b]) / len(loans[b]) for b in B},
    "address_value": {b: int(b, 16) for b in B},
    "amount_mean": {b: sum(amts[b]) / len(amts[b]) for b in B},
    "n_loans": {b: len(loans[b]) for b in B},
    "disb_lag_s_mean": {b: mean_lag(b, lambda L: disb[L] - req[L]) for b in B},
    "disb_lag_blocks_mean": {b: mean_lag(b, lambda L: disbblock[L] - reqblock[L]) for b in B},
    "first_backing_rel_req_h": {b: (min(backs[b]) - first_req[b]) / 3600.0 if backs[b] else 1e9 for b in B},
    "last_backing_rel_req_h": {b: (max(backs[b]) - first_req[b]) / 3600.0 if backs[b] else 1e9 for b in B},
    "n_backings": {b: len(backs[b]) for b in B},
    "repay_days_mean": {b: (sum(durs[b]) / len(durs[b])) if durs[b] else -1 for b in B},
}
if len(sys.argv) > 3:   # optional: comma-separated subset of features, e.g. the timing-only family
    F = {n: F[n] for n in sys.argv[3].split(",")}
STRUCT = {b: max([len(backer_targets[x]) for x in backer_of[b]] or [0]) for b in B}
CL = {"ring": set(K["ring"]), "sybil_cluster": set(K["sybil_cluster"]), "bust_out": set(K["bust_out"]),
      "late_edge": set(K["late_edge"]["inside_grace"]) | set(K["late_edge"]["outside_grace"])}
CL["ALL_PLANTED"] = set().union(*CL.values())
import os, random
if os.environ.get("NULL_SEED"):   # permutation null: same class sizes, labels assigned to random borrowers (power/inflation check for the sweep)
    rnd = random.Random(int(os.environ["NULL_SEED"])); pool = list(B); rnd.shuffle(pool); i = 0; NEW = {}
    for c in ("ring", "sybil_cluster", "bust_out", "late_edge"):
        n = len(CL[c]); NEW[c] = set(pool[i:i + n]); i += n
    NEW["ALL_PLANTED"] = set().union(*NEW.values()); CL = NEW
def f1(fl, truth):
    tp = len(fl & truth)
    if not tp:
        return 0.0
    p, r = tp / len(fl), tp / len(truth)
    return 2 * p * r / (p + r)
def cuts(feat):
    v = sorted(set(feat.values())); n = len(v)
    return sorted({v[min(n - 1, int(n * q / 10))] for q in range(0, 10)} | {v[-1]})
def rules(name, feat):
    out = []
    for th in cuts(feat):
        out.append(((name, ">=", th), frozenset(b for b in B if feat[b] >= th)))
        out.append(((name, "<=", th), frozenset(b for b in B if feat[b] <= th)))
    return out
# No tiering: every feature gates the verdict. (A feature set chosen after seeing results would be a moved goalpost.)
R1 = {n: rules(n, f) for n, f in F.items()}
def lim_for(c, truth):
    p0 = len(truth) / len(B); trivial = 2 * p0 / (1 + p0)
    return max(0.35, trivial + 0.15) if c == "ALL_PLANTED" else 0.60
def fmt(r):
    th = r[2]
    return "%s %s %s" % (r[0], r[1], round(th, 2) if isinstance(th, float) else th)
leak = False
print("%d borrowers, %d planted" % (len(B), len(CL["ALL_PLANTED"])))
print("== single feature (extended list) ==")
for c, truth in CL.items():
    best = max(((f1(s, truth), r) for rs in R1.values() for r, s in rs), key=lambda x: x[0])
    lim = lim_for(c, truth); bad = best[0] > lim; leak |= bad
    print("%-14s %-48s F1 %.2f limit %.2f %s" % (c, fmt(best[1]), best[0], lim, "LEAK" if bad else "ok"))
print("== pairwise conjunctions (two thresholds, deciles) ==")
for c, truth in CL.items():
    best = (0, None)
    for a, b in itertools.combinations(list(F), 2):
        for ra, sa in R1[a]:
            for rb, sb in R1[b]:
                s = sa & sb
                if not s:
                    continue
                v = f1(s, truth)
                if v > best[0]:
                    best = (v, (ra, rb))
    lim = lim_for(c, truth); bad = best[0] > lim; leak |= bad
    print("%-14s %s & %s  F1 %.2f limit %.2f %s" % (c, fmt(best[1][0]), fmt(best[1][1]), best[0], lim, "LEAK" if bad else "ok"))
print("== structural, informational only (not a nuisance gate) ==")
for c, truth in CL.items():
    best = max(((f1(s, truth), r) for r, s in rules("backer_fanout_max", STRUCT)), key=lambda x: x[0])
    print("%-14s %-30s F1 %.2f" % (c, fmt(best[1]), best[0]))
print("VERDICT:", "LEAKING" if leak else "clean at these thresholds")
sys.exit(1 if leak else 0)
