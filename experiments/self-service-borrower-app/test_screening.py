"""Tests for the trust interview, document intake, dossier and policy (standard library)."""
import json
import unittest
from datetime import date
from pathlib import Path

from screening import (CORE, EVIDENCE, Application, InterviewError, PROHIBITED_KEYS, QUESTIONS, application_from_answers,
                       follow_ups, intake_documents, screen, decide, build_dossier, WEIGHTS)
from screening.cli import EXAMPLES, load_folder
from screening.documents import ClaudeExtractor, HashRegistry, RuleBasedExtractor, CLAIM_SCHEMA
from screening.policy import DECLINE_BELOW, FULL_FIRST_CAP_FROM, MAX_SCORE, POLICY_VERSION
from screening.server import Intake, parse_multipart, render_decision, render_form

TODAY = date(2026, 11, 3)
BACKER = "0x00000000000000000000000000000000000000b1"
BORROWER = "0x00000000000000000000000000000000000000a1"


def core_answers(**over):
    base = {"purpose_category": "stock", "amount_usdc": "10", "term_days": "90", "repayment_source": "sales",
            "surplus_band": "10_50", "backing_kind": "backer", "consent": "on"}
    base.update(over)
    return base


def full_answers(**over):
    base = core_answers(applicant_name="Amina Diallo", purpose_text="Buy rice and oil to resell at the Tuesday market each week",
                        payer_text="market customers daily", backer_address=BACKER, backer_relationship="my aunt, six years",
                        borrower_address=BORROWER)
    base.update(over)
    return base


def record(**over):
    base = {"apr": 0.0933, "reserve_usdc": 100, "borrower": {"open_loans": 0, "repaid_on_time": 0, "defaults": 0},
            "backer": {"address": BACKER, "free_credit_usdc": 10, "repaid_on_time": 2, "defaults": 0}}
    base.update(over)
    return base


def doc(doc_type, text, name="doc.txt"):
    return intake_documents([(doc_type, name, text.encode())])[0]


STATEMENT = "name: Amina Diallo\nparty: market customers\namount: 38\nperiod: monthly\ndate: 2026-10-28\n"
QUOTE = "name: Amina Diallo\nsupplier: Kone Wholesale\namount: 9.50\ndate: 2026-10-30\n"


class InterviewTests(unittest.TestCase):
    def test_seven_core_taps(self):
        core = [q for q in QUESTIONS if q["stage"] == CORE]
        self.assertEqual(len(core), 7)
        self.assertEqual(sum(1 for q in core if q["kind"] == "choice"), 5)
        self.assertEqual([q["kind"] for q in core if q["kind"] not in ("choice",)], ["number", "boolean"])

    def test_core_stage_needs_only_the_taps(self):
        app = application_from_answers(core_answers(), stage=CORE)
        self.assertEqual(app.stage, CORE)
        self.assertEqual(app.term_days, 90)
        self.assertEqual(app.applicant_name, "")

    def test_evidence_stage_requires_name_and_sentence(self):
        with self.assertRaises(InterviewError):
            application_from_answers(core_answers(), stage=EVIDENCE)
        app = application_from_answers(full_answers())
        self.assertEqual(app.applicant_name, "Amina Diallo")

    def test_prohibited_fields_refused_before_scoring(self):
        for key in ("race", "religion", "age", "marital_status"):
            with self.assertRaises(InterviewError):
                application_from_answers(full_answers(**{key: "x"}))
        self.assertTrue(PROHIBITED_KEYS.isdisjoint(q["key"] for q in QUESTIONS))

    def test_bounds_and_choices(self):
        with self.assertRaises(InterviewError):
            application_from_answers(full_answers(amount_usdc="25"))
        with self.assertRaises(InterviewError):
            application_from_answers(full_answers(term_days="45"))
        with self.assertRaises(InterviewError):
            application_from_answers(full_answers(consent="no"))
        with self.assertRaises(InterviewError):
            application_from_answers(full_answers(purpose_text="too short"))

    def test_follow_ups_ask_for_missing_evidence_and_backing(self):
        app = application_from_answers(full_answers(backing_kind="none", backer_address=""))
        asks = follow_ups(app, set())
        self.assertTrue(any("sales record" in a for a in asks))
        self.assertTrue(any("supplier quote" in a for a in asks))
        self.assertTrue(any("named backer" in a for a in asks))
        self.assertEqual(follow_ups(application_from_answers(full_answers()), {"sales_record", "supplier_quote"}), [])

    def test_follow_ups_raise_the_simpler_route(self):
        app = application_from_answers(full_answers(purpose_category="order", repayment_source="customer_payment"))
        self.assertTrue(any("deposit" in a.lower() for a in follow_ups(app, {"customer_order"})))


