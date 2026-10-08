#!/usr/bin/env python3
"""Offline Beefy-harvest accounting audit; no RPC, keys, signing or spending.

Usage: python audit-harvest-only.py public-evidence.json
Checks internal consistency, NOT chain authenticity, source/deployment matching,
custody, historical independence, or completeness. Refetch all cited evidence.

Required packet: chain_id=8453; addresses={borrower,lender,strategy,weth};
controlled_addresses=[all known team-controlled addresses]; strategy_review=
{runtime_code_keccak256,source_evidence,fee_mechanism_evidence,
 no_team_seed_evidence}; snapshots={before,after}, each {block_number,block_hash,
 accounts:{address:{native_wei,weth_wei,nonce}}}; terms={principal_wei,fee_wei};
txs=[{kind,tx:{hash,chainId,from,to,value,input,nonce},receipt:{transactionHash,
 blockHash,blockNumber,status,gasUsed,effectiveGasPrice,l1Fee,logs},
 operator_fee_wei,operator_fee_evidence,native_flows:[{from,to,wei,proof}],
 repayment_principal_wei,repayment_fee_wei}].
Allowed kinds: funding,harvest,unwrap,repay,sweep. Raw logs must include ALL
canonical WETH logs, unmodified address/topics/data/logIndex. No preflight lens
balanceDelta, advertised callReward(), simulation, or old WETH counts as income.
Native flows must cover top-level value and every traced native movement touching
either audited actor. Unrelated movements between outside protocol addresses may
be included but do not enter this actor ledger.
Fully costed classification also requires offchain_costs={borrower,lender},
each {wei_equivalent,evidence}; justify even zero incremental cost explicitly.
"""

import json
import re
import sys

WETH = "0x4200000000000000000000000000000000000006"
TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
WITHDRAWAL = "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65"
DEPOSIT = "0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c"
APPROVAL = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
HARVEST = "0x0e5c011e"  # harvest(address)
UNWRAP = "0x2e1a7d4d"  # withdraw(uint256)


def amount(v):
    if isinstance(v, bool) or not isinstance(v, (int, str)):
        raise ValueError("integer amount required")
    n = int(v, 16 if isinstance(v, str) and v.startswith("0x") else 10) if isinstance(v, str) else v
    if n < 0:
        raise ValueError("negative amount")
    return n


