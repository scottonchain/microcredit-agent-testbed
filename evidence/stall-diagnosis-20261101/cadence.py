#!/usr/bin/env python3
"""Board cadence: comments per day, per lane, and silent gaps, from GitHub comment dumps.

Usage:
    python3 cadence.py DUMP.json [DUMP.json ...] [--gap-hours 5] [--csv OUT.csv]

Each DUMP.json is a page of `GET /repos/{owner}/{repo}/issues/{n}/comments` saved
as returned by the API (a JSON array of comment objects with `created_at`,
`user.login` and `body`). Stdlib only; no network. The lane is read from the body's
opening signature or TM2 `id` prefix, so a mislabelled signature is counted as
`other`, never guessed. A gap is the time between consecutive comments; it says the
board was silent, not that any agent was idle, and board silence while response
windows run is only a stall when nothing else was advanced (see README.md).
"""
import argparse
import collections
import csv
import datetime
import json
import re
import sys

LANE_PATTERNS = (
    ("hermes", re.compile(r"^(<!--\s*)?(HERMES|Hermes|\{\s*\"v\":\s*2,\s*\"id\":\s*\"h-)")),
    ("claude", re.compile(r"^(Claude|TM2 \| Claude|\{\"v\":2,\"id\":\"c-)")),
    ("codex", re.compile(r"^(Codex|```json\s*\{\"v\":2,\"id\":\"x-|\{\"v\":2,\"id\":\"x-)")),
    ("dot", re.compile(r"^dot \(")),
)


def lane_of(comment):
    login = comment.get("user", {}).get("login", "")
    if login.startswith("hermes"):
        return "hermes"
    body = comment.get("body", "")
    for lane, pattern in LANE_PATTERNS:
        if pattern.match(body):
            return lane
    return "other"


def parse_time(value):
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("dumps", nargs="+")
    parser.add_argument("--gap-hours", type=float, default=5.0)
    parser.add_argument("--csv")
    args = parser.parse_args(argv)

    comments = []
    for path in args.dumps:
        with open(path, encoding="utf-8") as handle:
            page = json.load(handle)
        if not isinstance(page, list):
            raise SystemExit(f"{path}: expected a JSON array of comments")
        comments.extend(page)
    seen = set()
    unique = []
    for comment in comments:
        if comment["id"] in seen:
            continue
        seen.add(comment["id"])
        unique.append(comment)
    unique.sort(key=lambda c: c["created_at"])
    if not unique:
        raise SystemExit("no comments")

    per_day = collections.defaultdict(collections.Counter)
    for comment in unique:
        per_day[comment["created_at"][:10]][lane_of(comment)] += 1
    lanes = ("codex", "claude", "hermes", "dot", "other")

    print(f"range {unique[0]['created_at']} .. {unique[-1]['created_at']} ({len(unique)} comments)")
    print("day        " + " ".join(f"{lane:>6}" for lane in lanes) + "  total")
    rows = []
    for day in sorted(per_day):
        counts = per_day[day]
        total = sum(counts.values())
        print(f"{day} " + " ".join(f"{counts[lane]:>6}" for lane in lanes) + f"  {total:>5}")
        rows.append([day] + [counts[lane] for lane in lanes] + [total])

    print(f"\nsilent gaps longer than {args.gap_hours:g} hours (board silence, not proof of idleness):")
    previous = None
    gaps = []
    for comment in unique:
        now = parse_time(comment["created_at"])
        if previous is not None:
            hours = (now - previous).total_seconds() / 3600
            if hours > args.gap_hours:
                gaps.append((previous, now, hours))
                print(f"  {previous:%Y-%m-%d %H:%M}Z -> {now:%Y-%m-%d %H:%M}Z  {hours:5.1f} h")
        previous = now

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["day", *lanes, "total"])
            writer.writerows(rows)
            writer.writerow([])
            writer.writerow(["gap_start_utc", "gap_end_utc", "hours"])
            for start, end, hours in gaps:
                writer.writerow([start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ"), f"{hours:.1f}"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
