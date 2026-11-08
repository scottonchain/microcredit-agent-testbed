import copy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from bounds import VerifiedCase
from durable import Ledger, Policy
from canonical_adapter import TRANSFER, REPAID, APPLIED, REPAY, CanonicalReader, repayment_observation
from service_binding import ReplyBindings, reply_data, word
from test_durable import Reader, observation, tx, POOL, TOKEN, BORROWER, HASH

BLOCK='0x'+'b'*64
PARENT='0x'+'c'*64
DESK='0x'+'4'*40
OFFICER='0x'+'5'*40


def addr_topic(a): return '0x'+a[2:].rjust(64,'0')
def data(*values): return '0x'+''.join(word(x) for x in values)


def fixture():
    transaction=tx(101)
    def log(index,emitter,topics,values):
        return {'address':emitter,'topics':topics,'data':data(*values),'logIndex':hex(index),
                'transactionHash':transaction,'transactionIndex':'0x0','blockNumber':'0x64','blockHash':BLOCK,'removed':False}
    logs=[log(0,TOKEN,[TRANSFER,addr_topic(BORROWER),addr_topic(POOL)],[10_000_100]),
          log(1,POOL,[APPLIED,data(1)],[100,10_000_000,10]),
          log(2,POOL,[REPAID,addr_topic(BORROWER),data(1)],[10_000_100])]
    return {'chainId':hex(84532),'block':{'number':'0x64','timestamp':hex(1000),'hash':BLOCK,'parentHash':PARENT,'transactions':[transaction]},
            'head':{'number':hex(120)},'canonicalHash':BLOCK,
            'transaction':{'hash':transaction,'chainId':hex(84532),'from':BORROWER,'to':POOL,'value':'0x0','nonce':'0x3',
                           'input':'0x'+REPAY+word(1)+word(10_000_100),'transactionIndex':'0x0','blockNumber':'0x64','blockHash':BLOCK},
            'receipts':[{'transactionHash':transaction,'transactionIndex':'0x0','blockNumber':'0x64','blockHash':BLOCK,'status':'0x1','logs':logs}],
            'before':{'blockHash':PARENT,'token':TOKEN,'account':POOL,'balance':hex(100_000_000)},
            'after':{'blockHash':BLOCK,'token':TOKEN,'account':POOL,'balance':hex(110_000_100)}}


class Provider:
    def __init__(self,b): self.b=b
    def bundle(self,t): return copy.deepcopy(self.b) if t==tx(101) else None
    def chain_id(self): return 84532
    def head(self): return 120
    def block_hash(self,n): return {50:HASH,99:PARENT,100:BLOCK}.get(n)


class Service:
    def __init__(self):
        self.state={'chain':84532,'desk':DESK,'pool':POOL,'usdc':TOKEN,'officer':OFFICER,'timestamp':1000,
                    'block':100,'hash':BLOCK,'maxLine':20_000_000,'backing':0,'freeStake':20_000_000,'freeCredit':0,'secured':0,'unsecured':0,'nonce':3,'threadLength':1,'defaultedLoans':0,'knownApplicant':True}
    def snapshot(self,borrower): return dict(self.state,applicant=borrower)
    def block_hash(self,n): return BLOCK if n==100 else None


