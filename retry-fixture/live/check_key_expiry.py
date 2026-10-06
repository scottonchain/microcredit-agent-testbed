#!/usr/bin/env python3
"""Offline check of KEY_EXPIRY_CHECK.json (no key, no network). Recomputes, from the records in this directory, the ages at
which the two keys were retried and the outcomes, and compares them with the stated values.
Records: AGENTMAIL_LIVE.json (first run, 2026-10-05), EXACT_BODY_CONTROL.json (A's key used again 2026-10-05 16:43 UTC),
KEY_EXPIRY_CHECK.json (the two retries, 2026-10-06). Exit 0 if every observation is as stated, 1 otherwise. Stdlib only."""
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
L = lambda n: json.load(open(os.path.join(HERE, n), encoding="utf-8"))
live, ctl, ke = L("AGENTMAIL_LIVE.json"), L("EXACT_BODY_CONTROL.json"), L("KEY_EXPIRY_CHECK.json")
P = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
H = lambda a, b: round((b - a).total_seconds() / 3600, 2)

first = lambda step: [r for r in live["requests"] if r["step"] == step + "1"][0]
A1, D1 = first("A"), first("D")
kA, kD = A1["idempotency_key"], D1["idempotency_key"]
retry = {r["step"]: r for r in ke["requests"] if r["step"].startswith("retry-")}
A_msg = A1["response"]["message_id"]
D_msg = live["messages_by_step"]["D"][0]["message_id"]
earlier = live["requests"] + ctl["requests"]
uses_A = [P(r["t_sent"]) for r in earlier if r.get("idempotency_key") == kA and r["method"] == "POST"]
uses_D = [P(r["t_sent"]) for r in earlier if r.get("idempotency_key") == kD and r["method"] == "POST"]
D_created = P(live["messages_by_step"]["D"][0]["created_at"])
A_created = P(live["messages_by_step"]["A"][0]["created_at"])
tA, tD = P(retry["retry-A"]["t_sent"]), P(retry["retry-D"]["t_sent"])
rA, rD = retry["retry-A"]["response"], retry["retry-D"]["response"]
new_today = [m for m in ke["messages_after"] if P(m["created_at"]) > P("2026-10-06T00:00:00Z")]

OBS = [
    ("D: hours from its message's created_at to the retry", H(D_created, tD), 24.98),
    ("A: hours from its message's created_at to the retry", H(A_created, tA), 24.99),
    ("D: hours from its key's last earlier use to the retry", H(max(uses_D), tD), 24.98),
    ("A: hours from its key's last earlier use to the retry", H(max(uses_A), tA), 22.4),
    ("D: earlier same-key requests after the first", len(uses_D) - 1, 1),
    ("A: earlier same-key requests after the first", len(uses_A) - 1, 3),
    ("retry-D HTTP status", retry["retry-D"]["status"], 200),
    ("retry-A HTTP status", retry["retry-A"]["status"], 200),
    ("retry-D returned the original message_id", rD["message_id"] == D_msg, False),
    ("retry-A returned the original message_id", rA["message_id"] == A_msg, False),
    ("send requests", ke["send_requests"], 2),
    ("run's messages listed before", len(ke["messages_before"]), 6),
    ("run's messages listed after", len(ke["messages_after"]), 8),
    ("of them created on 2026-10-06", len(new_today), 2),
    ("recorded verdicts", ke["verdicts"], {"D": "new send", "A": "new send"}),
]
bad = 0
for name, got, want in OBS:
    ok = got == want
    bad += not ok
    print("%-58s %-36s %s" % (name + ":", json.dumps(got), "as stated" if ok else "NOT as stated (stated %s)" % json.dumps(want)))
print("%d observations, %d as stated, %d problem(s)" % (len(OBS), len(OBS) - bad, bad))
sys.exit(1 if bad else 0)
