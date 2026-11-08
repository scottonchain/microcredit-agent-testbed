import copy
from pathlib import Path
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from bounds import VerifiedCase
from durable import Ledger,Policy
from backing_book import BackingBook
from canonical_adapter import CanonicalReader, funding_observation, DISBURSE,DISBURSED,TRANSFER
from test_interfaces import fixture,word,data,addr_topic,POOL,TOKEN,BORROWER,BLOCK,PARENT,DESK,OFFICER
from test_durable import tx


def funding_fixture():
    b=fixture();t=b['transaction'];t.update(input='0x'+DISBURSE+word(1),**{'from':OFFICER})
    logs=b['receipts'][0]['logs'];logs[0]['topics']=[TRANSFER,addr_topic(POOL),addr_topic(BORROWER)];logs[0]['data']=data(10_000_000)
    logs[1].update(topics=[DISBURSED,addr_topic(BORROWER),data(1)],data='0x'+BORROWER[2:].rjust(64,'0')+word(10_000_000))
    b['receipts'][0]['logs']=logs[:2];b['after']['balance']=hex(90_000_000)
    return b


class Source:
    def __init__(self):
        self.blocks={99:PARENT,100:BLOCK,101:'0x'+'d'*64,102:'0x'+'e'*64}
        self.bundles={tx(101):funding_fixture()}
        self.s={'chain':84532,'pool':POOL,'desk':DESK,'borrower':BORROWER,'timestamp':1100,'block':102,
                'hash':self.blocks[102],'secured':10_000_000,'unsecured':0,'otherBacking':0,'grantedCredit':0,
                'inventory_complete':True,'loans':{}}
    def backing_snapshot(self,desk,borrower):return copy.deepcopy(self.s)
    def chain_id(self):return 84532
    def head(self):return 150
    def block_hash(self,n):return self.blocks.get(n)
    def bundle(self,t):return copy.deepcopy(self.bundles.get(t))
    def add_repayment(self):
        b=fixture();h=tx(102);bh=self.blocks[101]
        b['transaction'].update(hash=h,blockNumber=hex(101),blockHash=bh)
        b['block'].update(number=hex(101),hash=bh,parentHash=BLOCK,transactions=[h])
        b['canonicalHash']=bh
        r=b['receipts'][0];r.update(transactionHash=h,blockNumber=hex(101),blockHash=bh)
        for log in r['logs']:log.update(transactionHash=h,blockNumber=hex(101),blockHash=bh)
        b['before'].update(blockHash=BLOCK,balance=hex(90_000_000));b['after'].update(blockHash=bh,balance=hex(100_000_100))
        self.bundles[h]=b


    def add_cycle(self,loan,first_block,funding_tx,repayment_tx):
        for n in range(first_block-1,first_block+2):self.blocks.setdefault(n,tx(10000+n))
        for original,h,n,is_funding in [(funding_fixture(),funding_tx,first_block,True),(fixture(),repayment_tx,first_block+1,False)]:
            b=original;bh=self.blocks[n];ph=self.blocks[n-1]
            b['transaction'].update(hash=h,blockNumber=hex(n),blockHash=bh)
            b['transaction']['input']='0x'+(DISBURSE+word(int(loan)) if is_funding else __import__('canonical_adapter').REPAY+word(int(loan))+word(10_000_100))
            b['block'].update(number=hex(n),hash=bh,parentHash=ph,transactions=[h]);b['canonicalHash']=bh
            r=b['receipts'][0];r.update(transactionHash=h,blockNumber=hex(n),blockHash=bh)
            for log in r['logs']:log.update(transactionHash=h,blockNumber=hex(n),blockHash=bh)
            if is_funding:r['logs'][1]['topics'][2]=data(int(loan))
            else:r['logs'][1]['topics'][1]=data(int(loan));r['logs'][2]['topics'][2]=data(int(loan))
            b['before']['blockHash']=ph;b['after']['blockHash']=bh
            self.bundles[h]=b


