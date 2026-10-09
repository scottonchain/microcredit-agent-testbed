"""Offline check of inam_backer_check.py with canned registry responses (no network).

    python3 -m unittest discover -s metrics -p 'test_*.py' -v
"""
import unittest
import io
import itertools
import json
import urllib.error
from contextlib import redirect_stdout
from unittest import mock

import inam_backer_check as m

ADDR = "0x00000000000000000000000000000000000000Aa"
ME, A, B = "did:key:zMe", "did:key:zA", "did:key:zB"
IDS = itertools.count()


def agent(did=ME, address=ADDR, **extra):
    return {"id": did, "linked": {"erc8004_id": address},
            "linkedProof": {"erc8004_id": {"method": "key_possession", "keyType": "secp256k1"}}, **extra}


def receipt(requester, worker, status="finalized", dispute="none", at="2026-10-01T00:00:00Z", capability="test.work"):
    return {"receiptId": f"sha256:{next(IDS):064x}", "status": status,
            "agentA": {"id": requester}, "agentB": {"id": worker}, "task": {"capability": capability},
            "result": {"completedAt": at}, "dispute": {"status": dispute}}


def registry(agents, receipts, reputation=None):
    def get(path, **query):
        if path == "/agents/search":
            return {"agents": agents, "hasMore": False}
        if path.endswith("/reputation"):
            return reputation if reputation is not None else {"evidenceLevel": "countersigned", "trustScore": 3.1, "flags": []}
        if path.endswith("/receipts"):
            return {"receipts": receipts}  # current SPEC's unpaginated public listing
        raise AssertionError(path)
    return mock.patch.object(m, "get", get)


class BackerCheck(unittest.TestCase):
    def test_no_link_means_no_history(self):
        other = {"id": ME, "linked": {"erc8004_id": "0x" + "1" * 40}}
        with registry([other], []):
            self.assertIsNone(m.check(ADDR)["inamId"])

    def test_counts_only_finished_work_done_by_the_borrower(self):
        me = agent(address=ADDR.lower())  # case-insensitive match
        rs = [receipt(A, ME), receipt(B, ME, at="2026-10-05T00:00:00Z"), receipt(A, ME, status="draft"),
              receipt(A, ME, status="finalized", dispute="open"), receipt(ME, B)]  # last: borrower was the requester
        with registry([me], rs):
            r = m.check(ADDR)
        self.assertEqual(r["inamId"], ME)
        self.assertEqual(r["jobsFinalized"], 3)
        self.assertEqual(r["distinctCounterparties"], 2)
        self.assertEqual(r["jobsDisputed"], 1)
        self.assertEqual(r["lastCompletedAt"], "2026-10-05T00:00:00Z")
        self.assertEqual(r["historyScope"], "public_registry_receipts")
        self.assertIn("not independently verified", r["assurance"])
        self.assertIn("disputes", r["summary"])

    def test_revoked(self):
        me = agent(revokedAt="2026-10-02T00:00:00Z", metadata={"demo": True})
        with registry([me], [receipt(A, ME)]):
            r = m.check(ADDR)
        self.assertIn("INAM ID is revoked", r["summary"])
        self.assertIn("demo registration", r["summary"])
        self.assertIn("historical records only", r["summary"])

    def test_demo_registration_is_not_reported_as_real_finished_work(self):
        with registry([agent(metadata={"demo": True})], [receipt(A, ME)]):
            r = m.check(ADDR)
        self.assertEqual(r["jobsFinalized"], 0)
        self.assertEqual(r["demoJobsFinalized"], 1)
        self.assertIn("not evidence of real work", r["summary"])

    def test_ordinary_agent_demo_receipts_are_excluded(self):
        with registry([agent()], [receipt(A, ME, capability="demo.sha256"), receipt(B, ME)]):
            r = m.check(ADDR)
        self.assertEqual(r["jobsFinalized"], 1)
        self.assertEqual(r["distinctCounterparties"], 1)
        self.assertEqual(r["demoJobsFinalized"], 1)
        self.assertIn("1 finalized demo receipts excluded", r["summary"])

    def test_empty_public_list_does_not_claim_no_private_history(self):
        with registry([agent()], []):
            r = m.check(ADDR)
        self.assertIn("private history unknown", r["summary"])
        self.assertNotIn("no finished work", r["summary"])

    def test_malformed_demo_flag_does_not_become_real_work(self):
        for flag in ("false", "true", 0, 1, None):
            with self.subTest(flag=flag), registry([agent(metadata={"demo": flag})], [receipt(A, ME)]):
                r = m.check(ADDR)
            self.assertEqual(r["lookupStatus"], "unknown")
            self.assertNotIn("jobsFinalized", r)

    def test_link_without_possession_metadata_stays_unknown(self):
        for proof in ({}, {"erc8004_id": {"method": "unverified_claim"}}):
            with self.subTest(proof=proof), registry([agent(linkedProof=proof)], []):
                r = m.check(ADDR)
            self.assertEqual(r["lookupStatus"], "unknown")
            self.assertNotIn("jobsFinalized", r)

    def test_multiple_linked_ids_are_not_arbitrarily_selected(self):
        with registry([agent(), agent(did=A)], []):
            r = m.check(ADDR)
        self.assertEqual(r["lookupStatus"], "unknown")
        self.assertIn("ambiguous", r["error"])

    def test_missing_reputation_fields_do_not_become_clean_or_zero(self):
        good = {"evidenceLevel": "countersigned", "trustScore": 3.1, "flags": []}
        for key in good:
            rep = {k: v for k, v in good.items() if k != key}
            with self.subTest(key=key), registry([agent()], [], reputation=rep):
                r = m.check(ADDR)
            self.assertEqual(r["lookupStatus"], "unknown")
            self.assertNotIn("trustScore", r)
            self.assertNotIn("flags", r)

    def test_missing_dispute_or_capability_is_not_clean_work(self):
        for field in ("dispute", "task"):
            bad = receipt(A, ME)
            del bad[field]
            with self.subTest(field=field), registry([agent()], [bad]):
                r = m.check(ADDR)
            self.assertEqual(r["lookupStatus"], "unknown")
            self.assertNotIn("jobsFinalized", r)

    def test_completion_timestamps_are_compared_as_instants(self):
        rs = [receipt(A, ME, at="2026-10-05T01:00:00+02:00"),
              receipt(B, ME, at="2026-10-05T00:00:00Z")]
        with registry([agent()], rs):
            r = m.check(ADDR)
        self.assertEqual(r["lastCompletedAt"], "2026-10-05T00:00:00Z")

    def test_missing_party_identity_does_not_become_a_counterparty(self):
        for party in ("agentA", "agentB"):
            bad = receipt(A, ME)
            bad[party]["id"] = None
            with self.subTest(party=party), registry([agent()], [bad]):
                r = m.check(ADDR)
            self.assertEqual(r["lookupStatus"], "unknown")
            self.assertNotIn("distinctCounterparties", r)


