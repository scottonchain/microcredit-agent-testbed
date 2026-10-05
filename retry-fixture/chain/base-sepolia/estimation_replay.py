#!/usr/bin/env python3
"""Replays, read-only, the two calls whose gas estimation failed once during the live-pool run, at every canonical block between the
score-override step and the call's own block, and writes ESTIMATION_REPLAY_live_pool.txt. Rate-limited politely (public RPC).
    python3 estimation_replay.py [EVIDENCE_live_pool.json]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib
HERE = os.path.dirname(os.path.abspath(__file__))
EV = sys.argv[1] if len(sys.argv) > 1 else "EVIDENCE_live_pool.json"
ev = json.load(open(os.path.join(HERE, EV)))
S = ev["steps"]
lines = ["Replay of the two calls whose eth_estimateGas failed once during the run (read-only eth_call at historical blocks, 600000 gas,",
         "from the relayer address). Written by estimation_replay.py on %s." % time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), ""]
# the error texts as the sending script journaled them (from the intent journal; no key material in them)
J = os.path.join(HERE, "JOURNAL.jsonl")
if os.path.exists(J):
    for e in (json.loads(l) for l in open(J)):
        if e.get("state") == "estimate_gas_failed":
            lines.append("journal %s: %s" % (e.get("t"), (e.get("text") or "")[:200].replace("\n", " ")))
    lines.append("")


def replay(step, to, block):
    for attempt in range(6):
        try:
            r = lib.rpc("eth_call", [{"from": lib.DEPLOYER, "to": to, "data": S[step]["calldata"], "gas": hex(600000)}, hex(block)])
            break
        except Exception as ex:   # HTTP 429 from the public RPC: back off
            time.sleep(4 * (attempt + 1))
    else:
        return "rpc unavailable"
    e = r.get("error")
    if not e:
        return "ok (no revert)"
    d = (e.get("data") or "")
    name = {"0x756688fe": "InvalidNonce()", "0x082f7846": "LoanNotActive()", "0x0819bdcd": "SignatureExpired()"}.get(d[:10], d[:10])
    return "revert %s | %s" % (name, (e.get("message") or "")[:70])


s3 = S["s3_chain1_first_submission"]
lines.append("s3 (first repay, tx %s, landed at block %d; signed nonce %d; loan %d borrowed at block %d):" % (s3["tx"], s3["block"], s3["signed_nonce"], s3["loan_id"], S["s2_borrow_loan_a"]["block"]))
for b in range(S["s0_score_override"]["block"] - 1, s3["block"]):
    lines.append("  block %d: %s" % (b, replay("s3_chain1_first_submission", lib.POOL, b)))
    time.sleep(1.5)
s8 = S["s8_chain6_repay_through_wrapper"]
w = S["s6_deploy_wrapper"]["contract_address"]
lines.append("")
lines.append("s8 (repay through the wrapper %s, tx %s, landed at block %d; loan %d borrowed at block %d):" % (w, s8["tx"], s8["block"], s8["loan_id"], S["s7_borrow_loan_b"]["block"]))
for b in range(S["s6_deploy_wrapper"]["block"], s8["block"]):
    lines.append("  block %d: %s" % (b, replay("s8_chain6_repay_through_wrapper", w, b)))
    time.sleep(1.5)
out = "\n".join(lines) + "\n"
open(os.path.join(HERE, "ESTIMATION_REPLAY_live_pool.txt"), "w").write(out)
print(out)
