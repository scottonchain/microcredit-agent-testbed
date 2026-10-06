#!/usr/bin/env python3
"""Live check of a provider-held idempotency key on AgentMail (retry-fixture email-14).

Sends ONLY from your own inbox to that same inbox; no other recipient.
Environment: AGENTMAIL_API_KEY (bearer key), AGENTMAIL_INBOX (inbox id, e.g. name@agentmail.to).
Usage: python3 agentmail_live_check.py OUT.json
Prints one line per send request and a summary computed from the recorded responses; writes every request and
response (status, body, response headers except cookies, client-side UTC timestamps) to OUT.json with the inbox id
replaced by "<inbox>" (partial record if the run stops early). Stdlib only (CPython 3.9+). At most 16 send requests.

Documented behaviour under test (https://docs.agentmail.to/idempotency): a send carrying an Idempotency-Key header is
sent once; a retry with the same key returns the original message_id and thread_id and sends no second email; the same
key with a different request returns 409; an explicitly empty key returns 400; keys expire 24 h after the send.

Steps (each with its own subject tagged with the run id; keys are fresh UUIDs):
  A  keyed send, response read; then the identical request with the same key
  B  the key of A with a different subject
  C  an explicitly empty Idempotency-Key header
  D  keyed send; the client gives up (read timeout = half the server time A1 took, floor 50 ms) and closes the
     connection without a response (email-14's setup: accepted or not, the client cannot tell); 5 s later the
     identical request with the same key
  E  the same client timeout without a key, then the identical request without a key (the no-key control)
  F  three trials: two identical requests with one key, released together on two open connections
     (a retry that arrives while the first request may still be executing)
  L  read paths after a send (A1, then two more keyed sends L2, L3): poll about every 1.5 s for 30 s
     GET message by id, the unfiltered list, and the subject-filtered list (served by search per the List
     Messages reference); record when each first returns the message, and the response keys and header names
  Z  settle 20 s, then count the run's messages per step in the unfiltered list
"""
import datetime as dt
import http.client
import json
import os
import socket
import sys
import threading
import time
import urllib.parse
import uuid

HOST = "api.agentmail.to"
KEY = os.environ["AGENTMAIL_API_KEY"]
INBOX = os.environ["AGENTMAIL_INBOX"]
OUT = sys.argv[1]
RUN = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
IB = "/v0/inboxes/" + urllib.parse.quote(INBOX, safe="")
SEND = IB + "/messages/send"
MAX_SENDS = 16
REC, PROBES, SENDS = [], [], [0]
LOCK = threading.Lock()
STATE = {"summary": None, "messages_by_step": None, "stopped": None}


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def subj(step):
    return "rf-live %s step-%s" % (RUN, step)


def body_for(step, subject=None):
    return {"to": [INBOX], "subject": subject or subj(step),
            "text": "retry-fixture live check, run %s, step %s. Self-addressed test message from an AI agent's own "
                    "inbox; nothing to answer." % (RUN, step)}


def headers(idem, has_body):
    h = {"Authorization": "Bearer " + KEY, "User-Agent": "retry-fixture-live/1", "Accept": "application/json"}
    if has_body:
        h["Content-Type"] = "application/json"
    if idem is not None:
        h["Idempotency-Key"] = idem
    return h


def parse(raw):
    try:
        return json.loads(raw.decode("utf-8") or "null")
    except Exception:
        return {"_raw": raw[:400].decode("utf-8", "replace")}


def call(step, method, path, body=None, idem=None, client_timeout=None, conn=None, record=True):
    """One request. client_timeout=None: read the response. client_timeout=x: after writing the request, wait at most
    x seconds for the response, then close the connection (the client gave up)."""
    if method == "POST" and path == SEND:
        with LOCK:
            if SENDS[0] >= MAX_SENDS:
                raise SystemExit("send budget exhausted")
            SENDS[0] += 1
    rec = {"step": step, "method": method, "path": path, "idempotency_key": idem, "body": body}
    c = conn or http.client.HTTPSConnection(HOST, timeout=60)
    data = json.dumps(body).encode() if body is not None else None
    t_send = time.time()
    rec["t_sent"] = iso(t_send)
    try:
        c.request(method, path, body=data, headers=headers(idem, body is not None))
        t_written = time.time()
        rec["t_written"] = iso(t_written)
        if client_timeout is not None:
            c.sock.settimeout(client_timeout)
        r = c.getresponse()
        raw = r.read()
        t_resp = time.time()
        rec.update({"status": r.status, "response": parse(raw),
                    "headers": {k.lower(): v for k, v in r.getheaders() if "cookie" not in k.lower()},
                    "t_response": iso(t_resp), "latency_ms": round((t_resp - t_send) * 1000),
                    "server_ms": round((t_resp - t_written) * 1000), "_t": t_resp})
        if client_timeout is not None:
            rec["client"] = "response arrived within the client timeout of %d ms (not an unknown outcome)" % round(client_timeout * 1000)
        if r.status == 429:
            time.sleep(float(rec["headers"].get("retry-after", "2") or 2))
    except (socket.timeout, TimeoutError):
        rec.update({"client": "gave up after %d ms without a response and closed the connection" % round((client_timeout or 60) * 1000),
                    "t_closed": iso(time.time()), "_t": time.time()})
    except Exception as e:
        rec.update({"error": "%s: %s" % (type(e).__name__, str(e)[:200]), "_t": time.time()})
    finally:
        try:
            c.close()
        except Exception:
            pass
    if record:
        with LOCK:
            REC.append(rec)
    if method == "POST":
        print("%-5s POST key=%-5s -> %s %s" % (step, "none" if idem is None else ("''" if idem == "" else "set"),
              rec.get("status", rec.get("client") or rec.get("error")), json.dumps(rec.get("response", ""))[:140]), flush=True)
    return rec


