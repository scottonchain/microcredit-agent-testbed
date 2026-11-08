import copy
import unittest
from pending_journal import PendingJournal
import test_interfaces as fixtures
from test_durable import tx

class Source:
    def __init__(self): self.outcome=None;self.hash=fixtures.BLOCK
    def observe(self,h):return copy.deepcopy(self.outcome)
    def head(self):return 150
    def block_hash(self,n):return self.hash

class Pending(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.Interfaces();self.fixture.setUp();self.fixture.consent()
        self.t=self.fixture.bind();self.source=Source()
        self.journal=PendingJournal(self.fixture.bindings,self.source)
    def tearDown(self):self.fixture.tearDown()
    def prepare(self):return self.journal.prepare('bind',self.t,tx(500),1100)
    def outcome(self,status=1):
        self.source.outcome={'hash':tx(500),'transaction':copy.deepcopy(self.t),'status':status,'block':100,'block_hash':fixtures.BLOCK}
    def test_unknown_attempt_never_releases(self):
        self.assertTrue(self.prepare());self.assertFalse(self.prepare())
        self.assertEqual(self.journal.reconcile('bind'),'HOLD')
        self.assertEqual(self.fixture.ledger.totals()['net'],10_000_000)
        self.assertFalse(self.journal.barrier()['release_allowed'])
    def test_replacement_hash_and_transaction_changes_rejected(self):
        self.prepare()
        with self.assertRaises(ValueError):self.journal.prepare('bind',self.t,tx(501),1100)
        self.outcome();self.source.outcome['transaction']['nonce']='0x4'
        with self.assertRaises(ValueError):self.journal.reconcile('bind')
    def test_confirmation_idempotent_retains_backing_and_reorg_incident(self):
        self.prepare();self.outcome()
        self.assertEqual(self.journal.reconcile('bind'),'CONFIRMED')
        self.assertEqual(self.journal.reconcile('bind'),'CONFIRMED')
        self.assertEqual(self.fixture.ledger.totals()['net'],10_000_000)
        self.source.hash=tx(999)
        self.assertFalse(self.journal.audit())
        self.assertGreater(self.fixture.ledger.db.execute('SELECT COUNT(*) FROM incidents').fetchone()[0],0)
    def test_root_audit_detects_journal_reorg_without_optional_journal_audit(self):
        self.prepare();self.outcome();self.journal.reconcile('bind')
        self.fixture.reader.hashes[100]=tx(999)
        with self.assertRaisesRegex(ValueError,'canonical incident'):self.fixture.bindings.validate('bind',self.t,1100)
        self.assertGreater(self.fixture.ledger.db.execute('SELECT COUNT(*) FROM incidents').fetchone()[0],0)
    def test_revert_also_retains_prior_backing(self):
        self.prepare();self.outcome(0)
        self.assertEqual(self.journal.reconcile('bind'),'REVERTED')
        self.assertEqual(self.fixture.ledger.totals()['net'],10_000_000)
    def test_withdrawal_between_validation_and_persistence_blocks(self):
        original=self.fixture.bindings.validate
        def interleaved(*args):
            result=original(*args)
            self.fixture.bindings.record_consent(fixtures.BORROWER,2,False,'fictional-practice',4000)
            return result
        self.fixture.bindings.validate=interleaved
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(self.fixture.ledger.db.execute('SELECT COUNT(*) FROM backing_attempts').fetchone()[0],0)
    def test_restart_preserves_pending_hash(self):
        self.prepare()
        from durable import Ledger
        from service_binding import ReplyBindings
        f=self.fixture;f.ledger.close();f.ledger=Ledger(f.path,f.policy,f.reader)
        f.bindings=ReplyBindings(f.ledger,fixtures.DESK,fixtures.OFFICER,f.service,{'practice':'Fictional practice only.'})
        journal=PendingJournal(f.bindings,self.source)
        self.assertEqual(journal.reconcile('bind'),'HOLD')
        with self.assertRaises(ValueError):journal.prepare('bind',self.t,tx(501),1100)
