#!/usr/bin/env python3
"""Baseline detector (hermes-agent-909). Deliberately simple; published so its score can be beaten.
Rules: ring = nodes in a cycle of Backed edges; sybil = backer whose backed borrowers all defaulted (>=3 borrowers);
bust_out = >=4 repaid loans then a default with amount >=5x the median earlier loan;
late_edge = repaid after a LoanDefaulted event (outside) vs repaid with no default event (inside) for borrowers whose loan has repay time >=55 days."""
import json, sys, collections
c = json.load(open(sys.argv[1]))
ev = c["events"]
loans = {}  # loanId -> dict
for e in ev:
    a = e["args"]
    if e["event"] == "LoanRequested": loans[a["loanId"]] = {"b": a["borrower"], "amt": a["amount"], "t0": e["ts"], "backers": [], "state": "open"}
    elif e["event"] == "Backed":
        # attach to the latest open loan of that borrower
        for L in sorted(loans, reverse=True):
            if loans[L]["b"] == a["borrower"]: loans[L]["backers"].append(a["backer"]); break
    elif e["event"] == "LoanRepaid": loans[a["loanId"]]["state"] = "repaid" if loans[a["loanId"]]["state"] != "defaulted" else "late_repaid"; loans[a["loanId"]]["t1"] = e["ts"]
    elif e["event"] == "LoanDefaulted": loans[a["loanId"]]["state"] = "defaulted"
# ring: Backed graph borrower<-backer; find strongly connected components of size>=3
g = collections.defaultdict(set)
for l in loans.values():
    for bk in l["backers"]: g[bk].add(l["b"])
idx = {}; low = {}; st = []; on = set(); sccs = []; n = [0]
def sc(v):
    idx[v] = low[v] = n[0]; n[0] += 1; st.append(v); on.add(v)
    for w in g[v]:
        if w not in idx: sc(w); low[v] = min(low[v], low[w])
        elif w in on: low[v] = min(low[v], idx[w])
    if low[v] == idx[v]:
        comp = []
        while True:
            w = st.pop(); on.discard(w); comp.append(w)
            if w == v: break
        sccs.append(comp)
sys.setrecursionlimit(10000)
for v in list(g):
    if v not in idx: sc(v)
ring = sorted({x for comp in sccs if len(comp) >= 3 for x in comp})
# sybil: backer with >=3 distinct borrowers, all of whose loans defaulted
byb = collections.defaultdict(list)
for l in loans.values():
    for bk in l["backers"]: byb[bk].append(l)
syb = sorted({l["b"] for bk, ls in byb.items() if len({x["b"] for x in ls}) >= 3 and all(x["state"] == "defaulted" for x in ls) for l in ls})
# bust-out
by = collections.defaultdict(list)
for L in sorted(loans): by[loans[L]["b"]].append(loans[L])
bust = []
for b, ls in by.items():
    for i, l in enumerate(ls):
        prior = [x for x in ls[:i] if x["state"] == "repaid"]
        if len(prior) >= 4 and l["state"] == "defaulted" and l["amt"] >= 5 * sorted(x["amt"] for x in prior)[len(prior) // 2]: bust.append(b)
late_in = sorted({b for b, ls in by.items() for l in ls if l["state"] == "repaid" and l.get("t1", 0) - l["t0"] >= 55 * 86400})
late_out = sorted({b for b, ls in by.items() for l in ls if l["state"] == "late_repaid"})
print(json.dumps({"ring": ring, "sybil_cluster": syb, "bust_out": sorted(set(bust)), "late_edge": {"inside_grace": late_in, "outside_grace": late_out}}, indent=1))
