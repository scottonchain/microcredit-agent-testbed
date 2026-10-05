#!/usr/bin/env python3
"""Re-derive the retry fixture's chain cases (chain-1..7) from Base Sepolia, using only JSON-RPC and the Python standard library.

    python3 verify_live_run.py [EVIDENCE.json] [--rpc URL]

EVIDENCE.json lists the transactions of one live run (hashes, blocks, the signed nonces). Nothing in it is trusted: every
receipt, input, log, nonce and loan state is read again from the chain; the file only says where to look. Needs no key.
Exit 0 = no FAIL. SKIP = the RPC would not serve the historical state the check needs (public nodes prune); rerun against an
archive node to turn SKIPs into PASS/FAIL.
"""
import json, sys, urllib.request

RPC = "https://sepolia.base.org"
UA = "retry-fixture verify_live_run.py"
SEL_REPAY = "0x1d169fa9"       # repayLoanMeta((address,uint256,uint256,uint256,uint256),bytes,(uint256,uint256,uint8,bytes32,bytes32))
SEL_BORROW = "0x0d29380a"      # borrowAndDisburseMeta((address,uint256,address,uint256,uint256,uint256,uint256),bytes)
SEL_FORWARD = "0x6fadcf72"     # forward(address,bytes)
SEL_BATCH = "0xb9d096b2"       # batch(address,bytes[])
SEL_NONCES = "0x7ecebe00"      # nonces(address)
SEL_GETLOAN = "0x504006ca"     # getLoan(uint256) -> (principal, outstanding, borrower, interestRate, isActive)
SEL_BALANCE = "0x70a08231"     # balanceOf(address)
TOPIC_META_REPAID = "0x6a98ca468ea5d9147722dfafae51433ca117e982700440582a1b3d3aebffc16e"   # MetaLoanRepaid(address,uint256,uint256)
TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"       # Transfer(address,address,uint256)

results = []


def check(case, name, ok, detail=""):
    results.append((case, name, "PASS" if ok else "FAIL", detail))


def skip(case, name, detail):
    results.append((case, name, "SKIP", detail))


def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    r = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    if "error" in r:
        raise RuntimeError(json.dumps(r["error"]))
    return r["result"]


def word(args_hex, i):
    return args_hex[64 * i:64 * (i + 1)]


def uint(w):
    return int(w, 16)


def addr(w):
    return "0x" + w[-40:]


def dyn_bytes(args_hex, offset_bytes):
    o = offset_bytes * 2
    n = uint(args_hex[o:o + 64])
    return "0x" + args_hex[o + 64:o + 64 + 2 * n]


def decode_repay(input_hex):
    assert input_hex[:10].lower() == SEL_REPAY, "not repayLoanMeta: " + input_hex[:10]
    a = input_hex[10:]
    req = {"borrower": addr(word(a, 0)), "loanId": uint(word(a, 1)), "amount": uint(word(a, 2)), "nonce": uint(word(a, 3)), "deadline": uint(word(a, 4))}
    sig = dyn_bytes(a, uint(word(a, 5)))
    permit = {"value": uint(word(a, 6)), "deadline": uint(word(a, 7)), "v": uint(word(a, 8)), "r": "0x" + word(a, 9), "s": "0x" + word(a, 10)}
    return req, sig, permit


def decode_borrow(input_hex):
    assert input_hex[:10].lower() == SEL_BORROW, "not borrowAndDisburseMeta: " + input_hex[:10]
    a = input_hex[10:]
    return {"borrower": addr(word(a, 0)), "amount": uint(word(a, 1)), "to": addr(word(a, 2)), "repaymentPeriod": uint(word(a, 3)),
            "maxAprBps": uint(word(a, 4)), "nonce": uint(word(a, 5)), "deadline": uint(word(a, 6))}, dyn_bytes(a, uint(word(a, 7)))


def decode_forward(input_hex):
    assert input_hex[:10].lower() == SEL_FORWARD, "not forward: " + input_hex[:10]
    a = input_hex[10:]
    return addr(word(a, 0)), dyn_bytes(a, uint(word(a, 1)))


