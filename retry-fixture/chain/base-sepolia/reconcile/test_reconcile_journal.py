import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import reconcile_journal as journal

POOL = "0x" + "1" * 40
SIGNER = "0x" + "2" * 40
INTENT = ("repayLoanMeta", None, SIGNER, 3, 17)


def receipt(status=1, logs=True):
    return {"status": hex(status), "logs": [{"address": POOL, "topics": [journal.TOPIC_META_REPAID,
            "0x" + SIGNER[2:].rjust(64, "0"), "0x" + f"{17:064x}"]}] if logs else []}


class JournalTests(unittest.TestCase):
    def test_reverted_transaction_cannot_inherit_other_nonce_consumption(self):
        verdict, _ = journal.receipt_verdict(INTENT, [INTENT], receipt(status=0, logs=False), 3, 4, POOL)
        self.assertEqual(verdict, "not landed")

    def test_matching_event_and_nonce_attribute_one_intent(self):
        verdict, _ = journal.receipt_verdict(INTENT, [INTENT], receipt(), 3, 4, POOL)
        self.assertEqual(verdict, "landed")

    def test_swallowed_call_without_event_is_ambiguous_if_nonce_moved_elsewhere(self):
        intent = ("repayLoanMeta via batch[0]", POOL, SIGNER, 3, 17)
        verdict, _ = journal.receipt_verdict(intent, [intent], receipt(logs=False), 3, 4, POOL)
        self.assertEqual(verdict, "ambiguous")

    def test_one_event_cannot_attribute_two_candidate_intents(self):
        verdict, _ = journal.receipt_verdict(INTENT, [INTENT, INTENT], receipt(), 3, 4, POOL)
        self.assertEqual(verdict, "ambiguous")

    def test_unconsumed_nonce_is_not_landed(self):
        verdict, _ = journal.receipt_verdict(INTENT, [INTENT], receipt(logs=False), 3, 3, POOL)
        self.assertEqual(verdict, "not landed")

    def test_all_recorded_journal_inputs_decode_without_mutation(self):
        source = Path(__file__).with_name("JOURNAL_live_pool.jsonl")
        original = source.read_bytes()
        decoded = sum(len(journal.signed_intents(row.get("data"))) for row in
                      (json.loads(line) for line in original.decode().splitlines()) if row.get("state") == "intent")
        self.assertGreater(decoded, 8)
        self.assertEqual(source.read_bytes(), original)

    def test_unreceipted_consumed_nonce_stays_ambiguous(self):
        source = Path(__file__).with_name("JOURNAL_live_pool.jsonl")
        original = [json.loads(line) for line in source.read_text().splitlines()]
        row = next(row for row in original if row.get("step") == "s3" and row.get("state") == "intent")
        def rpc(method, params):
            return {"eth_chainId": "0x14a34", "eth_blockNumber": "0x64"}[method]
        with tempfile.TemporaryDirectory() as directory, patch.object(journal, "rpc", side_effect=rpc), patch.object(journal, "nonces", return_value=2), contextlib.redirect_stdout(io.StringIO()) as out:
            path = Path(directory) / "journal.jsonl"
            path.write_text(json.dumps(row) + "\n")
            self.assertEqual(journal.main([str(path)]), 1)
            self.assertIn("AMBIGUOUS", out.getvalue())


if __name__ == "__main__":
    unittest.main()
