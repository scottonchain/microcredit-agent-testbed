#!/usr/bin/env python3
"""Settle a relayer's intent journal against Base Sepolia: journal row + nonces(signer), nothing else.

    python3 reconcile_journal.py JOURNAL.jsonl [--pool ADDR] [--rpc URL] [--json]

The journal is the relayer's own append-only record (written by lib.py during the live runs): an `intent` row BEFORE each
broadcast (destination, calldata) and a `broadcast` row AFTER it (tx hash). A relayer that crashed between the two rows, or
that lost the broadcast response, has an intent row and no hash: the fixture's chain-4 / chain-7 expected state says such a row
is settled by the journal plus nonces(signer), and "unknown" is reserved for a nonce consumed on chain with no journal row at all.
The original nonce-only rule over-attributed outcomes; the maintained checker requires receipt attribution and preserves missing evidence as ambiguous. Standard library only, JSON-RPC only, no key. It trusts nothing in the journal: calldata
of a receipted row is compared with the chain's tx input, and every verdict is derived from nonces(signer) read from the chain.

Per signed intent (one journal row may carry several: a batch envelope) it prints one of:
  landed      successful receipt, consumed nonce and a unique matching pool event; a receipt-less row may inherit
              that result only for the identical bytes of an already receipted intent
  not landed  reverted transaction, unconsumed nonce, or a different receipted intent consumed that nonce
  ambiguous   nonce consumption cannot be attributed uniquely to this transaction or to these signed bytes;
              an unreceipted local journal row alone never proves which intent consumed a nonce
  mismatch    destination or calldata contradicts the pool or the chain transaction
  unknown     a consumed nonce with no matching journal row
Rows that carry no signed intent (owner calls, token mint, contract creation, diagnostics) are settled by receipt only and listed.
Exit 0 only if nothing is ambiguous, mismatched or unknown.
"""
import argparse
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chain_read import (SEL_REPAY, SEL_BORROW, SEL_FORWARD, SEL_BATCH, SEL_NONCES,
                        read_rpc, word, uint, addr, decode_repay, decode_borrow, decode_forward, decode_batch, pad_addr)

RPC = "https://sepolia.base.org"
UA = "retry-fixture reconcile_journal.py"


def rpc(method, params):
    return read_rpc(RPC, method, params, UA)


def signed_intents(data, depth=0):
    """Decode bounded wrapper/batch calls without trusting journal byte lengths."""
    if depth > 16:
        raise ValueError("too many nested calldata wrappers")
    sel = (data or "")[:10].lower()
    if sel == SEL_REPAY:
        request, _, _ = decode_repay(data)
        return [("repayLoanMeta", None, request["borrower"], request["nonce"], request["loanId"])]
    if sel == SEL_BORROW:
        request, _ = decode_borrow(data)
        return [("borrowAndDisburseMeta", None, request["borrower"], request["nonce"], None)]
    if sel == SEL_FORWARD:
        target, inner = decode_forward(data)
        return [(kind + " via forward", nested or target, signer, nonce, loan) for kind, nested, signer, nonce, loan in signed_intents(inner, depth + 1)]
    if sel == SEL_BATCH:
        target, calls = decode_batch(data)
        return [(kind + " via batch[%d]" % index, nested or target, signer, nonce, loan)
                for index, inner in enumerate(calls)
                for kind, nested, signer, nonce, loan in signed_intents(inner, depth + 1)]
    return []


def nonces(pool, who, block):
    return uint(rpc("eth_call", [{"to": pool, "data": SEL_NONCES + pad_addr(who)}, hex(block) if isinstance(block, int) else block])[2:])


TOPIC_META_REPAID = "0x6a98ca468ea5d9147722dfafae51433ca117e982700440582a1b3d3aebffc16e"
TOPIC_META_CREATED = "0x0d2754b8bfc76e8643584e766f1b200bb01d13db597e80c9a9321dc4bd6386ed"


