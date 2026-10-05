#!/usr/bin/env python3
"""Settle a relayer's intent journal against Base Sepolia: journal row + nonces(signer), nothing else.

    python3 reconcile_journal.py JOURNAL.jsonl [--pool ADDR] [--rpc URL] [--json]

The journal is the relayer's own append-only record (written by lib.py during the live runs): an `intent` row BEFORE each
broadcast (destination, calldata) and a `broadcast` row AFTER it (tx hash). A relayer that crashed between the two rows, or
that lost the broadcast response, has an intent row and no hash: the fixture's chain-4 / chain-7 expected state says such a row
is settled by the journal plus nonces(signer), and "unknown" is reserved for a nonce consumed on chain with no journal row at all.
This script is that rule, executable. Standard library only, JSON-RPC only, no key. It trusts nothing in the journal: calldata
of a receipted row is compared with the chain's tx input, and every verdict is derived from nonces(signer) read from the chain.

Per signed intent (one journal row may carry several: a batch envelope) it prints one of:
  landed      the intent's nonce moved in the receipt's block (range [before, after) names it), or, with no hash, its nonce is
              consumed on chain and it is the only unreceipted journal row that carries that nonce
  not landed  the receipt's block shows the nonce unmoved (reverted or swallowed), or, with no hash, the nonce is not consumed
  ambiguous   no hash, the nonce is consumed, and more than one unreceipted journal row carries it (a re-signed intent after a
              revert reuses the nonce the revert gave back); the receipt or the logs must decide, nonces(signer) cannot
  mismatch    the chain's tx input differs from the journal's calldata (the journal is the authority only when it matches)
  unknown     a consumed nonce with no journal row at all (the missing-journal-row case): nothing on chain distinguishes a lost
              journal row from an intent that never existed
Rows that carry no signed intent (owner calls, token mint, contract creation, diagnostics) are settled by receipt only and listed.
Exit 0 only if nothing is ambiguous, mismatched or unknown.
"""
import json, sys, time, urllib.error, urllib.request

RPC = "https://sepolia.base.org"
UA = "retry-fixture reconcile_journal.py"
SEL_REPAY = "0x1d169fa9"       # repayLoanMeta((address,uint256,uint256,uint256,uint256),bytes,(uint256,uint256,uint8,bytes32,bytes32))
SEL_BORROW = "0x0d29380a"      # borrowAndDisburseMeta((address,uint256,address,uint256,uint256,uint256,uint256),bytes)
SEL_FORWARD = "0x6fadcf72"     # forward(address,bytes)           (test helper Wrapper)
SEL_BATCH = "0xb9d096b2"       # batch(address,bytes[])           (test helper SwallowingBatch)
SEL_NONCES = "0x7ecebe00"      # nonces(address)


def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    for attempt in range(8):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code not in (429, 502, 503, 504):
                raise
            time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError("rpc transport failed after retries: " + method)
    if "error" in r:
        raise RuntimeError(json.dumps(r["error"]))
    return r["result"]


def word(a, i):
    return a[64 * i:64 * (i + 1)]


def uint(w):
    return int(w, 16)


def addr(w):
    return "0x" + w[-40:]


def dyn_bytes(a, offset_bytes):
    o = offset_bytes * 2
    n = uint(a[o:o + 64])
    return "0x" + a[o + 64:o + 64 + 2 * n]


def signed_intents(data):
    """Decode the signed intent(s) a calldata carries: [(kind, target_or_None, signer, nonce, loanId_or_None)].
    Direct repay/borrow -> one; forward(target, inner) -> inner's; batch(target, calls) -> one per call. Unknown selector -> []."""
    sel = (data or "")[:10].lower()
    a = (data or "")[10:]
    if sel == SEL_REPAY:
        return [("repayLoanMeta", None, addr(word(a, 0)), uint(word(a, 3)), uint(word(a, 1)))]
    if sel == SEL_BORROW:
        return [("borrowAndDisburseMeta", None, addr(word(a, 0)), uint(word(a, 5)), None)]
    if sel == SEL_FORWARD:
        target, inner = addr(word(a, 0)), dyn_bytes(a, uint(word(a, 1)))
        return [(k + " via forward", target, s, n, l) for k, _, s, n, l in signed_intents(inner)]
    if sel == SEL_BATCH:
        target = addr(word(a, 0))
        arr = uint(word(a, 1)) * 2
        n = uint(a[arr:arr + 64])
        base = arr + 64
        out = []
        for i in range(n):
            rel = uint(a[base + 64 * i:base + 64 * (i + 1)]) * 2
            ln = uint(a[base + rel:base + rel + 64])
            inner = "0x" + a[base + rel + 64:base + rel + 64 + 2 * ln]
            out += [(k + " via batch[%d]" % i, target, s, nn, l) for k, _, s, nn, l in signed_intents(inner)]
        return out
    return []


