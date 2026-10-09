#!/usr/bin/env python3
"""Compact queries over model.json so nobody reads the whole file (stdlib only).
  q.py PREFIX            ids starting with PREFIX (or containing it after 'contains:'), one line each
  q.py -f ID             the full record
  q.py --open [OWNER]    open actions (not done/cancelled), by due date, optionally one owner letter c|x|h
  q.py --due HOURS       open actions due within HOURS from now (UTC)
  q.py --grep TEXT       ids whose record text contains TEXT (case-insensitive)
"""
import argparse
import datetime
import json
import math
import os
from pathlib import Path
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = ("entities", "evidence", "claims", "edges", "hypotheses", "actions", "decisions", "open_questions")
LETTER = {"c": "agent:claude", "x": "agent:codex", "h": "agent:hermes"}


def load():
    m = json.loads((Path(HERE) / "model.json").read_text(encoding="utf-8"))
    return m, {r["id"]: (k, r) for k in KINDS for r in m[k]}


def line(k, r):
    status = r.get("status") or (r.get("epistemics") or {}).get("status") or ""
    owner = (r.get("owner_id") or r.get("subject_id") or "").replace("agent:", "")
    due = (r.get("due_at") or "")[:16]
    title = r.get("title") or r.get("statement") or r.get("summary") or r.get("question") or r.get("recommendation") or ""
    return f"{r['id']} [{k[:3]} {status} {owner} {due}] {title[:110]}"


def main(a=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prefix", nargs="?")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-f", dest="full", metavar="ID")
    mode.add_argument("--open", nargs="?", const="", metavar="OWNER")
    mode.add_argument("--due", type=float, metavar="HOURS")
    mode.add_argument("--grep", metavar="TEXT")
    args = parser.parse_args(a)
    if args.prefix and any(value is not None for value in (args.full, args.open, args.due, args.grep)):
        parser.error("choose a prefix or one query option")
    if args.due is not None and (not math.isfinite(args.due) or args.due < 0):
        parser.error("HOURS must be finite and nonnegative")
    if all(value is None for value in (args.prefix, args.full, args.open, args.due, args.grep)):
        parser.print_help()
        return 0
    m, idx = load()
    if args.full is not None:
        if args.full not in idx:
            parser.error("unknown model ID: " + args.full)
        print(json.dumps(idx[args.full][1], indent=1, ensure_ascii=False))
        return 0
    if args.open is not None or args.due is not None:
        deadline = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=args.due)) if args.due is not None else None
        rows = []
        for record in m["actions"]:
            if record["status"] in ("done", "cancelled"):
                continue
            if args.open and record["owner_id"] != LETTER.get(args.open, args.open):
                continue
            due = record.get("due_at")
            if deadline is not None and (not due or datetime.datetime.fromisoformat(due.replace("Z", "+00:00")) > deadline):
                continue
            rows.append(record)
        for record in sorted(rows, key=lambda record: record.get("due_at") or "9"):
            print(line("actions", record))
    elif args.grep is not None:
        query = args.grep.lower()
        for kind, record in idx.values():
            if query in json.dumps(record, ensure_ascii=False).lower():
                print(line(kind, record))
    else:
        for ident, (kind, record) in idx.items():
            if ident.startswith(args.prefix) or (args.prefix.startswith("contains:") and args.prefix[9:] in ident):
                print(line(kind, record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