class IncompleteReads(unittest.TestCase):
    def test_agent_search_walks_short_pages_without_skipping_offsets(self):
        def get(path, **q):
            self.assertEqual(path, "/agents/search")
            return {"agents": [agent(address="0x" + "1" * 40)], "hasMore": True} if q["offset"] == 0 else {
                "agents": [agent(did=A)], "hasMore": False}
        with mock.patch.object(m, "get", side_effect=get) as fetched:
            self.assertEqual(m.agent_for(ADDR)["id"], A)
        self.assertEqual([c.kwargs["offset"] for c in fetched.call_args_list], [0, 1])

    def test_receipt_pagination_is_supported_if_registry_exposes_it(self):
        one, two = receipt(A, ME), receipt(B, ME)
        with mock.patch.object(m, "get", side_effect=[{"receipts": [one], "hasMore": True},
                                                     {"receipts": [two], "hasMore": False}]) as fetched:
            rows = list(m.paged("/agents/test/receipts", "receipts", allow_unpaged=True))
        self.assertEqual(rows, [one, two])
        self.assertEqual([c.kwargs["offset"] for c in fetched.call_args_list], [0, 1])

    def test_missing_or_invalid_search_marker_is_unknown_not_no_link(self):
        for page in ({"agents": []}, {"agents": [], "hasMore": None}, {"agents": [], "hasMore": "false"}):
            with self.subTest(page=page), mock.patch.object(m, "get", return_value=page):
                r = m.check(ADDR)
            self.assertEqual(r["lookupStatus"], "unknown")

    def test_search_failure_after_match_does_not_return_success(self):
        with mock.patch.object(m, "get", side_effect=[{"agents": [agent()], "hasMore": True},
                                                     m.RegistryError("registry HTTP 503")]):
            r = m.check(ADDR)
        self.assertEqual(r["lookupStatus"], "unknown")
        self.assertNotIn("jobsFinalized", r)

    def test_duplicate_and_empty_continuation_are_rejected(self):
        for pages in ([{"agents": [agent()], "hasMore": True}, {"agents": [agent()], "hasMore": False}],
                      [{"agents": [], "hasMore": True}]):
            with self.subTest(pages=pages), mock.patch.object(m, "get", side_effect=pages):
                self.assertEqual(m.check(ADDR)["lookupStatus"], "unknown")

    def test_receipt_listing_cannot_lose_pagination_marker_mid_scan(self):
        with mock.patch.object(m, "get", side_effect=[{"receipts": [receipt(A, ME)], "hasMore": True},
                                                     {"receipts": []}]):
            with self.assertRaises(m.RegistryError):
                list(m.paged("/agents/test/receipts", "receipts", allow_unpaged=True))

    def test_scan_limit_is_unknown(self):
        with mock.patch.object(m, "MAX_PAGES", 1), mock.patch.object(m, "get", return_value={
                "agents": [agent()], "hasMore": True}):
            self.assertEqual(m.check(ADDR)["lookupStatus"], "unknown")

    def test_http_failure_is_json_unknown_and_nonzero_exit(self):
        for error in (urllib.error.HTTPError("https://registry.invalid", 429, "rate limited", {}, None),
                      urllib.error.URLError("connection refused"), TimeoutError()):
            output = io.StringIO()
            with self.subTest(error=error), mock.patch.object(m.urllib.request, "urlopen", side_effect=error), redirect_stdout(output):
                code = m.main([ADDR, "--json"])
            self.assertEqual(code, 2)
            r = json.loads(output.getvalue())
            self.assertEqual(r["lookupStatus"], "unknown")
            self.assertNotIn("jobsFinalized", r)

    def test_invalid_json_stays_unknown(self):
        with mock.patch.object(m.urllib.request, "urlopen") as opened:
            opened.return_value.__enter__.return_value = io.StringIO("not JSON")
            self.assertEqual(m.check(ADDR)["lookupStatus"], "unknown")

    def test_address_must_be_hex(self):
        with mock.patch.object(m, "check") as checked, self.assertRaises(SystemExit):
            m.main(["0x" + "z" * 40])
        checked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
