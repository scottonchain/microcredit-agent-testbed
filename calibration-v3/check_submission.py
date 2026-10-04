#!/usr/bin/env python3
"""Check a calibration-v3 submission file WITHOUT the answer key (acceptance criteria 2 and 4 in OFFER.md).
Usage: python3 check_submission.py corpus.json sub.json [--any-corpus]
Exit 0: sub.json is in the submission format, names only borrowers that occur in corpus.json, and corpus.json is the
        unmodified calibration-v3 corpus. Paste the printed hashes and the file into your submission comment.
Exit 1: a format problem (every problem is printed). Exit 2: corpus.json is not the frozen calibration-v3 corpus
        (pass --any-corpus to check a submission against the conformance fixture or another corpus).
An all-empty submission is valid: negative results count. No key, no network, standard library only."""
import hashlib, json, re, sys

V3_CORPUS_SHA256 = "87622563f3aa42e9350771a8aa2b81eed5ee154e004d4a5fced96063e7278a86"
CLASSES = ("ring", "sybil_cluster", "bust_out")
LATE = ("inside_grace", "outside_grace")
ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(args) != 2:
    sys.exit(__doc__)
corpus_path, sub_path = args
any_corpus = "--any-corpus" in sys.argv

corpus_raw = open(corpus_path, "rb").read()
corpus_sha = hashlib.sha256(corpus_raw).hexdigest()
borrowers = {e["args"]["borrower"].lower() for e in json.loads(corpus_raw)["events"] if "borrower" in e["args"]}
sub_raw = open(sub_path, "rb").read()
sub_sha = hashlib.sha256(sub_raw).hexdigest()
problems, warnings = [], []
try:
    sub = json.loads(sub_raw)
except ValueError as exc:
    sub = None
    problems.append("not JSON: %s" % exc)

def check_list(name, value, seen):
    if not isinstance(value, list):
        problems.append("%s must be a list" % name)
        return 0
    count = 0
    for i, item in enumerate(value):
        if not isinstance(item, str) or not ADDR.match(item):
            problems.append("%s[%d] is not a 0x address: %r" % (name, i, item))
            continue
        addr = item.lower()
        if addr not in borrowers:
            problems.append("%s[%d] %s is not a borrower in the corpus" % (name, i, item))
            continue
        if addr in seen:
            warnings.append("%s[%d] %s is listed more than once (scored once per class)" % (name, i, item))
        seen.add(addr)
        count += 1
    return count

counts = {}
if isinstance(sub, dict):
    extra = set(sub) - set(CLASSES) - {"late_edge"}
    if extra:
        problems.append("unexpected top-level keys: %s" % sorted(extra))
    for name in CLASSES:
        if name not in sub:
            problems.append("missing key %r" % name)
        else:
            counts[name] = check_list(name, sub[name], set())
    if "late_edge" not in sub:
        problems.append("missing key 'late_edge'")
    elif not isinstance(sub["late_edge"], dict):
        problems.append("late_edge must be an object with inside_grace and outside_grace")
    else:
        extra = set(sub["late_edge"]) - set(LATE)
        if extra:
            problems.append("unexpected late_edge keys: %s" % sorted(extra))
        for name in LATE:
            if name not in sub["late_edge"]:
                problems.append("missing key late_edge.%s" % name)
            else:
                counts["late_edge." + name] = check_list("late_edge." + name, sub["late_edge"][name], set())
elif sub is not None:
    problems.append("top level must be an object")

match = corpus_sha == V3_CORPUS_SHA256
print("corpus sha256     %s (%s)" % (corpus_sha, "calibration-v3, unmodified" if match else "NOT the frozen calibration-v3 corpus"))
print("submission sha256 %s" % sub_sha)
if counts and not problems:
    print("flagged           " + ", ".join("%s %d" % kv for kv in counts.items()) + " (%d addresses, all borrowers of the corpus)" % sum(counts.values()))
for w in warnings:
    print("warning:", w)
for p in problems:
    print("problem:", p)
if problems:
    print("REJECTED: fix the problems above and re-run")
    sys.exit(1)
if not match and not any_corpus:
    print("REJECTED: run your detector on the unmodified calibration-v3/corpus.json (or pass --any-corpus for the fixture)")
    sys.exit(2)
print("OK: submission format accepted; paste this file and the two hashes above into your submission comment")
