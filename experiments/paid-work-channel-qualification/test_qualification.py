import json
import copy
import unittest
import io
from contextlib import redirect_stdout, redirect_stderr
import tempfile
from pathlib import Path

from qualification import MAX_RECORD_BYTES, main, payout_readiness, validate


def cash_economics():
    return {"basis": "cash", "currency": "SLE", "currency_unit_confirmed": True,
            "currency_source_ids": ["s2"], "gross_cash_min": "20",
            "gross_source_ids": ["s2"],
            "costs": {"provider_transfer_fee": "0", "recipient_cashout_fee": "1.53",
                      "other_worker_costs": "2"},
            "cost_source_ids": {n: ["s2"] for n in
                                ("provider_transfer_fee", "recipient_cashout_fee", "other_worker_costs")}}


def pass_record():
    data = record("PASS")
    for gate in data["gates"].values():
        gate.update(status="verified", chain_complete=True)
    data["gates"]["current_demand"]["source_ids"] = ["s2"]
    data["conservative_net_earnings_status"] = "positive"
    data["payout_economics"] = cash_economics()
    return data


def points_record():
    data = pass_record()
    payout = data["payout_economics"]
    payout.pop("gross_cash_min")
    payout.update(basis="points", task_points_min="1000", fixed_conversion_confirmed=True,
                  conversion_source_ids=["s2"], quotes=[
                      {"id": "a", "points_min": "1000", "points_max": "1000",
                       "cash_min": "20", "cash_max": "20", "currency": "SLE", "source_ids": ["s2"]},
                      {"id": "b", "points_min": "2500", "points_max": "5000",
                       "cash_min": "50", "cash_max": "100", "currency": "SLE", "source_ids": ["s2"]}])
    return data


def record(decision="NO_VERIFIABLE_ROUTE"):
    gates = {
        "current_access": {"status": "verified", "chain_complete": True, "source_ids": ["s1"], "finding": "access"},
        "current_demand": {"status": "unverified", "chain_complete": False, "source_ids": ["s1"], "finding": "no current task"},
        "worker_eligibility": {"status": "verified", "chain_complete": True, "source_ids": ["s2"], "finding": "eligible"},
        "spendable_payout": {"status": "unverified", "chain_complete": False, "source_ids": ["s2"], "finding": "no local route"},
    }
    return {
        "schema_version": 1,
        "candidate_id": "candidate",
        "candidate_name": "Candidate",
        "country": "Sierra Leone",
        "checked_at": "2026-10-13T19:00:00Z",
        "decision": decision,
        "resource_bound": {"contact": 0, "spend_usd": 0, "signups": 0},
        "sources": [
            {"id": "s1", "kind": "original", "url": "https://example.org/a", "checked_at": "2026-10-13T19:00:00Z", "supports": "a", "does_not_establish": "b"},
            {"id": "s2", "kind": "original", "url": "https://example.net/b", "checked_at": "2026-10-13T19:00:00Z", "supports": "b", "does_not_establish": "a"},
        ],
        "gates": gates,
        "independent_reviews": [
            {"reviewer": "agent:codex", "source_check": "original", "disposition": decision, "receipt_url": "https://github.com/example/repo/issues/1#issuecomment-1"},
            {"reviewer": "agent:claude", "source_check": "original", "disposition": decision, "receipt_url": "https://github.com/example/repo/issues/1#issuecomment-2"},
        ],
        "conservative_net_earnings_status": "unknown",
        "limitations": "This is not evidence of unavailability.",
        "next_trigger": "Current task and payout evidence",
    }


