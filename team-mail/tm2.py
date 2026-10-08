#!/usr/bin/env python3
"""Validate TM2 compact team mail (stdlib only). Usage: tm2.py FILE... [--model world-model/model.json]"""
import json, re, sys

ENV = ("v", "id", "k", "f", "t", "cc", "re", "by", "nd", "tr", "rs", "i")
ITEM = ("w", "op", "st", "o", "oa", "d", "e", "q", "n", "tx", "x")
KINDS = {"req", "inf", "agd", "ans", "acc", "amd", "rej", "ack"}
OPS = {"set", "ask", "ans", "acc", "amd", "rej", "add", "blk", "done", "ref", "note"}
STS = {"pr", "rd", "ip", "bl", "dn", "ca"}
OAS = {"req", "ack", "ex"}
RS = {"at", "ac", "ve", "vi", "an"}
WHO = {"c", "x", "h"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$")
ID = re.compile(r"^([cxh])-\d{8}-[a-z0-9-]{3,40}-r\d+$")
MODEL_ID = re.compile(r"^(action|claim|ev|hyp|question|decision|venue|goal|agent|work|project|edge):[A-Za-z0-9._:-]+$")
REF = re.compile(r"^(gh:(ctr|tb|th|vis|site)#\d+(c\d+)?|sha:(ctr|tb|th|vis|site)@[0-9a-f]{7,40}|https://\S+)$")
MAX_BYTES, MAX_TEXT, MAX_ITEMS, MAX_ASKS = 6144, 500, 8, 5


def _text(path, s, errs):
    if not isinstance(s, str):
        errs.append(f"{path}: not a string")
    elif len(s) > MAX_TEXT:
        errs.append(f"{path}: {len(s)} chars > {MAX_TEXT}")


def _asks(path, v, errs):
    if not isinstance(v, list) or not v:
        errs.append(f"{path}: need non-empty list"); return
    if len(v) > MAX_ASKS:
        errs.append(f"{path}: more than {MAX_ASKS}")
    for n, a in enumerate(v):
        if not (isinstance(a, dict) and set(a) == {"o", "a"} and a["o"] in WHO):
            errs.append(f"{path}[{n}]: need exactly o in c|x|h and a"); continue
        _text(f"{path}[{n}].a", a["a"], errs)


def validate(msg, model_ids=None):
    errs = []
    raw = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
    if not raw.isascii():
        errs.append("non-ASCII character")
    if len(raw.encode()) > MAX_BYTES:
        errs.append(f"{len(raw.encode())} bytes > {MAX_BYTES}")
    if not isinstance(msg, dict):
        return ["not an object"]
    for k in msg:
        if k not in ENV: errs.append(f"unknown key {k}")
    if msg.get("v") != 2: errs.append("v must be 2")
    m = ID.match(str(msg.get("id", "")))
    if not m: errs.append("bad id")
    if msg.get("f") not in WHO: errs.append("bad f")
    elif m and m.group(1) != msg["f"]: errs.append("id letter != f")
    if msg.get("k") not in KINDS: errs.append("bad k")
    for key in ("t", "cc"):
        if key in msg:
            v = msg[key]
            if not (isinstance(v, list) and v and set(v) <= WHO and msg.get("f") not in v):
                errs.append(f"bad {key}")
    if "re" in msg:
        v = msg["re"]; v = v if isinstance(v, list) else [v]
        if not all(isinstance(x, str) and x for x in v): errs.append("bad re")
    if "by" in msg and not ISO.match(str(msg["by"])): errs.append("bad by")
    if "nd" in msg: _asks("nd", msg["nd"], errs)
    if "tr" in msg: _text("tr", msg["tr"], errs)
    if "rs" in msg and msg["rs"] not in RS: errs.append("bad rs")
    items = msg.get("i")
    if not (isinstance(items, list) and 1 <= len(items) <= MAX_ITEMS):
        errs.append(f"i must have 1..{MAX_ITEMS} items"); items = []
    for n, it in enumerate(items):
        p = f"i[{n}]"
        if not isinstance(it, dict): errs.append(f"{p}: not an object"); continue
        for k in it:
            if k not in ITEM: errs.append(f"{p}: unknown key {k}")
        if not it.get("w"): errs.append(f"{p}: w required")
        elif model_ids is not None and MODEL_ID.match(it["w"]) and it["w"] not in model_ids:
            errs.append(f"{p}: w {it['w']} not in model")
        if it.get("op") not in OPS: errs.append(f"{p}: bad op")
        if "st" in it and it["st"] not in STS: errs.append(f"{p}: bad st")
        if "o" in it and it["o"] not in WHO: errs.append(f"{p}: bad o")
        if "oa" in it and it["oa"] not in OAS: errs.append(f"{p}: bad oa")
        if "d" in it and not ISO.match(str(it["d"])): errs.append(f"{p}: bad d")
        if "e" in it:
            if not (isinstance(it["e"], list) and it["e"]): errs.append(f"{p}: bad e")
            else:
                for r in it["e"]:
                    if not (isinstance(r, str) and (MODEL_ID.match(r) or REF.match(r))): errs.append(f"{p}: bad ref {r!r}")
                    elif model_ids is not None and MODEL_ID.match(r) and r not in model_ids: errs.append(f"{p}: ref {r} not in model")
        if "q" in it: _asks(f"{p}.q", it["q"], errs)
        if "n" in it:
            if not (isinstance(it["n"], dict) and it["n"] and all(isinstance(v, str) for v in it["n"].values())):
                errs.append(f"{p}: n must be {{name: string}}")
            else:
                for k, v in it["n"].items(): _text(f"{p}.n.{k}", v, errs)
        if "tx" in it and (type(it["tx"]) is not int or it["tx"] != 1): errs.append(f"{p}: tx must be 1")
        if "x" in it: _text(f"{p}.x", it["x"], errs)
    return errs


def dump(msg):
    return json.dumps(msg, separators=(",", ":"), ensure_ascii=True)


def subject(msg):
    return f"TM2 {msg['k']} {msg['id']}"


def main(argv):
    model_ids = None
    if "--model" in argv:
        i = argv.index("--model")
        m = json.load(open(argv[i + 1])); del argv[i:i + 2]
        model_ids = {x["id"] for k in ("entities", "evidence", "claims", "edges", "hypotheses", "actions", "decisions", "open_questions") for x in m[k]}
    bad = 0
    for f in argv[1:]:
        errs = validate(json.load(open(f)), model_ids)
        print(("OK   " if not errs else "FAIL ") + f)
        for e in errs: print("   ", e)
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
