import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from metrics import lending_dashboard as ld  # noqa: E402

# One real log from the recorded pool (Backed, block 53175211), kept as a decoding fixture.
REAL_BACKED_LOG = {
    "address": "0x73872b8fb7f1771c67911f03edc75abdc9514973",
    "topics": ["0xbd7c266a4d2bd99c36d0c7a7fb8e1b5adc9e4b5b1c3d1c1a0ea0fbb6ea8c4e9a",
               "0x000000000000000000000000fe1574f5b91b49927d44ff0206093243f5664e2c",
               "0x0000000000000000000000004e23411897b1c2bc31e3db03e074c370596cd4e6"],
    "data": "0x" + format(6_000_000, "064x") + format(0, "064x"),
    "blockNumber": "0x32b6c2b", "logIndex": "0x3",
    "transactionHash": "0x" + "ab" * 32,
}


class KeccakTest(unittest.TestCase):
    def test_known_vectors(self):
        self.assertEqual(ld.keccak256(b"").hex(), "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470")
        self.assertEqual(ld.keccak256(b"abc").hex(), "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45")
        self.assertEqual(ld.keccak256(b"x" * 300).hex()[:16], ld.keccak256(bytes(b"x" * 300)).hex()[:16])

    def test_selector_and_topics_match_the_contract(self):
        self.assertEqual(ld.selector("totalAssets()"), "0x01e1d114")
        self.assertEqual(ld.selector("transfer(address,uint256)"), "0xa9059cbb")
        topics = {ld.parse_event(s)["name"]: ld.parse_event(s)["topic"] for s in ld.POOL_EVENTS}
        # Topics observed on the recorded pool (deployment to block 54056560).
        self.assertTrue(topics["Staked"].startswith("0x9e71bc8e"))
        self.assertTrue(topics["LoanRequested"].startswith("0x470e775e"))
        self.assertTrue(topics["LoanRepaid"].startswith("0xc7ce0a35"))
        self.assertTrue(topics["RepaymentApplied"].startswith("0x79cc0b6d"))
        self.assertTrue(topics["Backed"].startswith("0xbd7c266a"))

    def test_profile_schema_uid_is_deterministic(self):
        uid = ld.schema_uid()
        self.assertEqual(len(uid), 66)
        self.assertEqual(uid, ld.schema_uid(ld.PROFILE_SCHEMA, ld.PROFILE_SCHEMA_RESOLVER, True))
        self.assertNotEqual(uid, ld.schema_uid(ld.PROFILE_SCHEMA, ld.PROFILE_SCHEMA_RESOLVER, False))


class AbiTest(unittest.TestCase):
    def test_decode_log_backed(self):
        events = {ld.parse_event(s)["topic"]: ld.parse_event(s) for s in ld.POOL_EVENTS}
        log = dict(REAL_BACKED_LOG, topics=[events and next(t for t, e in events.items() if e["name"] == "Backed")] + REAL_BACKED_LOG["topics"][1:])
        decoded = ld.decode_log(events, log)
        self.assertEqual(decoded["event"], "Backed")
        self.assertEqual(decoded["args"]["backer"], "0xfe1574f5b91b49927d44ff0206093243f5664e2c")
        self.assertEqual(decoded["args"]["secured"], 6_000_000)
        self.assertEqual(decoded["block"], 0x32b6c2b)
        self.assertIsNone(ld.decode_log(events, dict(log, topics=["0x" + "00" * 32])))

    def test_decode_dynamic_values(self):
        data = ld.encode_values(["uint256", "string", "bool"], [7, "Sololá", True])
        self.assertEqual(ld.decode_values(["uint256", "string", "bool"], data), [7, "Sololá", True])
        array = "0x" + format(32, "064x") + format(2, "064x") + format(5, "064x") + format(9, "064x")
        self.assertEqual(ld.decode_values(["uint256[]"], array), [[5, 9]])

    def test_profile_roundtrip(self):
        data = ld.encode_profile(12, "GT", "Sololá", "market trader", "inventory", 2, 1)
        profile = ld.decode_profile(data)
        self.assertEqual(profile["loanId"], 12)
        self.assertEqual(profile["country"], "GT")
        self.assertEqual(profile["occupation"], "market trader")
        self.assertEqual(profile["incomeBandLabel"], "2.15 to 3.65 USD a day")
        with self.assertRaises(ValueError):
            ld.encode_profile(1, "GT", "", "", "", 9, 1)


