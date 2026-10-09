"""Checks that the fixture detects the particular errors it claims to detect."""
import unittest
from unittest.mock import patch
import in_progress_409 as fixture
import kill_points
import scorecard


class InProgressChecks(unittest.TestCase):
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


class ScorecardChecks(unittest.TestCase):
    def test_every_effect_table_remains_an_independent_gate(self):
        for module, _ in scorecard.SCRIPTS:
            with self.subTest(script=module.__name__):
                rows = scorecard.rows_of(module)
                self.assertTrue(rows)
                self.assertTrue(all(row["ok"] for row in rows))
                key = next(iter(module.EXPECTED))
                value = module.EXPECTED[key]
                wrong = value + 1 if isinstance(value, int) else (value[0] + 1, *value[1:])
                with patch.dict(module.EXPECTED, {key: wrong}):
                    with self.assertRaisesRegex(SystemExit, "failed its expected table"):
                        scorecard.rows_of(module)

    def test_observation_failure_restores_the_shared_worker(self):
        provider, recover = kill_points.KillingProvider, kill_points.recover_as
        with patch.object(scorecard, "traced_run", side_effect=RuntimeError("probe failed")):
            with self.assertRaisesRegex(RuntimeError, "probe failed"):
                scorecard.observation_check()
        self.assertIs(kill_points.KillingProvider, provider)
        self.assertIs(kill_points.recover_as, recover)
        # A failed observation must not contaminate a later evaluation.
        self.assertTrue(all(row["ok"] for row in scorecard.rows_of(kill_points)))

    def test_observation_does_not_contaminate_subsequent_cells(self):
        before = {module: scorecard.rows_of(module) for module, _ in scorecard.SCRIPTS}
        scorecard.observation_check()
        for module, expected in before.items():
            with self.subTest(script=module.__name__):
                self.assertEqual(scorecard.rows_of(module), expected)


if __name__ == "__main__":
    unittest.main()
