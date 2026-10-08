#!/usr/bin/env python3
"""Dependency-free OFFLINE SYNTHETIC accounting controls, never chain evidence.

Every address except the constant WETH address, hash, block, receipt, log, amount
and evidence string below is invented test data. Nothing is fetched, signed or
broadcast. A verifier Boolean is a classification of this fixture, not an
assertion that any loan, gas expense, payout or profitable operation occurred.

Run beside audit-only.py: python -m unittest -v test_audit_negative_controls.py
"""

import copy
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("audit-only.py")
SPEC = importlib.util.spec_from_file_location("eth_accounting_audit", SCRIPT)
AUDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDITOR)

SYNTHETIC_PROVENANCE = "OFFLINE SYNTHETIC FIXTURE: NOT AN RPC RESULT OR EXECUTION"


def fake_address(n):
    return "0x" + format(n, "040x")


def fake_hash(n):
    return "0x" + format(n, "064x")


def synthetic_accounting_fixture():
    """Tiny integer ledger used only to expose misleading accounting claims."""
    b, lender, pool, claimer = map(fake_address, [1, 2, 3, 4])
    weth = AUDITOR.WETH_BASE
    state = lambda native, nonce: {
        "native_wei": native, "weth_wei": 0, "reward_wei": 0, "nonce": nonce}
    packet = {
        "synthetic": True,
        "chain_id": 8453,
        "addresses": {"borrower": b, "lender": lender, "prize_pool": pool,
                      "claimer": claimer, "weth": weth},
        "controlled_addresses": [b, lender],
        "terms": {"principal_wei": 1000, "fee_wei": 40},
        "offchain_costs": {role: {"wei_equivalent": 0,
                                  "evidence": SYNTHETIC_PROVENANCE}
                           for role in ["borrower", "lender"]},
        "snapshots": {
            "before": {"block_number": 100, "block_hash": fake_hash(100),
                       "accounts": {b: state(0, 0), lender: state(10000, 0)}},
            "after": {"block_number": 105, "block_hash": fake_hash(105),
                      "accounts": {b: state(300, 4), lender: state(10025, 1)}}},
        "txs": [],
    }
    sequence = [("funding", lender, b, 1000), ("claim", b, claimer, 0),
                ("withdraw", b, pool, 0), ("unwrap", b, weth, 0),
                ("repay", b, lender, 1040)]
    for index, (kind, sender, to, value) in enumerate(sequence, 1):
        record = {
            "tx": {"hash": fake_hash(index), "chainId": 8453,
                   "from": sender, "to": to, "value": value},
            "receipt": {"transactionHash": fake_hash(index),
                        "blockHash": fake_hash(100 + index),
                        "blockNumber": 100 + index, "status": 1,
                        "gasUsed": 10, "effectiveGasPrice": 1, "l1Fee": 5},
            "operator_fee_wei": 0, "operator_fee_evidence": SYNTHETIC_PROVENANCE,
            "kind": kind, "native_flows": []}
        if value:
            record["native_flows"] = [{"from": sender, "to": to, "wei": value,
                                        "proof": SYNTHETIC_PROVENANCE}]
        if kind == "claim":
            record["claim_events"] = [{"emitter": pool, "winner": fake_address(99),
                                        "claimRewardRecipient": b, "claimReward": 400}]
        if kind == "withdraw":
            record["withdrawal_events"] = [{"emitter": pool, "account": b,
                                             "to": b, "amount": 400}]
        if kind == "unwrap":
            record["native_flows"] = [{"from": weth, "to": b, "wei": 400,
                                        "proof": SYNTHETIC_PROVENANCE}]
        if kind == "repay":
            record.update(repayment_principal_wei=1000, repayment_fee_wei=40)
        packet["txs"].append(record)
    return packet


