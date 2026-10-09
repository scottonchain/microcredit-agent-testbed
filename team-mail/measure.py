#!/usr/bin/env python3
"""Compare TM1 originals with their TM2 conversions: size, approximate tokens, and which facts (ids, numbers,
dates, urls, hashes, comment ids) of the original are absent from the conversion. Usage: measure.py [examples-dir]"""
import json, os, re, sys
from pathlib import Path

FACT = re.compile(r"https?://[^\s\"',)]+|0x[0-9a-fA-F]{6,}|\b[0-9a-f]{7,40}\b|\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?|(?:action|claim|ev|hyp|question|decision|venue):[A-Za-z0-9._-]+|\$?\d[\d,]*(?:\.\d+)?%?")


REPOS = {"microcredit-contract": "ctr", "microcredit-agent-testbed": "tb", "microcredit-theory": "th", "microcredit-vision": "vis"}
GH = re.compile(r"https://github\.com/scottonchain/([\w-]+)/(?:issues|pull)/(\d+)(?:#issuecomment-(\d+))?")


def gh_refs(s):  # a github URL and its gh: ref are the same fact
    return GH.sub(lambda m: f"gh:{REPOS.get(m.group(1), m.group(1))}#{m.group(2)}" + (f"c{m.group(3)}" if m.group(3) else ""), s)


def toks(s):
    return len(re.findall(r"\w+|[^\w\s]", s))


def facts(s):
    out = set()
    for m in FACT.findall(s):
        m = m.rstrip(".,;)")
        if re.fullmatch(r"\d{1,2}", m):
            continue
        out.add(m.replace(",", "").lstrip("$"))
    return out


def norm_time(f):  # 2026-10-09T12:00:00Z and 2026-10-09T12:00Z are the same fact
    return re.sub(r"(T\d{2}:\d{2}):00Z", r"\1Z", f)


def main(d):
    tot1 = tot2 = tt1 = tt2 = 0
    for name in sorted(os.listdir(os.path.join(d, "tm1"))):
        a = gh_refs((Path(d) / "tm1" / name).read_text(encoding="utf-8"))
        b = gh_refs((Path(d) / "tm2" / name).read_text(encoding="utf-8"))
        fa = {norm_time(f) for f in facts(a)}
        fb = {norm_time(f) for f in facts(b)}
        miss = sorted(f for f in fa - fb if not any(f in g for g in fb))
        print(f"{name}: {len(a)} -> {len(b)} bytes ({100*len(b)//len(a)}%), ~tokens {toks(a)} -> {toks(b)} ({100*toks(b)//toks(a)}%), facts {len(fa)}, absent {len(miss)}")
        if miss:
            print("   absent:", ", ".join(miss[:40]))
        tot1 += len(a); tot2 += len(b); tt1 += toks(a); tt2 += toks(b)
    print(f"TOTAL: {tot1} -> {tot2} bytes ({100*tot2//tot1}%), ~tokens {tt1} -> {tt2} ({100*tt2//tt1}%)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).with_name("examples")))