def addr(v):
    if not isinstance(v, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", v):
        raise ValueError("invalid address")
    return v.lower()


def hash32(v):
    return isinstance(v, str) and bool(re.fullmatch(r"0x[0-9a-fA-F]{64}", v))


def topic_address(v):
    if not hash32(v) or v[2:26] != "0" * 24:
        raise ValueError("invalid indexed address")
    return addr("0x" + v[-40:])


def audit(p):
    errors = []

    def check(ok, why):
        if not ok:
            errors.append(why)

    check(amount(p["chain_id"]) == 8453, "wrong chain")
    actors = {k: addr(v) for k, v in p["addresses"].items()}
    b, lender, strategy = (actors[k] for k in ["borrower", "lender", "strategy"])
    controlled = {addr(v) for v in p["controlled_addresses"]}
    check(b != lender and {b, lender}.issubset(controlled), "actor identity/custody mismatch")
    check(strategy not in controlled, "team strategy does not qualify external service income")
    check(actors["weth"] == WETH, "wrong fee token")
    review = p["strategy_review"]
    check(hash32(review["runtime_code_keccak256"]) and
          all(review.get(k) for k in ["source_evidence", "fee_mechanism_evidence", "no_team_seed_evidence"]),
          "strategy/source/independence evidence missing")
    first, last = (p["snapshots"][k] for k in ["before", "after"])
    check(amount(last["block_number"]) > amount(first["block_number"]) and
          hash32(first["block_hash"]) and hash32(last["block_hash"]), "invalid snapshot interval")
    state = [{addr(a): {k: amount(v) for k, v in s.items()} for a, s in x["accounts"].items()}
             for x in [first, last]]
    before, after = state
    check(set(before) == set(after) == {b, lender}, "ledger actor coverage mismatch")
    native, token, gas, nonces = ({a: 0 for a in [b, lender]} for _ in range(4))
    nonces = {a: set() for a in nonces}
    hashes = set()
    earned = funded = paid_principal = paid_fee = unwrap_total = failed = 0
    check(len(p["txs"]) <= 50, "unbounded transaction packet")
    for r in p["txs"]:
        t, receipt, kind = r["tx"], r["receipt"], r["kind"]
        th = t["hash"].lower()
        check(hash32(th) and th not in hashes and receipt["transactionHash"].lower() == th,
              "duplicate/invalid transaction or receipt hash")
        hashes.add(th)
        check(amount(t["chainId"]) == 8453 and hash32(receipt["blockHash"]), "transaction chain/block mismatch")
        check(amount(first["block_number"]) < amount(receipt["blockNumber"]) <= amount(last["block_number"]),
              "transaction outside snapshot interval")
        sender, to, value = addr(t["from"]), addr(t["to"]), amount(t["value"])
        check(sender in gas and kind in {"funding", "harvest", "unwrap", "repay", "sweep"},
              "unaccounted sender or operation")
        if sender not in gas:
            continue
        nonce = amount(t["nonce"])
        check(nonce not in nonces[sender], "duplicate sender nonce")
        nonces[sender].add(nonce)
        check(bool(r["operator_fee_evidence"]), "operator fee assumption lacks evidence")
        gas[sender] += (amount(receipt["gasUsed"]) * amount(receipt["effectiveGasPrice"]) +
                        amount(receipt["l1Fee"]) + amount(r["operator_fee_wei"]))
        status = amount(receipt["status"])
        check(status in {0, 1}, "invalid receipt status")
        if status != 1:
            failed += 1
            check(not r.get("native_flows") and not receipt["logs"], "reverted value/logs recorded")
            continue
        calldata = t["input"].lower()
        if kind == "harvest":
            check(sender == b and to == strategy and value == 0 and
                  calldata == HARVEST + "0" * 24 + b[2:], "not exact harvest(borrower)")
        if kind == "funding":
            check(sender == lender and to == b and calldata == "0x", "invalid principal funding")
            funded += value
        if kind == "repay":
            principal, fee = amount(r["repayment_principal_wei"]), amount(r["repayment_fee_wei"])
            check(sender == b and to == lender and calldata == "0x" and principal + fee == value,
                  "native repayment/allocation mismatch")
            paid_principal += principal
            paid_fee += fee
        flows = r.get("native_flows", [])
        if value:
            check(any(addr(f["from"]) == sender and addr(f["to"]) == to and amount(f["wei"]) == value
                      for f in flows), "top-level value missing from flow ledger")
        record_withdrawal = 0
        log_indices = set()
        for log in receipt["logs"]:
            index = amount(log["logIndex"])
            check(index not in log_indices and not log.get("removed", False), "duplicate/removed receipt log")
            log_indices.add(index)
            if addr(log["address"]) != WETH:
                continue
            topics, data = log["topics"], log["data"]
            check(bool(topics) and hash32(data), "invalid WETH log encoding")
            if not topics or not hash32(data):
                continue
            event, quantity = topics[0].lower(), amount(data)
            if event == TRANSFER:
                check(len(topics) == 3, "invalid WETH Transfer topics")
                src, dst = topic_address(topics[1]), topic_address(topics[2])
                if src in token:
                    token[src] -= quantity
                if dst in token:
                    token[dst] += quantity
                if kind == "harvest" and src == strategy and dst == b:
                    earned += quantity
            elif event in {WITHDRAWAL, DEPOSIT}:
                check(len(topics) == 2, "invalid WETH wrap/unwrap topics")
                who = topic_address(topics[1])
                if who in token:
                    token[who] += quantity if event == DEPOSIT else -quantity
                if event == WITHDRAWAL and who == b:
                    check(kind == "unwrap", "borrower withdrawal outside unwrap phase")
                    record_withdrawal += quantity
            elif event != APPROVAL:
                check(False, "unknown canonical WETH event")
        if kind == "unwrap":
            check(sender == b and to == WETH and value == 0 and record_withdrawal > 0 and
                  calldata == UNWRAP + format(record_withdrawal, "064x"), "unwrap ABI/event mismatch")
            check(sum(amount(f["wei"]) for f in flows if addr(f["from"]) == WETH and addr(f["to"]) == b)
                  == record_withdrawal, "unwrap native output mismatch")
            unwrap_total += record_withdrawal
        for f in flows:
            src, dst, quantity = addr(f["from"]), addr(f["to"]), amount(f["wei"])
            check(bool(f["proof"]), "unproven native trace/value flow")
            if src not in native and dst not in native:
                continue
            check(src in native or (kind == "unwrap" and src == WETH and dst == b),
                  "external native gift cannot be service revenue")
            check(dst in native, "unexpected external native spending")
            if src in native:
                native[src] -= quantity
            if dst in native:
                native[dst] += quantity
    principal, fee = amount(p["terms"]["principal_wei"]), amount(p["terms"]["fee_wei"])
    check(principal > 0 and funded == principal and paid_principal == principal and paid_fee == fee,
          "principal/fee not funded and fully repaid in native ETH")
    for a in [b, lender]:
        check(after[a]["native_wei"] - before[a]["native_wei"] == native[a] - gas[a], "native conservation failed")
        check(after[a]["weth_wei"] - before[a]["weth_wei"] == token[a], "WETH log/balance conservation failed")
        check(nonces[a] == set(range(before[a]["nonce"], after[a]["nonce"])), "unrecorded sender nonce")
    wealth = lambda s: sum(s[a][k] for a in [b, lender] for k in ["native_wei", "weth_wei"])
    surplus = wealth(after) - wealth(before)
    check(surplus == earned - sum(gas.values()), "new external fee/team wealth reconciliation failed")
    cold = before[b]["native_wei"] == before[b]["weth_wei"] == before[b]["nonce"] == 0
    settled = all(after[a]["weth_wei"] == before[a]["weth_wei"] for a in [b, lender]) and unwrap_total == earned
    borrower_profit, lender_margin = earned - gas[b] - fee, fee - gas[lender]
    onchain = not errors and cold and settled and earned > 0 and borrower_profit > 0 and lender_margin >= 0
    costs = p.get("offchain_costs")
    known = (isinstance(costs, dict) and all(isinstance(costs.get(role), dict) and
             "wei_equivalent" in costs[role] and costs[role].get("evidence") for role in ["borrower", "lender"]))
    total_b = borrower_profit - amount(costs["borrower"]["wei_equivalent"]) if known else None
    total_l = lender_margin - amount(costs["lender"]["wei_equivalent"]) if known else None
    return {"venue": "beefy-harvest", "accounting_checks_pass": not errors, "errors": errors,
            "new_external_weth_fee_wei": earned, "unwrapped_wei": unwrap_total,
            "gas_wei_by_actor": gas, "failed_transactions": failed,
            "team_onchain_surplus_wei": surplus, "cold_native_weth_nonce_start": cold,
            "all_new_fee_cash_settled": settled, "borrower_onchain_profit_wei": borrower_profit,
            "lender_onchain_margin_wei": lender_margin, "offchain_costs_evidenced": bool(known),
            "borrower_fully_costed_profit_wei_equivalent": total_b,
            "lender_fully_costed_margin_wei_equivalent": total_l,
            "positive_settled_cold_start_onchain_proof": bool(onchain),
            "fully_costed_cash_settled_bootstrap_proof": bool(onchain and known and total_b > 0 and total_l >= 0),
            "limitation": "Offline consistency only; raw receipts/blocks and actual source/deployment/custody/independence must be independently verified. One harvest is not reliable income."}


if __name__ == "__main__":
    try:
        result = audit(json.load(open(sys.argv[1], encoding="utf-8")))
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["accounting_checks_pass"] else 1)
    except (IndexError, KeyError, TypeError, ValueError) as error:
        print(json.dumps({"accounting_checks_pass": False, "error_kind": type(error).__name__,
                          "error": "Invalid or incomplete public accounting packet."}))
        sys.exit(2)
