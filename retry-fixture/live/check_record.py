#!/usr/bin/env python3
"""Recompute the observations stated in live/README.md and cases.json (email-14, live_check) from the published records
live/AGENTMAIL_LIVE.json and live/LATE_READS.json, with no network and no key. Stdlib only (CPython 3.9+).
Usage: python3 check_record.py [path/to/AGENTMAIL_LIVE.json]   (LATE_READS.json is read from the same directory)
exit 0 = every observation as stated, 1 = listed problems."""
import datetime as dt
import json
import os
import sys

EXPECTED_LATE = {
    "late: full subject of step A": 0,
    "late: full subject of step D": 0,
    "late: full subject of step E": 0,
    "late: full subject of step F1": 1,
    "late: full subject of step F2": 1,
    "late: 'rf-live'": 6,
    "late: the run id": 6,
    "late: 'step'": 6,
    "late: 'step-A'": 0,
    "late: unfiltered list": 6,
    "late reads made 26 min or more after every A/D/E message was created": True,
}

EXPECTED = {
    "A1 status": 200,
    "A2 status (same key, identical request)": 200,
    "A2 returns A1's message_id": True,
    "messages for step A": 1,
    "B status (same key, other subject)": 409,
    "B code": "conflict",
    "messages for step B": 0,
    "C status (empty key)": 400,
    "C code": "validation_error",
    "messages for step C": 0,
    "D1 got no response (client gave up)": True,
    "D2 status (same key, 5 s later)": 200,
    "messages for step D": 1,
    "D2 returns the message created before D2 was written": True,
    "E1 got no response (client gave up)": True,
    "E2 status (no key, 5 s later)": 200,
    "messages for step E": 2,
    "one E message created before E2 was written": True,
    "F1 statuses": [200, 409],
    "F2 statuses": [200, 409],
    "F3 statuses": [403, 409],
    "every F 409 says already in progress": True,
    "messages for step F1": 1,
    "messages for step F2": 1,
    "messages for step F3": 0,
    "F3 403 code": "message_rejected",
    "L2 status": 403,
    "L3 status": 403,
    "A1 read by id: found on the first read": True,
    "A1 unfiltered list: found on the first read": True,
    "A1 subject-filtered list: reads": 19,
    "A1 subject-filtered list: found": False,
    "list response keys": ["count", "limit", "messages"],
    "messages created in the run": 6,
}