def receipt_verdict(intent, peers, receipt, before, after, pool):
    """Whole-block nonce movement alone does not attribute one transaction."""
    kind, target, signer, nonce, loan_id = intent
    if uint(receipt["status"]) == 0:
        return "not landed", "transaction reverted; other transactions in its block cannot make this intent land"
    if not before <= nonce < after:
        return "not landed", "the signed nonce was not consumed in the receipt block"
    topic = TOPIC_META_REPAID if kind.startswith("repayLoanMeta") else TOPIC_META_CREATED
    matching = [log for log in receipt.get("logs", [])
                if log.get("address", "").lower() == pool.lower()
                and len(log.get("topics", [])) == 3
                and log["topics"][0].lower() == topic
                and addr(log["topics"][1][2:]).lower() == signer.lower()
                and (loan_id is None or uint(log["topics"][2]) == loan_id)]
    candidates = [peer for peer in peers if peer[2].lower() == signer.lower()
                  and peer[0].split(" via ")[0] == kind.split(" via ")[0] and peer[4] == loan_id]
    if len(matching) != 1 or len(candidates) != 1:
        return "ambiguous", "nonce consumed but receipt events do not uniquely attribute this intent; trace or request-bound receipt needed"
    return "landed", "successful transaction, unique matching pool event and consumed signed nonce"