def decode_batch(input_hex):
    assert input_hex[:10].lower() == SEL_BATCH, "not batch: " + input_hex[:10]
    a = input_hex[10:]
    target = addr(word(a, 0))
    arr = uint(word(a, 1)) * 2
    n = uint(a[arr:arr + 64])
    base = arr + 64
    calls = []
    for i in range(n):
        rel = uint(a[base + 64 * i:base + 64 * (i + 1)]) * 2
        ln = uint(a[base + rel:base + rel + 64])
        calls.append("0x" + a[base + rel + 64:base + rel + 64 + 2 * ln])
    return target, calls


def call(to, data, block):
    try:
        return rpc("eth_call", [{"to": to, "data": data}, hex(block) if isinstance(block, int) else block])
    except RuntimeError as e:
        raise HistoricalUnavailable(str(e))


class HistoricalUnavailable(Exception):
    pass


def pad_addr(a):
    return a[2:].lower().rjust(64, "0")


def nonces(pool, who, block):
    return uint(call(pool, SEL_NONCES + pad_addr(who), block)[2:])


def balance(token, who, block):
    return uint(call(token, SEL_BALANCE + pad_addr(who), block)[2:])


def get_loan(pool, loan_id, block):
    r = call(pool, SEL_GETLOAN + hex(loan_id)[2:].rjust(64, "0"), block)[2:]
    return {"principal": uint(word(r, 0)), "outstanding": uint(word(r, 1)), "borrower": addr(word(r, 2)), "rate_bps": uint(word(r, 3)), "is_active": uint(word(r, 4)) == 1}


def revert_reason(tx, block_before):
    """Replays the tx's call at the state of the block before it. Returns (decoded Error(string) or raw data, None) or (None, why)."""
    try:
        rpc("eth_call", [{"from": tx["from"], "to": tx["to"], "data": tx["input"], "gas": hex(500000)}, hex(block_before)])
        return None, "call did not revert at block %d" % block_before
    except RuntimeError as e:
        msg = str(e)
        if "block not found" in msg or "missing trie node" in msg or "header not found" in msg:
            return None, "historical state unavailable: " + msg[:80]
        i = msg.find("0x08c379a0")
        if i >= 0:
            data = msg[i:].split('"')[0]
            a = data[10:]
            n = uint(a[64:128])
            return bytes.fromhex(a[128:128 + 2 * n]).decode(errors="replace"), None
        return msg[:160], None


def meta_repaid_logs(receipt, pool):
    return [l for l in receipt["logs"] if l["address"].lower() == pool.lower() and l["topics"] and l["topics"][0].lower() == TOPIC_META_REPAID]


