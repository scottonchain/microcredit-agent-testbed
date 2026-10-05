#!/usr/bin/env python3
"""Read-only follow-up to agentmail_live_check.py: query the List Messages subject filter (documented as a substring
match, served by search) with each sent step's full subject and with shorter substrings, and the unfiltered list.
Sends nothing. Environment: AGENTMAIL_API_KEY, AGENTMAIL_INBOX. Stdlib only (CPython 3.9+).
Usage: python3 late_reads.py AGENTMAIL_LIVE.json LATE_READS.json"""
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


def get(path):
    req = urllib.request.Request(IB + path, headers={"Authorization": "Bearer " + KEY, "User-Agent": "retry-fixture-live/1"})
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


steps = sorted(rec["messages_by_step"])
queries = [("full subject of step %s" % s, "rf-live %s step-%s" % (RUN, s)) for s in steps]
queries += [("'rf-live'", "rf-live"), ("the run id", RUN), ("'step'", "step"), ("'step-A'", "step-A"),
            ("'live ' + run id", "live " + RUN)]
out = {"run": RUN, "reads": []}
for label, q in queries:
    st, j = get("/messages?limit=100&subject=" + urllib.parse.quote(q, safe=""))
    ms = j.get("messages") or []
    out["reads"].append({"t": now(), "filter": label, "status": st, "count": j.get("count"),
                         "run_messages_returned": sum(1 for m in ms if RUN in (m.get("subject") or ""))})
st, j = get("/messages?limit=100")
out["reads"].append({"t": now(), "filter": "none (unfiltered list)", "status": st, "count": j.get("count"),
                     "run_messages_returned": sum(1 for m in (j.get("messages") or []) if RUN in (m.get("subject") or ""))})
for r in out["reads"]:
    print("%s  %-26s -> %s, run messages returned: %s" % (r["t"], r["filter"], r["status"], r["run_messages_returned"]))
txt = json.dumps(out, indent=1)
if KEY in txt or INBOX in txt:
    sys.exit("secret or inbox in output; not written")
open(sys.argv[2], "w").write(txt + "\n")
