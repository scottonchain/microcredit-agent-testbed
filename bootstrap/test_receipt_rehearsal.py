import copy
import unittest
from receipt_rehearsal import clean_rows, example, reconcile


class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.payload, self.grant, self.usage, self.invoice, self.artifact = example()

    def run_case(self, **kwargs):
        args = dict(grant=self.grant, usage=self.usage, invoice=self.invoice,
                    payload=self.payload, now=4, acceptance="accepted", payment="confirmed")
        args.update(kwargs)
        return reconcile(**args)

    def blocked(self, reason, **kwargs):
        r = self.run_case(**kwargs)
        self.assertFalse(r["simulation_settlement_eligible"])
        self.assertFalse(r["real_payment_authorized"])
        self.assertIn(reason, r["reasons"])
        return r

    def test_happy_path_is_only_simulation(self):
        r = self.run_case()
        self.assertTrue(r["simulation_settlement_eligible"])
        self.assertEqual(r["usage_micro_usdc"], 200000)
        self.assertFalse(r["real_payment_authorized"])

    def test_missing_usage_is_unknown_despite_invoice(self):
        r = self.blocked("usage_unknown", usage=None)
        self.assertIsNone(r["usage_micro_usdc"])

    def test_invoice_cannot_masquerade_as_usage(self):
        u = {**self.usage, "kind": "invoice"}
        self.assertIsNone(self.blocked("not_usage_evidence", usage=u)["usage_micro_usdc"])

    def test_authorizer_provider_conflict(self):
        g = {**self.grant, "authorizer_observed_micro_usdc": 199999}
        self.blocked("authorizer_provider_usage_conflict", grant=g)

    def test_invoice_usage_conflict(self):
        self.blocked("invoice_usage_conflict", invoice={**self.invoice, "amount_micro_usdc": 200001})

    def test_cap_is_not_an_observation(self):
        self.assertTrue(self.run_case()["simulation_settlement_eligible"])
        self.blocked("budget_exhausted", grant={**self.grant, "cap_micro_usdc": 199999})

    def test_receipt_substitution(self):
        for k in ("grant_id", "payload_sha256", "provider_id", "meter_id"):
            with self.subTest(field=k):
                self.blocked("usage_" + k + "_mismatch", usage={**self.usage, k: "other"})
        self.blocked("payload_mismatch", payload={**self.payload, "operation": "other"})

    def test_meter_is_payee_is_not_independent(self):
        g = {**self.grant, "meter_id": self.grant["provider_id"]}
        u = {**self.usage, "meter_id": g["meter_id"]}
        self.blocked("meter_is_payee_review_required", grant=g, usage=u)

    def test_customer_failure_and_payment_uncertainty(self):
        for state in ("rejected", "pending", "expired"):
            self.blocked("customer_" + state, acceptance=state)
        self.blocked("customer_payment_unknown", payment="unknown")
        self.blocked("customer_payment_unpaid", payment="unpaid")
        # Read-only reconciliation can resolve a receipt; no retry or payment occurs.
        self.assertTrue(self.run_case(payment="confirmed")["simulation_settlement_eligible"])

    def test_invalid_amounts_and_authorization_order(self):
        for value in (-1, True, 1.5, None):
            self.blocked("invalid_grant_amount_or_time", grant={**self.grant, "cap_micro_usdc": value})
        self.blocked("invalid_or_expired_authorization", grant={**self.grant, "authorized_at": 3})
        self.blocked("invalid_or_expired_authorization", now=101)

    def test_wrong_typed_receipts_hold_without_crashing(self):
        for value in ([], "not-a-receipt", 1, True):
            self.blocked("invalid_grant_identity", grant=value)
            self.blocked("invalid_usage", usage=value)
            self.blocked("invalid_invoice_kind", invoice=value)

    def test_missing_identifiers_do_not_become_literal_none(self):
        rows = [None, {"id": None, "name": "A", "amount_micro_usdc": 1, "source": "synthetic"},
                {"id": "A", "name": None, "amount_micro_usdc": 1, "source": "synthetic"},
                {"id": "A", "name": "A", "amount_micro_usdc": 1, "source": " "}]
        result = clean_rows(rows)
        self.assertEqual(result["cleaned"], [])
        self.assertEqual(len(result["rejected"]), len(rows))

    def test_no_input_mutation_or_network_side_effects(self):
        before = copy.deepcopy((self.grant, self.usage, self.invoice))
        self.run_case()
        self.assertEqual(before, (self.grant, self.usage, self.invoice))

    def test_cleaning_keeps_provenance_and_reports_rejected_rows(self):
        self.assertEqual(len(self.artifact["cleaned"]), 1)
        self.assertEqual(self.artifact["cleaned"][0]["source_line"], 1)
        self.assertEqual([x["reason"] for x in self.artifact["rejected"]],
                         ["duplicate_id", "missing_or_invalid_field"])


if __name__ == "__main__":
    unittest.main()