def main(argv=None):
    global RPC
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", nargs="?", default=str(Path(__file__).with_name("JOURNAL_live_pool.jsonl")))
    parser.add_argument("--pool", default="0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8", help="historical fixture pool")
    parser.add_argument("--rpc", default=RPC)
    parser.add_argument("--json", action="store_true", help="also write a new .reconciled.json sidecar; existing output is refused")
    args = parser.parse_args(argv)
    RPC = args.rpc
    pool, path = args.pool, args.journal
    pad_addr(pool)
    with open(path, encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("journal rows must be objects")
    if uint(rpc("eth_chainId", [])) != 84532:
        raise ValueError("RPC is not Base Sepolia (84532)")

    # 1. pair intent rows with broadcast rows: a broadcast row completes the most recent intent row that has no hash yet, the same
    #    destination and (when both rows name a step) the same step. An intent row followed by another intent row stays unreceipted:
    #    that is what a crash between the two rows, or a failed broadcast attempt, leaves behind. Rows without a step get a positional id.
    intents = []
    n_broadcast = 0
    orphans = []
    for i, r in enumerate(rows):
        if r.get("state") == "intent":
            intents.append(dict(r, step=r.get("step") or "row%02d" % i, tx=None, _i=i))
        elif r.get("state") == "broadcast":
            n_broadcast += 1
            cands = [x for x in reversed(intents) if x["tx"] is None and (x.get("to") or "") == (r.get("to") or "")
                     and (not r.get("step") or x["step"] == r["step"])]
            if cands:
                cands[0]["tx"] = r.get("tx")
            else:
                orphans.append(r)
    others = [r for r in rows if r.get("state") not in ("intent", "broadcast")]

    print("journal %s: %d rows = %d intent, %d broadcast (%d without a matching intent row), %d other (%s); pool %s; rpc %s" % (
        path, len(rows), len(intents), n_broadcast, len(orphans), len(others), ", ".join(sorted({o.get("state", "?") for o in others})) or "none", pool, RPC))
    for r in orphans:
        print("ORPHAN broadcast row without an intent row before it: tx %s to %s (a journal written after the send, not before: outside the rule)" % (r.get("tx"), r.get("to")))
    results = []          # per signed intent
    plain = []            # rows without a signed intent
    problems = len(orphans)
    receipted_landed = {}  # (signer, nonce) -> step, for the elimination step
    unreceipted = []       # (step, kind, signer, nonce, loanId)
    signers = set()

    for r in intents:
        step = r["step"]
        tx = r["tx"]
        si = signed_intents(r.get("data"))
        if not si:
            # owner call, mint, create: settled by receipt only
            if tx:
                rc = rpc("eth_getTransactionReceipt", [tx])
                st = uint(rc["status"]) if rc else None
                plain.append((step, "no signed intent", tx, uint(rc["blockNumber"]) if rc else None,
                              "settled by receipt: status %s%s" % (st, (", created " + rc["contractAddress"]) if rc and rc.get("contractAddress") else "")))
            else:
                plain.append((step, "no signed intent", None, None, "no hash: not a signed intent, no nonce to read; receipt or re-send decision is outside this rule"))
            continue
        for kind, target, signer, nonce, loan_id in si:
            signers.add(signer)
            if (target or r.get("to") or "").lower() != pool.lower():
                results.append((step, kind, signer, nonce, tx, None, "mismatch", "wrapped target %s is not the pool" % target)); problems += 1
                continue
            if tx:
                t = rpc("eth_getTransactionByHash", [tx])
                rc = rpc("eth_getTransactionReceipt", [tx])
                if not t or not rc:
                    unreceipted.append((step, kind, signer, nonce, loan_id, (r.get("data") or "").lower()))   # a hash the chain does not know (dropped, replaced) is no receipt
                    continue
                if (t.get("input") or "").lower() != (r.get("data") or "").lower() or (t.get("to") or "").lower() != (r.get("to") or "").lower():
                    results.append((step, kind, signer, nonce, tx, uint(rc["blockNumber"]), "mismatch", "chain tx input/to differ from the journal row's calldata/destination")); problems += 1
                    continue
                b = uint(rc["blockNumber"])
                before, after = nonces(pool, signer, b - 1), nonces(pool, signer, b)
                verdict, reason = receipt_verdict((kind, target, signer, nonce, loan_id), si, rc, before, after, pool)
                how = "receipt block %d: nonces(signer) %d -> %d, status %d; %s" % (b, before, after, uint(rc["status"]), reason)
                if verdict == "landed":
                    receipted_landed[(signer.lower(), nonce)] = (step, (r.get("data") or "").lower())
                elif verdict == "ambiguous":
                    problems += 1
                results.append((step, kind, signer, nonce, tx, b, verdict, how))

            else:
                unreceipted.append((step, kind, signer, nonce, loan_id, (r.get("data") or "").lower()))

    # 2. rows without a hash: latest nonces(signer) + elimination over the journal
    snapshot = rpc("eth_blockNumber", [])
    latest = {s: nonces(pool, s, snapshot) for s in signers}
    for step, kind, signer, nonce, loan_id, _digest in unreceipted:
        consumed = nonce < latest[signer]
        if not consumed:
            results.append((step, kind, signer, nonce, None, None, "not landed", "no hash; nonces(signer) latest = %d <= signed nonce %d: not consumed; a re-send cannot double-execute (nonce check)" % (latest[signer], nonce)))
            continue
        if (signer.lower(), nonce) in receipted_landed:
            landed_step, landed_data = receipted_landed[(signer.lower(), nonce)]
            identical = _digest == landed_data
            verdict = "landed" if identical else "not landed"
            reason = ("identical signed intent is established by receipted row %s" if identical else
                      "a different signed intent is established by receipted row %s at this nonce") % landed_step
            results.append((step, kind, signer, nonce, None, None, verdict, reason))
            continue
        peers = [u for u in unreceipted if u[2].lower() == signer.lower() and u[3] == nonce]
        reason = ("no hash; nonce %d consumed, but %d local journal row(s) cannot establish which signed bytes consumed it; "
                  "receipt, logs or trace required") % (nonce, len(peers))
        results.append((step, kind, signer, nonce, None, None, "ambiguous", reason))
        problems += 1

    # 3. the missing-journal-row case: a consumed nonce that no journal row LANDED (rows the chain shows unmoved do not explain a consumption)
    for s in sorted(signers):
        explained = {x[3] for x in results if x[2].lower() == s.lower() and x[6] in ("landed", "ambiguous")}
        for n in range(latest[s]):
            if n not in explained:
                results.append(("-", "(no journal row)", s, n, None, None, "unknown", "nonce %d consumed on chain and no journal row landed it: a lost row and an intent that never existed look the same from here" % n)); problems += 1

    # 4. report
    order = {"landed": 0, "not landed": 1, "ambiguous": 2, "mismatch": 3, "unknown": 4}
    for step, kind, tx, b, how in plain:
        print("%-9s %-24s %-13s %s%s" % ("--", step, "", (tx[:12] + " ") if tx else "", how))
    for step, kind, signer, nonce, tx, b, verdict, how in sorted(results, key=lambda x: (x[0] if x[0] != "-" else "zzz", x[3])):
        print("%-9s %-24s %-28s nonce %-2d %-13s %s%s" % (verdict.upper(), step, kind, nonce, (tx[:12] if tx else "(no hash)"), ("block %d: " % b) if b else "", how))
    counts = {k: sum(1 for x in results if x[6] == k) for k in order}
    print("signed intents: %d | %s | plain rows: %d | latest nonces(signer): %s" % (len(results), ", ".join("%s %d" % (k, v) for k, v in counts.items()), len(plain), {s: n for s, n in latest.items()}))
    if args.json:
        with open(path + ".reconciled.json", "x", encoding="utf-8") as output:
            json.dump({"results": results, "plain": plain, "latest": latest, "snapshot_block": snapshot}, output, indent=1)
    return 1 if problems else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print("RECONCILIATION_FAILED:", error, file=sys.stderr)
        raise SystemExit(1)
