#!/usr/bin/env python3
"""Exact-body control for same_key_retry.py (retry-fixture email-14 follow-up).

same_key_retry.py's control was a new message of the same template (other subject and text). This script removes
that difference: (1) step A's first keyed request from the recorded run, byte for byte, under a FRESH key (a new send
of exactly that content); (2) the same request with step A's own Idempotency-Key (a retry); (3) the unfiltered message
list before and after (only the recorded run's messages are kept in the record). Whatever (1) returns, (2) runs.
Sends only from one inbox to that same inbox (no other recipient). At most 2 send requests.
Environment: AGENTMAIL_API_KEY (bearer key), AGENTMAIL_INBOX (inbox id).
Usage: python3 exact_body_control.py AGENTMAIL_LIVE.json OUT.json
Writes every request and response (status, body, response headers without routing values, client-side UTC
timestamps) to OUT.json, with the inbox id replaced by "<inbox>" and the organization id by "<org>".
Stdlib only (CPython 3.9+).
"""
import datetime as dt
import http.client
import json
import os
import sys
import time
import urllib.parse
import uuid

HOST = "api.agentmail.to"
KEY = os.environ["AGENTMAIL_API_KEY"]
INBOX = os.environ["AGENTMAIL_INBOX"]
REC_IN, OUT = sys.argv[1], sys.argv[2]
MAX_SENDS = 2
RUN = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
IB = "/v0/inboxes/" + urllib.parse.quote(INBOX, safe="")
SEND = IB + "/messages/send"
ROUTING = ("x-amz-cf-id", "x-amz-cf-pop", "via", "apigw-requestid")
REC, SENDS, ORG = [], [0], []
src = json.load(open(REC_IN, encoding="utf-8"))
SRC_RUN = src["run"]


def iso():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def call(step, method, path, body=None, idem=None, note=None):
    if method == "POST":
        if SENDS[0] >= MAX_SENDS:
            raise SystemExit("send budget exhausted")
        SENDS[0] += 1
    h = {"Authorization": "Bearer " + KEY, "User-Agent": "retry-fixture-live/1", "Accept": "application/json"}
    data = None
    if body is not None:
        h["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if idem is not None:
        h["Idempotency-Key"] = idem
    rec = {"step": step, "method": method, "path": path, "idempotency_key": idem, "body": body, "note": note, "t_sent": iso()}
    c = http.client.HTTPSConnection(HOST, timeout=60)
    t0 = time.time()
    try:
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        try:
            resp = json.loads(raw.decode("utf-8") or "null")
        except Exception:
            resp = {"_raw": raw[:400].decode("utf-8", "replace")}
        rec.update({"status": r.status, "response": resp, "t_response": iso(), "latency_ms": round((time.time() - t0) * 1000),
                    "headers": {k.lower(): v for k, v in r.getheaders() if "cookie" not in k.lower() and k.lower() not in ROUTING}})
    except Exception as e:
        rec.update({"error": "%s: %s" % (type(e).__name__, str(e)[:200]), "t_response": iso()})
    finally:
        c.close()
    REC.append(rec)
    if method == "POST":
        resp = rec.get("response") if isinstance(rec.get("response"), dict) else {}
        print("%-14s POST key=%s -> %s %s" % (step, (idem or "none")[:8], rec.get("status", rec.get("error")),
                                            resp.get("message_id") or resp.get("name") or ""), flush=True)
    return rec


def run_messages():
    items, tok = [], None
    for _ in range(10):
        p = IB + "/messages?limit=100" + ("&page_token=" + urllib.parse.quote(tok, safe="") if tok else "")
        r = call("list", "GET", p)
        j = r.get("response") if isinstance(r.get("response"), dict) else {}
        r["response"] = {"keys": sorted(j.keys()), "count": j.get("count")}
        items += j.get("messages") or []
        tok = j.get("next_page_token")
        if not tok:
            break
    return sorted(({"subject": x.get("subject"), "message_id": x.get("message_id"), "created_at": x.get("created_at"),
                    "labels": x.get("labels")} for x in items if SRC_RUN in (x.get("subject") or "")),
                  key=lambda v: v["created_at"] or "")


def main():
    doc = {"what": "exact-body control for a same-key retry; see exact_body_control.py", "run": RUN, "recorded_run": SRC_RUN,
           "stopped": None}
    try:
        pre = call("pre", "GET", IB)
        if pre.get("status") != 200:
            doc["stopped"] = "inbox not readable: %s" % pre.get("status")
            return doc
        pr = pre.get("response") or {}
        ORG.extend(v for v in (pr.get("organization_id"), pr.get("pod_id")) if v)
        doc["messages_before"] = run_messages()
        a1 = [r for r in src["requests"] if r["step"] == "A1"][0]
        body = json.loads(json.dumps(a1["body"]).replace("<inbox>", INBOX))
        call("control-exact", "POST", SEND, body, idem=str(uuid.uuid4()),
             note="identical body to recorded request A1 of run %s, fresh key" % SRC_RUN)
        time.sleep(1)
        call("retry-A", "POST", SEND, body, idem=a1["idempotency_key"],
             note="identical to recorded request A1 of run %s (sent %s, status %s)" % (SRC_RUN, a1["t_sent"], a1.get("status")))
        time.sleep(3)
        doc["messages_after"] = run_messages()
    except BaseException as e:
        doc["stopped"] = "%s: %s" % (type(e).__name__, str(e)[:300])
    return doc


if __name__ == "__main__":
    d = main()
    d["send_requests"] = SENDS[0]
    d["requests"] = REC
    txt = json.dumps(d, indent=1, ensure_ascii=False).replace(INBOX, "<inbox>").replace(urllib.parse.quote(INBOX, safe=""), "<inbox>")
    for o in ORG:
        txt = txt.replace(o, "<org>")
    if KEY in txt:
        sys.exit("api key found in output; not written")
    open(OUT, "w", encoding="utf-8").write(txt + "\n")
    print("send requests:", SENDS[0], "| stopped:", d["stopped"])
    for k in ("messages_before", "messages_after"):
        if k in d:
            print(k, len(d[k]))
    sys.exit(0 if not d["stopped"] else 1)