def mid(rec):
    return rec.get("response").get("message_id") if isinstance(rec.get("response"), dict) else None


def code(rec):
    return rec.get("response").get("code") if isinstance(rec.get("response"), dict) else None


def probe(sample, rec, subject, deadline=30.0):
    """Poll three read paths until each returns the message sent in `rec`; times are seconds after its response."""
    m = mid(rec)
    t0 = rec["_t"]
    first = {"get_by_id": None, "list": None, "list_subject": None}
    paths = {"get_by_id": IB + "/messages/" + urllib.parse.quote(m or "", safe=""),
             "list": IB + "/messages?limit=20",
             "list_subject": IB + "/messages?limit=20&subject=" + urllib.parse.quote(subject, safe="")}
    n = 0
    while m and None in first.values() and time.time() - t0 < deadline:
        n += 1
        for name in first:
            if first[name] is not None:
                continue
            r = call("%s-%s" % (sample, name), "GET", paths[name], record=False)
            st = r.get("status")
            j = r.get("response") if isinstance(r.get("response"), dict) else {}
            if name == "get_by_id":
                hit = st == 200 and j.get("message_id") == m
                labels = j.get("labels") if hit else None
            else:
                hits = [x for x in (j.get("messages") or []) if x.get("message_id") == m]
                hit = bool(hits)
                labels = hits[0].get("labels") if hits else None
            el = round(r["_t"] - t0, 2)
            PROBES.append({"sample": sample, "path": name, "poll": n, "elapsed_s": el, "status": st, "found": hit,
                           "labels": labels, "response_keys": sorted(j.keys()) if isinstance(j, dict) else None,
                           "response_headers": sorted(r.get("headers", {}).keys()), "error": r.get("error")})
            if hit:
                first[name] = el
        time.sleep(1.5)
    misses = {k: sum(1 for p in PROBES if p["sample"] == sample and p["path"] == k and not p["found"]) for k in first}
    print("%-5s read paths, first seen (s after the send's response): %s | reads that missed it first: %s" % (sample, first, misses), flush=True)
    return {"sample": sample, "message_id": m, "first_seen_s": first, "misses_before_first_seen": misses, "polls": n}


def list_all():
    items, tok = [], None
    for _ in range(10):
        p = IB + "/messages?limit=100" + ("&page_token=" + urllib.parse.quote(tok, safe="") if tok else "")
        r = call("Z-list", "GET", p, record=False)
        j = r.get("response") if isinstance(r.get("response"), dict) else {}
        items += j.get("messages") or []
        tok = j.get("next_page_token")
        if not tok:
            break
    return items


