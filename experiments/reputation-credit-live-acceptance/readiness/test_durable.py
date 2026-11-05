import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from bounds import VerifiedCase
from durable import Ledger, Policy, Observation

POOL='0x'+'1'*40
TOKEN='0x'+'2'*40
BORROWER='0x'+'3'*40
HASH='0x'+'a'*64

def tx(i): return '0x'+format(i,'064x')
def case(i, controller='person', group='group'):
    return VerifiedCase(controller,group,'proof-'+str(i),True,True,100)


class Reader:
    """Synthetic test dependency; never a chain authenticity claim."""
    def __init__(self):
        self.records={}
        self.hashes={50:HASH,60:HASH}
        self.height=100
        self.chain=84532
    def observe(self, transaction, index): return self.records.get((transaction,index))
    def block_hash(self, block): return self.hashes.get(block)
    def head(self): return self.height
    def chain_id(self): return self.chain
    def add(self, observation):
        self.records[(observation.tx,observation.event_index)]=observation
        return observation


def observation(i, loan='loan-1', principal='10', kind='funding', **changes):
    return replace(Observation(84532,tx(i),50,HASH,1,kind,POOL,TOKEN,BORROWER,loan,
                   principal, BORROWER if kind=='funding' else POOL,
                   principal,0,1, POOL if kind=='funding' else BORROWER), **changes)


