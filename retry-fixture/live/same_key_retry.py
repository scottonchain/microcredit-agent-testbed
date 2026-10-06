#!/usr/bin/env python3
"""Same-key retry of a send recorded in live/AGENTMAIL_LIVE.json while the provider is refusing new sends
(retry-fixture email-14 follow-up).

Order: (1) one control send under a fresh key and a new subject (same template as the recorded run). It must be
refused with 403 message_rejected, i.e. new sends of this content are being refused right now; if it is answered
any other way the script stops and makes no retry. (2) For each named step, the identical request (same path, same
body bytes, same Idempotency-Key) as that step's first keyed send in the recorded run. (3) The unfiltered message
list before and after (only the recorded run's and this run's messages are kept in the record).
Sends only from one inbox to that same inbox (no other recipient). At most 3 send requests.
Environment: AGENTMAIL_API_KEY (bearer key), AGENTMAIL_INBOX (inbox id).
Usage: python3 same_key_retry.py AGENTMAIL_LIVE.json OUT.json --steps A
Writes every request and response (status, body, response headers without routing values, client-side UTC
timestamps) to OUT.json, with the inbox id replaced by "<inbox>" and the organization id by "<org>".
Stdlib only (CPython 3.9+).

Documented (https://docs.agentmail.to/idempotency, read 2026-10-05): a retry with the same key returns the original
message_id and thread_id and sends no second email; keys expire 24 hours after the send completes. Not documented:
whether a same-key retry is answered before or after the check that refuses new sends (here the free tier's daily
budget of messages classified as spam, which the recorded run exhausted).
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
STEPS = sys.argv[sys.argv.index("--steps") + 1].split(",")
MAX_SENDS = 3
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
        print("%-8s POST key=%s -> %s %s" % (step, (idem or "none")[:8], rec.get("status", rec.get("error")),
                                          resp.get("message_id") or resp.get("name") or ""), flush=True)
    return rec


def name(rec):
    return rec["response"].get("name") if isinstance(rec.get("response"), dict) else None


def run_messages():
    """Unfiltered list (all pages); keep only the recorded run's and this run's messages (matched by subject)."""
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

    def keep(run):
        return sorted(({"subject": x.get("subject"), "message_id": x.get("message_id"), "created_at": x.get("created_at"),
                        "labels": x.get("labels")} for x in items if run in (x.get("subject") or "")),
                      key=lambda v: v["created_at"] or "")
    return {"recorded_run": keep(SRC_RUN), "this_run": keep(RUN)}


def original(step):
    cands = [r for r in src["requests"] if r.get("method") == "POST" and r.get("idempotency_key")
             and (r["step"] == step or (r["step"].startswith(step) and r["step"][len(step):] in ("1", "2", "a", "b")))]
    assert cands, "no keyed send recorded for step " + step
    assert len({r["idempotency_key"] for r in cands}) == 1 and len({json.dumps(r["body"]) for r in cands}) == 1, step
    return sorted(cands, key=lambda r: r["t_sent"])[0]


def main():
    doc = {"what": "a same-key retry of recorded sends while new sends are refused; see same_key_retry.py", "run": RUN,
           "recorded_run": SRC_RUN, "steps": STEPS, "stopped": None}
    try:
        pre = call("pre", "GET", IB)
        if pre.get("status") != 200:
            doc["stopped"] = "inbox not readable: %s" % pre.get("status")
            return doc
        pr = pre.get("response") or {}
        ORG.extend(v for v in (pr.get("organization_id"), pr.get("pod_id")) if v)
        doc["messages_before"] = run_messages()
        ctl = {"to": [INBOX], "subject": "rf-live %s control" % RUN,
               "text": "retry-fixture live check, run %s, control. Self-addressed test message from an AI agent's own "
                       "inbox; nothing to answer." % RUN}
        c = call("control", "POST", SEND, ctl, idem=str(uuid.uuid4()), note="fresh key, new subject, same template")
        if not (c.get("status") == 403 and name(c) == "MessageRejectedError"):
            doc["stopped"] = "control not refused (%s %s): new sends are not being refused now; no retry made" % (c.get("status"), name(c))
        else:
            for s in STEPS:
                o = original(s)
                body = json.loads(json.dumps(o["body"]).replace("<inbox>", INBOX))
                call("retry-" + s, "POST", SEND, body, idem=o["idempotency_key"],
                     note="identical to recorded request %s of run %s (sent %s, status %s)" % (o["step"], SRC_RUN, o["t_sent"], o.get("status")))
                time.sleep(1)
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
            print(k, {r: len(v) for r, v in d[k].items()})
    sys.exit(0 if not d["stopped"] else 1)
