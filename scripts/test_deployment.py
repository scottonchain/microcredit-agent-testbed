import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch

from deployment import Cast, CastError, UINT256_MAX, load_deployment, token_units


class DeploymentTests(unittest.TestCase):
    def test_exact_fractional_and_large_amounts(self):
        self.assertEqual(token_units("0.000001"), 1)
        self.assertEqual(token_units("0005.250001"), 5_250_001)
        self.assertEqual(token_units("9223372036854"), 9_223_372_036_854_000_000)
        self.assertEqual(token_units("0", allow_zero=True), 0)

    def test_rejects_shell_expressions_and_invalid_units(self):
        for value in ("0", "-1", "NaN", "1e6", "1.0000001", "1+2", "$(touch nowhere)", "1 2", str(UINT256_MAX)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                token_units(value)

    def test_descriptor_overrides_are_independent_and_validated(self):
        original = load_deployment({})
        changed = load_deployment({"POOL": "0x" + "1" * 40})
        self.assertNotEqual(original["pool"], changed["pool"])
        self.assertEqual(load_deployment({}), original)
        with self.assertRaises(ValueError):
            load_deployment({"USDC": "invalid"})

    def test_wrong_chain_rejected(self):
        client = Cast(load_deployment({}))
        with patch.object(client, "run", return_value="1"), self.assertRaisesRegex(CastError, "expected Base Sepolia"):
            client.check_chain()

    def test_wrong_token_and_decimals_rejected(self):
        client = Cast(load_deployment({}))
        with patch.object(client, "call", return_value=["0x" + "1" * 40]), self.assertRaisesRegex(CastError, "wiring mismatch"):
            client.check_wiring()
        d = client.deployment
        with patch.object(client, "call", side_effect=[[d["token"]["address"]], [d["scores"]], [d["pool"]], [18]]), self.assertRaisesRegex(CastError, "decimals"):
            client.check_wiring()

    def test_timeout_never_retries_or_prints_the_command(self):
        client = Cast(load_deployment({}))
        with patch("deployment.subprocess.run", side_effect=subprocess.TimeoutExpired(["cast", "private-value"], 60)) as run:
            with self.assertRaises(CastError) as caught:
                client.send("private-value", client.deployment["pool"], "stake(uint256)", 1)
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("private-value", str(caught.exception))

    def test_failed_receipt_stops_dependent_send(self):
        client = Cast(load_deployment({}))
        receipt = {"transactionHash": "0x" + "a" * 64, "status": "0x0"}
        with patch.object(client, "run", return_value=json.dumps(receipt)), self.assertRaisesRegex(CastError, "reverted"):
            client.send("test-placeholder", client.deployment["pool"], "stake(uint256)", 1)

    def test_errors_redact_key(self):
        client = Cast(load_deployment({}))
        result = subprocess.CompletedProcess([], 1, "", "rejected private-value")
        with patch("deployment.subprocess.run", return_value=result), self.assertRaises(CastError) as caught:
            client.run("wallet", "address", "--private-key", "private-value")
        self.assertNotIn("private-value", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