class Interfaces(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'ledger.db'
        self.policy=Policy(84532,POOL,TOKEN,'20','10','20','40','20','40')
        self.reader=Reader()
        self.ledger=Ledger(self.path,self.policy,self.reader,initialize=True)
        self.ledger.reserve('intent',VerifiedCase('person','group','evidence',True,True,5000),BORROWER,'1',10,1000)
        self.service=Service()
        self.bindings=ReplyBindings(self.ledger,DESK,OFFICER,self.service,{'practice':'Fictional practice only.'})
    def tearDown(self): self.ledger.close(); self.temp.cleanup()
    def check(self,b): return repayment_observation(b,self.policy,tx(101),2,1100)
    def consent(self): self.bindings.record_consent(BORROWER,1,True,'fictional-practice',4000)
    def bind(self): return self.bindings.bind('bind','intent',BORROWER,10,'practice',3000,1100)

    def test_raw_abi_principal_interest_and_cash_are_separate(self):
        result=self.check(fixture())
        self.assertEqual(result.principal,'10')
        self.assertEqual(result.transfer_amount,'10.0001')
        self.assertEqual(result.event_index,2)
        self.assertEqual(result.transfer_index,0)

    def test_adapter_drives_actual_ledger_reader_interface(self):
        self.ledger.prepare_attempt('intent',tx(1),1100)
        self.reader.add(observation(1,loan='1'))
        self.ledger.reconcile_funding('intent',0)
        self.ledger.reader=CanonicalReader(Provider(fixture()),self.policy,lambda:1100)
        self.assertTrue(self.ledger.apply_repayment('intent',tx(101),2))
        self.assertFalse(self.ledger.apply_repayment('intent',tx(101),2))
        self.assertEqual(self.ledger.totals(),{'net':0,'gross':10_000_000})
        self.assertFalse(self.ledger.execution_permission()['allowed'])

    def test_wrong_domain_status_freshness_and_canonical_hash(self):
        for mutate in [lambda b:b.update(chainId='0x1'),lambda b:b.update(canonicalHash=PARENT),
                       lambda b:b['receipts'][0].update(status='0x0'),lambda b:b['block'].update(timestamp='0x0'),
                       lambda b:b['head'].update(number='0x65'),lambda b:b['transaction'].update(to=TOKEN)]:
            b=fixture();mutate(b)
            with self.assertRaises(ValueError): self.check(b)

    def test_no_gross_donation_or_queued_withdrawal_masquerades_as_net_recovery(self):
        for incoming in (True,False):
            b=fixture();extra=copy.deepcopy(b['receipts'][0]['logs'][0]);extra['logIndex']='0x3'
            extra['topics']=[TRANSFER,addr_topic(BORROWER if incoming else POOL),addr_topic(POOL if incoming else BORROWER)]
            b['receipts'][0]['logs'].append(extra)
            with self.assertRaises(ValueError): self.check(b)
        b=fixture();b['after']['balance']=b['before']['balance']
        with self.assertRaises(ValueError): self.check(b)

    def test_complete_block_inventory_and_other_activity_required(self):
        b=fixture();b['block']['transactions'].append(tx(102))
        with self.assertRaises(ValueError): self.check(b)
        r=copy.deepcopy(b['receipts'][0]);r['transactionHash']=tx(102);r['transactionIndex']='0x1'
        for i,log in enumerate(r['logs']):
            log.update(transactionHash=tx(102),transactionIndex='0x1',logIndex=hex(i+3))
        b['receipts'].append(r)
        with self.assertRaises(ValueError): self.check(b)

    def test_bad_loan_amount_log_order_and_duplicate_logs(self):
        for mutate in [lambda l:l[1].update(data=data(100,9_000_000,10)),lambda l:l[1].update(topics=[APPLIED,data(2)]),
                       lambda l:l[0].update(logIndex='0x4'),lambda l:l.append(copy.deepcopy(l[0])),
                       lambda l:l[2].update(removed=True),lambda l:l[0].update(address=POOL)]:
            b=fixture();mutate(b['receipts'][0]['logs'])
            with self.assertRaises(ValueError): self.check(b)

    def test_wrong_transfer_source_padding_and_snapshot_anchor(self):
        b=fixture();b['receipts'][0]['logs'][0]['topics'][1]=addr_topic(POOL)
        with self.assertRaises(ValueError): self.check(b)
        b=fixture();b['receipts'][0]['logs'][2]['topics'][1]='0x'+'1'*64
        with self.assertRaises(ValueError): self.check(b)
        b=fixture();b['before']['blockHash']=BLOCK
        with self.assertRaises(ValueError): self.check(b)

    def test_permit_meta_and_batched_calls_hold_instead_of_guess(self):
        for payload in ['0x12345678','0x'+REPAY+word(1)+word(10_000_100)+word(1)]:
            b=fixture();b['transaction']['input']=payload
            with self.assertRaises(ValueError): self.check(b)

    def test_reply_abi_matches_solidity_dynamic_layout_and_never_grants(self):
        self.consent();t=self.bind()
        self.assertEqual(t['data'],reply_data(BORROWER,'Fictional practice only.',10_000_000))
        raw=t['data'][10:]
        self.assertEqual(int(raw[64:128],16),96)
        self.assertEqual(int(raw[128:192],16),10_000_000)
        self.assertEqual(bytes.fromhex(raw[256:])[:int(raw[192:256],16)],b'Fictional practice only.')
        self.assertEqual(self.bindings.validate('bind',t,1100),{'binding_valid':True,'execution_allowed':False,'reason':'NO_ACCEPTED_LIVE_EXECUTOR'})

    def test_encoding_matches_independent_actual_abi_library_fixtures(self):
        expected=json.loads((Path(__file__).parent/'abi-encoding-fixtures.json').read_text())
        self.assertEqual(reply_data(BORROWER,'Fictional practice only.',10_000_000),expected['reply'])
        self.assertEqual('0x'+REPAY+word(1)+word(10_000_100),expected['repayLoan'])

    def test_wrong_applicant_snapshot_cannot_authorize_reply(self):
        self.consent()
        self.service.snapshot=lambda borrower:dict(self.service.state,applicant=OFFICER)
        with self.assertRaises(ValueError): self.bind()

    def test_current_withdrawal_invalidates_already_bound_transaction(self):
        self.consent();t=self.bind()
        self.bindings.record_consent(BORROWER,2,False,'fictional-practice',4000)
        with self.assertRaises(ValueError): self.bindings.validate('bind',t,1101)
        with self.assertRaises(ValueError): self.bindings.record_consent(BORROWER,1,True,'fictional-practice',4000)

    def test_reconsent_new_revision_does_not_resurrect_old_binding(self):
        self.consent();t=self.bind()
        self.bindings.record_consent(BORROWER,2,False,'fictional-practice',4000)
        self.bindings.record_consent(BORROWER,3,True,'fictional-practice',4000)
        with self.assertRaises(ValueError): self.bindings.validate('bind',t,1101)

    def test_transaction_sender_nonce_chain_destination_value_calldata_exact(self):
        self.consent();t=self.bind()
        for field,value in [('from',BORROWER),('nonce','0x4'),('chainId','0x1'),('to',POOL),('value','0x1'),('data',t['data']+'00')]:
            changed=dict(t,**{field:value})
            with self.assertRaises(ValueError): self.bindings.validate('bind',changed,1100)

    def test_current_service_change_and_expiry_hold(self):
        self.consent();t=self.bind()
        baseline=dict(self.service.state)
        for field,value in [('officer',BORROWER),('nonce',4),('maxLine',1),('freeStake',1),('backing',1),('pool',TOKEN)]:
            self.service.state=dict(baseline,**{field:value})
            with self.assertRaises(ValueError): self.bindings.validate('bind',t,1100)
        self.service.state=baseline
        with self.assertRaises(ValueError): self.bindings.validate('bind',t,3000)

    def test_missing_consent_unreviewed_text_and_insufficient_reservation(self):
        with self.assertRaises(ValueError): self.bind()
        self.consent()
        with self.assertRaises(ValueError): self.bindings.bind('bind','intent',BORROWER,11,'practice',3000,1100)
        with self.assertRaises(ValueError): self.bindings.bind('bind','intent',BORROWER,10,'applicant-script',3000,1100)

    def test_binding_survives_restart_and_nonce_cannot_be_reused(self):
        self.consent();t=self.bind()
        self.ledger.close();self.ledger=Ledger(self.path,self.policy,self.reader)
        self.bindings=ReplyBindings(self.ledger,DESK,OFFICER,self.service,{'practice':'Fictional practice only.'})
        self.assertFalse(self.bindings.validate('bind',t,1100)['execution_allowed'])
        with self.assertRaises(sqlite3.IntegrityError): self.bindings.bind('second','intent',BORROWER,10,'practice',3000,1100)
        self.ledger.db.execute("INSERT INTO incidents VALUES('hold')")
        with self.assertRaises(ValueError): self.bindings.validate('bind',t,1100)

    def test_credit_first_pool_cannot_be_mislabelled_stake_backed(self):
        self.consent()
        self.service.state['freeCredit']=1
        with self.assertRaises(ValueError): self.bind()
        self.service.state.update(freeCredit=0,unsecured=1,backing=1)
        with self.assertRaises(ValueError): self.bind()

    def test_binding_audits_historical_funding_before_preparation_and_validation(self):
        other='0x'+'6'*40
        self.ledger.reserve('prior',VerifiedCase('other','other','prior-proof',True,True,5000),other,'2',10,1000)
        self.ledger.prepare_attempt('prior',tx(2),1100)
        self.reader.add(observation(2,loan='2',borrower=other,transfer_to=other))
        self.ledger.reconcile_funding('prior',0)
        self.consent();t=self.bind()
        self.reader.hashes[50]=tx(999)
        with self.assertRaises(ValueError): self.bindings.validate('bind',t,1100)
        self.assertGreater(self.ledger.db.execute('SELECT COUNT(*) FROM incidents').fetchone()[0],0)
        with self.assertRaises(ValueError): self.bind()

    def test_actual_applicant_thread_default_and_minimum_backing_preconditions(self):
        self.consent()
        initial=dict(self.service.state)
        for name,value in [('knownApplicant',False),('threadLength',80),('defaultedLoans',1)]:
            self.service.state=dict(initial,**{name:value})
            with self.assertRaises(ValueError): self.bind()
        self.service.state=initial
        with self.assertRaises(ValueError): self.bindings.bind('bind','intent',BORROWER,'0.5','practice',3000,1100)

    def test_policy_or_public_message_change_invalidates_old_binding(self):
        self.consent();t=self.bind()
        other=ReplyBindings(self.ledger,DESK,OFFICER,self.service,{'practice':'Different reviewed text.'})
        with self.assertRaises(ValueError): other.validate('bind',t,1100)