class Durable(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'ledger.db'
        self.policy=Policy(84532,POOL,TOKEN,'20','10','20','40','20','40')
        self.reader=Reader()
        self.ledger=Ledger(self.path,self.policy,self.reader,initialize=True)
    def tearDown(self):
        self.ledger.close()
        self.temp.cleanup()
    def reserve(self, i=1, **kwargs):
        return self.ledger.reserve('intent-'+str(i),case(i,**kwargs),BORROWER,'loan-'+str(i),'10',0)
    def active(self, i=1, **kwargs):
        self.reserve(i,**kwargs)
        self.ledger.prepare_attempt('intent-'+str(i),tx(i),0)
        self.reader.add(observation(i,loan='loan-'+str(i)))
        self.assertEqual(self.ledger.reconcile_funding('intent-'+str(i),0),'ACTIVE')
    def repay(self, i=1, r=101, principal='10', **changes):
        self.reader.add(observation(r,loan='loan-'+str(i),principal=principal,kind='repayment',**changes))
        return self.ledger.apply_repayment('intent-'+str(i),tx(r),0)

    def test_restart_preserves_reservation_limits_and_frozen_policy(self):
        self.reserve()
        self.ledger.close()
        self.ledger=Ledger(self.path,self.policy,self.reader)
        self.assertEqual(self.ledger.totals()['net'],10_000_000)
        with self.assertRaises(ValueError): self.reserve(2)
        with self.assertRaises(ValueError): Ledger(self.path,replace(self.policy,net_controller='100'),self.reader)
        with self.assertRaises(ValueError): Ledger(Path(self.temp.name)/'missing.db',self.policy)

    def test_exact_retry_and_changed_payload(self):
        self.assertTrue(self.reserve())
        self.assertFalse(self.reserve())
        with self.assertRaises(ValueError): self.ledger.reserve('intent-1',case(1),BORROWER,'loan-1','9',0)
        self.assertTrue(self.ledger.prepare_attempt('intent-1',tx(1),0))
        self.assertFalse(self.ledger.prepare_attempt('intent-1',tx(1),0))
        with self.assertRaises(ValueError): self.ledger.prepare_attempt('intent-1',tx(2),0)

    def test_parallel_connections_share_atomic_total_cap(self):
        def attempt(i):
            ledger=Ledger(self.path,self.policy,self.reader)
            try:
                ledger.reserve('parallel-'+str(i),case(i,'p'+str(i),'g'+str(i)),BORROWER,'loan-'+str(i),10,0)
                return True
            except ValueError: return False
            finally: ledger.close()
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt,range(20))),2)
        self.assertEqual(self.ledger.totals()['net'],20_000_000)

    def test_process_exit_after_pending_does_not_retry_or_release(self):
        self.reserve()
        script='''import json,os,sys
from durable import Ledger,Policy
l=Ledger(sys.argv[1],Policy(**json.loads(sys.argv[2])))
l.prepare_attempt('intent-1',sys.argv[3],0)
os._exit(23)
'''
        from dataclasses import asdict
        result=subprocess.run([sys.executable,'-c',script,str(self.path),json.dumps(asdict(self.policy)),tx(1)],cwd=Path(__file__).parent)
        self.assertEqual(result.returncode,23)
        self.assertEqual(self.ledger.row('intent-1')['state'],'PENDING')
        self.assertEqual(self.ledger.reconcile_funding('intent-1',0),'HOLD_UNKNOWN')
        self.assertEqual(self.ledger.totals()['net'],10_000_000)
        self.assertFalse(self.ledger.execution_permission()['allowed'])

    def test_funding_exact_binding_and_confirmed_revert(self):
        self.reserve()
        self.ledger.prepare_attempt('intent-1',tx(1),0)
        for change in [dict(principal='9'),dict(loan='other'),dict(token=POOL),dict(transfer_to=POOL),dict(transfer_from=BORROWER),dict(borrower=POOL)]:
            self.reader.add(observation(1,**change))
            with self.assertRaises(ValueError): self.ledger.reconcile_funding('intent-1',0)
            self.assertEqual(self.ledger.row('intent-1')['state'],'PENDING')
        self.reader.add(observation(1,status=0))
        self.assertEqual(self.ledger.reconcile_funding('intent-1',0),'REVERTED')
        self.assertEqual(self.ledger.totals(),{'net':0,'gross':10_000_000})

    def test_missing_reader_cannot_credit_claim(self):
        self.active()
        self.ledger.reader=None
        with self.assertRaises(ValueError): self.ledger.apply_repayment('intent-1',tx(101),0)
        self.assertEqual(self.ledger.row('intent-1')['recovered'],0)

    def test_wrong_chain_failed_shallow_or_noncanonical_receipt_rejected(self):
        self.active()
        for change in [dict(chain=1),dict(status=0),dict(block=99),dict(block_hash=tx(8)),dict(token=POOL),dict(pool=BORROWER)]:
            with self.assertRaises(ValueError): self.repay(**change)
            self.assertEqual(self.ledger.row('intent-1')['recovered'],0)

    def test_transfer_amount_destination_and_loan_binding(self):
        self.active()
        for change in [dict(transfer_to=BORROWER),dict(transfer_from=POOL),dict(transfer_amount='9'),dict(borrower=POOL),dict(loan='other'),dict(principal='11')]:
            self.reader.add(observation(101,kind='repayment',**change))
            with self.assertRaises(ValueError): self.ledger.apply_repayment('intent-1',tx(101),0)
        self.assertEqual(self.ledger.row('intent-1')['recovered'],0)

    def test_partial_recovery_default_and_late_recovery(self):
        self.active()
        self.repay(principal='3',transfer_amount='4')  # extra1 is interest, not principal
        self.assertEqual(self.ledger.totals()['net'],7_000_000)
        self.ledger.mark_default('intent-1')
        self.ledger.close()
        self.ledger=Ledger(self.path,self.policy,self.reader)
        self.assertEqual(self.ledger.row('intent-1')['state'],'DEFAULTED')
        self.repay(r=102,principal='7')
        self.assertEqual(self.ledger.totals(),{'net':0,'gross':10_000_000})
        self.assertEqual(self.ledger.row('intent-1')['state'],'REPAID')

    def test_duplicate_receipt_idempotent_after_restart(self):
        self.active()
        self.assertTrue(self.repay())
        self.ledger.close()
        self.ledger=Ledger(self.path,self.policy,self.reader)
        self.assertFalse(self.ledger.apply_repayment('intent-1',tx(101),0))
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],1)

    def test_same_transfer_cannot_be_allocated_to_another_loan(self):
        self.active()
        self.active(2,controller='second')
        self.repay()
        # Different repayment event forged against same token transfer log.
        self.reader.add(observation(101,loan='loan-2',kind='repayment',event_index=2,transfer_index=1))
        with self.assertRaises(sqlite3.IntegrityError): self.ledger.apply_repayment('intent-2',tx(101),2)
        self.assertEqual(self.ledger.row('intent-2')['recovered'],0)  # SQL update rolled back
        self.assertEqual(self.ledger.totals()['net'],10_000_000)

    def test_failure_between_balance_update_and_receipt_insert_is_atomic(self):
        self.active()
        self.ledger.db.execute("CREATE TRIGGER fail_receipt BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT,'fault'); END")
        with self.assertRaises(sqlite3.IntegrityError): self.repay()
        self.assertEqual(self.ledger.row('intent-1')['recovered'],0)
        self.ledger.db.execute('DROP TRIGGER fail_receipt')
        self.assertTrue(self.repay())

    def test_process_crash_during_settlement_rolls_back_both_records(self):
        self.active()
        script="""import json,os,sys
from durable import Ledger,Policy
from test_durable import Reader,observation,tx
r=Reader()
r.add(observation(101,kind='repayment'))
l=Ledger(sys.argv[1],Policy(**json.loads(sys.argv[2])),r)
l.db.create_function('crash_now',0,lambda:os._exit(24))
l.db.execute('CREATE TEMP TRIGGER crash_receipt BEFORE INSERT ON receipts BEGIN SELECT crash_now(); END')
l.apply_repayment('intent-1',tx(101),0)
"""
        from dataclasses import asdict
        result=subprocess.run([sys.executable,'-c',script,str(self.path),json.dumps(asdict(self.policy))],cwd=Path(__file__).parent)
        self.assertEqual(result.returncode,24)
        self.ledger.close()
        self.ledger=Ledger(self.path,self.policy,self.reader)
        self.assertEqual(self.ledger.row('intent-1')['recovered'],0)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0],0)
        self.assertTrue(self.repay())

    def test_farming_and_new_evidence_cannot_raise_lifetime_caps(self):
        for i in (1,2):
            self.active(i)
            self.repay(i=i,r=100+i)
        self.assertEqual(self.ledger.totals(),{'net':0,'gross':20_000_000})
        with self.assertRaises(ValueError): self.reserve(3)
        self.assertFalse(self.ledger.execution_permission()['allowed'])

    def test_reorg_persists_hold_and_cannot_enable_reservation(self):
        self.active()
        self.repay(block=60)
        self.reader.hashes[60]=tx(99)
        with self.assertRaises(ValueError): self.reserve(2)
        self.reader.hashes[60]=HASH
        self.ledger.close()
        self.ledger=Ledger(self.path,self.policy,self.reader)
        with self.assertRaises(ValueError): self.reserve(2)
        self.assertFalse(self.ledger.audit_canonical())

    def test_preexisting_reservation_cannot_prepare_after_incident(self):
        self.active()
        self.reserve(2,controller='second')
        self.reader.hashes[50]=tx(99)
        self.assertFalse(self.ledger.audit_canonical())
        self.reader.hashes[50]=HASH
        with self.assertRaises(ValueError): self.ledger.prepare_attempt('intent-2',tx(2),0)
        self.assertEqual(self.ledger.row('intent-2')['state'],'RESERVED')
        self.assertIsNone(self.ledger.row('intent-2')['funding_tx'])

    def test_expired_reservation_cannot_prepare_a_new_attempt(self):
        self.reserve()
        with self.assertRaises(ValueError): self.ledger.prepare_attempt('intent-1',tx(1),100)
        self.assertEqual(self.ledger.row('intent-1')['state'],'RESERVED')
        self.assertIsNone(self.ledger.row('intent-1')['funding_tx'])

    def test_receipt_cannot_precede_funding(self):
        self.active()
        self.reader.hashes[40]=HASH
        with self.assertRaises(ValueError): self.repay(block=40)

    def test_duplicate_evidence_or_loan_cannot_evade_idempotency(self):
        self.reserve()
        for proof, loan in [(case(1,'other'), 'other-loan'),(case(2,'other'),'loan-1')]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.ledger.reserve('second',proof,BORROWER,loan,10,0)
        self.assertEqual(self.ledger.totals()['net'],10_000_000)

    # Added by the independent AI reviewer; preserved as regression coverage.
    def worker(self, receipt):
        db=Ledger(self.path,self.policy,self.reader)
        try:
            return db.apply_repayment('intent-1',tx(receipt),0)
        except ValueError:
            return 'rejected'
        finally:
            db.close()
    def test_independent_concurrent_overpayment(self):
        self.active()
        for i in (201,202): self.reader.add(observation(i,kind='repayment',principal='6'))
        with ThreadPoolExecutor(max_workers=2) as p: results=list(p.map(self.worker,[201,202]))
        self.assertCountEqual(results,[True,'rejected'])
        self.assertEqual(self.ledger.row('intent-1')['recovered'],6_000_000)
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM receipts').fetchone()[0],1)
    def test_independent_concurrent_same_receipt(self):
        self.active()
        self.reader.add(observation(201,kind='repayment'))
        with ThreadPoolExecutor(max_workers=8) as p: results=list(p.map(self.worker,[201]*12))
        self.assertEqual(results.count(True),1)
        self.assertEqual(results.count(False),11)
        self.assertEqual(self.ledger.totals()['net'],0)
    def test_independent_reader_failure_reserves_remain(self):
        self.active()
        self.reader.hashes.clear()
        with self.assertRaises(ValueError): self.ledger.prepare_attempt('intent-1',tx(1),0)
        self.assertEqual(self.ledger.totals()['net'],10_000_000)
        self.assertGreater(self.ledger.db.execute('SELECT count(*) FROM incidents').fetchone()[0],0)
