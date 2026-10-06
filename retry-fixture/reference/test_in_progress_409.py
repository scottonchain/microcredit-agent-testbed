"""Checks that the fixture detects the particular errors it claims to detect."""
import unittest
from unittest.mock import patch
import in_progress_409 as fixture


class RegressionChecks(unittest.TestCase):
    def test_scenario_oracles_and_intentional_failure_controls(self):
        for name in fixture.EXPECTED:
            with self.subTest(name=name):
                self.assertTrue(fixture.check(fixture.run(name)))
        for name in ("switch_control", "expiry_control"):
            self.assertEqual(fixture.run(name)["evaluator"]["effects"], 2)

    def test_failed_is_not_a_substitute_for_unknown(self):
        for field in ("after_409", "outcomes"):
            with self.subTest(field=field):
                row = fixture.run("deadline")
                row[field]["original-key"] = "failed"
                self.assertFalse(fixture.check(row))

    def test_hidden_duplicate_fails_the_control_oracle(self):
        row = fixture.run("switch_control")
        row["evaluator"]["effects"] = 1
        self.assertFalse(fixture.check(row))

    def test_changing_hold_policy_to_switch_key_is_detected(self):
        original = fixture.Client.retry

        def mutant(client, now, **kwargs):
            if now == 5:
                kwargs["switch_key"] = True
            return original(client, now, **kwargs)

        with patch.object(fixture.Client, "retry", mutant):
            self.assertFalse(fixture.check(fixture.run("hold")))


if __name__ == "__main__":
    unittest.main()