def pad_addr(a):
    return a[2:].lower().rjust(64, "0")


def nonces(pool, who, block):
    return uint(rpc("eth_call", [{"to": pool, "data": SEL_NONCES + pad_addr(who)}, hex(block) if isinstance(block, int) else block])[2:])


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    global RPC
    if "--rpc" in sys.argv:
        RPC = sys.argv[sys.argv.index("--rpc") + 1]
    pool = sys.argv[sys.argv.index("--pool") + 1] if "--pool" in sys.argv else "0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8"
    path = args[0] if args else "JOURNAL_live_pool.jsonl"
    rows = [json.loads(l) for l in open(path) if l.strip()]

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
    hashes = {x["step"]: [x["tx"]] for x in intents if x["tx"]}

    print("journal %s: %d rows = %d intent, %d broadcast (%d without a matching intent row), %d other (%s); pool %s; rpc %s" % (
        path, len(rows), len(intents), n_broadcast, len(orphans), len(others), ", ".join(sorted({o.get("state", "?") for o in others})) or "none", pool, RPC))
    for r in orphans:
        print("ORPHAN broadcast row without an intent row before it: tx %s to %s (a journal written after the send, not before: outside the rule)" % (r.get("tx"), r.get("to")))
    results = []          # per signed intent
    plain = []            # rows without a signed intent
    problems = 0
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
            if target and target.lower() != pool.lower():
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
                landed = before <= nonce < after
                how = "receipt block %d: nonces(signer) %d -> %d, status %d" % (b, before, after, uint(rc["status"]))
                if landed:
                    receipted_landed[(signer.lower(), nonce)] = step
                    results.append((step, kind, signer, nonce, tx, b, "landed", how + "; range [%d, %d) names nonce %d" % (before, after, nonce)))
                else:
                    results.append((step, kind, signer, nonce, tx, b, "not landed", how + "; nonce %d unmoved%s" % (nonce, " (envelope succeeded, intent did not)" if uint(rc["status"]) == 1 else " (tx reverted)")))
            else:
                unreceipted.append((step, kind, signer, nonce, loan_id, (r.get("data") or "").lower()))

    # 2. rows without a hash: latest nonces(signer) + elimination over the journal
    latest = {s: nonces(pool, s, "latest") for s in signers}
    for step, kind, signer, nonce, loan_id, _digest in unreceipted:
        consumed = nonce < latest[signer]
        if not consumed:
            results.append((step, kind, signer, nonce, None, None, "not landed", "no hash; nonces(signer) latest = %d <= signed nonce %d: not consumed; a re-send cannot double-execute (nonce check)" % (latest[signer], nonce)))
            continue
        if (signer.lower(), nonce) in receipted_landed:
            results.append((step, kind, signer, nonce, None, None, "not landed", "no hash; nonce %d is consumed but a receipted row (%s) landed it: this row did not" % (nonce, receipted_landed[(signer.lower(), nonce)])))
            continue
        peers = [u for u in unreceipted if u[2].lower() == signer.lower() and u[3] == nonce]
        distinct = {u[5] for u in peers}   # calldata digests: identical bytes are one intent submitted more than once (chain-1), not two intents
        if len(distinct) == 1:
            results.append((step, kind, signer, nonce, None, None, "landed", "no hash; nonce %d consumed (latest %d) and %s: settled by journal + nonces(signer)" % (
                nonce, latest[signer], "this is the only unreceipted journal row carrying it" if len(peers) == 1 else "the %d unreceipted rows carrying it are byte-identical (one intent, resubmitted)" % len(peers))))
        else:
            results.append((step, kind, signer, nonce, None, None, "ambiguous", "no hash; nonce %d consumed, but %d unreceipted journal rows with different bytes carry it (%s): a re-signed intent reused the nonce; nonces(signer) cannot say which landed; receipt or logs needed" % (nonce, len(peers), ", ".join(p[0] for p in peers)))); problems += 1

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
    if "--json" in sys.argv:
        json.dump({"results": results, "plain": plain, "latest": latest}, open(path + ".reconciled.json", "w"), indent=1)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
