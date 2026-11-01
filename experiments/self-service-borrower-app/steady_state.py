#!/usr/bin/env python3
"""Steady-state arithmetic for a small revolving USDC pool.

Answers one operator question from 2026-11-01: can the numbers be adjusted so
that defaults do not wipe out the interest, so the pool grows in steady state?

The model is deliberately small and exact. Per loan of principal P for T days
at annual rate a, with per-loan default probability d, loss given default L
(share of principal not recovered from stake or other security) and per-loan
cost c (gas subsidy, paymaster fee, assessment inference, support):

    interest           = P * a * T / 365
    expected net       = (1 - d) * interest - d * L * P - c
    break-even rate a* = (d * L * P + c) / ((1 - d) * P * T / 365)

A defaulted loan is assumed to pay no interest. Growth per year on reserve R at
utilisation u is u * (365 / T) * expected_net / P. The ruin estimate draws loan
outcomes sequentially from a seeded generator, caps each loan at a fifth of the
reserve (NORTH_STAR.md exposure rule) and reports the share of runs in which the
reserve falls below the smallest useful loan. Expected-value neutrality is not
solvency: a finite pool can be exhausted by an ordinary loss sequence.

Analysis only. No live rate, default rate or cost is measured here; every input
is a labelled assumption. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass

DAYS_IN_YEAR = 365


@dataclass(frozen=True)
class LoanTerms:
    principal: float
    term_days: int
    apr: float
    default_per_loan: float
    loss_given_default: float = 1.0
    cost_per_loan: float = 0.0

    def validate(self) -> None:
        if self.principal <= 0 or self.term_days <= 0:
            raise ValueError("principal and term_days must be positive")
        if not 0 <= self.default_per_loan < 1:
            raise ValueError("default_per_loan must be in [0, 1)")
        if not 0 <= self.loss_given_default <= 1:
            raise ValueError("loss_given_default must be in [0, 1]")
        if self.apr < 0 or self.cost_per_loan < 0:
            raise ValueError("apr and cost_per_loan must be non-negative")


def interest(terms: LoanTerms) -> float:
    terms.validate()
    return terms.principal * terms.apr * terms.term_days / DAYS_IN_YEAR


def expected_net(terms: LoanTerms) -> float:
    terms.validate()
    d = terms.default_per_loan
    return (1 - d) * interest(terms) - d * terms.loss_given_default * terms.principal - terms.cost_per_loan


def break_even_apr(terms: LoanTerms) -> float:
    """Smallest annual rate at which expected net per loan is zero."""
    terms.validate()
    d = terms.default_per_loan
    numerator = d * terms.loss_given_default * terms.principal + terms.cost_per_loan
    denominator = (1 - d) * terms.principal * terms.term_days / DAYS_IN_YEAR
    return numerator / denominator


def break_even_default(terms: LoanTerms) -> float:
    """Largest per-loan default probability at which expected net is zero, at the given rate."""
    terms.validate()
    i = interest(terms)
    loss = terms.loss_given_default * terms.principal
    # (1 - d) i - d loss - c = 0  ->  d = (i - c) / (i + loss)
    if i + loss == 0:
        return 0.0
    return max(0.0, (i - terms.cost_per_loan) / (i + loss))


def annual_growth_rate(terms: LoanTerms, utilisation: float) -> float:
    """Expected growth of the pool per year as a share of capital, at the given utilisation."""
    if not 0 <= utilisation <= 1:
        raise ValueError("utilisation must be in [0, 1]")
    turns = DAYS_IN_YEAR / terms.term_days
    return utilisation * turns * expected_net(terms) / terms.principal


def ruin_probability(terms: LoanTerms, reserve: float, loans: int, runs: int, seed: int = 1,
                     exposure_share: float = 0.2, floor: float = 1.0) -> dict:
    """Share of seeded runs in which the reserve drops below `floor` within `loans` loans.

    Each loan is min(terms.principal, exposure_share * reserve). Interest is earned
    pro rata on the actual loan size. Costs are charged per loan.
    """
    terms.validate()
    if reserve <= 0 or loans <= 0 or runs <= 0:
        raise ValueError("reserve, loans and runs must be positive")
    rng = random.Random(seed)
    ruined = 0
    finals = []
    rate = terms.apr * terms.term_days / DAYS_IN_YEAR
    for _ in range(runs):
        r = reserve
        for _ in range(loans):
            size = min(terms.principal, exposure_share * r)
            if size < floor:
                break
            if rng.random() < terms.default_per_loan:
                r -= size * terms.loss_given_default
            else:
                r += size * rate
            r -= terms.cost_per_loan
            if r < floor:
                break
        if r < floor:
            ruined += 1
        finals.append(r)
    finals.sort()
    return {
        "runs": runs,
        "loans": loans,
        "ruin_probability": ruined / runs,
        "median_final_reserve": finals[len(finals) // 2],
        "p10_final_reserve": finals[len(finals) // 10],
    }


def table(principal: float = 25.0) -> list[dict]:
    rows = []
    for term in (30, 90):
        for d in (0.0077, 0.01, 0.03, 0.05, 0.10, 0.20):
            for lgd in (1.0, 0.2):
                t = LoanTerms(principal, term, 0.0, d, lgd)
                rows.append({"term_days": term, "default_per_loan": d, "loss_given_default": lgd,
                             "break_even_apr": round(break_even_apr(t), 4)})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--principal", type=float, default=25.0)
    parser.add_argument("--term-days", type=int, default=30)
    parser.add_argument("--apr", type=float, default=0.0933, help="live testnet rate is 0.0933")
    parser.add_argument("--default", dest="default_per_loan", type=float, default=0.01)
    parser.add_argument("--lgd", type=float, default=1.0)
    parser.add_argument("--cost", type=float, default=0.0)
    parser.add_argument("--utilisation", type=float, default=0.5)
    parser.add_argument("--reserve", type=float, default=100.0)
    parser.add_argument("--loans", type=int, default=100)
    parser.add_argument("--runs", type=int, default=2000)
    parser.add_argument("--table", action="store_true", help="print the break-even table only")
    args = parser.parse_args(argv)
    if args.table:
        print(json.dumps(table(args.principal), indent=1))
        return 0
    terms = LoanTerms(args.principal, args.term_days, args.apr, args.default_per_loan, args.lgd, args.cost)
    out = {
        "inputs": terms.__dict__,
        "interest_per_loan": round(interest(terms), 6),
        "expected_net_per_loan": round(expected_net(terms), 6),
        "break_even_apr_at_this_default": round(break_even_apr(terms), 4),
        "break_even_default_at_this_apr": round(break_even_default(terms), 4),
        "annual_growth_rate_at_utilisation": round(annual_growth_rate(terms, args.utilisation), 4),
        "ruin": ruin_probability(terms, args.reserve, args.loans, args.runs),
        "note": "Assumptions, not measurements. Pool growth is the reserve scorecard only; human benefit is scored separately.",
    }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
