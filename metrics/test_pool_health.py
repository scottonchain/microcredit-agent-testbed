import contextlib
import io
import unittest
from unittest.mock import patch

import pool_health
from scripts.deployment import CastError, load_deployment


class SnapshotClient:
    def __init__(self, *, violation=False, changed_hash=False):
        self.calls = []
        self.violation = violation
        self.changed_hash = changed_hash
        self.block_calls = 0

    def check_chain(self):
        pass

    def check_wiring(self, block=None):
        self.wiring_block = block

    def block(self, number="latest"):
        self.block_calls += 1
        return {"number": "0x64", "timestamp": "0xa", "hash": "0x" + ("b" if self.changed_hash and self.block_calls > 1 else "a") * 64}

    def call(self, to, signature, *args, block=None):
        self.calls.append((signature, block))
        if signature.startswith("getScores") or signature.startswith("getBorrowers"):
            return [["0x" + "1" * 40]]
        if signature in ("getBackers()(address[])", "getBackedBorrowers()(address[])", "getLenders()(address[])", "getAllLoanIds()(uint256[])"):
            return [[]]
        if signature.startswith("getBorrowLimit"):
            return [11 if self.violation else 10, 10]
        if signature.startswith("grantedCredit"):
            return [10]
        return [0]


class PoolHealthTests(unittest.TestCase):
    def test_all_reads_use_one_recorded_block(self):
        client = SnapshotClient()
        report = pool_health.read_report(load_deployment({}), client)
        self.assertTrue(report["integrity"]["holds"])
        self.assertEqual(report["snapshot"]["blockNumber"], 100)
        self.assertEqual(client.wiring_block, 100)
        self.assertTrue(client.calls)
        self.assertEqual({block for _, block in client.calls}, {100})

    def test_reorg_invalidates_the_snapshot(self):
        with self.assertRaisesRegex(CastError, "block changed"):
            pool_health.read_report(load_deployment({}), SnapshotClient(changed_hash=True))

    def test_conservation_violation_is_nonzero_exit(self):
        with patch.object(pool_health, "Cast", return_value=SnapshotClient(violation=True)), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pool_health.main(["--json"]), 1)
        self.assertIn('"holds": false', out.getvalue())

    def test_failed_read_cannot_create_success_report(self):
        with patch.object(pool_health, "Cast") as factory, contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            factory.return_value.check_chain.side_effect = CastError("RPC unavailable")
            self.assertEqual(pool_health.main(["--json"]), 1)
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
