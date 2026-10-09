"""Offline check of inam_backer_check.py with canned registry responses (no network).

    python3 -m unittest discover -s metrics -p 'test_*.py' -v
"""
import unittest
from unittest import mock

import inam_backer_check as m

ADDR = "0x00000000000000000000000000000000000000Aa"
ME, A, B = "did:key:zMe", "did:key:zA", "did:key:zB"


def receipt(requester, worker, status="finalized", dispute="none", at="2026-10-01T00:00:00Z"):
    return {"status": status, "agentA": {"id": requester}, "agentB": {"id": worker},
            "result": {"completedAt": at}, "dispute": {"status": dispute}}


def registry(agents, receipts):
    def get(path, **query):
        if path == "/agents/search":
            return {"agents": agents, "hasMore": False}
        if path.endswith("/reputation"):
            return {"evidenceLevel": "countersigned", "trustScore": 3.1, "flags": []}
        if path.endswith("/receipts"):
            return {"receipts": receipts, "hasMore": False}
        raise AssertionError(path)
    return mock.patch.object(m, "get", get)


class BackerCheck(unittest.TestCase):
    def test_no_link_means_no_history(self):
        other = {"id": ME, "linked": {"erc8004_id": "0x" + "1" * 40}}
        with registry([other], []):
            self.assertIsNone(m.check(ADDR)["inamId"])

    def test_counts_only_finished_work_done_by_the_borrower(self):
        me = {"id": ME, "linked": {"erc8004_id": ADDR.lower()}}  # case-insensitive match
        rs = [receipt(A, ME), receipt(B, ME, at="2026-10-05T00:00:00Z"), receipt(A, ME, status="draft"),
              receipt(A, ME, status="finalized", dispute="open"), receipt(ME, B)]  # last: borrower was the requester
        with registry([me], rs):
            r = m.check(ADDR)
        self.assertEqual(r["inamId"], ME)
        self.assertEqual(r["jobsFinalized"], 3)
        self.assertEqual(r["distinctCounterparties"], 2)
        self.assertEqual(r["jobsDisputed"], 1)
        self.assertEqual(r["lastCompletedAt"], "2026-10-05T00:00:00Z")

    def test_revoked(self):
        me = {"id": ME, "linked": {"erc8004_id": ADDR}, "revokedAt": "2026-10-02T00:00:00Z"}
        with registry([me], []):
            self.assertEqual(m.check(ADDR)["summary"], "INAM ID is revoked")


if __name__ == "__main__":
    unittest.main()
