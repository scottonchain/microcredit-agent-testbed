#!/usr/bin/env python3
"""Compact queries over model.json so nobody reads the whole file (stdlib only).
  q.py PREFIX            ids starting with PREFIX (or containing it after 'contains:'), one line each
  q.py -f ID             the full record
  q.py --open [OWNER]    open actions (not done/cancelled), by due date, optionally one owner letter c|x|h
  q.py --due HOURS       open actions due within HOURS from now (UTC)
  q.py --grep TEXT       ids whose record text contains TEXT (case-insensitive)
"""
import datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
KINDS = ("entities", "evidence", "claims", "edges", "hypotheses", "actions", "decisions", "open_questions")
LETTER = {"c": "agent:claude", "x": "agent:codex", "h": "agent:hermes"}


def load():
    m = json.load(open(os.path.join(HERE, "model.json")))
    return m, {r["id"]: (k, r) for k in KINDS for r in m[k]}


def line(k, r):
    status = r.get("status") or (r.get("epistemics") or {}).get("status") or ""
    owner = (r.get("owner_id") or r.get("subject_id") or "").replace("agent:", "")
    due = (r.get("due_at") or "")[:16]
    title = r.get("title") or r.get("statement") or r.get("summary") or r.get("question") or r.get("recommendation") or ""
    return f"{r['id']} [{k[:3]} {status} {owner} {due}] {title[:110]}"


def main(a):
    m, idx = load()
    if not a:
        print(__doc__); return 0
    if a[0] == "-f":
        print(json.dumps(idx[a[1]][1], indent=1, ensure_ascii=False)); return 0
    if a[0] in ("--open", "--due"):
        now = datetime.datetime.now(datetime.timezone.utc)
        rows = []
        for r in m["actions"]:
            if r["status"] in ("done", "cancelled"): continue
            if a[0] == "--open" and len(a) > 1 and r["owner_id"] != LETTER.get(a[1], a[1]): continue
            if a[0] == "--due":
                d = r.get("due_at")
                if not d or datetime.datetime.fromisoformat(d.replace("Z", "+00:00")) > now + datetime.timedelta(hours=float(a[1])): continue
            rows.append(r)
        for r in sorted(rows, key=lambda r: r.get("due_at") or "9"): print(line("actions", r))
        return 0
    if a[0] == "--grep":
        t = a[1].lower()
        for k in KINDS:
            for r in m[k]:
                if t in json.dumps(r, ensure_ascii=False).lower(): print(line(k, r))
        return 0
    for i, (k, r) in idx.items():
        if i.startswith(a[0]) or (a[0].startswith("contains:") and a[0][9:] in i): print(line(k, r))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
