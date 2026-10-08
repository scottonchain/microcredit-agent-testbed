#!/usr/bin/env python3
"""OFFLINE SYNTHETIC harvest controls; no fixture is execution evidence.

All addresses/hashes/blocks/receipts/logs except the WETH constant are invented.
Assertions test accounting classifications only. No RPC, wallet, key or signer.
Run beside auditor: python -m unittest -v test_audit_harvest_negative_controls.py
"""

import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "harvest_accounting_audit", Path(__file__).with_name("audit-harvest-only.py"))
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
SYNTHETIC = "OFFLINE SYNTHETIC; NOT RPC, TRANSACTION OR EARNINGS EVIDENCE"


def address(n):
    return "0x" + format(n, "040x")


def hash32(n):
    return "0x" + format(n, "064x")


def topic(who):
    return "0x" + "0" * 24 + who[2:]


def fixture():
    borrower, lender, strategy = map(address, [1, 2, 3])
    state = lambda native, nonce: {"native_wei": native, "weth_wei": 0, "nonce": nonce}
    p = {"synthetic": True, "chain_id": 8453,
         "addresses": {"borrower": borrower, "lender": lender,
                       "strategy": strategy, "weth": AUDIT.WETH},
         "controlled_addresses": [borrower, lender],
         "strategy_review": {"runtime_code_keccak256": hash32(123),
                             "source_evidence": SYNTHETIC,
                             "fee_mechanism_evidence": SYNTHETIC,
                             "no_team_seed_evidence": SYNTHETIC},
         "terms": {"principal_wei": 1000, "fee_wei": 40},
         "offchain_costs": {role: {"wei_equivalent": 0, "evidence": SYNTHETIC}
                            for role in ["borrower", "lender"]},
         "snapshots": {
             "before": {"block_number": 100, "block_hash": hash32(100),
                        "accounts": {borrower: state(0, 0), lender: state(10000, 0)}},
             "after": {"block_number": 104, "block_hash": hash32(104),
                       "accounts": {borrower: state(315, 3), lender: state(10025, 1)}}},
         "txs": []}
    for i, (kind, sender, to, value, data, nonce) in enumerate([
            ("funding", lender, borrower, 1000, "0x", 0),
            ("harvest", borrower, strategy, 0, AUDIT.HARVEST + "0" * 24 + borrower[2:], 0),
            ("unwrap", borrower, AUDIT.WETH, 0, AUDIT.UNWRAP + format(400, "064x"), 1),
            ("repay", borrower, lender, 1040, "0x", 2)], 1):
        r = {"kind": kind, "tx": {"hash": hash32(i), "chainId": 8453,
                                  "from": sender, "to": to, "value": value,
                                  "input": data, "nonce": nonce},
             "receipt": {"transactionHash": hash32(i), "blockHash": hash32(100 + i),
                         "blockNumber": 100 + i, "status": 1, "gasUsed": 10,
                         "effectiveGasPrice": 1, "l1Fee": 5, "logs": []},
             "operator_fee_wei": 0, "operator_fee_evidence": SYNTHETIC,
             "native_flows": []}
        if value:
            r["native_flows"] = [{"from": sender, "to": to, "wei": value, "proof": SYNTHETIC}]
        if kind == "harvest":
            r["receipt"]["logs"] = [{"address": AUDIT.WETH, "logIndex": 0,
                                     "topics": [AUDIT.TRANSFER, topic(strategy), topic(borrower)],
                                     "data": hash32(400)}]
        if kind == "unwrap":
            r["receipt"]["logs"] = [{"address": AUDIT.WETH, "logIndex": 0,
                                     "topics": [AUDIT.WITHDRAWAL, topic(borrower)],
                                     "data": hash32(400)}]
            r["native_flows"] = [{"from": AUDIT.WETH, "to": borrower, "wei": 400, "proof": SYNTHETIC}]
        if kind == "repay":
            r.update(repayment_principal_wei=1000, repayment_fee_wei=40)
        p["txs"].append(r)
    return p


class SyntheticHarvestCorruptionControls(unittest.TestCase):
    def setUp(self):
        self.p = fixture()
        self.b = self.p["addresses"]["borrower"]
        self.assertTrue(AUDIT.audit(self.p)["accounting_checks_pass"], "synthetic arithmetic setup")

    def test_counterfeit_token_event_is_not_weth_fee(self):
        self.p["txs"][1]["receipt"]["logs"][0]["address"] = address(77)
        self.assertFalse(AUDIT.audit(self.p)["accounting_checks_pass"])

    def test_other_sender_transfer_is_not_strategy_caller_income(self):
        self.p["txs"][1]["receipt"]["logs"][0]["topics"][1] = topic(address(77))
        report = AUDIT.audit(self.p)
        self.assertEqual(report["new_external_weth_fee_wei"], 0)
        self.assertFalse(report["accounting_checks_pass"])

    def test_old_weth_unwrap_or_lens_quote_is_not_new_revenue(self):
        self.p["snapshots"]["before"]["accounts"][self.b]["weth_wei"] = 400
        self.p["txs"][1]["receipt"]["logs"] = []
        self.p["preflight_lens_balance_delta"] = 400  # This is deliberately irrelevant.
        report = AUDIT.audit(self.p)
        self.assertTrue(report["accounting_checks_pass"])
        self.assertEqual(report["new_external_weth_fee_wei"], 0)
        self.assertFalse(report["positive_settled_cold_start_onchain_proof"])

    def test_missing_l1_gas_breaks_balance_conservation(self):
        for r in self.p["txs"]:
            r["receipt"]["l1Fee"] = 0
        self.assertFalse(AUDIT.audit(self.p)["accounting_checks_pass"])

    def test_partial_unwrap_does_not_qualify_cash_settlement(self):
        self.p["snapshots"]["after"]["accounts"][self.b].update(native_wei=265, weth_wei=50)
        r = self.p["txs"][2]
        r["receipt"]["logs"][0]["data"] = hash32(350)
        r["tx"]["input"] = AUDIT.UNWRAP + format(350, "064x")
        r["native_flows"][0]["wei"] = 350
        report = AUDIT.audit(self.p)
        self.assertTrue(report["accounting_checks_pass"])
        self.assertFalse(report["positive_settled_cold_start_onchain_proof"])

    def test_unknown_offchain_costs_prevent_complete_classification(self):
        del self.p["offchain_costs"]
        report = AUDIT.audit(self.p)
        self.assertTrue(report["accounting_checks_pass"])
        self.assertFalse(report["fully_costed_cash_settled_bootstrap_proof"])

    def test_team_strategy_does_not_count_external_service_income(self):
        self.p["controlled_addresses"].append(self.p["addresses"]["strategy"])
        self.assertFalse(AUDIT.audit(self.p)["accounting_checks_pass"])

    def test_reverted_receipt_cannot_supply_fee_events(self):
        self.p["txs"][1]["receipt"]["status"] = 0
        self.assertFalse(AUDIT.audit(self.p)["accounting_checks_pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
