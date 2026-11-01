#!/usr/bin/env python3
"""Compact queries over model.json so nobody reads the whole file (stdlib only).
  q.py PREFIX            ids starting with PREFIX (or containing it after 'contains:'), one line each
  q.py -f ID             the full record
  q.py --open [OWNER]    open actions (not done/cancelled), by due date, optionally one owner letter c|x|h
  q.py --due HOURS       open actions due within HOURS from now (UTC)
  q.py --grep TEXT       ids whose record text contains TEXT (case-insensitive)
  q.py --recall TEXT     bounded learning records, including closed actions, with sources and alternatives
  q.py --recall TEXT --limit N   return at most N lessons (default 5)
"""
import argparse
import datetime
import json
import math
import os
import re
from pathlib import Path
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = ("entities", "evidence", "claims", "edges", "hypotheses", "actions", "decisions", "open_questions", "coverage")
LETTER = {"c": {"agent:claude"}, "x": {"agent:codex", "agent:coordinator"}, "h": {"agent:hermes"}}


def load():
    m = json.loads((Path(HERE) / "model.json").read_text(encoding="utf-8"))
    return m, {r["id"]: (k, r) for k in KINDS for r in m[k]}


def line(k, r):
    status = r.get("status") or (r.get("epistemics") or {}).get("status") or ""
    owner = (r.get("owner_id") or r.get("subject_id") or "").replace("agent:", "")
    due = (r.get("due_at") or "")[:16]
    title = r.get("title") or r.get("name") or r.get("statement") or r.get("summary") or r.get("question") or r.get("recommendation") or ""
    return f"{r['id']} [{k[:3]} {status} {owner} {due}] {title[:110]}"


def recall(model, index, query, limit=5, now=None):
    """Lexical retrieval only: matching is not evidence strength or permission."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    terms = set(re.findall(r"[^\W_]+", query.casefold()))
    matches = []
    available = 0
    for action in model['actions']:
        learning = action.get('learning')
        if not learning:
            continue
        available += 1
        words = set(re.findall(r"[^\W_]+", json.dumps(
            [action['id'], action.get('title', ''), learning], ensure_ascii=False).casefold()))
        matched = sorted(terms & words)
        if not matched or (query in index and query != action['id']):
            continue
        references = set(learning['evidence_ids'] + learning['counterevidence_ids'])
        for alternative in learning['alternatives']:
            references.update(alternative['related_ids'])
        missing = references - index.keys()
        if missing:
            raise ValueError('learning has unresolved references: ' + ', '.join(sorted(missing)))
        due = learning['freshness']['recheck_by']
        refresh_due = bool(due and datetime.datetime.fromisoformat(due.replace('Z', '+00:00')) <= now)
        matches.append({
            'action_id': action['id'], 'title': action.get('title', ''),
            'status': action['status'], 'matched_terms': matched,
            'refresh_due': refresh_due, 'learning': learning,
            'linked_records': [{'kind': index[i][0], 'record': index[i][1]} for i in sorted(references)],
        })
    matches.sort(key=lambda row: (-len(row['matched_terms']), row['action_id']))
    return {
        'model_version': model.get('model_version'), 'model_updated_at': model.get('updated_at'),
        'query': query, 'method': 'lexical term overlap; not confidence or authority',
        'learning_records_available': available, 'matching_records': len(matches),
        'truncated': len(matches) > limit, 'results': matches[:limit],
        'limits': 'Only annotated actions are searched. No match means a retrieval gap, not no opportunity. '
                  'Use --grep and read decision-critical records in full. Alternatives are untested hypotheses; '
                  'action status, consent and permissions remain authoritative. Refresh mutable sources before use.',
    }


def main(a=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prefix", nargs="?")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("-f", dest="full", metavar="ID")
    mode.add_argument("--open", nargs="?", const="", metavar="OWNER")
    mode.add_argument("--due", type=float, metavar="HOURS")
    mode.add_argument("--grep", metavar="TEXT")
    mode.add_argument("--recall", metavar="TEXT")
    parser.add_argument("--limit", type=int, default=5, metavar="N")
    args = parser.parse_args(a)
    if args.prefix and any(value is not None for value in (args.full, args.open, args.due, args.grep, args.recall)):
        parser.error("choose a prefix or one query option")
    if args.limit < 1 or args.limit > 20:
        parser.error("N must be between 1 and 20")
    if args.limit != 5 and args.recall is None:
        parser.error("--limit requires --recall")
    if args.recall is not None and not re.search(r"[^\W_]+", args.recall):
        parser.error("TEXT must contain a search term")
    if args.due is not None and (not math.isfinite(args.due) or args.due < 0):
        parser.error("HOURS must be finite and nonnegative")
    if all(value is None for value in (args.prefix, args.full, args.open, args.due, args.grep, args.recall)):
        parser.print_help()
        return 0
    m, idx = load()
    if args.recall is not None:
        try:
            result = recall(m, idx, args.recall, args.limit)
        except ValueError as error:
            parser.error(str(error))
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return 0
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
            if args.open and record["owner_id"] not in LETTER.get(args.open, {args.open}):
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