class SyntheticAccountingNegativeControls(unittest.TestCase):
    """All classifications below concern invented arithmetic, never real ETH."""

    def setUp(self):
        self.packet = synthetic_accounting_fixture()
        self.borrower = self.packet["addresses"]["borrower"]
        self.lender = self.packet["addresses"]["lender"]
        self.assertTrue(AUDITOR.audit(self.packet)["accounting_checks_pass"],
                        "synthetic starting arithmetic must be consistent")

    def classify(self):
        return AUDITOR.audit(self.packet)

    def set_financing_fee(self, fee):
        """Adjust the entire synthetic ledger, so a rejection is not imbalance."""
        self.packet["terms"]["fee_wei"] = fee
        repayment = self.packet["txs"][4]
        repayment["tx"]["value"] = 1000 + fee
        repayment["native_flows"][0]["wei"] = 1000 + fee
        repayment["repayment_fee_wei"] = fee
        balances = self.packet["snapshots"]["after"]["accounts"]
        balances[self.borrower]["native_wei"] = 340 - fee
        balances[self.lender]["native_wei"] = 9985 + fee

    def test_omitted_l1_fees_break_actual_balance_conservation(self):
        for record in self.packet["txs"]:
            record["receipt"]["l1Fee"] = 0
        self.assertFalse(self.classify()["accounting_checks_pass"])

    def test_success_receipt_without_new_claim_fee_is_not_income(self):
        self.packet["txs"][1]["claim_events"] = []
        report = self.classify()
        self.assertFalse(report["accounting_checks_pass"])
        self.assertFalse(report["positive_settled_cold_start_onchain_proof"])

    def test_retained_weth_is_not_cash_settlement(self):
        balances = self.packet["snapshots"]["after"]["accounts"][self.borrower]
        balances.update(native_wei=250, weth_wei=50)
        self.packet["txs"][3]["native_flows"][0]["wei"] = 350
        report = self.classify()
        self.assertTrue(report["accounting_checks_pass"])
        self.assertFalse(report["positive_settled_cold_start_onchain_proof"])

    def test_lender_gas_subsidy_does_not_qualify_positive_proof(self):
        self.set_financing_fee(10)
        report = self.classify()
        self.assertTrue(report["accounting_checks_pass"])
        self.assertEqual(report["lender_loan_margin_before_nonloan_sweeps_wei"], -5)
        self.assertFalse(report["positive_settled_cold_start_onchain_proof"])

    def test_missing_offchain_costs_do_not_qualify_fully_costed_proof(self):
        del self.packet["offchain_costs"]
        report = self.classify()
        self.assertTrue(report["accounting_checks_pass"])
        self.assertFalse(report["fully_costed_cash_settled_bootstrap_proof"])

    def test_receipt_status_outside_zero_one_is_rejected(self):
        self.packet["txs"][1]["receipt"]["status"] = 2
        self.assertFalse(self.classify()["accounting_checks_pass"])

    def test_reverted_attempt_still_charges_both_gas_components(self):
        failed = copy.deepcopy(self.packet["txs"][1])
        failed["tx"]["hash"] = fake_hash(6)
        failed["receipt"].update(transactionHash=fake_hash(6), blockHash=fake_hash(106),
                                   blockNumber=106, status="0x0")
        failed["claim_events"] = []
        self.packet["txs"].append(failed)
        after = self.packet["snapshots"]["after"]
        after.update(block_number=106, block_hash=fake_hash(106))
        after["accounts"][self.borrower].update(native_wei=285, nonce=5)
        report = self.classify()
        self.assertTrue(report["accounting_checks_pass"])
        self.assertEqual(report["failed_transactions"], 1)
        self.assertEqual(report["gas_wei_by_actor"][self.borrower], 75)

    def test_zero_lender_margin_means_cost_covered_not_lender_profit(self):
        self.set_financing_fee(15)
        report = self.classify()
        self.assertTrue(report["accounting_checks_pass"])
        self.assertEqual(report["lender_loan_margin_before_nonloan_sweeps_wei"], 0)
        self.assertTrue(report["loan_funding_gas_covered_by_fee"])
        # Only the synthetic classifier boundary is tested; no chain truth.
        self.assertTrue(report["fully_costed_cash_settled_bootstrap_proof"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
