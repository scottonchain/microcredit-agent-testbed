#!/usr/bin/env python3
"""
Pool health and credit-integrity metrics, read from the live pool's state with Foundry's `cast`.
Nothing is sent; every value is a view call at the latest block, so anyone can recompute it.

    python3 metrics/pool_health.py            # human-readable report
    python3 metrics/pool_health.py --json     # machine-readable

Covers METRICS.md 6 (issuer and backer concentration) and 9 (credit manufactured: the Theorem 1
check, sum of borrow limits <= sum of granted credit + committed stake), plus the pool's balance
sheet and loan outcomes. Metrics that need events over time (cohorts, first-time share) or an
off-chain attestation (human vs bot) are not here; see issue #7.
Override the deployment with RPC, POOL, LENS, SCORES.
"""
import json
import os
import subprocess
import sys

RPC = os.environ.get("RPC", "https://sepolia.base.org")
POOL = os.environ.get("POOL", "0xe3264D64cEF7C7675a548524D883b597e7894169")
LENS = os.environ.get("LENS", "0x01C0586B3Cef50b427411c1278Be25605e8329Dc")
SCORES = os.environ.get("SCORES", "0x5bDe901dA88fc351d93B7cF7AaEb72Af55D38b02")
USDC = 1e6
STATUS = ["None", "Requested", "Active", "Repaid", "Defaulted", "Cancelled"]  # LoanStatus


def call(to, sig, *args):
    """Decoded return values of a view call, as a list (cast's --json output)."""
    out = subprocess.run(["cast", "call", "--json", "--rpc-url", RPC, to, sig, *map(str, args)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def num(to, sig, *args):
    return int(call(to, sig, *args)[0])


def addresses(to, sig):
    return list(call(to, sig)[0])


def main():
    pool = {name: num(POOL, f"{name}()(uint256)") for name in [
        "totalAssets", "lenderCash", "totalLentOut", "reservedLiquidity", "firstLossReserve",
        "totalImpaired", "totalDuesPaid", "protocolFees", "totalStaked", "lenderCount", "getLoanRate"]}
    pool["utilisationBps"] = num(LENS, "getUtilisation()(uint256)")
    pool["sharePrice"] = num(LENS, "sharePrice()(uint256)")

    scored = addresses(SCORES, "getScores()(address[],uint256[])")
    accounts = sorted({a.lower() for sig in ["getBorrowers()(address[])", "getBackers()(address[])",
                                            "getBackedBorrowers()(address[])", "getLenders()(address[])"]
                       for a in addresses(POOL, sig)} | {a.lower() for a in scored})

    limits = granted = committed_stake = 0
    lines = {}
    for a in accounts:
        limits += num(POOL, "getBorrowLimit(address)(uint256,uint256)", a)
        g = num(POOL, "grantedCredit(address)(uint256)", a)
        granted += g
        committed_stake += num(POOL, "stakeCommitted(address)(uint256)", a)
        if g:
            lines[a] = g

    backers = {}
    secured = unsecured = edges = 0
    for b in addresses(POOL, "getBackedBorrowers()(address[])"):
        for backer, s_amt, u_amt in call(POOL, "getBackings(address)((address,uint256,uint256)[])", b)[0]:
            edges += 1
            secured += int(s_amt)
            unsecured += int(u_amt)
            backers[backer.lower()] = backers.get(backer.lower(), 0) + int(s_amt) + int(u_amt)

    loans = {}
    for i in call(POOL, "getAllLoanIds()(uint256[])")[0]:
        status = STATUS[num(POOL, "getLoanTerms(uint256)(uint8,uint256,uint256,uint256,uint256)", i)]
        loans[status] = loans.get(status, 0) + 1

    issuance = {"totalHeld": num(SCORES, "totalHeld()(uint256)"), "maxTotalScore": num(SCORES, "maxTotalScore()(uint256)"),
                "totalScore": num(SCORES, "totalScore()(uint256)"), "scoredAccounts": len(scored)}

    def top_share(d):
        total = sum(d.values())
        return (max(d.values()) / total) if total else 0.0

    report = {
        "pool": pool,
        "integrity": {"accounts": len(accounts), "sumLimits": limits, "sumGrantedCredit": granted,
                      "sumCommittedStake": committed_stake, "slack": granted + committed_stake - limits,
                      "holds": limits <= granted + committed_stake},
        "issuance": issuance,
        "concentration": {"largestLineShare": top_share(lines), "largestBackerShare": top_share(backers),
                          "backingEdges": edges, "securedBacking": secured, "unsecuredBacking": unsecured},
        "loans": loans,
    }
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
        return
    p, i, c, q = pool, report["integrity"], report["concentration"], issuance
    print(f"Pool {POOL} on {RPC}")
    print(f"  assets {p['totalAssets']/USDC:,.2f}  cash {p['lenderCash']/USDC:,.2f}  lent {p['totalLentOut']/USDC:,.2f}  "
          f"reserved {p['reservedLiquidity']/USDC:,.2f}  utilisation {p['utilisationBps']/100:.2f}%  share price {p['sharePrice']/USDC:.4f}")
    print(f"  first-loss reserve {p['firstLossReserve']/USDC:,.2f} (dues {p['totalDuesPaid']/USDC:,.2f})  impaired {p['totalImpaired']/USDC:,.2f}  "
          f"staked {p['totalStaked']/USDC:,.2f}  fees {p['protocolFees']/USDC:,.2f}  lenders {p['lenderCount']}  APR {p['getLoanRate']} bps")
    print(f"Credit integrity (METRICS 9, Theorem 1) over {i['accounts']} accounts:")
    print(f"  sum of limits {i['sumLimits']/USDC:,.2f} <= granted {i['sumGrantedCredit']/USDC:,.2f} + committed stake "
          f"{i['sumCommittedStake']/USDC:,.2f}: {'holds' if i['holds'] else 'VIOLATED'} (slack {i['slack']/USDC:,.2f})")
    print(f"Issuance: held {q['totalHeld']/1e6:.2f} of {q['maxTotalScore']/1e6:.2f} lines, {q['scoredAccounts']} scored accounts")
    print(f"Concentration (METRICS 6): largest line {c['largestLineShare']:.0%} of granted credit, largest backer "
          f"{c['largestBackerShare']:.0%} of backing; {c['backingEdges']} edges, secured {c['securedBacking']/USDC:,.2f}, "
          f"unsecured {c['unsecuredBacking']/USDC:,.2f}")
    print(f"Loans: {', '.join(f'{k} {v}' for k, v in sorted(report['loans'].items())) or 'none'}")


if __name__ == "__main__":
    main()
