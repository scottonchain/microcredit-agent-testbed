"""Synthetic accounting controls only, never evidence of a real order."""
import unittest
from economics import calculate


def fixture():
    return dict(customer_cash_received=150, non_financing_cash_costs=100,
                finance_fees_paid=5, participant_boundary="one synthetic owner",
                participant_earned_cash_source_verified=True,
                participant_earned_cash_received=45, participant_unreimbursed_costs=0,
                participant_finance_fees_paid=0, participant_all_hours=5,
                participant_hourly_floor=8, baseline_net_human_cash=0,
                baseline_hours=0, pool_opening_cash=100, principal_advanced=100,
                principal_returned=100, principal_written_off=0,
                pool_fee_cash_received=5, pool_cash_costs=2,
                pool_capital_lock_cost=1, pool_topups=0, unpaid_support_cost=1)


class AccountingTests(unittest.TestCase):
    def test_principal_not_counted_twice(self):
        r = calculate(fixture())
        self.assertEqual(r["business_net_operating_cash"], "45")
        self.assertEqual(r["human_outcome"]["net_spendable_earned_cash"], "45")
        self.assertTrue(r["passes_three_accounting_gates"])

    def test_topup_not_profit(self):
        row = fixture(); row["pool_topups"] = 50
        r = calculate(row)["pool_outcome"]
        self.assertEqual(r["closing_cash_including_topups"], "153")
        self.assertEqual(r["full_cost_surplus_excluding_topups"], "1")

    def test_default_reduces_pool(self):
        row = fixture(); row.update(principal_returned=90, principal_written_off=10)
        self.assertEqual(calculate(row)["pool_outcome"]["full_cost_surplus_excluding_topups"], "-9")

    def test_unsettled_cycle_incomplete(self):
        row = fixture(); row["principal_returned"] = 90
        r = calculate(row)
        self.assertEqual(r["pool_outcome"]["status"], "incomplete")
        self.assertFalse(r["passes_three_accounting_gates"])

    def test_missing_hours_not_zero(self):
        row = fixture(); row["participant_all_hours"] = None
        self.assertEqual(calculate(row)["human_outcome"]["status"], "incomplete")

    def test_rework_lowers_hourly_income(self):
        row = fixture(); row["participant_all_hours"] = 10
        self.assertFalse(calculate(row)["human_outcome"]["meets_participant_floor"])

    def test_negative_baseline_is_not_discarded(self):
        row = fixture(); row["baseline_net_human_cash"] = -10
        self.assertEqual(calculate(row)["human_outcome"]["incremental_cash_vs_stated_baseline"], "55")

    def test_agency_profit_is_not_unknown_human_income(self):
        row = fixture(); row["participant_earned_cash_received"] = None
        r = calculate(row)
        self.assertEqual(r["business_net_operating_cash"], "45")
        self.assertEqual(r["human_outcome"]["status"], "incomplete")
        self.assertFalse(r["passes_three_accounting_gates"])

    def test_agency_profit_with_zero_human_distribution_fails(self):
        row = fixture(); row["participant_earned_cash_received"] = 0
        r = calculate(row)
        self.assertEqual(r["business_net_operating_cash"], "45")
        self.assertFalse(r["passes_three_accounting_gates"])

    def test_unverified_loan_proceeds_cannot_be_human_income(self):
        row = fixture(); row["participant_earned_cash_source_verified"] = False
        self.assertEqual(calculate(row)["human_outcome"]["status"], "incomplete")

    def test_zero_income_cannot_pass_via_negative_baseline_and_zero_floor(self):
        row = fixture()
        row.update(participant_earned_cash_received=0,
                   baseline_net_human_cash=-10, participant_hourly_floor=0)
        r = calculate(row)
        self.assertTrue(r["human_outcome"]["positive_incremental_cash"])
        self.assertFalse(r["passes_three_accounting_gates"])

    def test_malformed_import_is_incomplete(self):
        row = fixture(); row["participant_earned_cash_received"] = "not a number"
        self.assertEqual(calculate(row)["human_outcome"]["status"], "incomplete")
        row["customer_cash_received"] = "bad"
        with self.assertRaises(ValueError):
            calculate(row)


if __name__ == "__main__":
    unittest.main()
