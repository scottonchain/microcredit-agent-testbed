#!/usr/bin/env python3
"""Key-expiry check for retry-fixture email-14 (agentprophet's caveat: keys expire and a retry becomes a new send).
STAGED 2026-10-05, NOT RUN. Run once inside the window printed below; it refuses to send outside it.

AgentMail documents (https://docs.agentmail.to/idempotency, read 2026-10-05): keys "expire 24 hours after the send
completes, after which the key can be reused". Two keys of run 20261005T140846Z-74eabe differ only in later use:
  D's key: sent 2026-10-05 14:09:18Z, replayed 14:09:24Z, not used since.
  A's key: sent 2026-10-05 14:08:47Z, replayed 14:09:18Z, 16:35:55Z and 16:43:55Z (the two follow-ups).
Window: from 24 h + 10 min after D's message was created to 24 h - 10 min after A's last use (about
2026-10-06 14:19Z .. 16:33Z). Inside it, both keys are older than 24 h counted from their sends, and only A's
was used within the last 24 h. One retry of each, identical to its first request:
  D new send, A replay  -> the 24 h counts from a key's last use (a replay renews it)
  D new send, A new     -> the 24 h counts from the send; a retry after it sends a second message
  D replay,   A replay  -> keys outlive 24 h here (the documented expiry not observed at this age)
  403 / other           -> inconclusive (recorded as is)
Sends only from one inbox to that same inbox. At most 2 send requests (a key that expired sends one message).
Environment: AGENTMAIL_API_KEY, AGENTMAIL_INBOX.
Usage: python3 key_expiry_check.py AGENTMAIL_LIVE.json EXACT_BODY_CONTROL.json OUT.json
Record: inbox id -> "<inbox>", organization id -> "<org>", routing headers dropped. Stdlib only (CPython 3.9+).
"""
import datetime as dt
import http.client
import json
import os
import sys
import time
import urllib.parse

HOST = "api.agentmail.to"
KEY = os.environ["AGENTMAIL_API_KEY"]
INBOX = os.environ["AGENTMAIL_INBOX"]
REC_IN, LAST_USE_IN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
IB = "/v0/inboxes/" + urllib.parse.quote(INBOX, safe="")
SEND = IB + "/messages/send"
ROUTING = ("x-amz-cf-id", "x-amz-cf-pop", "via", "apigw-requestid")
REC, SENDS, ORG = [], [0], []
src = json.load(open(REC_IN, encoding="utf-8"))
later = json.load(open(LAST_USE_IN, encoding="utf-8"))
P = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
now = lambda: dt.datetime.now(dt.timezone.utc)
iso = lambda: now().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def first(step):
    return [r for r in src["requests"] if r["step"] == step + "1"][0]


A1, D1 = first("A"), first("D")
D_created = P(src["messages_by_step"]["D"][0]["created_at"])
A_last = max(P(r["t_sent"]) for r in src["requests"] + later["requests"] if r.get("idempotency_key") == A1["idempotency_key"])
OPEN, CLOSE = D_created + dt.timedelta(hours=24, minutes=10), A_last + dt.timedelta(hours=24, minutes=-10)


def call(step, method, path, body=None, idem=None):
    if method == "POST":
        assert SENDS[0] < 2, "send budget exhausted"
        SENDS[0] += 1
    h = {"Authorization": "Bearer " + KEY, "User-Agent": "retry-fixture-live/1", "Accept": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    if body is not None:
        h["Content-Type"] = "application/json"
    if idem is not None:
        h["Idempotency-Key"] = idem
    rec = {"step": step, "method": method, "path": path, "idempotency_key": idem, "body": body, "t_sent": iso()}
    c = http.client.HTTPSConnection(HOST, timeout=60)
    try:
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        raw = r.read()
        try:
            resp = json.loads(raw.decode("utf-8") or "null")
        except Exception:
            resp = {"_raw": raw[:400].decode("utf-8", "replace")}
        rec.update({"status": r.status, "response": resp, "t_response": iso(),
                    "headers": {k.lower(): v for k, v in r.getheaders() if "cookie" not in k.lower() and k.lower() not in ROUTING}})
    except Exception as e:
        rec.update({"error": "%s: %s" % (type(e).__name__, str(e)[:200]), "t_response": iso()})
    finally:
        c.close()
    REC.append(rec)
    return rec


def listed():
    items, tok = [], None
    for _ in range(10):
        r = call("list", "GET", IB + "/messages?limit=100" + ("&page_token=" + urllib.parse.quote(tok, safe="") if tok else ""))
        j = r.get("response") if isinstance(r.get("response"), dict) else {}
        r["response"] = {"keys": sorted(j.keys()), "count": j.get("count")}
        items += j.get("messages") or []
        tok = j.get("next_page_token")
        if not tok:
            break
    return sorted(({"subject": x.get("subject"), "message_id": x.get("message_id"), "created_at": x.get("created_at")}
                   for x in items if src["run"] in (x.get("subject") or "")), key=lambda v: v["created_at"] or "")


def verdict(rec, original):
    resp = rec.get("response") if isinstance(rec.get("response"), dict) else {}
    if rec.get("status") == 200:
        return "replay" if resp.get("message_id") == original else "new send"
    return "inconclusive: %s %s" % (rec.get("status", rec.get("error")), resp.get("code"))


def main():
    t = now()
    doc = {"what": "key-expiry check; see key_expiry_check.py", "recorded_run": src["run"], "window_open": OPEN.isoformat(),
           "window_close": CLOSE.isoformat(), "started": t.isoformat(), "stopped": None}
    print("window", OPEN.isoformat(), "..", CLOSE.isoformat(), "| now", t.isoformat(), flush=True)
    if not (OPEN <= t <= CLOSE):
        doc["stopped"] = "outside the window; nothing sent"
        return doc
    pre = call("pre", "GET", IB)
    if pre.get("status") != 200:
        doc["stopped"] = "inbox not readable: %s" % pre.get("status")
        return doc
    pr = pre.get("response") or {}
    ORG.extend(v for v in (pr.get("organization_id"), pr.get("pod_id")) if v)
    doc["messages_before"] = listed()
    out = {}
    for step, orig in (("D", D1), ("A", A1)):
        body = json.loads(json.dumps(orig["body"]).replace("<inbox>", INBOX))
        original_id = src["summary"]["D_client_timeout_then_same_key"]["retry_message_id"] if step == "D" else orig["response"]["message_id"]
        r = call("retry-" + step, "POST", SEND, body, idem=orig["idempotency_key"])
        out[step] = verdict(r, original_id)
        print("retry-%s -> %s %s" % (step, r.get("status", r.get("error")), out[step]), flush=True)
        time.sleep(1)
    time.sleep(3)
    doc["messages_after"] = listed()
    doc["verdicts"] = out
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
    print("send requests:", SENDS[0], "| stopped:", d["stopped"], "| verdicts:", d.get("verdicts"))
    sys.exit(0 if not d["stopped"] else 2)
