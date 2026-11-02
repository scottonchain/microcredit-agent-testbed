import math
import unittest

from pool_stability import (SCREENS, Design, Screen, assess, binomial_tail, expected_net_per_loan, log_drift,
                            lundberg_exponent, max_raw_default_passing, named_cohort_design, outcomes,
                            recommended_design, ruin_bound, screened_default, search, simulate, stop_rule_power)


class ScreeningTests(unittest.TestCase):
    def test_no_screen_is_identity(self):
        out = screened_default(0.10, Screen())
        self.assertAlmostEqual(out["admitted_default"], 0.10)
        self.assertAlmostEqual(out["admission_rate"], 1.0)
        self.assertEqual(out["screen_cost_per_loan"], 0.0)

    def test_evidence_plus_backer_screen_cuts_ten_percent_to_about_three(self):
        out = screened_default(0.10, SCREENS["evidence+backer"])
        self.assertAlmostEqual(out["admitted_default"], 0.02 / 0.65, places=6)
        self.assertAlmostEqual(out["admission_rate"], 0.65)
        # Ten cents per applicant becomes about fifteen cents per funded first loan.
        self.assertAlmostEqual(out["screen_cost_per_loan"], 0.10 / 0.65, places=6)

    def test_screening_is_monotone_in_sensitivity(self):
        weak = screened_default(0.10, Screen(0.3, 0.2))["admitted_default"]
        strong = screened_default(0.10, Screen(0.9, 0.2))["admitted_default"]
        self.assertLess(strong, weak)

    def test_false_rejection_raises_cost_not_default(self):
        a = screened_default(0.10, Screen(0.6, 0.0, 0.05))
        b = screened_default(0.10, Screen(0.6, 0.5, 0.05))
        self.assertGreater(b["screen_cost_per_loan"], a["screen_cost_per_loan"])
        # Rejecting more good applicants makes the admitted pool slightly worse, never better.
        self.assertGreaterEqual(b["admitted_default"], a["admitted_default"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            screened_default(0.10, Screen(1.5, 0.0))
        with self.assertRaises(ValueError):
            screened_default(1.0, Screen())


class OutcomeTests(unittest.TestCase):
    def test_probabilities_sum_to_one_and_tiers_are_present(self):
        rows = outcomes(recommended_design(), 0.10)
        self.assertAlmostEqual(sum(o.prob for o in rows), 1.0)
        self.assertEqual({o.tier for o in rows}, {"first", "repeat"})
        self.assertEqual({o.event for o in rows}, {"repaid", "defaulted"})

    def test_fully_backed_loans_cost_the_pool_nothing_on_default(self):
        for o in outcomes(recommended_design(), 0.10):
            if o.event == "defaulted":
                self.assertEqual(o.pool_gain, 0.0)
                self.assertEqual(o.system_gain, -1.0)

    def test_half_backed_repeat_loans_split_the_loss(self):
        for o in outcomes(named_cohort_design(), 0.10):
            if o.event == "defaulted" and o.tier == "repeat":
                self.assertAlmostEqual(o.pool_gain, -0.5)

    def test_backer_interest_share_moves_interest_not_loss(self):
        base = Design(backer_interest_share=0.0)
        shared = Design(backer_interest_share=0.5)
        self.assertLess(expected_net_per_loan(shared, 0.05)["pool"], expected_net_per_loan(base, 0.05)["pool"])
        self.assertAlmostEqual(expected_net_per_loan(shared, 0.05)["system"], expected_net_per_loan(base, 0.05)["system"])


class LundbergTests(unittest.TestCase):
    def test_exponent_solves_the_lundberg_equation(self):
        design = Design(90, 0.1833, backing_first=0.0, backing_repeat=0.0, screen=SCREENS["evidence+backer"])
        theta = lundberg_exponent(design, 0.10)
        self.assertIsNotNone(theta)
        from pool_stability import _relative_outcomes
        rows = _relative_outcomes(design, 0.10, 0.2, 25.0)
        self.assertAlmostEqual(sum(p * (1 + x) ** (-theta) for p, x in rows), 1.0, places=8)

    def test_no_exponent_when_the_log_drift_is_not_positive(self):
        design = Design(30, 0.0933, backing_first=0.0, backing_repeat=0.0)
        self.assertLess(log_drift(design, 0.10), 0)
        self.assertIsNone(lundberg_exponent(design, 0.10))
        self.assertEqual(ruin_bound(design, 0.10)["ruin_bound"], 1.0)

    def test_bound_shrinks_with_a_larger_reserve_and_with_backing(self):
        design = Design(90, 0.1833, backing_first=0.0, backing_repeat=0.0, screen=SCREENS["evidence+backer"])
        small = ruin_bound(design, 0.10, reserve=100.0, pause=25.0)["ruin_bound"]
        large = ruin_bound(design, 0.10, reserve=400.0, pause=25.0)["ruin_bound"]
        self.assertLess(large, small)
        backed = Design(90, 0.1833, backing_first=1.0, backing_repeat=1.0, screen=SCREENS["evidence+backer"])
        self.assertLess(ruin_bound(backed, 0.10)["ruin_bound"], small)

    def test_bound_dominates_long_seeded_simulations(self):
        # Cases where the bound is strictly between 0 and 1, checked against the simulation.
        cases = (
            (Design(90, 0.1833, backing_first=0.0, backing_repeat=0.0, screen=SCREENS["evidence+backer"]), 0.10),
            (Design(90, 0.0933, backing_first=0.0, backing_repeat=0.0, screen=SCREENS["evidence+backer"]), 0.05),
            (Design(90, 0.1833, backing_first=0.5, backing_repeat=0.25, screen=SCREENS["evidence+backer"]), 0.20),
        )
        for design, raw in cases:
            bound = ruin_bound(design, raw)["ruin_bound"]
            self.assertGreater(bound, 0.0)
            self.assertLess(bound, 1.0)
            sim = simulate(design, raw, loans=1000, runs=400, seed=5)
            self.assertLessEqual(sim["ruin_probability"], bound)

    def test_validation(self):
        with self.assertRaises(ValueError):
            ruin_bound(Design(), 0.05, reserve=20.0, pause=25.0)


class DesignTests(unittest.TestCase):
    def test_open_access_design_grows_the_pool_across_the_band_and_the_system_to_ten_percent(self):
        design = recommended_design()
        for raw in (0.03, 0.05, 0.10, 0.20):
            row = assess(design, raw)
            self.assertTrue(row["pool_grows"], raw)
            self.assertLess(row["ruin_bound"], 1e-6)
        limits = max_raw_default_passing(design)
        self.assertGreaterEqual(limits["pool_max_raw_default"], 0.49)
        self.assertAlmostEqual(limits["system_max_raw_default"], 0.11)

    def test_named_cohort_design_passes_to_fourteen_percent_raw(self):
        limits = max_raw_default_passing(named_cohort_design())
        self.assertAlmostEqual(limits["pool_max_raw_default"], 0.14)
        self.assertAlmostEqual(limits["system_max_raw_default"], 0.11)

    def test_thirty_day_live_rate_without_backing_or_screening_never_grows(self):
        design = Design(30, 0.0933, backing_first=0.0, backing_repeat=0.0)
        limits = max_raw_default_passing(design)
        self.assertEqual(limits["pool_max_raw_default"], 0.0)

    def test_paying_backers_half_the_interest_breaks_pool_growth_at_the_live_rate(self):
        design = Design(90, 0.0933, backing_first=1.0, backing_repeat=0.5, backer_interest_share=0.5,
                        screen=SCREENS["evidence+backer"])
        self.assertLessEqual(max_raw_default_passing(design)["pool_max_raw_default"], 0.02)

    def test_search_orders_passing_designs_first(self):
        rows = search()
        self.assertTrue(rows[0]["pool_passes_band"])
        self.assertTrue(rows[0]["system_passes_band"])
        self.assertIn("18.33%", rows[0]["design"])
        self.assertFalse(rows[-1]["pool_passes_band"])

    def test_simulation_is_deterministic_and_tracks_the_system_scorecard(self):
        design = named_cohort_design()
        a = simulate(design, 0.10, loans=200, runs=50, seed=3)
        b = simulate(design, 0.10, loans=200, runs=50, seed=3)
        self.assertEqual(a, b)
        # Backers absorb losses, so the system ends below the pool when there are defaults.
        self.assertLess(a["median_final_system"], a["median_final_reserve"])


class StopRuleTests(unittest.TestCase):
    def test_binomial_tail_matches_closed_form(self):
        # P(at least 2 of 20) at 3% = 1 - 0.97^20 - 20 * 0.03 * 0.97^19
        expected = 1 - 0.97 ** 20 - 20 * 0.03 * 0.97 ** 19
        self.assertAlmostEqual(binomial_tail(20, 2, 0.03), expected, places=10)
        self.assertAlmostEqual(binomial_tail(20, 0, 0.03), 1.0, places=12)
        self.assertAlmostEqual(binomial_tail(20, 21, 0.03), 0.0)

    def test_two_in_twenty_rule_is_weak_at_three_percent_and_strong_at_twenty(self):
        power = {r["true_default"]: r["stop_probability"] for r in stop_rule_power()}
        self.assertLess(power[0.03], 0.15)
        self.assertGreater(power[0.20], 0.90)


if __name__ == "__main__":
    unittest.main()
