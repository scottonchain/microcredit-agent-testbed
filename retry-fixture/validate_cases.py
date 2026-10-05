#!/usr/bin/env python3
"""Lint for retry-fixture/cases.json (stdlib only). Exit 0 = every case passes, 1 = problems listed on stdout.

Rules (v0.1 draft):
  top level: "status" (str), "principle" (str), "cases" (list)
  every case: "id" matching ^(email|chain)-[0-9]+$ and unique; "setup" and "expected" non-empty strings;
              "tested_by_us" bool; "status" in STATUS_VOCAB and consistent with tested_by_us
  tested_by_us true : needs "test" (which test, where) and "observed" (what the test showed)
  tested_by_us false: needs "source" (whose words the expected state is) and status "proposed / not-run"
Usage: python3 validate_cases.py [path/to/cases.json]
"""
import json, re, sys

STATUS_VOCAB = {"tested by us", "proposed / not-run"}
ID_RE = re.compile(r"^(email|chain)-[0-9]+$")

def lint(doc):
    problems = []
    if not isinstance(doc, dict):
        return ["top level is not an object"]
    for k, t in (("status", str), ("principle", str), ("cases", list)):
        if not isinstance(doc.get(k), t):
            problems.append("top level: missing or wrong-typed %r" % k)
    cases = doc.get("cases") if isinstance(doc.get("cases"), list) else []
    seen = set()
    for i, c in enumerate(cases):
        tag = "case[%d]" % i
        if not isinstance(c, dict):
            problems.append(tag + ": not an object"); continue
        cid = c.get("id")
        tag = "%s (%s)" % (tag, cid)
        if not isinstance(cid, str) or not ID_RE.match(cid):
            problems.append(tag + ": id missing or not email-N / chain-N")
        elif cid in seen:
            problems.append(tag + ": duplicate id")
        seen.add(cid)
        for k in ("setup", "expected"):
            if not isinstance(c.get(k), str) or not c.get(k).strip():
                problems.append(tag + ": %r missing or empty" % k)
        tbu = c.get("tested_by_us")
        if not isinstance(tbu, bool):
            problems.append(tag + ": tested_by_us must be true/false"); continue
        st = c.get("status")
        if st not in STATUS_VOCAB:
            problems.append(tag + ": status %r not in %s" % (st, sorted(STATUS_VOCAB)))
        if tbu:
            if st != "tested by us":
                problems.append(tag + ": tested_by_us true but status is not 'tested by us'")
            for k in ("test", "observed"):
                if not isinstance(c.get(k), str) or not c.get(k).strip():
                    problems.append(tag + ": tested case needs %r" % k)
        else:
            if st != "proposed / not-run":
                problems.append(tag + ": tested_by_us false but status is not 'proposed / not-run'")
            if not isinstance(c.get("source"), str) or not c.get("source").strip():
                problems.append(tag + ": untested case needs 'source' (whose words the expected state is)")
    return problems

def main(argv):
    path = argv[1] if len(argv) > 1 else __file__.rsplit("/", 1)[0] + "/cases.json"
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    problems = lint(doc)
    cases = doc.get("cases") if isinstance(doc, dict) and isinstance(doc.get("cases"), list) else []
    n_tested = sum(1 for c in cases if isinstance(c, dict) and c.get("tested_by_us") is True)
    print("cases: %d (tested by us: %d, proposed / not-run: %d)" % (len(cases), n_tested, len(cases) - n_tested))
    for c in cases:
        if isinstance(c, dict):
            print("  %-8s %-18s %s" % (c.get("id"), c.get("status"), "test: " + str(c.get("test"))[:70] if c.get("tested_by_us") else "source: " + str(c.get("source"))[:70]))
    if problems:
        print("FAIL: %d problem(s)" % len(problems))
        for p in problems:
            print("  - " + p)
        return 1
    print("OK: all cases pass")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