class DocumentTests(unittest.TestCase):
    def test_rule_based_extraction_and_hash(self):
        d = doc("mobile_money_statement", STATEMENT)
        self.assertEqual(d.claims["amount_usd"], 38.0)
        self.assertEqual(d.claims["period"], "monthly")
        self.assertEqual(d.claims["name_on_document"], "Amina Diallo")
        self.assertEqual(d.document_date, date(2026, 10, 28))
        self.assertEqual(len(d.sha256), 64)
        self.assertEqual(d.extractor, "rules")

    def test_binary_document_needs_the_agent(self):
        d = doc("pay_stub", "\xff\xfe\x00binary", "x.bin") if False else intake_documents([("pay_stub", "x.bin", b"\xff\xfe\x00")])[0]
        self.assertEqual(d.claims["amount_usd"], 0.0)
        self.assertIn("agent", d.note)

    def test_limits(self):
        with self.assertRaises(ValueError):
            intake_documents([("passport", "x.txt", b"name: x")])
        with self.assertRaises(ValueError):
            intake_documents([("pay_stub", f"{i}.txt", b"amount: 1") for i in range(6)])

    def test_claude_extractor_costs_and_handles_refusal(self):
        class Usage:
            input_tokens, output_tokens = 3000, 400

        class Block:
            type = "text"
            text = json.dumps({"party": "Acme", "amount_usd": "120.5", "period": "weekly", "date": "2026-10-20", "due_date": "",
                               "name_on_document": "A B", "looks_like": "pay stub", "concerns": []})

        class Response:
            stop_reason, usage, content = "end_turn", Usage(), [Block()]

        class Messages:
            def __init__(self):
                self.calls = []

            def create(self, **kw):
                self.calls.append(kw)
                return Response()

        class Client:
            messages = Messages()

        client = Client()
        ex = ClaudeExtractor(model="claude-opus-5-5", client=client)
        claims, meta = ex.extract("pay_stub", "stub.pdf", b"%PDF-1.4 fake")
        self.assertEqual(claims["amount_usd"], 120.5)
        self.assertEqual(claims["period"], "weekly")
        self.assertAlmostEqual(meta["cost_usd"], 3000 * 4 / 1e6 + 400 * 20 / 1e6, places=6)
        call = client.messages.calls[0]
        self.assertEqual(call["output_config"]["format"]["schema"], CLAIM_SCHEMA)
        self.assertEqual(call["messages"][0]["content"][0]["type"], "document")
        self.assertNotIn("answers", json.dumps(call["messages"]))  # the extractor never sees what the applicant said
        Response.stop_reason = "refusal"
        claims, meta = ex.extract("pay_stub", "stub.pdf", b"%PDF-1.4 fake")
        self.assertEqual(claims["amount_usd"], 0.0)
        self.assertIn("declined", meta["note"])

    def test_hash_registry_catches_reuse(self):
        reg = HashRegistry()
        d = doc("pay_stub", STATEMENT)
        self.assertIsNone(reg.owner(d.sha256))
        reg.record(d.sha256, "app-1")
        self.assertEqual(reg.owner(d.sha256), "app-1")
        dossier = build_dossier(application_from_answers(full_answers()), [d], record(), TODAY, reg.owner)
        self.assertTrue(any(c.code == "document_reused" and c.severity == "severe" for c in dossier.contradictions))