def synthetic_events():
    """Two borrowers: A repays loan 1 on time, B defaults on loan 2; A takes loan 3, still active."""
    def ev(name, block, index, **args):
        return {"event": name, "args": args, "block": block, "logIndex": index, "tx": f"0x{block:064x}", "address": "pool"}
    a, b, backer = "0x" + "aa" * 20, "0x" + "bb" * 20, "0x" + "cc" * 20
    return [
        ev("Deposited", 100, 0, lender=backer, assets=100_000_000, shares=1),
        ev("Staked", 100, 1, account=a, amount=5_000_000),
        ev("Backed", 101, 0, backer=backer, borrower=b, secured=10_000_000, unsecured=0),
        ev("LoanRequested", 110, 0, borrower=a, loanId=1, amount=10_000_000, interestRate=933),
        ev("LoanDisbursed", 111, 0, borrower=a, loanId=1, to=a, amount=10_000_000),
        ev("LoanRequested", 112, 0, borrower=b, loanId=2, amount=20_000_000, interestRate=933),
        ev("LoanDisbursed", 113, 0, borrower=b, loanId=2, to=b, amount=20_000_000),
        ev("LoanRepaid", 120, 0, borrower=a, loanId=1, amount=10_100_000),
        ev("RepaymentApplied", 120, 1, loanId=1, interest=100_000, principal=10_000_000, fee=0),
        ev("LoanDefaulted", 130, 0, borrower=b, loanId=2, writtenOff=15_000_000, recovered=5_000_000),
        ev("LoanRequested", 140, 0, borrower=a, loanId=3, amount=12_000_000, interestRate=933),
        ev("LoanDisbursed", 141, 0, borrower=a, loanId=3, to=a, amount=12_000_000),
        ev("Backed", 150, 0, backer=backer, borrower=b, secured=0, unsecured=0),
    ]


def block_time(block):
    return 1_700_000_000 + block * 100


def synthetic_terms():
    """getLoanTerms(status, term, requestedAt, disbursedAt, dueAt) on the same clock as the events."""
    day = 86400
    return {1: (3, 30 * day, block_time(110), block_time(111), block_time(111) + 30 * day),
            2: (4, 30 * day, block_time(112), block_time(113), block_time(113) + 30 * day),
            3: (2, 30 * day, block_time(140), block_time(141), block_time(141) + 30 * day)}


class AggregationTest(unittest.TestCase):
    def setUp(self):
        self.events = synthetic_events()
        self.times = {e["block"]: block_time(e["block"]) for e in self.events}
        self.loans = ld.build_loans(self.events, self.times, synthetic_terms())

    def test_loans(self):
        by_id = {l["id"]: l for l in self.loans}
        self.assertEqual([l["id"] for l in self.loans], [1, 2, 3])
        self.assertEqual(by_id[1]["status"], "Repaid")
        self.assertTrue(by_id[1]["onTime"])
        self.assertEqual(by_id[1]["interest"], 100_000)
        self.assertIsNone(by_id[1]["firstLoan"])
        self.assertIsNone(by_id[3]["firstLoan"])
        self.assertEqual(by_id[2]["closed"]["as"], "Defaulted")
        self.assertEqual(by_id[2]["writtenOff"], 15_000_000)
        self.assertEqual(by_id[3]["status"], "Active")
        self.assertIsNone(by_id[3]["closed"])

    def test_human_metrics(self):
        stake = ld.stake_by_account(self.events)
        metrics = ld.human_metrics(self.loans, [], stake)
        self.assertEqual(metrics["repaymentRate"], {"closedLoans": 2, "repaid": 1, "defaulted": 1, "onTime": 1, "rate": 0.5})
        self.assertIsNone(metrics["humanBorrowers"])
        self.assertIsNone(metrics["sponsorExpenditure"])
        self.assertNotIn("netYield", metrics)
        self.assertNotIn("firstTimeBorrowerShare", metrics)
        self.assertEqual(ld.human_metrics(self.loans, [{"loanId": 1, "borrower": "unverified"}], stake), metrics)
        self.assertEqual(ld.profile_breakdown([{"country": "private"}]), {})

    def test_backing_and_monthly(self):
        self.assertEqual(ld.backing_edges(self.events), [])  # the second Backed event cleared the edge
        series = ld.monthly_series(self.loans, self.events, self.times)
        self.assertEqual(len(series), 1)
        self.assertEqual(series[-1]["cumulative"]["disbursed"], 42_000_000)
        self.assertEqual(series[-1]["cumulative"]["repaid"], 10_100_000)
        self.assertEqual(series[-1]["cumulative"]["interest"], 100_000)
        self.assertEqual(series[-1]["cumulative"]["deposited"], 100_000_000)
        self.assertEqual(series[-1]["loans"], 3)


