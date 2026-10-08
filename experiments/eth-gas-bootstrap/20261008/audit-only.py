#!/usr/bin/env python3
"""Offline, integer-only independent accounting audit; never signs or uses secrets.

Usage: python audit-only.py normalized-public-evidence.json
This validates a public evidence packet's internal consistency, NOT its truth or
completeness. Independently refetch the cited blocks/transactions/logs first.
No synthetic transaction fixtures or invented execution results are supplied.

Required packet:
  chain_id=8453; addresses={borrower,lender,prize_pool,claimer,weth};
  controlled_addresses=[...]; snapshots={before,after}, each {block_hash,
  block_number, accounts:{address:{native_wei,weth_wei,reward_wei,nonce}}};
  terms={principal_wei,fee_wei}; txs=[{tx:{hash,chainId,from,to,value},
  receipt:{transactionHash,blockHash,blockNumber,status,gasUsed,
  effectiveGasPrice,l1Fee}, operator_fee_wei, operator_fee_evidence,
  kind, native_flows:[{from,to,wei,proof}], claim_events:[{emitter,winner,
  claimRewardRecipient,claimReward}], withdrawal_events:[{emitter,account,
  to,amount}], repayment_principal_wei, repayment_fee_wei}].
  kinds are funding,claim,withdraw,unwrap,repay,sweep; optional extras may fail.
  Native flows include top-level value AND traced internal ETH, such as WETH
  withdrawals; do not include gas or WETH token transfers as native flows.
  All outside-address flow proofs must be independently checked; this script
  cannot authenticate a quoted RPC result, custody claim, or decoded log.
"""

import json
import re
import sys

WETH_BASE = "0x4200000000000000000000000000000000000006"


def number(value):
    if isinstance(value, bool):
        raise ValueError("boolean used as amount")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str):
        result = int(value, 16 if value.startswith("0x") else 10)
    else:
        raise ValueError("integer amount required")
    if result < 0:
        raise ValueError("negative amount")
    return result


def address(value):
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise ValueError("invalid address")
    return value.lower()