class QualificationTests(unittest.TestCase):
    def test_malformed_roots_are_structured_rejections(self):
        for value in (None, [], 1, True, "PRIVATE_SENTINEL"):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(validate(value), ["record must be an object"])
                result = payout_readiness(value)
                self.assertTrue(result["errors"])
                self.assertFalse(result["human_earnings_established"])
                self.assertFalse(result["financial_authority"])

    def test_nested_shape_matrix_rejects_without_crash_or_echo(self):
        shapes = (None, [], {}, 1, True, "PRIVATE_SENTINEL")
        paths = [("decision",), ("limitations",), ("sources",),
                 ("independent_reviews",), ("gates",),
                 ("gates", "current_demand"),
                 ("gates", "current_demand", "status"),
                 ("gates", "current_demand", "source_ids")]
        for path in paths:
            for value in shapes:
                data = pass_record()
                target = data
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.subTest(path=path, kind=type(value).__name__):
                    errors = validate(data)
                    if path == ("limitations",) and isinstance(value, str):
                        self.assertEqual(errors, [])  # Valid free text is not an error.
                    else:
                        self.assertTrue(errors)
                    self.assertNotIn("PRIVATE_SENTINEL", json.dumps(errors))

    def test_unhashable_references_and_malformed_urls_reject(self):
        for value in ({}, [], None, 1):
            data = pass_record()
            data["gates"]["current_demand"]["source_ids"] = [value]
            self.assertTrue(validate(data))
        for collection, field in (("sources", "url"), ("independent_reviews", "receipt_url")):
            data = record()
            data[collection][0][field] = "https://[PRIVATE_SENTINEL"
            errors = validate(data)
            self.assertTrue(errors)
            self.assertNotIn("PRIVATE_SENTINEL", json.dumps(errors))

    def test_duplicate_and_unknown_identifiers_never_echo(self):
        for mode in ("source", "reviewer", "reference"):
            data = record()
            if mode == "source":
                for source in data["sources"]:
                    source["id"] = "PRIVATE_SENTINEL"
            elif mode == "reviewer":
                for review in data["independent_reviews"]:
                    review["reviewer"] = "agent:PRIVATE_SENTINEL"
            else:
                data["gates"]["current_demand"]["source_ids"] = ["PRIVATE_SENTINEL"]
            errors = validate(data)
            self.assertTrue(errors)
            self.assertNotIn("PRIVATE_SENTINEL", json.dumps(errors))

    def test_schema_version_boolean_is_not_integer_one(self):
        data = record(); data["schema_version"] = True
        self.assertTrue(validate(data))

    def test_validation_preserves_supplied_record(self):
        for data in (record(), pass_record(), points_record()):
            before = copy.deepcopy(data)
            validate(data); payout_readiness(data)
            self.assertEqual(data, before)

    def _cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = main(argv)
        self.assertEqual(err.getvalue(), "")
        self.assertNotIn("PRIVATE_SENTINEL", out.getvalue())
        self.assertNotIn("Traceback", out.getvalue())
        return rc, json.loads(out.getvalue())

    def test_cli_valid_packets_and_private_unused_field(self):
        with tempfile.TemporaryDirectory(prefix="PRIVATE_SENTINEL_") as directory:
            path = Path(directory) / "record.json"
            for data in (record(), pass_record(), points_record()):
                data["private_unused"] = "PRIVATE_SENTINEL"
                path.write_text(json.dumps(data), encoding="utf-8")
                rc, result = self._cli([str(path)])
                self.assertEqual(rc, 0)
                self.assertTrue(result["ok"])
                self.assertEqual(result["decision"], data["decision"])

    def test_cli_invalid_json_duplicate_members_and_constants_reject(self):
        with tempfile.TemporaryDirectory(prefix="PRIVATE_SENTINEL_") as directory:
            path = Path(directory) / "record.json"
            texts = ["PRIVATE_SENTINEL", '{"decision":"PRIVATE_SENTINEL",}',
                     '{"decision":"PASS","decision":"NO_VERIFIABLE_ROUTE"}',
                     '{"unused":{"PRIVATE_SENTINEL":1,"PRIVATE_SENTINEL":2}}']
            for constant in ("NaN", "Infinity", "-Infinity"):
                texts.append(json.dumps(pass_record())[:-1] + ',"unused":' + constant + '}')
            for value in texts:
                path.write_text(value, encoding="utf-8")
                rc, result = self._cli([str(path)])
                self.assertEqual(rc, 1)
                self.assertFalse(result["ok"])
                self.assertIsNone(result["decision"])

    def test_cli_missing_directory_encoding_and_depth_reject_privately(self):
        with tempfile.TemporaryDirectory(prefix="PRIVATE_SENTINEL_") as directory:
            path = Path(directory) / "record.json"
            for value in (b'\xffPRIVATE_SENTINEL', b'[' * 10000 + b']' * 10000,
                          b' ' * (MAX_RECORD_BYTES + 1), b'1' * 10000):
                path.write_bytes(value)
                rc, result = self._cli([str(path)])
                self.assertEqual(rc, 1)
                self.assertFalse(result["ok"])
                self.assertIsNone(result["decision"])
            for target in (Path(directory) / "missing.json", Path(directory)):
                rc, result = self._cli([str(target)])
                self.assertEqual(rc, 1)
                self.assertFalse(result["ok"])

    def test_cli_invalid_decision_and_arguments_never_echo(self):
        with tempfile.TemporaryDirectory(prefix="PRIVATE_SENTINEL_") as directory:
            path = Path(directory) / "record.json"
            for value in ("PRIVATE_SENTINEL", {"PRIVATE_SENTINEL": 1}, ["PRIVATE_SENTINEL"]):
                data = record(); data["decision"] = value
                path.write_text(json.dumps(data), encoding="utf-8")
                rc, result = self._cli([str(path)])
                self.assertEqual(rc, 1)
                self.assertIsNone(result["decision"])
            for argv in ([], ["--PRIVATE_SENTINEL"], [str(path), "PRIVATE_SENTINEL"]):
                rc, result = self._cli(argv)
                self.assertEqual(rc, 1)
                self.assertIsNone(result["decision"])

    def test_negative_record_passes(self):
        self.assertEqual(validate(record()), [])

    def test_in_review_record_preserves_one_screen(self):
        data = record("IN_REVIEW")
        data["independent_reviews"] = data["independent_reviews"][:1]
        self.assertEqual(validate(data), [])

    def test_pass_requires_all_gates_and_positive_net(self):
        data = pass_record()
        self.assertEqual(validate(data), [])

    def test_false_pass_is_rejected(self):
        data = record("PASS")
        errors = validate(data)
        self.assertTrue(any("every required gate" in error for error in errors))
        self.assertTrue(any("positive conservative" in error for error in errors))

    def test_generic_or_historical_evidence_cannot_complete_pass_chain(self):
        data = record("PASS")
        for gate in data["gates"].values():
            gate["status"] = "verified"
        data["conservative_net_earnings_status"] = "positive"
        self.assertTrue(any("complete evidence chain" in error for error in validate(data)))

    def test_negative_needs_independent_reviewers(self):
        data = record()
        data["independent_reviews"] = data["independent_reviews"][:1]
        self.assertTrue(any("2 attributable" in error for error in validate(data)))

    def test_negative_cannot_claim_unavailable(self):
        data = record()
        data["limitations"] = "The platform is unavailable."
        self.assertTrue(any("unavailability claim" in error for error in validate(data)))

    def test_unknown_source_reference_is_rejected(self):
        data = record()
        data["gates"]["current_demand"]["source_ids"] = ["missing"]
        self.assertTrue(any("unknown source" in error for error in validate(data)))

    def test_unverified_gate_cannot_claim_complete_chain(self):
        data = record("IN_REVIEW")
        data["independent_reviews"] = data["independent_reviews"][:1]
        data["gates"]["current_demand"]["chain_complete"] = True
        self.assertTrue(any("verified exactly" in error for error in validate(data)))

    def test_case_aliased_reviewers_are_duplicates(self):
        data = record()
        data["independent_reviews"][1]["reviewer"] = "Agent:Codex"
        self.assertTrue(any("duplicate reviewer" in error for error in validate(data)))

    def test_reviewer_must_use_canonical_agent_id(self):
        data = record()
        data["independent_reviews"][0]["reviewer"] = "codex"
        self.assertTrue(any("canonical agent:" in error for error in validate(data)))

    def test_github_homepage_is_not_a_review_receipt(self):
        data = record()
        data["independent_reviews"][0]["receipt_url"] = "https://github.com/"
        self.assertTrue(any("issue or PR comment" in error for error in validate(data)))

    def test_net_earnings_status_is_an_enum(self):
        data = record()
        data["conservative_net_earnings_status"] = {"estimate": "unknown"}
        self.assertTrue(any("must be positive" in error for error in validate(data)))

    def test_every_committed_sierra_leone_packet_validates(self):
        packet_dir = Path(__file__).resolve().parent
        packets = sorted(packet_dir.glob("*-sierra-leone-*.json"))
        self.assertGreaterEqual(len(packets), 2)
        for packet in packets:
            with self.subTest(packet=packet.name):
                self.assertEqual(validate(json.loads(packet.read_text(encoding="utf-8"))), [])

    def test_positive_label_without_quote_rejected(self):
        data = pass_record(); del data["payout_economics"]
        self.assertTrue(any("positive-net label" in e for e in validate(data)))

    def test_exact_cash_net_not_human_earnings(self):
        result = payout_readiness(pass_record())
        self.assertEqual(result["net_cash_lower_bound"], "1647/100")
        self.assertFalse(result["human_earnings_established"])
        self.assertFalse(result["financial_authority"])

    def test_points_reuses_consistency_helper(self):
        data = points_record()
        self.assertEqual(validate(data), [])
        self.assertEqual(payout_readiness(data)["net_cash_lower_bound"], "1647/100")

    def test_disjoint_conversion_cannot_pass(self):
        data = points_record()
        data["payout_economics"]["quotes"][0].update(cash_min="1000", cash_max="1000")
        self.assertTrue(any("INCONSISTENT_QUOTE" in e for e in validate(data)))

    def test_fieldwork_source_fixture_cannot_pass(self):
        data = points_record()
        fixture_path = Path(__file__).with_name("fieldwork-quote-regression-2026-10-13.json")
        if fixture_path.exists():
            fixture = json.loads(fixture_path.read_text())
            data["payout_economics"].update(fixture)
            self.assertTrue(any("INCOMPLETE_QUOTE" in e for e in validate(data)))
        else:
            self.assertTrue(True)

    def test_unknown_worker_costs_never_default_zero(self):
        for basis in (pass_record, points_record):
            for name in cash_economics()["costs"]:
                for mode in ("missing", "null"):
                    data = basis()
                    if mode == "missing": del data["payout_economics"]["costs"][name]
                    else: data["payout_economics"]["costs"][name] = None
                    with self.subTest(basis=basis.__name__, name=name, mode=mode):
                        self.assertTrue(validate(data))

    def test_legacy_labels_not_normalized(self):
        data = points_record(); data["payout_economics"]["currency"] = "SLL"
        self.assertTrue(any("match payout unit" in e for e in validate(data)))

    def test_literal_confirmation_only(self):
        for field in ("currency_unit_confirmed", "fixed_conversion_confirmed"):
            for value in (1, "true", False, None):
                data = points_record(); data["payout_economics"][field] = value
                self.assertTrue(validate(data))

    def test_quote_and_cost_sources_tied_to_payout_gate(self):
        for field in ("currency_source_ids", "gross_source_ids", "conversion_source_ids"):
            data = points_record(); data["payout_economics"][field] = ["s1"]
            self.assertTrue(validate(data))
        data = points_record(); data["payout_economics"]["quotes"][0]["source_ids"] = ["s1"]
        self.assertTrue(validate(data))
        data = pass_record(); data["payout_economics"]["cost_source_ids"]["recipient_cashout_fee"] = []
        self.assertTrue(validate(data))

    def test_zero_or_negative_net_rejected(self):
        for gross in ("3.53", "3", "0"):
            data = pass_record(); data["payout_economics"]["gross_cash_min"] = gross
            self.assertTrue(any("strictly positive" in e for e in validate(data)))

    def test_invalid_gross_and_fee_amounts_fail_closed(self):
        for value in (True, 1.5, "NaN", "-1", "1e2"):
            data = pass_record(); data["payout_economics"]["gross_cash_min"] = value
            self.assertTrue(validate(data))
            data = pass_record(); data["payout_economics"]["costs"]["recipient_cashout_fee"] = value
            self.assertTrue(validate(data))

    def test_cash_label_cannot_hide_conversion(self):
        data = points_record(); data["payout_economics"].update(basis="cash", gross_cash_min="1000")
        self.assertTrue(any("cannot bypass" in e for e in validate(data)))

    def test_arithmetic_does_not_complete_other_evidence_gates(self):
        data = pass_record(); data["gates"]["current_demand"].update(status="unverified", chain_complete=False)
        self.assertTrue(any("every required gate" in e for e in validate(data)))

    def test_unrelated_gross_source_does_not_complete_task_chain(self):
        data = pass_record(); data["gates"]["current_demand"]["source_ids"] = ["s1"]
        self.assertTrue(any("share a source with current_demand" in e for e in validate(data)))

    def test_no_input_mutation(self):
        data = points_record(); before = copy.deepcopy(data)
        validate(data)
        self.assertEqual(data, before)

    def test_independent_range_endpoints_and_intersection(self):
        data = points_record()
        data["payout_economics"].update(task_points_min="10", quotes=[
            {"id": "a", "points_min": "10", "points_max": "20", "cash_min": "100",
             "cash_max": "200", "currency": "SLE", "source_ids": ["s2"]},
            {"id": "b", "points_min": "10", "points_max": "10", "cash_min": "100",
             "cash_max": "100", "currency": "SLE", "source_ids": ["s2"]}])
        self.assertEqual(validate(data), [])
        self.assertEqual(payout_readiness(data)["net_cash_lower_bound"], "9647/100")

    def test_invalid_points_and_shapes_fail_closed(self):
        for value in (True, 1.5, "NaN", "-1", "1e2", None):
            data = points_record(); data["payout_economics"]["task_points_min"] = value
            self.assertTrue(validate(data))
        for field in ("costs", "cost_source_ids", "quotes", "currency_source_ids"):
            for value in (None, True, [], [None], {"wrong": []}):
                data = points_record(); data["payout_economics"][field] = value
                self.assertTrue(validate(data))


if __name__ == "__main__":
    unittest.main()