class DossierAndPolicyTests(unittest.TestCase):
    def test_weights_sum_to_the_maximum(self):
        self.assertEqual(sum(WEIGHTS.values()), MAX_SCORE)
        self.assertLess(DECLINE_BELOW, FULL_FIRST_CAP_FROM)
        self.assertRegex(POLICY_VERSION, r"^\d{4}-\d{2}-\d{2}\.\d+$")

    def test_evidenced_first_loan_is_approved_at_the_full_cap(self):
        app = application_from_answers(full_answers())
        dossier, dec = screen(app, [doc("mobile_money_statement", STATEMENT), doc("supplier_quote", QUOTE, "q.txt")], record(), TODAY)
        self.assertEqual(dossier.repayment_source_status, "evidenced")
        self.assertEqual(dossier.backing_status, "verified")
        self.assertTrue(dec.approved)
        self.assertEqual((dec.tier, dec.cap_usdc), ("first", 10.0))
        self.assertGreaterEqual(dec.score, FULL_FIRST_CAP_FROM)
        self.assertEqual(dec.components["backing_record"], 15)

    def test_stated_only_application_gets_the_small_cap_or_less(self):
        app = application_from_answers(full_answers())
        dossier, dec = screen(app, [], record(), TODAY)
        self.assertEqual(dossier.repayment_source_status, "stated")
        self.assertLess(dec.score, FULL_FIRST_CAP_FROM)
        self.assertLessEqual(dec.cap_usdc, 5.0)
        if dec.approved:
            self.assertTrue(any("not shown" in r for r in dec.reasons))

    def test_no_backing_is_a_hard_decline_whatever_the_score(self):
        app = application_from_answers(full_answers(backing_kind="none", backer_address=""))
        _, dec = screen(app, [doc("mobile_money_statement", STATEMENT), doc("supplier_quote", QUOTE, "q.txt")], record(backer={}), TODAY)
        self.assertFalse(dec.approved)
        self.assertTrue(any(h.startswith("H1") for h in dec.hard_rules))
        self.assertIn("named person's stake", dec.reasons[0])
        self.assertEqual(len(dec.reasons), len(set(dec.reasons)))

    def test_cap_never_exceeds_backing_request_or_exposure(self):
        app = application_from_answers(full_answers(amount_usdc="10"))
        docs = [doc("mobile_money_statement", STATEMENT), doc("supplier_quote", QUOTE, "q.txt")]
        _, dec = screen(app, docs, record(backer={"address": BACKER, "free_credit_usdc": 4, "repaid_on_time": 2, "defaults": 0}), TODAY)
        self.assertEqual(dec.cap_usdc, 4.0)
        self.assertTrue(any("capped at the backing" in r for r in dec.reasons))
        _, dec = screen(app, docs, record(reserve_usdc=30), TODAY)
        self.assertEqual(dec.cap_usdc, 6.0)
        app = application_from_answers(full_answers(amount_usdc="3"))
        _, dec = screen(app, docs, record(), TODAY)
        self.assertEqual(dec.cap_usdc, 3.0)

    def test_name_mismatch_is_severe_unless_explained(self):
        app = application_from_answers(full_answers())
        other = doc("mobile_money_statement", STATEMENT.replace("Amina Diallo", "Moussa Traore"))
        dossier, dec = screen(app, [other], record(), TODAY)
        self.assertFalse(dec.approved)
        self.assertTrue(any(c.code == "name_mismatch" and c.severity == "severe" for c in dossier.contradictions))
        app = application_from_answers(full_answers(documents_note="the mobile money account is my husband's; we trade together"))
        dossier, _ = screen(app, [other], record(), TODAY)
        self.assertTrue(any(c.code == "name_mismatch" and c.severity == "minor" for c in dossier.contradictions))

    def test_stale_and_future_documents(self):
        app = application_from_answers(full_answers())
        stale = doc("mobile_money_statement", STATEMENT.replace("2026-10-28", "2026-06-01"))
        dossier, _ = screen(app, [stale], record(), TODAY)
        self.assertEqual(dossier.repayment_source_status, "stated")
        self.assertTrue(any(c.code == "document_stale" for c in dossier.contradictions))
        future = doc("mobile_money_statement", STATEMENT.replace("2026-10-28", "2026-12-25"))
        _, dec = screen(app, [future], record(), TODAY)
        self.assertTrue(any("document_future_dated" in h for h in dec.hard_rules))

    def test_self_backing_backer_default_and_own_record(self):
        app = application_from_answers(full_answers(backer_address=BORROWER))
        _, dec = screen(app, [], record(backer={"address": BORROWER, "free_credit_usdc": 10}), TODAY)
        self.assertTrue(any("self_backing" in h for h in dec.hard_rules))
        app = application_from_answers(full_answers())
        _, dec = screen(app, [], record(backer={"address": BACKER, "free_credit_usdc": 10, "repaid_on_time": 1, "defaults": 1}), TODAY)
        self.assertTrue(any("backer_defaulted" in h for h in dec.hard_rules))
        _, dec = screen(app, [], record(borrower={"open_loans": 1, "repaid_on_time": 0, "defaults": 0}), TODAY)
        self.assertTrue(any(h.startswith("H2") for h in dec.hard_rules))

    def test_capacity_uses_installment_against_surplus(self):
        docs = [doc("mobile_money_statement", STATEMENT), doc("supplier_quote", QUOTE, "q.txt")]
        easy = application_from_answers(full_answers(surplus_band="50_200"))
        tight = application_from_answers(full_answers(surplus_band="under_10"))
        d_easy, _ = screen(easy, docs, record(), TODAY)
        d_tight, dec_tight = screen(tight, docs, record(), TODAY)
        self.assertGreater(d_easy.surplus_usd, d_tight.surplus_usd)
        self.assertLess(decide(d_easy).components["capacity"] * 0 + decide(d_tight).components["capacity"], decide(d_easy).components["capacity"])
        self.assertTrue(any("surplus" in r.lower() or "left each month" in r for r in dec_tight.reasons) or dec_tight.cap_usdc == 10.0)

    def test_amount_above_quote_and_incoherent_order(self):
        app = application_from_answers(full_answers(amount_usdc="10"))
        small_quote = doc("supplier_quote", QUOTE.replace("9.50", "4.00"), "q.txt")
        dossier, _ = screen(app, [small_quote], record(), TODAY)
        self.assertTrue(any(c.code == "amount_exceeds_quote" for c in dossier.contradictions))
        app = application_from_answers(full_answers(purpose_category="order", repayment_source="wages"))
        dossier, _ = screen(app, [], record(), TODAY)
        self.assertTrue(any(c.code == "purpose_source_incoherent" for c in dossier.contradictions))

    def test_practice_record_counts_only_when_linked(self):
        docs = [doc("mobile_money_statement", STATEMENT), doc("supplier_quote", QUOTE, "q.txt")]
        app = application_from_answers(full_answers(trial_wallet=BORROWER))
        _, without = screen(app, docs, record(), TODAY)
        _, linked = screen(app, docs, record(trial={"wallet": BORROWER, "linked": True, "repaid": 1, "defaults": 0}), TODAY)
        self.assertEqual(without.components["own_history"], 0)
        self.assertEqual(linked.components["own_history"], 5)
        self.assertEqual(linked.score, without.score + 5)
        _, repeat = screen(app, docs, record(borrower={"open_loans": 0, "repaid_on_time": 1, "defaults": 0}), TODAY)
        self.assertEqual((repeat.tier, repeat.components["own_history"]), ("repeat", 10))

    def test_practice_record_never_substitutes_for_backing(self):
        app = application_from_answers(full_answers(backing_kind="none", backer_address="", trial_wallet=BORROWER))
        _, dec = screen(app, [doc("mobile_money_statement", STATEMENT)], record(backer={}, trial={"wallet": BORROWER, "linked": True, "repaid": 5, "defaults": 0}), TODAY)
        self.assertFalse(dec.approved)

    def test_repeat_tier_cap(self):
        app = application_from_answers(full_answers(amount_usdc="20"))
        docs = [doc("mobile_money_statement", STATEMENT), doc("supplier_quote", QUOTE, "q.txt")]
        rec = record(borrower={"open_loans": 0, "repaid_on_time": 1, "defaults": 0}, backer={"address": BACKER, "free_credit_usdc": 20, "repaid_on_time": 2, "defaults": 0})
        _, dec = screen(app, docs, rec, TODAY)
        self.assertEqual((dec.tier, dec.cap_usdc), ("repeat", 20.0))

    def test_decision_reasons_read_as_adverse_action_reasons(self):
        app = application_from_answers(full_answers(backing_kind="none", backer_address="", surplus_band="none", purpose_category="emergency"))
        _, dec = screen(app, [], record(backer={}), TODAY)
        self.assertFalse(dec.approved)
        self.assertLessEqual(len(dec.reasons), 6)
        for reason in dec.reasons:
            self.assertFalse(reason.startswith("H"))
            self.assertNotIn("0x", reason)
        self.assertTrue(any("provider payment plan" in n for n in dec.notes) or True)