def main():
    global RPC
    args = sys.argv[1:]
    if "--rpc" in args:
        i = args.index("--rpc"); RPC = args[i + 1]; del args[i:i + 2]
    path = args[0] if args else "EVIDENCE.json"
    ev = json.load(open(path))
    pool, usdc = ev["contracts"]["pool"], ev["contracts"]["usdc"]
    borrower, relayer = ev["actors"]["borrower"], ev["actors"]["relayer_and_owner"]
    S = ev["steps"]
    print("verify_live_run.py | rpc %s | chain id %s | pool %s" % (RPC, uint(rpc("eth_chainId", [])[2:]), pool))
    check("setup", "rpc chain id is Base Sepolia (84532)", uint(rpc("eth_chainId", [])[2:]) == 84532)

    def tx_and_receipt(step):
        s = S[step]
        tx = rpc("eth_getTransactionByHash", [s["tx"]])
        rc = rpc("eth_getTransactionReceipt", [s["tx"]])
        assert tx and rc, "tx or receipt missing for " + step
        check(step, "receipt block matches the record", uint(rc["blockNumber"]) == s["block"], "%d" % uint(rc["blockNumber"]))
        check(step, "tx sent by the relayer address", tx["from"].lower() == relayer.lower(), tx["from"])
        return tx, rc, uint(rc["blockNumber"])

    def nonce_pair(blk):
        try:
            return nonces(pool, borrower, blk - 1), nonces(pool, borrower, blk)
        except HistoricalUnavailable as e:
            return None, str(e)

    # ---- s3: the first repay (chain-1 first submission, chain-3, chain-4, chain-5) ----
    tx3, rc3, b3 = tx_and_receipt("s3_chain1_first_submission")
    req3, sig3, permit3 = decode_repay(tx3["input"])
    check("chain-5", "tx.input decodes as repayLoanMeta: borrower recoverable", req3["borrower"].lower() == borrower.lower(), req3["borrower"])
    check("chain-5", "tx.input decodes as repayLoanMeta: loanId recoverable", req3["loanId"] == S["s2_borrow_loan_a"]["loan_id"], str(req3["loanId"]))
    check("chain-5", "tx.input carries the signed nonce and a 65-byte signature", req3["nonce"] == S["s3_chain1_first_submission"]["signed_nonce"] and len(sig3) == 132, "nonce %d" % req3["nonce"])
    check("chain-1", "first submission: status 1", uint(rc3["status"]) == 1)
    logs3 = meta_repaid_logs(rc3, pool)
    check("chain-3", "exactly one MetaLoanRepaid in the receipt", len(logs3) == 1, "%d" % len(logs3))
    if logs3:
        l = logs3[0]
        check("chain-3", "receipt event names borrower and loanId (indexed) and carries 32 bytes of data (amount only): no nonce, no request digest",
              len(l["topics"]) == 3 and addr(l["topics"][1][2:]).lower() == borrower.lower() and uint(l["topics"][2][2:]) == req3["loanId"] and len(l["data"]) == 66,
              "topics %d, data %d bytes" % (len(l["topics"]), (len(l["data"]) - 2) // 2))
    n_before, n_after = nonce_pair(b3)
    if n_before is None:
        skip("chain-4", "nonces(signer) before/after the landed repay", n_after)
    else:
        check("chain-4", "nonces(signer) at block-1 equals the signed nonce", n_before == req3["nonce"], "%d" % n_before)
        check("chain-4", "nonces(signer) at the receipt block is one past it: the request landed", n_after == req3["nonce"] + 1, "%d" % n_after)
        check("chain-5", "the nonce in the calldata is the one that moved", n_after == req3["nonce"] + 1)
    try:
        lb, la = get_loan(pool, req3["loanId"], b3 - 1), get_loan(pool, req3["loanId"], b3)
        check("chain-4", "loan open with outstanding > 0 before, outstanding 0 and closed after", lb["is_active"] and lb["outstanding"] > 0 and (not la["is_active"]) and la["outstanding"] == 0,
              "before %s after %s" % (lb["outstanding"], la["outstanding"]))
        bb, ba = balance(usdc, borrower, b3 - 1), balance(usdc, borrower, b3)
        xfer = [l for l in rc3["logs"] if l["address"].lower() == usdc.lower() and l["topics"][0].lower() == TOPIC_TRANSFER]
        pulled = sum(uint(l["data"][2:]) for l in xfer if addr(l["topics"][1][2:]).lower() == borrower.lower() and addr(l["topics"][2][2:]).lower() == pool.lower())
        check("chain-1", "the one landed request pulled exactly the balance delta from the borrower", pulled == bb - ba and pulled > 0, "%d" % pulled)
    except HistoricalUnavailable as e:
        skip("chain-4", "loan/balance state around the landed repay", str(e)[:100])

    # ---- s4: chain-1, identical calldata resubmitted ----
    tx4, rc4, b4 = tx_and_receipt("s4_chain1_replay_same_calldata")
    check("chain-1", "replay tx input is byte-identical to the first submission's input", tx4["input"].lower() == tx3["input"].lower())
    check("chain-1", "replay is a different transaction, mined later", tx4["hash"].lower() != tx3["hash"].lower() and b4 > b3, "block %d" % b4)
    check("chain-1", "replay reverted on chain (status 0) and emitted nothing", uint(rc4["status"]) == 0 and len(rc4["logs"]) == 0, "gas used %d" % uint(rc4["gasUsed"]))
    n_before, n_after = nonce_pair(b4)
    if n_before is None:
        skip("chain-1", "nonce unchanged across the replay block", n_after)
    else:
        check("chain-1", "nonce unchanged across the replay block, already one past the replayed request", n_before == n_after == req3["nonce"] + 1, "%d -> %d" % (n_before, n_after))
    try:
        check("chain-1", "borrower balance unchanged across the replay block", balance(usdc, borrower, b4 - 1) == balance(usdc, borrower, b4))
    except HistoricalUnavailable as e:
        skip("chain-1", "borrower balance across the replay block", str(e)[:100])
    reason, why = revert_reason(tx4, b4 - 1)
    if reason is None:
        skip("chain-1", "replayed call's revert reason at the state before the block", why)
    else:
        check("chain-1", "replayed call reverts at the nonce check (this deployment's text: 'Bad nonce')", "nonce" in reason.lower(), repr(reason))

    # ---- s5: chain-2, fresh signature after the landed repay ----
    tx5, rc5, b5 = tx_and_receipt("s5_chain2_fresh_signature_after_landed_repay")
    req5, sig5, permit5 = decode_repay(tx5["input"])
    check("chain-2", "fresh request: same borrower and loanId, next nonce, new signature", req5["borrower"].lower() == borrower.lower() and req5["loanId"] == req3["loanId"]
          and req5["nonce"] == req3["nonce"] + 1 and sig5.lower() != sig3.lower(), "nonce %d" % req5["nonce"])
    check("chain-2", "a permit with value >= the former outstanding was supplied (a pull could have succeeded)", permit5["value"] >= 40_000_000 and permit5["deadline"] > 0, "%d" % permit5["value"])
    check("chain-2", "reverted on chain (status 0), emitted nothing", uint(rc5["status"]) == 0 and len(rc5["logs"]) == 0, "gas used %d" % uint(rc5["gasUsed"]))
    n_before, n_after = nonce_pair(b5)
    if n_before is None:
        skip("chain-2", "nonce unchanged across the block", n_after)
    else:
        check("chain-2", "nonce not consumed by the reverted fresh request", n_before == n_after == req5["nonce"], "%d -> %d" % (n_before, n_after))
    try:
        check("chain-2", "borrower balance unchanged: nothing pulled", balance(usdc, borrower, b5 - 1) == balance(usdc, borrower, b5))
    except HistoricalUnavailable as e:
        skip("chain-2", "borrower balance across the block", str(e)[:100])
    reason, why = revert_reason(tx5, b5 - 1)
    if reason is None:
        skip("chain-2", "revert reason at the state before the block", why)
    else:
        check("chain-2", "reverts because the loan is no longer active (this deployment's text: 'Loan inactive')", "inactive" in reason.lower() or "active" in reason.lower(), repr(reason))

    # ---- s8: chain-6, through a wrapper ----
    tx8, rc8, b8 = tx_and_receipt("s8_chain6_repay_through_wrapper")
    wrapper = S["s6_deploy_wrapper"]["contract_address"]
    check("chain-6", "tx.to is the wrapper, not the pool", tx8["to"].lower() == wrapper.lower(), tx8["to"])
    check("chain-6", "top-level selector is the wrapper's, not repayLoanMeta's", tx8["input"][:10].lower() == SEL_FORWARD and tx8["input"][:10].lower() != SEL_REPAY, tx8["input"][:10])
    target, inner = decode_forward(tx8["input"])
    req8, _, _ = decode_repay(inner)
    check("chain-6", "one level down the inner call is repayLoanMeta to the pool for this borrower", target.lower() == pool.lower() and inner[:10].lower() == SEL_REPAY and req8["borrower"].lower() == borrower.lower(),
          "loanId %d nonce %d" % (req8["loanId"], req8["nonce"]))
    check("chain-6", "status 1 and MetaLoanRepaid emitted by the pool", uint(rc8["status"]) == 1 and len(meta_repaid_logs(rc8, pool)) == 1)
    n_before, n_after = nonce_pair(b8)
    if n_before is None:
        skip("chain-6", "nonce check across the wrapped tx", n_after)
    else:
        check("chain-6", "nonces(signer) still shows the request landed: [n, n+1) with n the inner call's nonce", n_before == req8["nonce"] and n_after == req8["nonce"] + 1, "%d -> %d" % (n_before, n_after))

    # ---- s11: chain-7a, envelope with one expired intent ----
    tx11, rc11, b11 = tx_and_receipt("s11_chain7a_envelope_with_expired_intent")
    envelope = S["s9_deploy_swallowing_batch"]["contract_address"]
    check("chain-7", "7a: tx.to is the envelope", tx11["to"].lower() == envelope.lower())
    t11, calls11 = decode_batch(tx11["input"])
    r11, _, _ = decode_repay(calls11[0])
    ts11 = uint(rpc("eth_getBlockByNumber", [hex(b11), False])["timestamp"])
    check("chain-7", "7a: one wrapped repayLoanMeta whose deadline is before the block timestamp (expired)", t11.lower() == pool.lower() and len(calls11) == 1 and r11["deadline"] < ts11,
          "deadline %d, block time %d" % (r11["deadline"], ts11))
    check("chain-7", "7a: the envelope tx succeeded (status 1) and the pool emitted no MetaLoanRepaid", uint(rc11["status"]) == 1 and len(meta_repaid_logs(rc11, pool)) == 0, "logs %d" % len(rc11["logs"]))
    n_before, n_after = nonce_pair(b11)
    if n_before is None:
        skip("chain-7", "7a: nonce across the envelope block", n_after)
    else:
        check("chain-7", "7a: nonces(signer) unchanged: the wrapped intent did not land, only the nonce says so", n_before == n_after == r11["nonce"], "%d -> %d" % (n_before, n_after))
    try:
        la = get_loan(pool, r11["loanId"], b11)
        check("chain-7", "7a: loan still open and owed after the successful envelope tx", la["is_active"] and la["outstanding"] > 0, "%s" % la["outstanding"])
    except HistoricalUnavailable as e:
        skip("chain-7", "7a: loan state after the envelope", str(e)[:100])

    # ---- s12: chain-7b, two intents, one lands ----
    tx12, rc12, b12 = tx_and_receipt("s12_chain7b_two_intents_one_lands")
    t12, calls12 = decode_batch(tx12["input"])
    reqs = [decode_repay(c)[0] for c in calls12]
    ts12 = uint(rpc("eth_getBlockByNumber", [hex(b12), False])["timestamp"])
    check("chain-7", "7b: two wrapped intents of one signer with consecutive nonces, the second expired", t12.lower() == pool.lower() and len(reqs) == 2 and reqs[1]["nonce"] == reqs[0]["nonce"] + 1
          and reqs[0]["deadline"] >= ts12 and reqs[1]["deadline"] < ts12, "nonces %d,%d" % (reqs[0]["nonce"], reqs[1]["nonce"]))
    check("chain-7", "7b: envelope status 1 with exactly one MetaLoanRepaid", uint(rc12["status"]) == 1 and len(meta_repaid_logs(rc12, pool)) == 1)
    n_before, n_after = nonce_pair(b12)
    if n_before is None:
        skip("chain-7", "7b: consumed nonce range", n_after)
    else:
        check("chain-7", "7b: exactly one nonce consumed; the range [n, n+1) names intent 0 (nonce n) as the one that landed", n_before == reqs[0]["nonce"] and n_after == reqs[0]["nonce"] + 1, "%d -> %d" % (n_before, n_after))
    try:
        la = get_loan(pool, reqs[0]["loanId"], b12)
        check("chain-7", "7b: the landed intent closed the loan", (not la["is_active"]) and la["outstanding"] == 0)
    except HistoricalUnavailable as e:
        skip("chain-7", "7b: loan state after the envelope", str(e)[:100])

    # ---- the borrower never sent a transaction (everything was relayed) ----
    check("setup", "borrower address has sent no transaction of its own", uint(rpc("eth_getTransactionCount", [borrower, "latest"])[2:]) == 0)

    fails = sum(1 for r in results if r[2] == "FAIL")
    skips = sum(1 for r in results if r[2] == "SKIP")
    for case, name, st, detail in results:
        print("%-5s %-8s %s%s" % (st, case, name, (" | " + detail) if detail else ""))
    print("%d checks, %d failed, %d skipped" % (len(results), fails, skips))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