class BackingFunding(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'ledger.db'
        self.policy=Policy(84532,POOL,TOKEN,'20','10','20','40','20','40')
        self.source=Source();self.reader=CanonicalReader(self.source,self.policy,lambda:1100)
        self.ledger=Ledger(self.path,self.policy,self.reader,initialize=True)
        self.book=BackingBook(self.ledger,self.source)
        self.ledger.reserve('pledge',VerifiedCase('person','group','proof',True,True,5000),BORROWER,'commitment:desk',10,1000)
        self.book.register('pledge',DESK)
    def tearDown(self):self.ledger.close();self.temp.cleanup()
    def draw(self):
        self.source.s['loans']['1']={'state':'REQUESTED','principal':10_000_000,'recovered':0}
        self.book.reserve_draw('pledge','1',10,1100)
        self.book.funding('1',tx(101),1)
        self.source.s['loans']['1']['state']='ACTIVE'
    def paid(self):
        self.draw();self.source.add_repayment();self.book.repayment('1',tx(102),2)
        self.source.s['loans']['1'].update(state='REPAID',recovered=10_000_000)

    def test_direct_disbursement_any_caller_but_only_borrower_receives(self):
        o=funding_observation(funding_fixture(),self.policy,tx(101),1,1100)
        self.assertEqual((o.kind,o.borrower,o.principal,o.transfer_from),('funding',BORROWER,'10',POOL))
        self.assertNotEqual(funding_fixture()['transaction']['from'],BORROWER)

    def test_wrong_funding_amount_recipient_or_cash_delta_holds(self):
        for mutate in [lambda b:b['after'].update(balance=hex(100_000_000)),
                       lambda b:b['receipts'][0]['logs'][0].update(data=data(9_000_000)),
                       lambda b:b['receipts'][0]['logs'][1].update(data='0x'+OFFICER[2:].rjust(64,'0')+word(10_000_000)),
                       lambda b:b['transaction'].update(input='0x'+DISBURSE+word(2))]:
            b=funding_fixture();mutate(b)
            with self.assertRaises(ValueError):funding_observation(b,self.policy,tx(101),1,1100)

    def test_real_adapter_funding_repayment_keeps_root_backing_reserved(self):
        self.paid()
        self.assertEqual(self.ledger.totals()['net'],10_000_000)
        self.assertEqual(self.ledger.row('pledge')['state'],'RESERVED')
        self.assertFalse(self.book.repayment('1',tx(102),2))
        with self.assertRaises(ValueError):self.book.release('pledge',1100)
        self.assertFalse(self.ledger.execution_permission()['allowed'])

    def test_backing_cannot_be_counted_twice_for_concurrent_draws(self):
        self.draw()
        self.source.s['loans']['2']={'state':'REQUESTED','principal':10_000_000,'recovered':0}
        with self.assertRaises(ValueError):self.book.reserve_draw('pledge','2',10,1100)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM draws').fetchone()[0],1)

    def test_repeat_draws_count_against_lifetime_gross_not_repaid_score(self):
        self.paid()
        self.source.s['loans']['2']={'state':'REQUESTED','principal':10_000_000,'recovered':0}
        self.assertTrue(self.book.reserve_draw('pledge','2',10,1100))
        self.source.add_cycle('2',103,tx(201),tx(202))
        self.book.funding('2',tx(201),1)
        self.book.repayment('2',tx(202),2)
        self.source.s['loans']['2'].update(state='REPAID',recovered=10_000_000)
        self.source.s['loans']['3']={'state':'REQUESTED','principal':1,'recovered':0}
        with self.assertRaises(ValueError):self.book.reserve_draw('pledge','3','0.000001',1100)
        self.assertEqual(self.ledger.totals()['net'],10_000_000)

    def test_even_zero_backing_does_not_release_without_transaction_barrier(self):
        self.paid();self.source.s['secured']=0
        with self.assertRaisesRegex(ValueError,'release disabled'):self.book.release('pledge',1100)
        self.assertEqual(self.ledger.totals(),{'net':10_000_000,'gross':10_000_000})

    def test_draw_rechecks_held_commitment_inside_transaction(self):
        self.source.s['loans']['1']={'state':'REQUESTED','principal':10_000_000,'recovered':0}
        original=self.book._state
        def interleaved(intent,now):
            snapshot=original(intent,now)
            with self.ledger.atomic():
                self.ledger.db.execute("UPDATE pledges SET status='RELEASED'")
                self.ledger.db.execute("UPDATE loans SET state='REPAID',recovered=principal")
            return snapshot
        self.book._state=interleaved
        with self.assertRaisesRegex(ValueError,'no longer fully held'):self.book.reserve_draw('pledge','1',10,1100)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM draws').fetchone()[0],0)

    def test_missing_inventory_extra_capacity_and_untracked_loan_hold(self):
        baseline=copy.deepcopy(self.source.s)
        for key,value in [('inventory_complete',False),('grantedCredit',1),('otherBacking',1),('unsecured',1)]:
            self.source.s=copy.deepcopy(baseline);self.source.s[key]=value
            self.source.s['loans']['1']={'state':'REQUESTED','principal':10_000_000,'recovered':0}
            with self.assertRaises(ValueError):self.book.reserve_draw('pledge','1',10,1100)
        self.source.s=baseline;self.source.s['loans']={'1':{'state':'REQUESTED','principal':10_000_000,'recovered':0},'999':{'state':'ACTIVE','principal':1,'recovered':0}}
        with self.assertRaises(ValueError):self.book.reserve_draw('pledge','1',10,1100)

    def test_commitment_and_loan_namespaces_cannot_mix(self):
        with self.assertRaises(ValueError):self.ledger.prepare_attempt('pledge',tx(1),1100)
        with self.assertRaises(ValueError):self.ledger.reserve('mixed',VerifiedCase('new','new','new',True,True,5000),OFFICER,'123',10,1100)

    def test_restart_preserves_draws_cash_receipts_and_commitment(self):
        self.paid();self.ledger.close();self.ledger=Ledger(self.path,self.policy,self.reader)
        self.book=BackingBook(self.ledger,self.source)
        self.assertFalse(self.book.repayment('1',tx(102),2))
        self.assertEqual(self.ledger.totals()['net'],10_000_000)
        self.source.blocks[100]=tx(999)
        self.assertFalse(self.ledger.audit_canonical())
        self.assertGreater(self.ledger.db.execute('SELECT COUNT(*) FROM incidents').fetchone()[0],0)

    def test_pending_or_unknown_draw_never_frees_commitment(self):
        self.source.s['loans']['1']={'state':'REQUESTED','principal':10_000_000,'recovered':0}
        self.book.reserve_draw('pledge','1',10,1100)
        self.assertEqual(self.book.funding('1',tx(999),1),'HOLD_UNKNOWN')
        self.source.s.update(secured=0)
        self.source.s['loans']['1']['state']='CANCELLED'
        with self.assertRaises(ValueError):self.book.release('pledge',1100)
        self.assertEqual(self.ledger.totals()['net'],10_000_000)