def observe(d):
    req = {r["step"]: r for r in d["requests"]}
    by = d["messages_by_step"]

    def sent(step):
        return [m for m in by.get(step, []) if "sent" in (m.get("labels") or [])]

    def mid(step):
        r = req[step].get("response")
        return r.get("message_id") if isinstance(r, dict) else None

    def code(step):
        r = req[step].get("response")
        return r.get("code") if isinstance(r, dict) else None

    def no_response(step):
        return "status" not in req[step] and str(req[step].get("client", "")).startswith("gave up")

    def trial(i):
        a, b = req["F%da" % i], req["F%db" % i]
        return sorted([a.get("status"), b.get("status")])

    f409 = [r for r in d["requests"] if r["step"][:1] == "F" and r.get("status") == 409]
    pr = [p for p in d["probes"] if p["sample"] == "A1"]
    first = {k: [p for p in pr if p["path"] == k] for k in ("get_by_id", "list", "list_subject")}
    d_msgs, e_msgs = sent("D"), sent("E")
    o = {
        "A1 status": req["A1"].get("status"),
        "A2 status (same key, identical request)": req["A2"].get("status"),
        "A2 returns A1's message_id": mid("A2") is not None and mid("A2") == mid("A1"),
        "messages for step A": len(sent("A")),
        "B status (same key, other subject)": req["B"].get("status"),
        "B code": code("B"),
        "messages for step B": len(sent("B")),
        "C status (empty key)": req["C"].get("status"),
        "C code": code("C"),
        "messages for step C": len(sent("C")),
        "D1 got no response (client gave up)": no_response("D1"),
        "D2 status (same key, 5 s later)": req["D2"].get("status"),
        "messages for step D": len(d_msgs),
        "D2 returns the message created before D2 was written": len(d_msgs) == 1 and d_msgs[0]["message_id"] == mid("D2")
        and d_msgs[0]["created_at"] < req["D2"]["t_written"],
        "E1 got no response (client gave up)": no_response("E1"),
        "E2 status (no key, 5 s later)": req["E2"].get("status"),
        "messages for step E": len(e_msgs),
        "one E message created before E2 was written": sum(1 for m in e_msgs if m["created_at"] < req["E2"]["t_written"]) == 1
        and any(m["message_id"] == mid("E2") for m in e_msgs),
        "F1 statuses": trial(1),
        "F2 statuses": trial(2),
        "F3 statuses": trial(3),
        "every F 409 says already in progress": bool(f409) and all("already in progress" in r["response"].get("message", "") for r in f409),
        "messages for step F1": len(sent("F1")),
        "messages for step F2": len(sent("F2")),
        "messages for step F3": len(sent("F3")),
        "F3 403 code": [code(s) for s in ("F3a", "F3b") if req[s].get("status") == 403][0],
        "L2 status": req["L2"].get("status"),
        "L3 status": req["L3"].get("status"),
        "A1 read by id: found on the first read": bool(first["get_by_id"]) and first["get_by_id"][0]["found"],
        "A1 unfiltered list: found on the first read": bool(first["list"]) and first["list"][0]["found"],
        "A1 subject-filtered list: reads": len(first["list_subject"]),
        "A1 subject-filtered list: found": any(p["found"] for p in first["list_subject"]),
        "list response keys": sorted({k for p in d["probes"] if p["path"] != "get_by_id" for k in (p["response_keys"] or [])}),
        "messages created in the run": sum(len(sent(s)) for s in by),
    }
    return o


def ts(s):
    return dt.datetime.strptime(s.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S.%f%z" if "." in s else "%Y-%m-%dT%H:%M:%S%z")


def observe_late(d, late):
    names = {"full subject of step %s" % s: "late: full subject of step %s" % s for s in ("A", "D", "E", "F1", "F2")}
    names.update({"'rf-live'": "late: 'rf-live'", "the run id": "late: the run id", "'step'": "late: 'step'",
                  "'step-A'": "late: 'step-A'", "none (unfiltered list)": "late: unfiltered list"})
    o = {}
    for r in late["reads"]:
        if r["filter"] in names and r["status"] == 200:
            o[names[r["filter"]]] = r["run_messages_returned"]
    first = min(ts(r["t"]) for r in late["reads"])
    created = [ts(m["created_at"]) for s in ("A", "D", "E") for m in d["messages_by_step"].get(s, [])]
    o["late reads made 26 min or more after every A/D/E message was created"] = bool(created) and late["run"] == d["run"] and \
        all((first - c).total_seconds() >= 26 * 60 for c in created)
    return o


def main(argv):
    path = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "AGENTMAIL_LIVE.json")
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    with open(os.path.join(os.path.dirname(os.path.abspath(path)), "LATE_READS.json"), encoding="utf-8") as f:
        late = json.load(f)
    o = observe(d)
    o.update(observe_late(d, late))
    exp = dict(EXPECTED)
    exp.update(EXPECTED_LATE)
    problems = [(k, v, o.get(k)) for k, v in exp.items() if o.get(k) != v]
    for k in exp:
        print("%-70s %s" % (k, json.dumps(o.get(k))))
    print("run %s: %d observations, %d as stated, %d problem(s)" % (d.get("run"), len(exp), len(exp) - len(problems), len(problems)))
    for k, v, got in problems:
        print("  - %s: expected %s, record shows %s" % (k, json.dumps(v), json.dumps(got)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