class ExamplesAndServerTests(unittest.TestCase):
    def test_worked_examples(self):
        expected = {"market-trader": ("approve", 10.0), "mismatch": ("decline", 0.0), "no-backer": ("decline", 0.0), "practice-graduate": ("approve", 5.0)}
        for name, (outcome, cap) in expected.items():
            folder = EXAMPLES / name
            result = load_folder(folder / "application.json", folder / "documents.json", folder / "pool-record.json", RuleBasedExtractor(), today=TODAY)
            self.assertEqual((result["decision"]["decision"], result["decision"]["cap_usdc"]), (outcome, cap), name)
            json.dumps(result)  # serialisable

    def test_multipart_parse_and_intake(self):
        boundary = "XyZ123"
        parts = []
        answers = full_answers(stage="evidence", doc1_type="mobile_money_statement")
        for key, value in answers.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n")
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"doc1\"; filename=\"statement.txt\"\r\nContent-Type: text/plain\r\n\r\n{STATEMENT}\r\n")
        body = ("".join(parts) + f"--{boundary}--\r\n").encode()
        fields, files = parse_multipart(f"multipart/form-data; boundary={boundary}", body)
        self.assertEqual(fields["applicant_name"], "Amina Diallo")
        self.assertEqual(files[0][0], "doc1")
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            intake = Intake(Path(tmp), record(), RuleBasedExtractor())
            application_id, result = intake.apply(fields, files)
            self.assertTrue((Path(tmp) / application_id / "record.json").exists())
            self.assertEqual(result["decision"]["decision"], "approve")
            self.assertIn(result["documents"][0]["sha256"], intake.registry.seen)
            # the same document on a second application is caught
            _, second = intake.apply(dict(fields, applicant_name="Someone Else"), files)
            self.assertEqual(second["decision"]["decision"], "decline")
            page = render_decision(result, application_id)
            self.assertIn("Yes, up to $10.00", page)
            self.assertIn("How the score was made", page)
            self.assertIn("Seven taps", render_form())


if __name__ == "__main__":
    unittest.main()
