#!/usr/bin/env python3
"""Compute basic features from corpus.json and (optionally) score a submission.
Usage: python3 score.py corpus.json            -> prints per-borrower features (a starting point, not a detector)
       python3 score.py corpus.json sub.json key.json -> scores sub against key (key is published at reveal time)
Submission format: {"ring": [addr,...], "sybil_cluster": [...], "bust_out": [...], "late_edge": {"inside_grace": [...], "outside_grace": [...]}}"""
import json, sys, collections
c = json.load(open(sys.argv[1]))
if len(sys.argv) == 2:
    f = collections.defaultdict(lambda: collections.Counter())
    for e in c["events"]:
        a = e["args"]
        if "borrower" in a: f[a["borrower"]][e["event"]] += 1
    print("borrowers:", len(f))
    for b, cnt in list(f.items())[:10]: print(b, dict(cnt))
    sys.exit()
sub = json.load(open(sys.argv[2])); key = json.load(open(sys.argv[3]))["key"]
def flat(d, p=""):
    for k, v in d.items():
        if isinstance(v, dict): yield from flat(v, p + k + ".")
        elif k != "seed": yield p + k, {x.lower() for x in v}
K = dict(flat(key)); S = dict(flat(sub))
allb = {e["args"]["borrower"].lower() for e in c["events"] if "borrower" in e["args"]}
tp = fp = fn = 0
for k, truth in K.items():
    got = S.get(k, set())
    t, f, n = len(truth & got), len(got - truth), len(truth - got)
    tp += t; fp += f; fn += n
    print("%-24s truth %2d found %2d false+ %2d missed %2d" % (k, len(truth), t, f, n))
print("overall precision %.2f recall %.2f; false-positive rate over %d borrowers: %.3f" % (
    tp / max(1, tp + fp), tp / max(1, tp + fn), len(allb), fp / max(1, len(allb) - sum(len(v) for v in K.values()))))
