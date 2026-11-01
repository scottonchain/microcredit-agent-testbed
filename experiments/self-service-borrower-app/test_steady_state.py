import unittest

from steady_state import (LoanTerms, annual_growth_rate, break_even_apr, break_even_default, design_proof,
                          expected_net, interest, ruin_probability, table)


class BreakEvenTests(unittest.TestCase):
    def test_live_rate_matches_published_arithmetic(self):
        # NORTH_STAR / human borrowing plan: 25 USDC for 30 days at 9.33% is about 0.19 USDC.
        t = LoanTerms(25, 30, 0.0933, 0.0)
        self.assertAlmostEqual(interest(t), 0.1917, places=3)

    def test_break_even_default_at_live_rate_is_under_one_percent(self):
        t = LoanTerms(25, 30, 0.0933, 0.0)
        d = break_even_default(t)
        self.assertGreater(d, 0.007)
        self.assertLess(d, 0.008)
        # The two break-even functions are inverses of each other at that point.
        self.assertAlmostEqual(break_even_apr(LoanTerms(25, 30, 0.0, d)), 0.0933, places=4)

    def test_unsecured_digital_benchmark_needs_payday_pricing(self):
        # 10% per-loan default with full loss needs more than 100% APR on a 30-day loan.
        self.assertGreater(break_even_apr(LoanTerms(25, 30, 0.0, 0.10, 1.0)), 1.0)
        # Recovering 80% from stake brings the same default rate under 30%.
        self.assertLess(break_even_apr(LoanTerms(25, 30, 0.0, 0.10, 0.2)), 0.30)

    def test_break_even_is_monotone_in_default_loss_and_cost(self):
        base = LoanTerms(25, 30, 0.0, 0.02, 1.0, 0.0)
        self.assertLess(break_even_apr(base), break_even_apr(LoanTerms(25, 30, 0.0, 0.03, 1.0, 0.0)))
        self.assertGreater(break_even_apr(base), break_even_apr(LoanTerms(25, 30, 0.0, 0.02, 0.5, 0.0)))
        self.assertLess(break_even_apr(base), break_even_apr(LoanTerms(25, 30, 0.0, 0.02, 1.0, 0.10)))

    def test_longer_term_lowers_break_even_for_a_per_loan_default_rate(self):
        self.assertLess(break_even_apr(LoanTerms(25, 90, 0.0, 0.05)), break_even_apr(LoanTerms(25, 30, 0.0, 0.05)))

    def test_fifty_cent_assessment_cost_dominates_a_25_usdc_loan(self):
        with_cost = break_even_apr(LoanTerms(25, 30, 0.0, 0.01, 1.0, 0.50))
        without = break_even_apr(LoanTerms(25, 30, 0.0, 0.01, 1.0, 0.0))
        self.assertGreater(with_cost - without, 0.20)

    def test_growth_sign_follows_expected_net(self):
        growing = LoanTerms(25, 30, 0.0933, 0.005)
        shrinking = LoanTerms(25, 30, 0.0933, 0.02)
        self.assertGreater(expected_net(growing), 0)
        self.assertGreater(annual_growth_rate(growing, 0.5), 0)
        self.assertLess(annual_growth_rate(shrinking, 0.5), 0)
        # Zero loss, half utilisation: under 5% a year at the live rate.
        self.assertAlmostEqual(annual_growth_rate(LoanTerms(25, 30, 0.0933, 0.0), 0.5), 0.04665, places=4)

    def test_table_shape(self):
        rows = table()
        self.assertEqual(len(rows), 24)
        self.assertTrue(all(r["break_even_apr"] >= 0 for r in rows))

    def test_validation(self):
        with self.assertRaises(ValueError):
            interest(LoanTerms(0, 30, 0.1, 0.0))
        with self.assertRaises(ValueError):
            interest(LoanTerms(25, 30, 0.1, 1.0))
        with self.assertRaises(ValueError):
            annual_growth_rate(LoanTerms(25, 30, 0.1, 0.0), 1.5)


class DesignProofTests(unittest.TestCase):
    def test_full_loss_designs_fail_and_stake_covered_designs_pass_the_band(self):
        rows = design_proof(runs=200)
        by = {r["design"]: r for r in rows}
        self.assertFalse(by["live rate, 30 days, full loss to pool"]["passes_band"])
        self.assertFalse(by["live rate, 90 days, full loss to pool"]["passes_band"])
        # At the live rate, 80% stake cover is marginal at 10% default (negative by a fraction of a cent).
        self.assertFalse(by["live rate, 90 days, stakers cover 80%"]["passes_band"])
        self.assertTrue(by["18.33% (10%-default calibration row), 90 days, stakers cover 80%"]["passes_band"])
        self.assertTrue(by["live rate, 90 days, stakers cover 100%"]["passes_band"])
        for r in rows:
            self.assertEqual([p["default_per_loan"] for p in r["points"]], [0.03, 0.05, 0.10])


class RuinTests(unittest.TestCase):
    def test_deterministic_for_a_seed(self):
        t = LoanTerms(25, 30, 0.0933, 0.03)
        a = ruin_probability(t, 100, 100, 300, seed=7)
        b = ruin_probability(t, 100, 100, 300, seed=7)
        self.assertEqual(a, b)

    def test_zero_default_never_ruins_and_grows(self):
        t = LoanTerms(25, 30, 0.0933, 0.0)
        out = ruin_probability(t, 100, 100, 50)
        self.assertEqual(out["ruin_probability"], 0.0)
        self.assertGreater(out["median_final_reserve"], 100)

    def test_exposure_cap_limits_a_single_loss(self):
        # One loan at most a fifth of the reserve: a single default cannot take more than 20 of 100.
        t = LoanTerms(100, 30, 0.0, 0.999999)
        out = ruin_probability(t, 100, 1, 20, floor=1.0)
        self.assertEqual(out["ruin_probability"], 0.0)
        self.assertGreaterEqual(out["p10_final_reserve"], 80 - 1e-9)

    def test_expected_value_neutral_pool_still_ruins_without_the_exposure_cap(self):
        d = 0.05
        apr = break_even_apr(LoanTerms(25, 30, 0.0, d))
        neutral = LoanTerms(25, 30, apr, d)
        self.assertAlmostEqual(expected_net(neutral), 0.0, places=9)
        # Fixed 25 USDC loans from a 100 USDC reserve: four net losses end the pool.
        uncapped = ruin_probability(neutral, 100, 500, 400, seed=3, exposure_share=1.0, floor=25.0)
        self.assertGreater(uncapped["ruin_probability"], 0.10)
        # The one-fifth exposure rule shrinks loans with the reserve and makes ruin rare.
        capped = ruin_probability(neutral, 100, 500, 400, seed=3, exposure_share=0.2, floor=5.0)
        self.assertLess(capped["ruin_probability"], uncapped["ruin_probability"])

if __name__ == "__main__":
    unittest.main()