def run():
    print("run", RUN, flush=True)
    pre = call("pre", "GET", IB)
    if pre.get("status") != 200:
        STATE["stopped"] = "inbox not readable: %s" % pre.get("status")
        return
    lags = []
    kA = str(uuid.uuid4())
    a1 = call("A1", "POST", SEND, body_for("A"), idem=kA)
    if a1.get("status") != 200 or not mid(a1):
        STATE["stopped"] = "A1 did not return 200 with a message_id; stopped after one send request"
        return
    lags.append(probe("A1", a1, subj("A")))
    a2 = call("A2", "POST", SEND, body_for("A"), idem=kA)
    b = call("B", "POST", SEND, body_for("B"), idem=kA)
    c = call("C", "POST", SEND, body_for("C"), idem="")
    ct = min(5.0, max(0.05, a1["server_ms"] / 2000.0))
    kD = str(uuid.uuid4())
    d1 = call("D1", "POST", SEND, body_for("D"), idem=kD, client_timeout=ct)
    time.sleep(5)
    d2 = call("D2", "POST", SEND, body_for("D"), idem=kD)
    e1 = call("E1", "POST", SEND, body_for("E"), client_timeout=ct)
    time.sleep(5)
    e2 = call("E2", "POST", SEND, body_for("E"))
    trials = []
    for i in (1, 2, 3):
        k = str(uuid.uuid4())
        conns = [http.client.HTTPSConnection(HOST, timeout=60) for _ in range(2)]
        for cn in conns:
            cn.connect()
        bar = threading.Barrier(2)
        res = [None, None]

        def worker(j, k=k, i=i, conns=conns, bar=bar, res=res):
            bar.wait()
            res[j] = call("F%d%s" % (i, "ab"[j]), "POST", SEND, body_for("F%d" % i), idem=k, conn=conns[j])

        ths = [threading.Thread(target=worker, args=(j,)) for j in range(2)]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        trials.append({"trial": i, "status": [r.get("status") for r in res], "code": [code(r) for r in res],
                       "message_id": [mid(r) for r in res], "t_sent": [r.get("t_sent") for r in res],
                       "latency_ms": [r.get("latency_ms") for r in res], "error": [r.get("error") for r in res]})
        time.sleep(2)
    for s in ("L2", "L3"):
        r = call(s, "POST", SEND, body_for(s), idem=str(uuid.uuid4()))
        lags.append(probe(s, r, subj(s)))
    time.sleep(20)
    items = [x for x in list_all() if RUN in (x.get("subject") or "")]
    by = {}
    for x in items:
        step = (x.get("subject") or "").rsplit("step-", 1)[-1]
        by.setdefault(step, []).append({"message_id": x.get("message_id"), "thread_id": x.get("thread_id"),
                                        "timestamp": x.get("timestamp"), "created_at": x.get("created_at"),
                                        "labels": x.get("labels")})
    STATE["messages_by_step"] = by

    def sent_items(step):
        return [v for v in by.get(step, []) if "sent" in (v["labels"] or [])]

    def counts(step):
        vs = by.get(step, [])
        return {"items": len(vs), "labelled_sent": sum(1 for v in vs if "sent" in (v["labels"] or [])),
                "labelled_received": sum(1 for v in vs if "received" in (v["labels"] or []))}

    def sent_view(step):
        return [{"message_id": v["message_id"], "timestamp": v["timestamp"], "created_at": v["created_at"]} for v in sent_items(step)]

    STATE["summary"] = {
        "run": RUN,
        "A_retry_same_key": {"first": a1.get("status"), "retry": a2.get("status"),
                             "same_message_id": mid(a1) == mid(a2), "sent_messages": len(sent_items("A"))},
        "B_same_key_other_subject": {"status": b.get("status"), "code": code(b), "sent_messages": len(sent_items("B"))},
        "C_empty_key": {"status": c.get("status"), "code": code(c), "sent_messages": len(sent_items("C"))},
        "client_timeout_ms": round(ct * 1000),
        "D_client_timeout_then_same_key": {"first": d1.get("status", d1.get("client") or d1.get("error")),
                                           "retry": d2.get("status"), "retry_message_id": mid(d2),
                                           "sent_messages": len(sent_items("D")), "sent": sent_view("D"),
                                           "first_written_at": d1.get("t_written"), "retry_written_at": d2.get("t_written")},
        "E_client_timeout_then_no_key": {"first": e1.get("status", e1.get("client") or e1.get("error")),
                                         "retry": e2.get("status"), "retry_message_id": mid(e2),
                                         "sent_messages": len(sent_items("E")), "sent": sent_view("E"),
                                         "first_written_at": e1.get("t_written"), "retry_written_at": e2.get("t_written")},
        "F_concurrent_same_key": [dict(t, sent_messages=len(sent_items("F%d" % t["trial"]))) for t in trials],
        "L_read_paths": lags,
        "Z_counts_by_step": {k: counts(k) for k in sorted(by)},
        "list_response_keys_seen": sorted({k for p in PROBES if p["path"] != "get_by_id" for k in (p["response_keys"] or [])}),
        "list_response_header_names_seen": sorted({k for p in PROBES if p["path"] != "get_by_id" for k in p["response_headers"]}),
        "send_requests": SENDS[0],
    }
    print(json.dumps(STATE["summary"], indent=1), flush=True)


def main():
    try:
        run()
    except BaseException as e:
        STATE["stopped"] = "%s: %s" % (type(e).__name__, str(e)[:300])
        print("STOPPED:", STATE["stopped"], flush=True)
    finally:
        for r in REC:
            r.pop("_t", None)
        doc = {"what": "retry-fixture email-14 live check on AgentMail; see agentmail_live_check.py", "run": RUN,
               "stopped": STATE["stopped"], "send_requests": SENDS[0], "summary": STATE["summary"],
               "requests": REC, "probes": PROBES, "messages_by_step": STATE["messages_by_step"]}
        txt = json.dumps(doc, indent=1, ensure_ascii=False).replace(INBOX, "<inbox>").replace(urllib.parse.quote(INBOX, safe=""), "<inbox>")
        if KEY in txt:
            print("api key found in output; not written", flush=True)
            sys.exit(2)
        with open(OUT, "w") as f:
            f.write(txt + "\n")
    sys.exit(0 if STATE["summary"] else 1)


if __name__ == "__main__":
    main()
