import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import chain_read
import lib

HERE = Path(__file__).resolve().parent
TX = "0x" + "a" * 64


class BroadcastTests(unittest.TestCase):
    def test_ambiguous_errors_are_single_attempt(self):
        for text in ("timeout", "429", "already known", "underpriced", "estimate gas", "private-placeholder"):
            with self.subTest(text=text), patch.object(lib.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", text)) as run:
                with self.assertRaises(lib.BroadcastOutcomeUnknown) as caught:
                    lib._send_async(["send", "--private-key", "private-placeholder"])
                self.assertEqual(run.call_count, 1)
                self.assertNotIn("private-placeholder", str(caught.exception))

    def test_timeout_does_not_expose_key_or_resend(self):
        with patch.object(lib.subprocess, "run", side_effect=subprocess.TimeoutExpired(["cast", "private-placeholder"], 180)) as run:
            with self.assertRaises(lib.BroadcastOutcomeUnknown) as caught:
                lib._send_async(["send", "--private-key", "private-placeholder"])
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("private-placeholder", str(caught.exception))

    def test_signing_command_errors_and_timeouts_redact_keys(self):
        result = subprocess.CompletedProcess([], 1, "", "invalid private-placeholder")
        with patch.object(lib.subprocess, "run", return_value=result), self.assertRaises(RuntimeError) as caught:
            lib.cast("wallet", "sign", "--private-key", "private-placeholder")
        self.assertNotIn("private-placeholder", str(caught.exception))
        with patch.object(lib.subprocess, "run", side_effect=subprocess.TimeoutExpired(["cast", "private-placeholder"], 90)), self.assertRaises(RuntimeError) as caught:
            lib.cast("wallet", "sign", "--private-key", "private-placeholder")
        self.assertNotIn("private-placeholder", str(caught.exception))

    def test_unknown_outcome_preserves_intent_before_send(self):
        entries = []
        def attempt(args):
            self.assertEqual(entries[0]["state"], "intent")
            raise lib.BroadcastOutcomeUnknown("unknown")
        with patch.object(lib, "journal", side_effect=lambda row: entries.append(row)), patch.object(lib, "_send_async", side_effect=attempt), patch.object(lib, "wait_receipt") as wait:
            with self.assertRaises(lib.BroadcastOutcomeUnknown):
                lib.broadcast(["send"], {"step": "synthetic", "to": "0x" + "1" * 40, "data": "0x"})
        self.assertEqual([entry["state"] for entry in entries], ["intent", "broadcast_unknown"])
        wait.assert_not_called()

    def test_success_waits_on_the_exact_returned_hash(self):
        with patch.object(lib, "journal") as journal, patch.object(lib, "_send_async", return_value=TX), patch.object(lib, "wait_receipt", return_value={"status": "0x0"}) as wait:
            self.assertEqual(lib.broadcast(["send"], {"step": "synthetic", "to": None}), {"status": "0x0"})
        wait.assert_called_once_with(TX)
        self.assertEqual(journal.call_args.args[0]["tx"], TX)

    def test_journal_flushes_before_return(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(lib, "JOURNAL", str(Path(directory) / "journal.jsonl")), patch.object(lib.os, "fsync") as sync:
            lib.journal({"state": "intent", "step": "synthetic"})
            self.assertEqual(json.loads((Path(directory) / "journal.jsonl").read_text())["state"], "intent")
            self.assertEqual(sync.call_count, 2)  # file contents and new directory entry


class DecoderTests(unittest.TestCase):
    def test_both_published_runs_decode_unchanged(self):
        count = 0
        for filename in ("EVIDENCE.json", "EVIDENCE_live_pool.json"):
            evidence = json.loads((HERE / filename).read_text())
            for step in evidence["steps"].values():
                data = step.get("calldata", "")
                decoder = {chain_read.SEL_REPAY: chain_read.decode_repay, chain_read.SEL_BORROW: chain_read.decode_borrow,
                           chain_read.SEL_FORWARD: chain_read.decode_forward, chain_read.SEL_BATCH: chain_read.decode_batch}.get(data[:10].lower())
                if decoder:
                    self.assertTrue(decoder(data))
                    count += 1
        self.assertGreater(count, 8)

    def test_bad_offsets_and_lengths_fail(self):
        for data, offset in (("0" * 64, 1), ("0" * 64, 64), ("f" * 64, 0), ("g" * 64, 0)):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                chain_read.dyn_bytes(data, offset)
        with self.assertRaises(ValueError):
            chain_read.decode_batch(chain_read.SEL_BATCH + "0" * 64 + f"{64:064x}" + "f" * 64)

    def test_read_rpc_refuses_broadcast_methods(self):
        with patch.object(chain_read.urllib.request, "urlopen") as request, self.assertRaises(ValueError):
            chain_read.read_rpc("https://example.invalid", "eth_sendRawTransaction", [], "test")
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
