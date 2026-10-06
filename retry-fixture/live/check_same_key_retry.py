#!/usr/bin/env python3
"""Recompute the observations stated in live/README.md (follow-up of 2026-10-05 16:35-16:44 UTC) and in cases.json
(email-14, live_check.while_refused) from the published records live/SAME_KEY_RETRY.json, live/EXACT_BODY_CONTROL.json
and live/AGENTMAIL_LIVE.json, with no network and no key. Stdlib only (CPython 3.9+).
Usage: python3 check_same_key_retry.py [DIR]   (default: this file's directory)
exit 0 = every observation as stated, 1 = listed problems."""
import datetime as dt
import json
import os
import sys

EXPECTED = {
    # run 20261005T163554Z-1232b9 (same_key_retry.py)
    "1232b9: send requests": 2,
    "1232b9: control key is not a key of the recorded run": True,
    "1232b9: control subject differs from A's": True,
    "1232b9: control status": 403,
    "1232b9: control code": "message_rejected",
    "1232b9: retry-A path, key and body identical to recorded A1": True,
    "1232b9: retry-A written after the control's response (client clock)": True,
    "1232b9: retry-A status": 200,
    "1232b9: retry-A returns A1's message_id and thread_id": True,
    "1232b9: hours from A's message creation to retry-A (0.1)": 2.5,
    "1232b9: recorded run's message ids before == after == the recorded 6": True,
    "1232b9: messages with this run's subjects after": 0,
    # run 20261005T164354Z-140acc (exact_body_control.py)
    "140acc: send requests": 2,
    "140acc: control key is not a key of the recorded run": True,
    "140acc: control path and body identical to recorded A1": True,
    "140acc: control status": 403,
    "140acc: control code": "message_rejected",
    "140acc: retry-A path, key and body identical to recorded A1": True,
    "140acc: retry-A written after the control's response (client clock)": True,
    "140acc: retry-A status": 200,
    "140acc: retry-A returns A1's message_id and thread_id": True,
    "140acc: hours from A's message creation to retry-A (0.1)": 2.6,
    "140acc: recorded run's message ids before == after == the recorded 6": True,
    "140acc: messages with A's subject after": 1,
    # across the three records
    "same-key retries of A that returned A1's message_id (A2 + 2 follow-ups)": 3,
    "replay responses: status, body keys and header names equal A1's first response": True,
    "messages sent by the follow-up runs": 0,
}


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def body_eq(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def observe_run(tag, d, src, exact):
    o = {}
    a1 = [r for r in src["requests"] if r["step"] == "A1"][0]
    src_keys = {r.get("idempotency_key") for r in src["requests"] if r.get("idempotency_key")}
    recorded_ids = sorted(m["message_id"] for v in src["messages_by_step"].values() for m in v)
    sends = [r for r in d["requests"] if r["method"] == "POST"]
    o[tag + ": send requests"] = len(sends)
    ctl = [r for r in sends if r["step"].startswith("control")][0]
    ra = [r for r in sends if r["step"] == "retry-A"][0]
    o[tag + ": control key is not a key of the recorded run"] = bool(ctl["idempotency_key"]) and ctl["idempotency_key"] not in src_keys
    if exact:
        o[tag + ": control path and body identical to recorded A1"] = ctl["path"] == a1["path"] and body_eq(ctl["body"], a1["body"])
    else:
        o[tag + ": control subject differs from A's"] = ctl["body"]["subject"] != a1["body"]["subject"]
    o[tag + ": control status"] = ctl.get("status")
    o[tag + ": control code"] = (ctl.get("response") or {}).get("code")
    o[tag + ": retry-A path, key and body identical to recorded A1"] = (
        ra["path"] == a1["path"] and ra["idempotency_key"] == a1["idempotency_key"] and body_eq(ra["body"], a1["body"]))
    o[tag + ": retry-A written after the control's response (client clock)"] = ts(ra["t_sent"]) >= ts(ctl["t_response"])
    o[tag + ": retry-A status"] = ra.get("status")
    resp = ra.get("response") or {}
    o[tag + ": retry-A returns A1's message_id and thread_id"] = (
        resp.get("message_id") == a1["response"]["message_id"] and resp.get("thread_id") == a1["response"]["thread_id"])
    a_msg = src["messages_by_step"]["A"]
    o[tag + ": hours from A's message creation to retry-A (0.1)"] = round(
        (ts(ra["t_sent"]) - ts(a_msg[0]["created_at"])).total_seconds() / 3600.0, 1) if len(a_msg) == 1 else None
    before = d["messages_before"]["recorded_run"] if isinstance(d["messages_before"], dict) else d["messages_before"]
    after = d["messages_after"]["recorded_run"] if isinstance(d["messages_after"], dict) else d["messages_after"]
    o[tag + ": recorded run's message ids before == after == the recorded 6"] = (
        sorted(m["message_id"] for m in before) == sorted(m["message_id"] for m in after) == recorded_ids and len(recorded_ids) == 6)
    if exact:
        o[tag + ": messages with A's subject after"] = sum(1 for m in after if m["subject"] == a1["body"]["subject"])
    else:
        o[tag + ": messages with this run's subjects after"] = len(d["messages_after"]["this_run"])
    new = len(after) - len(before) + (len(d["messages_after"]["this_run"]) if isinstance(d["messages_after"], dict) else 0)
    return o, ra, new


def main(argv):
    base = argv[1] if len(argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    load = lambda n: json.load(open(os.path.join(base, n), encoding="utf-8"))
    src, d1, d2 = load("AGENTMAIL_LIVE.json"), load("SAME_KEY_RETRY.json"), load("EXACT_BODY_CONTROL.json")
    assert d1["recorded_run"] == d2["recorded_run"] == src["run"], "records are from different runs"
    o1, r1, n1 = observe_run("1232b9", d1, src, exact=False)
    o2, r2, n2 = observe_run("140acc", d2, src, exact=True)
    o = dict(o1)
    o.update(o2)
    a1 = [r for r in src["requests"] if r["step"] == "A1"][0]
    a2 = [r for r in src["requests"] if r["step"] == "A2"][0]
    replays = [a2, r1, r2]
    o["same-key retries of A that returned A1's message_id (A2 + 2 follow-ups)"] = sum(
        1 for r in replays if (r.get("response") or {}).get("message_id") == a1["response"]["message_id"])
    o["replay responses: status, body keys and header names equal A1's first response"] = all(
        r.get("status") == a1["status"] and sorted(r["response"]) == sorted(a1["response"])
        and sorted(r.get("headers") or {}) == sorted(a1.get("headers") or {}) for r in replays)
    o["messages sent by the follow-up runs"] = n1 + n2
    problems = [(k, v, o.get(k)) for k, v in EXPECTED.items() if o.get(k) != v]
    for k in EXPECTED:
        print("%-76s %s" % (k, json.dumps(o.get(k))))
    print("follow-ups %s and %s of run %s: %d observations, %d as stated, %d problem(s)" % (
        d1["run"], d2["run"], src["run"], len(EXPECTED), len(EXPECTED) - len(problems), len(problems)))
    for k, v, got in problems:
        print("  - %s: expected %s, record shows %s" % (k, json.dumps(v), json.dumps(got)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
