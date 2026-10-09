#!/usr/bin/env python3
"""Read pool health and credit conservation at one block, using Foundry's cast.

No transaction is sent. Defaults come from deployments/current.json; RPC, POOL,
LENS, SCORES and USDC can override it. The chain and contract wiring are checked.
Exit 0 means a complete snapshot with the conservation check holding, 1 means
failure or a violated invariant. A report includes its block and hash; a changed
block hash during collection invalidates the report.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.deployment import Cast, CastError, as_int, format_units, load_deployment

STATUS = ("None", "Requested", "Active", "Repaid", "Defaulted", "Cancelled")
POOL_FIELDS = (
    "totalAssets", "lenderCash", "totalLentOut", "reservedLiquidity", "firstLossReserve",
    "totalImpaired", "totalDuesPaid", "protocolFees", "totalStaked", "lenderCount", "getLoanRate",
)
ACCOUNT_FIELDS = ("getBorrowers", "getBackers", "getBackedBorrowers", "getLenders")


def top_share(values):
    total = sum(values.values())
    return max(values.values()) / total if total else 0.0


def read_report(deployment, client, block="latest"):
    client.check_chain()
    header = client.block(block)
    number = as_int(header["number"])
    client.check_wiring(block=number)
    pool_address, lens, scores = deployment["pool"], deployment["lens"], deployment["scores"]

    def call(contract, signature, *args):
        return client.call(contract, signature, *args, block=number)

    def num(contract, signature, *args):
        return as_int(call(contract, signature, *args)[0])

    pool = {name: num(pool_address, f"{name}()(uint256)") for name in POOL_FIELDS}
    pool["utilisationBps"] = num(lens, "getUtilisation()(uint256)")
    pool["sharePrice"] = num(lens, "sharePrice()(uint256)")
    scored = call(scores, "getScores()(address[],uint256[])")[0]
    groups = {name: call(pool_address, f"{name}()(address[])")[0] for name in ACCOUNT_FIELDS}
    accounts = sorted({account.lower() for group in [scored, *groups.values()] for account in group})

    limits = granted = committed_stake = 0
    lines = {}
    for account in accounts:
        limits += num(pool_address, "getBorrowLimit(address)(uint256,uint256)", account)
        amount = num(pool_address, "grantedCredit(address)(uint256)", account)
        granted += amount
        committed_stake += num(pool_address, "stakeCommitted(address)(uint256)", account)
        if amount:
            lines[account] = amount

    backers = {}
    secured = unsecured = edges = 0
    for borrower in groups["getBackedBorrowers"]:
        for backer, secured_amount, unsecured_amount in call(pool_address, "getBackings(address)((address,uint256,uint256)[])", borrower)[0]:
            secured_amount, unsecured_amount = as_int(secured_amount), as_int(unsecured_amount)
            edges += 1
            secured += secured_amount
            unsecured += unsecured_amount
            name = backer.lower()
            backers[name] = backers.get(name, 0) + secured_amount + unsecured_amount

    loans = {}
    for ident in call(pool_address, "getAllLoanIds()(uint256[])")[0]:
        state = num(pool_address, "getLoanTerms(uint256)(uint8,uint256,uint256,uint256,uint256)", ident)
        if not 0 <= state < len(STATUS):
            raise CastError(f"unrecognized loan status {state}; update the ABI before interpreting the report")
        loans[STATUS[state]] = loans.get(STATUS[state], 0) + 1

    issuance = {name: num(scores, f"{name}()(uint256)") for name in ("totalHeld", "maxTotalScore", "totalScore")}
    issuance["scoredAccounts"] = len(scored)
    if client.block(number)["hash"].lower() != header["hash"].lower():
        raise CastError("block changed during collection; discard this snapshot and read again")
    return {
        "snapshot": {"chainId": deployment["chain_id"], "blockNumber": number, "blockHash": header["hash"],
                     "blockTimestamp": as_int(header["timestamp"]), "pool": pool_address,
                     "lens": lens, "scores": scores, "token": deployment["token"]["address"]},
        "pool": pool,
        "integrity": {"accounts": len(accounts), "sumLimits": limits, "sumGrantedCredit": granted,
                      "sumCommittedStake": committed_stake, "slack": granted + committed_stake - limits,
                      "holds": limits <= granted + committed_stake},
        "issuance": issuance,
        "concentration": {"largestLineShare": top_share(lines), "largestBackerShare": top_share(backers),
                          "backingEdges": edges, "securedBacking": secured, "unsecuredBacking": unsecured},
        "loans": loans,
    }


def print_report(report):
    p, i, c, q, snapshot = (report[key] for key in ("pool", "integrity", "concentration", "issuance", "snapshot"))
    print(f"Pool {snapshot['pool']} on chain {snapshot['chainId']} at block {snapshot['blockNumber']} ({snapshot['blockHash']})")
    print(f"  assets {format_units(p['totalAssets'])}  cash {format_units(p['lenderCash'])}  lent {format_units(p['totalLentOut'])}  "
          f"reserved {format_units(p['reservedLiquidity'])}  utilisation {p['utilisationBps']/100:.2f}%  share price {format_units(p['sharePrice'], 4)}")
    print(f"  first-loss reserve {format_units(p['firstLossReserve'])} (dues {format_units(p['totalDuesPaid'])})  impaired {format_units(p['totalImpaired'])}  "
          f"staked {format_units(p['totalStaked'])}  fees {format_units(p['protocolFees'])}  lenders {p['lenderCount']}  APR {p['getLoanRate']} bps")
    print(f"Credit integrity (METRICS 9, Theorem 1) over {i['accounts']} accounts:")
    print(f"  sum of limits {format_units(i['sumLimits'])} <= granted {format_units(i['sumGrantedCredit'])} + committed stake "
          f"{format_units(i['sumCommittedStake'])}: {'holds' if i['holds'] else 'VIOLATED'} (slack {format_units(i['slack'])})")
    print(f"Issuance: held {format_units(q['totalHeld'])} of {format_units(q['maxTotalScore'])} lines, {q['scoredAccounts']} scored accounts")
    print(f"Concentration (METRICS 6): largest line {c['largestLineShare']:.0%} of granted credit, largest backer "
          f"{c['largestBackerShare']:.0%} of backing; {c['backingEdges']} edges, secured {format_units(c['securedBacking'])}, "
          f"unsecured {format_units(c['unsecuredBacking'])}")
    print(f"Loans: {', '.join(f'{key} {value}' for key, value in sorted(report['loans'].items())) or 'none'}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable report with integer base-unit amounts")
    parser.add_argument("--block", default="latest", help="read a specific historical block instead of latest")
    args = parser.parse_args(argv)
    try:
        deployment = load_deployment()
        report = read_report(deployment, Cast(deployment), args.block)
    except (CastError, ValueError, OSError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2)) if args.json else print_report(report)
    return 0 if report["integrity"]["holds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
