#!/usr/bin/env python3
"""Read-only: replay each recorded refusal eth_call at explicit historical blocks. Pass 1 log lines carry the same format as pass 2.
For each refusal: (a) the block stored in results.json (the case-start HEAD, which the original call did NOT use: it called 'latest'),
(b) the block of the last tx logged before the refusal line in run.log (the state the original call most plausibly saw; inference, labelled).
Reconstruction time is recorded. No signed bytes, no state change."""
import json, re, subprocess, time, urllib.request
RPC = "https://sepolia.base.org"
CAST = "/root/.foundry/versions/foundry-rs/foundry/v1.8.4/cast"
D = "/root/work/live-sim-20261008"
POOL = "0x73872B8fB7F1771C67911f03edc75aBdc9514973"
UNIT = 1_000_000
ARGS = {  # label -> (role, sig, args-builder)
    "back_onward": ("borrower", "back(address,uint256)", lambda w, n: (w[f"s{n}-other"], UNIT)),
    "overlimit": ("borrower", "requestLoan(uint256)", lambda w, n: (1_010_000,)),
    "colluder_nocredit": ("other", "requestLoan(uint256)", lambda w, n: (UNIT,)),
    "repeat": ("borrower", "requestLoan(uint256)", lambda w, n: (UNIT,)),
    "cut_backing": ("sponsor", "back(address,uint256)", lambda w, n: (w[f"s{n}-borrower"], 0)),
    "closed_history": ("borrower", "requestLoan(uint256)", lambda w, n: (UNIT,)),
}
def kind(label):
    l = label.lower()
    if "onward" in l: return "back_onward"
    if "overlimit" in l: return "overlimit"
    if "colluder" in l: return "colluder_nocredit"
    if "repeat" in l: return "repeat"
    if "cut backing" in l: return "cut_backing"
    if "closed history" in l: return "closed_history"
def rpc_call(frm, data, block):
    r = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"from": frm, "to": POOL, "data": data}, hex(block)]}).encode(),
                               headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
    d = json.load(urllib.request.urlopen(r, timeout=30))
    if "error" in d: return ("revert", d["error"].get("data") or d["error"].get("message"))
    return ("ok", d["result"])
out = {"reconstruction_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "passes": {}}
for name, res, log, wal in (("pass1", "results.json", "run.log", "scenario_wallets_public.json"), ("pass2", "pass2out/results.json", "pass2out/run.log", "pass2out/scenario_wallets_public.json")):
    R = json.load(open(f"{D}/{res}")); W = json.load(open(f"{D}/{wal}"))
    lines = open(f"{D}/{log}").read().splitlines()
    rows = []
    # walk log in order; refusals appear in results in log order
    last_block = None; refl = []
    for ln in lines:
        m = re.search(r" TX .* block (\d+)$", ln)
        if m: last_block = int(m.group(1))
        if " REFUSAL " in ln: refl.append((ln, last_block))
    flat = [(c, r) for c, v in sorted(R["cases"].items()) for r in v.get("refusals", [])]
    assert len(flat) == len(refl), (name, len(flat), len(refl))
    for (cn, r), (ln, lb) in zip(flat, refl):
        k = kind(r["label"]); role, sig, ab = ARGS[k]
        sender = W[f"s{cn}-{role}"]
        data = subprocess.run([CAST, "calldata", sig, *map(str, ab(W, cn))], capture_output=True, text=True).stdout.strip()
        rep = {}
        for tag, b in (("stored_case_start_block", r["block"]), ("last_tx_block_before_log_line", lb)):
            st, rd = rpc_call(sender, data, b)
            rep[tag] = {"block": b, "result": st, "data": rd, "selector_match": (st == "revert" and str(rd).startswith(r["expected_selector"]))}
        rows.append({"case": cn, "label": r["label"], "sender": sender, "call": sig, "calldata": data, "expected_selector": r["expected_selector"],
                     "original_observation": {"call_block_tag": "latest (unpinned)", "stored_block_field": r["block"], "revert_data": r["revert_data"], "match": r["match"], "log_line": ln[:60]}, "replay": rep})
    out["passes"][name] = rows
json.dump(out, open(f"{D}/supplement/refusal_replay.json", "w"), indent=1)
for n, rows in out["passes"].items():
    for x in rows:
        print(n, x["case"], x["label"][:50], "|", {k: (v["block"], v["result"], str(v["data"])[:10], v["selector_match"]) for k, v in x["replay"].items()})