class FakeRpc(ld.Rpc):
    """Serves eth_getLogs with a range cap, counting calls, with no network."""
    def __init__(self, cap):
        super().__init__("fake://", retries=1)
        self.cap, self.ranges = cap, []

    def request(self, method, params):
        self.calls += 1
        if method == "eth_getLogs":
            start, end = int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16)
            if end - start + 1 > self.cap:
                raise ld.RpcError("eth_getLogs is limited to a range")
            self.ranges.append((start, end))
            return [{"blockNumber": hex(start)}]
        raise AssertionError(method)


class RpcTest(unittest.TestCase):
    def test_logs_split_until_the_node_accepts(self):
        rpc = FakeRpc(cap=1_000)
        logs = rpc.logs(["0x" + "11" * 20], 0, 2_999, chunk=16_000)
        self.assertEqual(len(logs), len(rpc.ranges))
        self.assertEqual(rpc.ranges[0][0], 0)
        self.assertEqual(rpc.ranges[-1][1], 2_999)
        self.assertTrue(all(end - start + 1 <= 1_000 for start, end in rpc.ranges))
        self.assertEqual(sum(end - start + 1 for start, end in rpc.ranges), 3_000)

    def test_logs_give_up_below_the_public_cap(self):
        with self.assertRaises(ld.RpcError):
            FakeRpc(cap=10).logs(["0x" + "11" * 20], 0, 99, chunk=200)

    def test_no_network_on_import_or_schema_uid(self):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(ld.main(["--schema-uid"]), 0)
            self.assertEqual(json.loads(out.getvalue())["uid"], ld.schema_uid())


class SnapshotFileTest(unittest.TestCase):
    """The committed snapshot is a complete report at one block; the page relies on these keys."""
    def test_committed_snapshot_shape(self):
        path = Path(__file__).resolve().parents[1] / "dashboard" / "data" / "snapshot.json"
        if not path.exists():
            self.skipTest("no committed snapshot")
        report = json.loads(path.read_text(encoding="utf-8"))
        for key in ("snapshot", "abi", "pool", "flows", "loans", "loanStatus", "monthly", "backing", "profileSchema",
                    "profiles", "profileBreakdown", "humanMetrics", "caveats"):
            self.assertIn(key, report)
        self.assertEqual(report["snapshot"]["chainId"], 84532)
        self.assertEqual(len(report["snapshot"]["blockHash"]), 66)
        self.assertEqual(report["profileSchema"]["uid"], ld.schema_uid())
        self.assertEqual(report["abi"]["selectors"]["totalAssets()"], "0x01e1d114")
        self.assertIn(ld.parse_event(ld.POOL_EVENTS[0])["topic"], report["abi"]["events"])
        self.assertEqual(sum(report["loanStatus"].values()), len(report["loans"]))
        js = (path.parent / "snapshot.js").read_text(encoding="utf-8")
        self.assertTrue(js.startswith("window.LENDING_SNAPSHOT = "))
        self.assertEqual(json.loads(js[len("window.LENDING_SNAPSHOT = "):].rstrip().rstrip(";")), report)


if __name__ == "__main__":
    unittest.main()
