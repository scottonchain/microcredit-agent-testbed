"""Offline bindings for the actual CreditDesk.reply(address,string,uint256) ABI.

This does not sign/send or authorize live execution. Trusted service snapshots and
consent-controller writes are required dependencies, not applicant assertions.
Consent revisions are private operational data; tests use fictional subjects.
"""
import hashlib
import json
from durable import address, identifier, units, txhash
from canonical_adapter import REPLY


def word(value):
    if type(value) is not int or not 0<=value<2**256: raise ValueError('uint256 required')
    return format(value,'064x')


def reply_data(borrower,text,backing_units):
    raw=text.encode('utf-8')
    if len(raw)>1000: raise ValueError('CreditDesk MAX_TEXT')
    return '0x'+REPLY+address(borrower)[2:].rjust(64,'0')+word(96)+word(backing_units)+word(len(raw))+raw.hex().ljust(((len(raw)+31)//32)*64,'0')


class ReplyBindings:
    def __init__(self, ledger, desk, officer, service_reader, approved_messages):
        self.ledger=ledger
        self.desk,self.officer=address(desk),address(officer)
        self.reader=service_reader
        self.messages=dict(approved_messages)
        self.fingerprint=hashlib.sha256(json.dumps({'ledger':ledger.config,'desk':self.desk,'officer':self.officer,
                                    'messages':self.messages,'selector':REPLY},sort_keys=True).encode()).hexdigest()
        with ledger.atomic():
            ledger.db.execute('''CREATE TABLE IF NOT EXISTS consents (
                subject TEXT PRIMARY KEY, revision INTEGER NOT NULL, allowed INTEGER NOT NULL,
                purpose TEXT NOT NULL, expires INTEGER NOT NULL)''')
            ledger.db.execute('''CREATE TABLE IF NOT EXISTS reply_bindings (
                id TEXT PRIMARY KEY, reservation TEXT UNIQUE NOT NULL REFERENCES loans(intent),
                subject TEXT NOT NULL, revision INTEGER NOT NULL, expires INTEGER NOT NULL,
                fingerprint TEXT NOT NULL, payload TEXT NOT NULL, prior_backing INTEGER NOT NULL,
                chain INTEGER NOT NULL, sender TEXT NOT NULL, nonce INTEGER NOT NULL,
                UNIQUE(chain,sender,nonce))''')

    def record_consent(self,subject,revision,allowed,purpose,expires):
        """Trusted private consent-controller operation, never an applicant tool.
        Monotonic revisions prevent rollback/replay; withdrawal invalidates binds.
        """
        subject=address(subject)
        if type(revision) is not int or not 0<revision<2**63 or type(allowed) is not bool or type(expires) is not int:
            raise ValueError('typed consent fields required')
        if purpose!='fictional-practice': raise ValueError('unsupported consent purpose')
        with self.ledger.atomic():
            old=self.ledger.db.execute('SELECT * FROM consents WHERE subject=?',(subject,)).fetchone()
            if old and revision<=old['revision']:
                if (revision,int(allowed),purpose,expires)==(old['revision'],old['allowed'],old['purpose'],old['expires']): return False
                raise ValueError('consent rollback or conflicting revision')
            self.ledger.db.execute('INSERT OR REPLACE INTO consents VALUES(?,?,?,?,?)', (subject,revision,int(allowed),purpose,expires))
            return True

    def _consent(self,subject,now):
        row=self.ledger.db.execute('SELECT * FROM consents WHERE subject=?',(subject,)).fetchone()
        if not row or row['allowed']!=1 or row['purpose']!='fictional-practice' or now>=row['expires']:
            raise ValueError('current consent missing, expired or withdrawn')
        return row

    def _snapshot(self,borrower,now):
        if self.reader is None: raise ValueError('no trusted service reader')
        state=self.reader.snapshot(borrower)
        if (state['chain']!=self.ledger.policy.chain or address(state['applicant'])!=borrower or address(state['desk'])!=self.desk or
            address(state['pool'])!=self.ledger.config['pool'] or address(state['usdc'])!=self.ledger.config['token'] or
            address(state['officer'])!=self.officer or type(state['timestamp']) is not int or
            not -120<=now-state['timestamp']<=900 or txhash(self.reader.block_hash(state['block']))!=txhash(state['hash'])):
            raise ValueError('service domain, authority or freshness mismatch')
        for name in ('maxLine','backing','freeStake','freeCredit','secured','unsecured','nonce','threadLength','defaultedLoans'):
            if type(state[name]) is not int or not 0<=state[name]<2**63: raise ValueError('invalid service state')
        if state.get('knownApplicant') is not True or state['threadLength']>=80 or state['defaultedLoans']!=0:
            raise ValueError('applicant/thread/default preconditions fail')
        if state['secured']+state['unsecured']!=state['backing'] or state['unsecured']!=0 or state['freeCredit']!=0:
            raise ValueError('secured-only candidate requires no free or committed unsecured credit')
        return state

    def _reservation(self,intent,borrower,now):
        row=self.ledger.row(intent)
        evidence=json.loads(row['payload'])[0]
        if row['borrower']!=borrower or row['state']!='RESERVED' or now>=evidence['expires']:
            raise ValueError('reservation binding/state/expiry mismatch')
        if self.ledger.db.execute('SELECT 1 FROM incidents LIMIT 1').fetchone(): raise ValueError('incident hold')
        return row

    def bind(self,binding_id,reservation,borrower,backing,message_id,expires,now):
        identifier(binding_id); borrower=address(borrower); backing=units(backing)
        if type(now) is not int or type(expires) is not int or now>=expires: raise ValueError('invalid binding expiry')
        if message_id not in self.messages: raise ValueError('unreviewed public message')
        if not self.ledger.audit_canonical(): raise ValueError('canonical incident hold')
        state=self._snapshot(borrower,now)
        if (backing!=0 and backing<1_000_000) or borrower==self.desk: raise ValueError('pool minimum backing/self-backing')
        if backing>state['maxLine'] or backing<state['backing']: raise ValueError('unsupported backing change')
        delta=backing-state['backing']
        if delta>state['freeStake']: raise ValueError('insufficient desk backing capacity')
        transaction={'chainId':hex(self.ledger.policy.chain),'from':self.officer,'to':self.desk,'nonce':hex(state['nonce']),
                     'value':'0x0','data':reply_data(borrower,self.messages[message_id],backing)}
        encoded=json.dumps(transaction,sort_keys=True)
        with self.ledger.atomic():
            c=self._consent(borrower,now); r=self._reservation(reservation,borrower,now)
            if delta>r['principal'] or expires>min(c['expires'],json.loads(r['payload'])[0]['expires']):
                raise ValueError('reservation or consent does not cover binding')
            old=self.ledger.db.execute('SELECT * FROM reply_bindings WHERE id=?',(binding_id,)).fetchone()
            values=(reservation,borrower,c['revision'],expires,self.fingerprint,encoded,state['backing'],self.ledger.policy.chain,self.officer,state['nonce'])
            if old:
                if tuple(old[k] for k in ('reservation','subject','revision','expires','fingerprint','payload','prior_backing','chain','sender','nonce'))!=values:
                    raise ValueError('changed binding replay')
                return transaction
            self.ledger.db.execute('INSERT INTO reply_bindings VALUES(?,?,?,?,?,?,?,?,?,?,?)',(binding_id,*values))
            return transaction

    def validate(self,binding_id,transaction,now):
        if type(now) is not int: raise ValueError('trusted clock required')
        b=self.ledger.db.execute('SELECT * FROM reply_bindings WHERE id=?',(binding_id,)).fetchone()
        if not b: raise ValueError('unknown binding')
        if not self.ledger.audit_canonical(): raise ValueError('canonical incident hold')
        state=self._snapshot(b['subject'],now)
        with self.ledger.atomic():
            c=self._consent(b['subject'],now)
            self._reservation(b['reservation'],b['subject'],now)
            if (now>=b['expires'] or c['revision']!=b['revision'] or b['fingerprint']!=self.fingerprint or
                json.dumps(transaction,sort_keys=True)!=b['payload'] or state['nonce']!=b['nonce'] or
                state['backing']!=b['prior_backing']):
                raise ValueError('transaction/consent/policy/state changed')
            # Re-derive calldata amount from exact reviewed encoding, not caller text.
            backing=int(transaction['data'][10+128:10+192],16)
            if backing>state['maxLine'] or backing-state['backing']>state['freeStake']:
                raise ValueError('current service limits changed')
            return {'binding_valid':True,'execution_allowed':False,'reason':'NO_ACCEPTED_LIVE_EXECUTOR'}
