"""Offline negative controls for the read-only gate, never live evidence."""
from datetime import datetime, timezone
import unittest
from preflight import GateError, RPC, descriptor, snapshot


class FakeRPC:
    def __init__(self, *, chain="0x14a34", empty=False, reorg=False, local=False):
        self.chain, self.empty, self.reorg, self.local = chain, empty, reorg, local
        self.blocks = 0

    def call(self, method, params):
        if method == "eth_chainId":
            return self.chain
        if method == "web3_clientVersion":
            return "anvil/v1" if self.local else "test-fixture"
        if method == "eth_getCode":
            return "0x" if self.empty else "0x6000"
        if method == "eth_getBlockByNumber":
            self.blocks += 1
            return {"number": "0x10", "hash": "0x" + ("22" if self.reorg and self.blocks > 1 else "11") * 32,
                    "timestamp": hex(int(datetime.now(timezone.utc).timestamp()))}
        raise AssertionError(method)


class GateTests(unittest.TestCase):
    def test_wrong_chain_never_collects_acceptance(self):
        with self.assertRaisesRegex(GateError, "WRONG_CHAIN"):
            snapshot(descriptor(), FakeRPC(chain="0x1"))

    def test_fork_and_missing_code_rejected(self):
        for opts, expected in (({"local": True}, "LOCAL_TEST_NODE"), ({"empty": True}, "NO_VALID_CODE")):
            with self.subTest(opts=opts), self.assertRaisesRegex(GateError, expected):
                snapshot(descriptor(), FakeRPC(**opts))

    def test_reorg_discards_observation(self):
        with self.assertRaisesRegex(GateError, "BLOCK_CHANGED"):
            snapshot(descriptor(), FakeRPC(reorg=True))

    def test_write_methods_refused_before_network(self):
        with self.assertRaisesRegex(GateError, "NON_READ_METHOD"):
            RPC("https://sepolia.base.org").call("eth_sendRawTransaction", [])

    def test_identity_snapshot_has_no_mechanism_verdict(self):
        result = snapshot(descriptor(), FakeRPC())
        self.assertEqual(result["chain_id"], 84532)
        self.assertEqual(set(result["contracts"]), {"pool", "lens", "scores", "token"})
        self.assertIn("mechanism unverified", result["scope"])


if __name__ == "__main__":
    unittest.main()
