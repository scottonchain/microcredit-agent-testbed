import contextlib
import io
import os
import unittest
from unittest.mock import Mock, patch

import quickstart
from scripts.deployment import CastError, load_deployment

ACCOUNT = "0x" + "1" * 40
TOPIC = "0x" + "a" * 64


class QuickstartTests(unittest.TestCase):
    def test_help_needs_no_wallet_or_rpc(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(quickstart, "Cast") as client, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                quickstart.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        client.assert_not_called()

    def test_readonly_account_never_reads_a_key(self):
        client = Mock()
        client.call.return_value = [17]
        with patch.dict(os.environ, {"ACCOUNT": ACCOUNT}, clear=True), patch.object(quickstart, "Cast", return_value=client), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(quickstart.main(["try-borrow", "0.25"]), 0)
        client.run.assert_not_called()
        client.send.assert_not_called()
        self.assertEqual(client.call.call_args.args[2], 250_000)

    def test_borrow_uses_receipt_not_last_account_loan(self):
        d = load_deployment({})
        receipt = {"logs": [{"address": d["pool"], "topics": [TOPIC, "0x" + ACCOUNT[2:].rjust(64, "0"), "0x2a"]}]}
        client = Mock()
        client.run.side_effect = [ACCOUNT, TOPIC]
        client.send.side_effect = [receipt, {"status": "0x1"}]
        with patch.dict(os.environ, {"PRIVATE_KEY": "test-placeholder"}, clear=True), patch.object(quickstart, "Cast", return_value=client), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(quickstart.main(["borrow", "0.25"]), 0)
        self.assertEqual(client.send.call_args.args[-1], 42)
        client.call.assert_not_called()

    def test_ambiguous_request_never_disburses(self):
        client = Mock()
        client.run.side_effect = [ACCOUNT, TOPIC]
        client.send.return_value = {"logs": []}
        with patch.dict(os.environ, {"PRIVATE_KEY": "test-placeholder"}, clear=True), patch.object(quickstart, "Cast", return_value=client), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(quickstart.main(["borrow", "0.25"]), 1)
        self.assertEqual(client.send.call_count, 1)

    def test_failed_approval_never_deposits(self):
        client = Mock()
        client.run.return_value = ACCOUNT
        client.send.side_effect = CastError("approval reverted")
        with patch.dict(os.environ, {"PRIVATE_KEY": "test-placeholder"}, clear=True), patch.object(quickstart, "Cast", return_value=client), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(quickstart.main(["lend", "0.25"]), 1)
        self.assertEqual(client.send.call_count, 1)

    def test_argument_validation_precedes_any_chain_call(self):
        with patch.object(quickstart, "Cast") as client, contextlib.redirect_stderr(io.StringIO()):
            for args in (["lend"], ["lend", "1+2"], ["back", ACCOUNT, "-1"], ["repay", "-5"]):
                with self.subTest(args=args), self.assertRaises(SystemExit):
                    quickstart.main(args)
        client.assert_not_called()

    def test_borrow_event_filters_other_pools_and_borrowers(self):
        d = load_deployment({})
        topics = [TOPIC, "0x" + ACCOUNT[2:].rjust(64, "0"), "0x2a"]
        with self.assertRaises(CastError):
            quickstart.requested_loan({"logs": [{"address": ACCOUNT, "topics": topics}]}, d["pool"], ACCOUNT, TOPIC)


if __name__ == "__main__":
    unittest.main()
