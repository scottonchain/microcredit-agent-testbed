import json
from pathlib import Path
import tempfile
import unittest
from coordination.check_workspace import REPOS, check


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for repo in REPOS:
            (self.root / repo).mkdir()
        tb = self.root / REPOS[0]
        self.tb = tb
        (tb / "deployments").mkdir()
        address = "0x" + "1" * 40
        deployment = dict(chain_id=84532, rpc_url="https://example.test", pool=address,
                          lens=address, scores=address, token={"address": address},
                          source={"contract_commit": "abcdef1"})
        (tb / "deployments/current.json").write_text(json.dumps(deployment))
        card = {"chain": dict(chainId=84532, rpc="https://example.test", pool=address,
                             lens=address, scoreProvider=address, testToken=address, contractCommit="abcdef1")}
        self.card = json.dumps(card)
        (tb / "agent-card.json").write_text(self.card)
        for repo in (tb, self.root / REPOS[4]):
            (repo / ".well-known").mkdir()
            for name in ("agent-card.json", "agent.json"):
                (repo / ".well-known" / name).write_text(self.card)
        app = self.root / REPOS[1] / "packages/nextjs"
        (app / "contracts").mkdir(parents=True)
        (app / "utils").mkdir()
        (app / "contracts/deployedContracts.ts").write_text('  84532: {\n' + '\n'.join(
            f'    {name}: {{ address: "{address}" }},' for name in ("DecentralizedMicrocredit", "MicrocreditLens", "OracleScoreProvider")) + '\n  },')
        (app / "utils/microcredit.ts").write_text(f'{address}\ndeployedCommit: "abcdef1"')

    def test_matching_workspace(self):
        self.assertEqual(check(self.root, verify_remotes=False), [])

    def test_mirror_drift_is_detected_and_only_explicitly_repaired(self):
        mirror = self.tb / ".well-known/agent-card.json"
        mirror.write_text("{}")
        self.assertTrue(check(self.root, verify_remotes=False))
        self.assertEqual(mirror.read_text(), "{}")
        self.assertEqual(check(self.root, verify_remotes=False, sync_cards=True), [])
        self.assertEqual(mirror.read_text(), self.card)

    def test_deployment_mismatch_does_not_propagate_to_mirrors(self):
        card = json.loads(self.card)
        card["chain"]["pool"] = "0x" + "2" * 40
        (self.tb / "agent-card.json").write_text(json.dumps(card))
        self.assertTrue(check(self.root, verify_remotes=False, sync_cards=True))
        self.assertEqual((self.tb / ".well-known/agent-card.json").read_text(), self.card)

    def test_legacy_discovery_aliases_are_checked_and_repaired(self):
        for repo in (self.tb, self.root / REPOS[4]):
            alias = repo / ".well-known/agent.json"
            alias.write_text("{}")
            self.assertTrue(check(self.root, verify_remotes=False))
            self.assertEqual(check(self.root, verify_remotes=False, sync_cards=True), [])
            self.assertEqual(alias.read_text(), self.card)

    def test_missing_checkout_fails(self):
        (self.root / REPOS[2]).rmdir()
        self.assertEqual(check(self.root, verify_remotes=False), ["Missing checkout: " + REPOS[2]])

    def test_application_mismatch_blocks_card_writes(self):
        mirror = self.tb / ".well-known/agent-card.json"
        mirror.write_text("{}")
        config = self.root / REPOS[1] / "packages/nextjs/utils/microcredit.ts"
        config.write_text("mismatched app configuration")
        self.assertTrue(check(self.root, verify_remotes=False, sync_cards=True))
        self.assertEqual(mirror.read_text(), "{}")