def audit(packet):
    errors = []

    def check(condition, message):
        if not condition:
            errors.append(message)

    check(number(packet["chain_id"]) == 8453, "not Base mainnet")
    addrs = {k: address(v) for k, v in packet["addresses"].items()}
    borrower, lender = addrs["borrower"], addrs["lender"]
    owned = {address(v) for v in packet["controlled_addresses"]}
    check(borrower != lender, "lender and borrower must be separate")
    check({borrower, lender}.issubset(owned), "actor custody missing")
    check(addrs["weth"] == WETH_BASE, "not canonical Base WETH")
    snapshots = packet["snapshots"]
    before, after = snapshots["before"], snapshots["after"]
    check(number(after["block_number"]) > number(before["block_number"]),
          "snapshot interval invalid")
    states = []
    for snapshot in [before, after]:
        check(bool(re.fullmatch(r"0x[0-9a-fA-F]{64}", snapshot["block_hash"])),
              "snapshot block hash missing")
        states.append({address(a): {k: number(v) for k, v in s.items()}
                       for a, s in snapshot["accounts"].items()})
    initial, final = states
    check(set(initial) == set(final) == {borrower, lender},
          "snapshot must cover exactly both ledger actors")
    gas = {borrower: 0, lender: 0}
    flow = {borrower: 0, lender: 0}
    nonce_count = {borrower: 0, lender: 0}
    rewards = withdrawn = principal_repaid = fee_repaid = funding = 0
    seen = set()
    success_claims = failed_txs = 0
    check(len(packet["txs"]) <= 50, "unbounded transaction packet")
    for record in packet["txs"]:
        tx, receipt = record["tx"], record["receipt"]
        tx_hash = tx["hash"].lower()
        check(tx_hash not in seen, "duplicate transaction")
        seen.add(tx_hash)
        check(bool(re.fullmatch(r"0x[0-9a-f]{64}", tx_hash)), "bad transaction hash")
        check(receipt["transactionHash"].lower() == tx_hash, "receipt mismatch")
        check(number(tx["chainId"]) == 8453, "transaction chain mismatch")
        sender = address(tx["from"])
        check(sender in gas, "unaccounted gas-paying actor")
        if sender not in gas:
            continue
        nonce_count[sender] += 1
        block = number(receipt["blockNumber"])
        check(number(before["block_number"]) < block <= number(after["block_number"]),
              "transaction outside snapshot interval")
        check(bool(receipt["blockHash"]), "receipt block hash absent")
        # Base L1 fee is separate from EVM gas; zero requires actual evidence.
        l2 = number(receipt["gasUsed"]) * number(receipt["effectiveGasPrice"])
        l1 = number(receipt["l1Fee"])
        operator = number(record["operator_fee_wei"])
        check(bool(record["operator_fee_evidence"]), "operator fee assumption unproved")
        gas[sender] += l2 + l1 + operator
        succeeded = number(receipt["status"]) == 1
        if not succeeded:
            failed_txs += 1
            check(not record.get("native_flows"), "reverted native movement recorded")
            check(not record.get("claim_events"), "reverted reward recorded")
            check(not record.get("withdrawal_events"), "reverted withdrawal recorded")
            continue
        native = record.get("native_flows", [])
        value = number(tx["value"])
        if value:
            check(any(address(f["from"]) == sender and
                      address(f["to"]) == address(tx["to"]) and
                      number(f["wei"]) == value for f in native),
                  "top-level transaction value missing from movement ledger")
        for movement in native:
            src, dst = address(movement["from"]), address(movement["to"])
            amount = number(movement["wei"])
            check(bool(movement["proof"]), "native flow lacks trace/log proof")
            if src in flow:
                flow[src] -= amount
            if dst in flow:
                flow[dst] += amount
        if record["kind"] == "funding":
            check(sender == lender and address(tx["to"]) == borrower,
                  "funding identity mismatch")
            funding += value
        if record["kind"] == "repay":
            check(sender == borrower and address(tx["to"]) == lender,
                  "repayment identity mismatch")
            principal = number(record["repayment_principal_wei"])
            fee = number(record["repayment_fee_wei"])
            check(principal + fee == value, "repayment allocation mismatch")
            principal_repaid += principal
            fee_repaid += fee
        if record["kind"] == "claim":
            check(sender == borrower and address(tx["to"]) == addrs["claimer"],
                  "claim caller/contract mismatch")
        for event in record.get("claim_events", []):
            check(record["kind"] == "claim", "reward outside documented claim")
            check(address(event["emitter"]) == addrs["prize_pool"], "wrong reward emitter")
            check(address(event["claimRewardRecipient"]) == borrower, "wrong fee recipient")
            check(address(event["winner"]) not in owned, "own/team prize is not external work")
            rewards += number(event["claimReward"])
            success_claims += 1
        for event in record.get("withdrawal_events", []):
            check(record["kind"] == "withdraw", "withdrawal outside documented call")
            check(sender == borrower and address(tx["to"]) == addrs["prize_pool"],
                  "withdrawal must be called by accrued reward owner")
            check(address(event["emitter"]) == addrs["prize_pool"] and
                  address(event["account"]) == borrower and
                  address(event["to"]) == borrower, "withdrawal identity mismatch")
            withdrawn += number(event["amount"])
    principal = number(packet["terms"]["principal_wei"])
    fee = number(packet["terms"]["fee_wei"])
    check(principal > 0, "no positive ETH loan principal")
    check(funding == principal, "advance does not match agreed principal")
    check(principal_repaid == principal, "principal not fully repaid")
    check(fee_repaid == fee, "financing fee not fully repaid")
    for actor in [borrower, lender]:
        check(final[actor]["native_wei"] - initial[actor]["native_wei"] ==
              flow[actor] - gas[actor], "native balance conservation failed: " + actor)
        check(final[actor]["nonce"] - initial[actor]["nonce"] == nonce_count[actor],
              "unrecorded actor transaction: " + actor)
    check(final[borrower]["reward_wei"] - initial[borrower]["reward_wei"] ==
          rewards - withdrawn, "new fee/accrual/withdrawal reconciliation failed")
    check(final[lender]["reward_wei"] == initial[lender]["reward_wei"],
          "unexplained lender reward change")
    wealth = lambda s: sum(s[a][k] for a in [borrower, lender]
                           for k in ["native_wei", "weth_wei", "reward_wei"])
    delta = wealth(final) - wealth(initial)
    check(delta == rewards - sum(gas.values()), "team native/WETH/accrual conservation failed")
    # Strict cold-start proof: no prior borrower assets/receivables are counted.
    cold = all(initial[borrower][k] == 0 for k in ["native_wei", "weth_wei", "reward_wei"])
    settled = final[borrower]["reward_wei"] == 0
    borrower_profit = rewards - gas[borrower] - fee
    lender_margin = fee - gas[lender]
    positive = rewards > 0 and delta > 0 and success_claims > 0 and borrower_profit > 0
    return {"accounting_checks_pass": not errors, "errors": errors,
            "cold_start_empty_borrower": cold, "new_reward_wei": rewards,
            "withdrawn_wei": withdrawn, "unsettled_reward_wei": final[borrower]["reward_wei"],
            "gas_wei_by_actor": gas, "failed_transactions": failed_txs,
            "team_onchain_surplus_wei": delta,
            "borrower_onchain_economic_profit_wei": borrower_profit,
            "lender_loan_margin_before_nonloan_sweeps_wei": lender_margin,
            "loan_funding_gas_covered_by_fee": lender_margin >= 0,
            "positive_settled_cold_start_onchain_proof": not errors and cold and settled and positive,
            "limitation": "Offline consistency only. Refetch raw evidence; additionally price all provider, computation and coordination costs. One result does not establish repeatability or reliable income."}


if __name__ == "__main__":
    try:
        result = audit(json.load(open(sys.argv[1], encoding="utf-8")))
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["accounting_checks_pass"] else 1)
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"accounting_checks_pass": False, "error": str(exc)}))
        sys.exit(2)
