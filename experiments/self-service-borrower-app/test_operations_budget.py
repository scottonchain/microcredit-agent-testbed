import unittest
from fractions import Fraction

from operations_budget import (COST_ITEMS, allocated_cost_cents, annualized_cost, budget,
                               early_interest_refund, interest_cents, maximum_charge)


def example(**changes):
    row = dict(label="fictional arithmetic fixture", principal_cents=1000,
               rate_bps=933, term_days=90, discounted=True, door="consumer",
               consumer_loans_this_year=0, cost_basis="unknown",
               allocation_basis="funded_first_loan", volume_basis="assumed",
               costs_cents={key: None for key in COST_ITEMS})
    row.update(changes)
    return row


class OperationsBudgetTests(unittest.TestCase):
    def test_first_loan_example_reconciles_dollar_cash_flows(self):
        out = budget(example())
        self.assertEqual(out["interest_cents"], 23)
        self.assertEqual(out["borrower_receives_cents"], 977)
        self.assertEqual(out["borrower_repays_cents"], 1000)
        self.assertEqual(Fraction(out["annualized_cost_fraction"]), Fraction(23 * 365, 977 * 90))
        self.assertFalse(out["execution_authorized"])

    def test_repeat_loan_interest_is_paid_at_maturity(self):
        out = budget(example(principal_cents=2000, discounted=False))
        self.assertEqual(out["borrower_receives_cents"], 2000)
        self.assertEqual(out["borrower_repays_cents"], 2046)

    def test_hypothetical_25_cent_30_day_quote_exceeds_consumer_door(self):
        self.assertGreater(annualized_cost(1000, 25, 30, False), Fraction(30, 100))
        self.assertGreater(annualized_cost(1000, 25, 30, True), Fraction(31, 100))
        self.assertEqual(maximum_charge(1000, 1200, 30, False), 9)
        self.assertEqual(maximum_charge(1000, 1200, 30, True), 9)

    def test_actual_round_two_25_cent_90_day_illustration_is_below_diagnostic_ceiling(self):
        self.assertLess(annualized_cost(1000, 25, 90, False), Fraction(12, 100))
        self.assertLess(annualized_cost(1000, 25, 90, True), Fraction(12, 100))

    def test_screen_cost_counts_rejected_applicants_and_rounds_up(self):
        # D7's assumed 100 applicants at10c,65 funded:15.3846c each.
        self.assertEqual(allocated_cost_cents(100 * 10, 65), 16)
        costs = {key: 0 for key in COST_ITEMS}
        costs.update(assessment=16, support=2)
        self.assertIn("ABOVE_D7_15_CENT_COST_STOP", budget(example(costs_cents=costs, cost_basis="reported"))["findings"])
        with self.assertRaises(ValueError):
            allocated_cost_cents(10, 0)

    def test_nominal_ceiling_does_not_ignore_discounted_proceeds(self):
        out = budget(example(rate_bps=1200))
        self.assertEqual(out["interest_cents"], 29)
        self.assertIn("ABOVE_CONSUMER_12_PERCENT_DIAGNOSTIC", out["findings"])
        self.assertEqual(out["consumer_maximum_charge_cents"], 28)

    def test_maximum_whole_cent_charge_is_exact_at_boundary(self):
        for principal in (100, 1000, 2000):
            for days in (30, 90, 365):
                for discounted in (False, True):
                    charge = maximum_charge(principal, 1200, days, discounted)
                    self.assertLessEqual(annualized_cost(principal, charge, days, discounted), Fraction(12, 100))
                    self.assertGreater(annualized_cost(principal, charge + 1, days, discounted), Fraction(12, 100))

    def test_unknown_fees_never_become_a_zero_cost_quote(self):
        out = budget(example())
        self.assertIsNone(out["all_in_lender_cost_cents"])
        self.assertIsNone(out["rail_cost_cents"])
        self.assertEqual(set(out["unknown_costs"]), set(COST_ITEMS))
        self.assertIn("COST_MEASUREMENT_REQUIRED", out["findings"])

    def test_reported_prices_do_not_count_as_measurement(self):
        costs = {key: 0 for key in COST_ITEMS}
        self.assertIn("COST_MEASUREMENT_REQUIRED", budget(example(costs_cents=costs, cost_basis="reported"))["findings"])

    def test_measured_costs_with_future_volume_are_not_measured_allocation(self):
        costs = {key: 0 for key in COST_ITEMS}
        out = budget(example(costs_cents=costs, cost_basis="measured", allocation_basis="completed_cohort_loan"))
        self.assertIn("VOLUME_MEASUREMENT_REQUIRED", out["findings"])
        out = budget(example(costs_cents=costs, cost_basis="measured", volume_basis="observed"))
        self.assertNotIn("VOLUME_MEASUREMENT_REQUIRED", out["findings"])
        self.assertFalse(out["execution_authorized"])

    def test_all_costs_count_and_stop_thresholds_are_strict(self):
        costs = {key: 0 for key in COST_ITEMS}
        costs["support"] = 15
        self.assertNotIn("ABOVE_D7_15_CENT_COST_STOP", budget(example(costs_cents=costs))["findings"])
        costs["allocated_overhead"] = 1
        self.assertIn("ABOVE_D7_15_CENT_COST_STOP", budget(example(costs_cents=costs))["findings"])
        costs["allocated_overhead"] = 0
        costs["collection"] = 100
        self.assertNotIn("ABOVE_D16_10_PERCENT_RAIL_STOP", budget(example(costs_cents=costs))["findings"])
        costs["collection"] = 101
        self.assertIn("ABOVE_D16_10_PERCENT_RAIL_STOP", budget(example(costs_cents=costs))["findings"])

    def test_fixed_provider_charges_count_in_both_cost_gates(self):
        costs = {key: 0 for key in COST_ITEMS}
        costs.update(collection=16, allocated_overhead=31)
        out = budget(example(costs_cents=costs, cost_basis="reported"))
        self.assertEqual(out["rail_cost_cents"], 47)
        self.assertEqual(out["all_in_lender_cost_cents"], 47)
        self.assertIn("ABOVE_D7_15_CENT_COST_STOP", out["findings"])
        self.assertNotIn("ABOVE_D16_10_PERCENT_RAIL_STOP", out["findings"])
        costs["collection"] = 70
        out = budget(example(costs_cents=costs, cost_basis="reported"))
        self.assertEqual(out["rail_cost_cents"], 101)
        self.assertIn("ABOVE_D16_10_PERCENT_RAIL_STOP", out["findings"])

    def test_consumer_counter_stops_before_25th_not_after(self):
        flag = "CONSUMER_COUNTER_REQUIRES_CHANGE_BEFORE_LOAN_25"
        self.assertNotIn(flag, budget(example(consumer_loans_this_year=23))["findings"])
        self.assertIn(flag, budget(example(consumer_loans_this_year=24))["findings"])
        self.assertNotIn(flag, budget(example(door="business", consumer_loans_this_year=24))["findings"])

    def test_prepaid_interest_is_refunded_on_early_payment(self):
        self.assertEqual(early_interest_refund(23, 90, 0), 23)
        self.assertEqual(early_interest_refund(23, 90, 30), 16)
        self.assertEqual(early_interest_refund(23, 90, 90), 0)

    def test_invalid_amounts_and_missing_cost_lines_fail(self):
        for bad in (-1, True, 1.5, "10"):
            with self.assertRaises(ValueError):
                interest_cents(bad, 933, 90)
        with self.assertRaises(ValueError):
            annualized_cost(100, 100, 90, True)
        with self.assertRaises(ValueError):
            annualized_cost(1000, 20, 90, "false")
        with self.assertRaises(ValueError):
            budget(example(costs_cents={}))
        with self.assertRaises(ValueError):
            budget(example(borrower_fee_cents=50))
        incomplete = example()
        del incomplete["rate_bps"]
        with self.assertRaises(ValueError):
            budget(incomplete)
        with self.assertRaises(ValueError):
            early_interest_refund(23, 90, 91)


if __name__ == "__main__":
    unittest.main()
