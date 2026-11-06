"""Offline case accounting. Business cash, human income and pool surplus differ.

One currency and one explicit participant boundary are required. Principal flows
and debt forgiveness are not earned human income. Missing human payout evidence
leaves human outcomes incomplete even when a business margin can be computed.
This is not underwriting, causal evidence or a funding offer.
"""
import json
import sys
from decimal import Decimal, InvalidOperation


def number(row, key, signed=False):
    value = row.get(key)
    if value is None or isinstance(value, bool):
        raise ValueError(f"Missing measured input: {key}")
    try:
        value = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"Invalid measured input: {key}") from error
    if not value.is_finite() or (value < 0 and not signed):
        raise ValueError(f"Invalid measured input: {key}")
    return value


def calculate(row):
    business = {key: number(row, key) for key in (
        "customer_cash_received", "non_financing_cash_costs", "finance_fees_paid")}
    business_cash = (business["customer_cash_received"]
                     - business["non_financing_cash_costs"]
                     - business["finance_fees_paid"])
    result = {"business_net_operating_cash": str(business_cash),
              "human_outcome": {"status": "incomplete"},
              "pool_outcome": {"status": "incomplete"},
              "passes_three_accounting_gates": False,
              "qualification": "Accounting only. Verify consent, ownership, alternatives, additionality and recurrence separately."}
    try:
        if not row.get("participant_boundary"):
            raise ValueError("Missing explicit participant accounting boundary")
        if row.get("participant_earned_cash_source_verified") is not True:
            raise ValueError("Earned human payout provenance unverified; exclude loans and debt forgiveness")
        n = {key: number(row, key, signed=key == "baseline_net_human_cash") for key in (
            "participant_earned_cash_received", "participant_unreimbursed_costs",
            "participant_finance_fees_paid", "participant_all_hours",
            "participant_hourly_floor", "baseline_net_human_cash", "baseline_hours")}
        if n["participant_all_hours"] <= 0:
            raise ValueError("Participant all-hours total must be positive")
        human_cash = (n["participant_earned_cash_received"]
                      - n["participant_unreimbursed_costs"]
                      - n["participant_finance_fees_paid"])
        hourly = human_cash / n["participant_all_hours"]
        incremental = human_cash - n["baseline_net_human_cash"]
        result["human_outcome"] = {
            "status": "accounted", "boundary": row["participant_boundary"],
            "net_spendable_earned_cash": str(human_cash),
            "incremental_cash_vs_stated_baseline": str(incremental),
            "all_hours_effective_pay": str(hourly),
            "meets_participant_floor": hourly >= n["participant_hourly_floor"],
            "positive_incremental_cash": incremental > 0,
            "positive_earned_cash": human_cash > 0,
            "baseline_effective_pay": str(n["baseline_net_human_cash"] / n["baseline_hours"]) if n["baseline_hours"] else None,
        }
    except ValueError as error:
        result["human_outcome"]["reason"] = str(error)
    try:
        n = {key: number(row, key) for key in (
            "pool_opening_cash", "principal_advanced", "principal_returned",
            "principal_written_off", "pool_fee_cash_received", "pool_cash_costs",
            "pool_capital_lock_cost", "pool_topups", "unpaid_support_cost")}
        if n["principal_returned"] + n["principal_written_off"] != n["principal_advanced"]:
            raise ValueError("Cycle unsettled: principal returned plus writeoffs must equal advances")
        cash_delta = n["pool_fee_cash_received"] - n["pool_cash_costs"] - n["principal_written_off"]
        economic_delta = cash_delta - n["pool_capital_lock_cost"] - n["unpaid_support_cost"]
        closing = n["pool_opening_cash"] + cash_delta + n["pool_topups"]
        if closing < 0:
            raise ValueError("Negative closing cash: missing funding, liability or inconsistent records")
        result["pool_outcome"] = {
            "status": "settled", "closing_cash_including_topups": str(closing),
            "cash_change_excluding_topups": str(cash_delta),
            "full_cost_surplus_excluding_topups": str(economic_delta),
            "positive_full_cost_surplus": economic_delta > 0,
        }
    except ValueError as error:
        result["pool_outcome"]["reason"] = str(error)
    human, pool = result["human_outcome"], result["pool_outcome"]
    result["passes_three_accounting_gates"] = (
        human.get("positive_incremental_cash", False)
        and human.get("positive_earned_cash", False)
        and human.get("meets_participant_floor", False)
        and pool.get("positive_full_cost_surplus", False))
    return result


if __name__ == "__main__":
    try:
        result = calculate(json.load(open(sys.argv[1], encoding="utf-8")))
    except (ValueError, IndexError) as error:
        print(json.dumps({"status": "incomplete", "reason": str(error)}))
        sys.exit(2)
    print(json.dumps(result, indent=2))
