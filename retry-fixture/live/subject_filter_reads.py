#!/usr/bin/env python3
"""Read-only follow-up to late_reads.py: is the subject filter's miss about one-character tokens rather than time?
The List Messages reference documents the filter as a substring match. Each query below is a substring of the subject of
one or more of the run's messages (subjects: 'rf-live <run id> step-<S>', S in A, D, E, F1, F2), so a substring match must
return every message it is a substring of. Sends nothing. Environment: AGENTMAIL_API_KEY, AGENTMAIL_INBOX. Stdlib only.
Usage: python3 subject_filter_reads.py AGENTMAIL_LIVE.json SUBJECT_FILTER.json"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

KEY = os.environ["AGENTMAIL_API_KEY"]
INBOX = os.environ["AGENTMAIL_INBOX"]
rec = json.load(open(sys.argv[1]))
RUN = rec["run"]
IB = "https://api.agentmail.to/v0/inboxes/" + urllib.parse.quote(INBOX, safe="")
subjects = {}
for step, msgs in rec["messages_by_step"].items():
    for m in msgs:
        subjects[m["message_id"]] = "rf-live %s step-%s" % (RUN, step)


def get(path):
    req = urllib.request.Request(IB + path, headers={"Authorization": "Bearer " + KEY, "User-Agent": "retry-fixture-live/1"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


queries = ["rf-live %s step" % RUN, "step-F1", "step-F", "F1", "step-D", "step D", "step A", "step-E"]
out = {"run": RUN, "reads": []}
for q in queries:
    expected = sorted(s.rsplit("step-", 1)[-1] for s in subjects.values() if q in s)
    st, j = get("/messages?limit=100&subject=" + urllib.parse.quote(q, safe=""))
    got = sorted((m.get("subject") or "").rsplit("step-", 1)[-1] for m in (j.get("messages") or []) if RUN in (m.get("subject") or ""))
    t = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    out["reads"].append({"t": t, "query": q, "status": st, "substring_of_steps": expected, "returned_steps": got})
    print("%s  subject=%-38r -> %s | a substring match must return: %-22s | returned: %s" % (t, q, st, expected, got))
txt = json.dumps(out, indent=1)
if KEY in txt or INBOX in txt:
    sys.exit("secret or inbox in output; not written")
open(sys.argv[2], "w").write(txt + "\n")
