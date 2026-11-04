#!/usr/bin/env python3
"""D16 exact-cent operating budget; offline arithmetic, never a loan decision.

This does not implement a legally defined APR calculation, price a provider,
validate consent or deploy/sign/send anything. Unknown costs stay unknown.
See evidence/human-first-mainnet-20261103/operations.md for the operating rules.
"""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
import json
from pathlib import Path


COST_ITEMS = (
    "disbursement", "collection", "treasury_conversion", "gas",
    "assessment", "support", "allocated_overhead", "capital_lock",
)
CASE_FIELDS = {
    "label", "principal_cents", "rate_bps", "term_days", "discounted", "door",
    "consumer_loans_this_year", "cost_basis", "costs_cents",
    "allocation_basis", "volume_basis",
}


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def interest_cents(principal_cents, rate_bps, term_days):
    """Simple ACT/365 interest, rounded down in the borrower's favour."""
    integer(principal_cents, "principal_cents", 1)
    integer(rate_bps, "rate_bps")
    integer(term_days, "term_days", 1)
    return principal_cents * rate_bps * term_days // (10_000 * 365)


def annualized_cost(principal_cents, charge_cents, term_days, discounted):
    """Single-payment diagnostic, including an upfront charge in net proceeds."""
    integer(principal_cents, "principal_cents", 1)
    integer(charge_cents, "charge_cents")
    integer(term_days, "term_days", 1)
    if type(discounted) is not bool:
        raise ValueError("discounted must be a boolean")
    financed = principal_cents - charge_cents if discounted else principal_cents
    if financed <= 0:
        raise ValueError("charge leaves no positive amount financed")
    return Fraction(charge_cents * 365, financed * term_days)


def maximum_charge(principal_cents, ceiling_bps, term_days, discounted):
    """Largest whole-cent charge within the annualized-cost diagnostic ceiling."""
    integer(principal_cents, "principal_cents", 1)
    integer(ceiling_bps, "ceiling_bps")
    integer(term_days, "term_days", 1)
    if type(discounted) is not bool:
        raise ValueError("discounted must be a boolean")
    denominator = 10_000 * 365 + (ceiling_bps * term_days if discounted else 0)
    return principal_cents * ceiling_bps * term_days // denominator


def early_interest_refund(charge_cents, term_days, days_used):
    """Unearned prepaid interest refunded to the next whole cent; no penalty."""
    integer(charge_cents, "charge_cents")
    integer(term_days, "term_days", 1)
    integer(days_used, "days_used")
    if days_used > term_days:
        raise ValueError("days_used cannot exceed term_days")
    earned = charge_cents * days_used // term_days
    return charge_cents - earned


def allocated_cost_cents(total_cost_cents, funded_loans):
    """Allocate all costs (including rejected applicants) and round up."""
    integer(total_cost_cents, "total_cost_cents")
    integer(funded_loans, "funded_loans", 1)
    return (total_cost_cents + funded_loans - 1) // funded_loans


def percentage(value):
    with localcontext() as context:
        context.prec = max(30, len(str(abs(value.numerator))) + len(str(value.denominator)) + 10)
        return str((Decimal(value.numerator) * 100 / Decimal(value.denominator)).quantize(Decimal("0.000001")))


def budget(case):
    """Report a proposed budget's arithmetic; no readiness/approval is implied."""
    if not isinstance(case, dict) or set(case) != CASE_FIELDS:
        raise ValueError("case must contain exactly: " + ", ".join(sorted(CASE_FIELDS)))
    if not isinstance(case["label"], str) or not case["label"].strip():
        raise ValueError("label must be a non-empty string")
    principal = integer(case["principal_cents"], "principal_cents", 1)
    days = integer(case["term_days"], "term_days", 1)
    rate = integer(case["rate_bps"], "rate_bps")
    discounted = case["discounted"]
    charge = interest_cents(principal, rate, days)
    diagnostic = annualized_cost(principal, charge, days, discounted)
    costs = case["costs_cents"]
    if not isinstance(costs, dict) or set(costs) != set(COST_ITEMS):
        raise ValueError("costs_cents must contain exactly: " + ", ".join(COST_ITEMS))
    unknown = [name for name, cost in costs.items() if cost is None]
    for name, cost in costs.items():
        if cost is not None:
            integer(cost, name)
    total = None if unknown else sum(costs.values())
    rail_items = ("disbursement", "collection", "treasury_conversion", "gas")
    rail = None if any(costs[k] is None for k in rail_items) else sum(costs[k] for k in rail_items)
    basis = case["cost_basis"]
    if basis not in ("unknown", "reported", "measured"):
        raise ValueError("cost_basis must be unknown, reported or measured")
    findings = []
    if basis != "measured" or unknown:
        findings.append("COST_MEASUREMENT_REQUIRED")
    allocation = case["allocation_basis"]
    if allocation not in ("funded_first_loan", "completed_cohort_loan"):
        raise ValueError("allocation_basis must be funded_first_loan or completed_cohort_loan")
    volume = case["volume_basis"]
    if volume not in ("assumed", "observed"):
        raise ValueError("volume_basis must be assumed or observed")
    if volume != "observed":
        findings.append("VOLUME_MEASUREMENT_REQUIRED")
    if total is not None and total > 15:
        findings.append("ABOVE_D7_15_CENT_COST_STOP")
    if rail is not None and rail * 10 > principal:
        findings.append("ABOVE_D16_10_PERCENT_RAIL_STOP")
    door = case["door"]
    if door not in ("business", "consumer"):
        raise ValueError("door must be business or consumer")
    if door == "consumer":
        if diagnostic > Fraction(12, 100):
            findings.append("ABOVE_CONSUMER_12_PERCENT_DIAGNOSTIC")
        count = integer(case["consumer_loans_this_year"], "consumer_loans_this_year")
        if count >= 24:
            findings.append("CONSUMER_COUNTER_REQUIRES_CHANGE_BEFORE_LOAN_25")
    return {
        "label": case["label"],
        "scope": "offline budget only; no borrower, provider quote or deployment approval",
        "principal_cents": principal,
        "interest_cents": charge,
        "borrower_receives_cents": principal - charge if discounted else principal,
        "borrower_repays_cents": principal if discounted else principal + charge,
        "annualized_cost_fraction": str(diagnostic),
        "annualized_cost_percent": percentage(diagnostic),
        "consumer_maximum_charge_cents": maximum_charge(principal, 1200, days, discounted),
        "all_in_lender_cost_cents": total,
        "rail_cost_cents": rail,
        "unknown_costs": unknown,
        "cost_basis": basis,
        "allocation_basis": allocation,
        "volume_basis": volume,
        "findings": findings,
        "execution_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path, help="JSON array of hypothetical or private proposed budgets")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    print(json.dumps([budget(case) for case in cases], indent=2))


if __name__ == "__main__":
    main()
