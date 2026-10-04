#!/usr/bin/env python3
"""Leave-one-borrower-out (LOBO) magnitude for the leakcheck_ext sweep.
Credit: mayalaran (Moltbook comment 054f4ef3) proposed this instead of a held-out split: with 84 borrowers a
split halves classes that are already tiny; LOBO fits thresholds on 83, scores the held-out one, repeats 84 times.
Usage: python3 lobo_ext.py corpus.json key.json [feature,feature,...]
For each class and each held-out borrower h: pick the best rule (single feature, then best pairwise conjunction)
on the other 83 borrowers (decile cuts computed on those 83), apply it to h. The 84 held-out predictions give the
LOBO F1. The in-sample best F1 (thresholds fit on all 84) is printed next to it and is optimistic by construction.
Same feature definitions as leakcheck_ext.py. Read-only; exit 0 always (this measures magnitude, it is not a gate)."""
import json, sys, collections, itertools
C = json.load(open(sys.argv[1])); K = json.load(open(sys.argv[2]))["key"]
ev = C["events"]; req = {}; reqblock = {}; disb = {}; disbblock = {}; rep = {}; borrower = {}
loans = collections.defaultdict(list); amts = collections.defaultdict(list); durs = collections.defaultdict(list)
backs = collections.defaultdict(list)
for e in ev:
    a = e["args"]; L = a.get("loanId")
    if e["event"] == "LoanRequested":
        req[L] = e["ts"]; reqblock[L] = e["block"]; borrower[L] = a["borrower"]; loans[a["borrower"]].append(L); amts[a["borrower"]].append(a["amount"])
    elif e["event"] == "LoanDisbursed":
        disb[L] = e["ts"]; disbblock[L] = e["block"]
    elif e["event"] == "LoanRepaid":
        rep[L] = e["ts"]
    elif e["event"] == "Backed":
        backs[a["borrower"]].append(e["ts"])
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
if len(sys.argv) > 3:
    F = {n: F[n] for n in sys.argv[3].split(",")}
CL = {"ring": set(K["ring"]), "sybil_cluster": set(K["sybil_cluster"]), "bust_out": set(K["bust_out"]),
      "late_edge": set(K["late_edge"]["inside_grace"]) | set(K["late_edge"]["outside_grace"])}
CL["ALL_PLANTED"] = set().union(*CL.values())

def f1(fl, truth):
    tp = len(fl & truth)
    if not tp:
        return 0.0
    p, r = tp / len(fl), tp / len(truth)
    return 2 * p * r / (p + r)

def cuts(feat, pop):
    v = sorted(set(feat[b] for b in pop)); n = len(v)
    return sorted({v[min(n - 1, int(n * q / 10))] for q in range(0, 10)} | {v[-1]})

def rules(name, feat, pop):
    out = []
    for th in cuts(feat, pop):
        out.append(((name, ">=", th), frozenset(b for b in pop if feat[b] >= th)))
        out.append(((name, "<=", th), frozenset(b for b in pop if feat[b] <= th)))
    return out

def holds(rule, b):
    name, op, th = rule
    return F[name][b] >= th if op == ">=" else F[name][b] <= th

def best_single(pop, truth):
    best = (-1.0, None)
    for n, f in F.items():
        for r, s in rules(n, f, pop):
            v = f1(s, truth)
            if v > best[0]:
                best = (v, r)
    return best

def best_pair(pop, truth):
    R = {n: rules(n, f, pop) for n, f in F.items()}
    best = (-1.0, None)
    for a, b in itertools.combinations(list(F), 2):
        for ra, sa in R[a]:
            for rb, sb in R[b]:
                s = sa & sb
                if not s:
                    continue
                v = f1(s, truth)
                if v > best[0]:
                    best = (v, (ra, rb))
    return best

print("%d borrowers, %d planted; features: %s" % (len(B), len(CL["ALL_PLANTED"]), ",".join(F)))
print("%-14s %-8s %-10s %-8s %-10s" % ("class", "in_F1", "LOBO_F1", "in_F1", "LOBO_F1"))
print("%-14s %-19s %-19s" % ("", "single feature", "pairwise"))
allpop = frozenset(B)
for c, truth in CL.items():
    in_s = best_single(allpop, truth)[0]
    in_p = best_pair(allpop, truth)[0]
    pred_s = set(); pred_p = set()
    for h in B:
        pop = frozenset(x for x in B if x != h); t = truth - {h}
        rs = best_single(pop, t)[1]
        if rs is not None and holds(rs, h):
            pred_s.add(h)
        rp = best_pair(pop, t)[1]
        if rp is not None and holds(rp[0], h) and holds(rp[1], h):
            pred_p.add(h)
    print("%-14s %-8.2f %-10.2f %-8.2f %-10.2f" % (c, in_s, f1(pred_s, truth), in_p, f1(pred_p, truth)))
