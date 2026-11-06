"""Offline durable policy prototype. No signer, sender, RPC or live approval API.

External observations are trusted ONLY through an injected, independently owned
reader. None is installed by default. Tests inject synthetic readers; they do not
establish authentic chain state. All currency stored as exact integer micro-units.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from decimal import Decimal
import json
from pathlib import Path
import re
import sqlite3

from bounds import VerifiedCase, amount

ADDRESS = re.compile(r'0x[0-9a-fA-F]{40}\Z')
HASH = re.compile(r'0x[0-9a-fA-F]{64}\Z')


def units(value):
    return int(amount(value) * 1_000_000)


def identifier(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200:
        raise ValueError('bounded identifier required')
    return value


def address(value):
    if not isinstance(value, str) or not ADDRESS.fullmatch(value):
        raise ValueError('address required')
    return value.lower()


def txhash(value):
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise ValueError('hash required')
    return value.lower()


@dataclass(frozen=True)
class Policy:
    chain: int
    pool: str
    token: str
    net_total: str
    net_controller: str
    net_group: str
    gross_total: str
    gross_controller: str
    gross_group: str
    confirmations: int = 12  # illustrative, not a validated finality guarantee


@dataclass(frozen=True)
class Observation:
    """Reader-normalized semantics, NOT a claim about a deployed contract ABI.

    Reader must authenticate chain/events/amounts independently of the applicant.
    Receipt success/failure and funding/repayment are separate facts.
    """
    chain: int
    tx: str
    block: int
    block_hash: str
    status: int
    kind: str
    pool: str
    token: str
    borrower: str
    loan: str
    principal: str
    transfer_to: str
    transfer_amount: str
    event_index: int
    transfer_index: int
    transfer_from: str


class Ledger:
    """Persistent accounting and intent state; actual credit always disabled.

    Readers must expose chain_id(), head(), block_hash(number), and
    observe(tx,event_index). Unknown reads return None. A missing reader holds.
    No endpoint, signer, borrower-controlled callable or RPC fallback is accepted.
    A reader is a trusted implementation dependency, not a verification shortcut.
    """
    def __init__(self, path, policy, reader=None, *, initialize=False):
        if str(path) == ':memory:' or not isinstance(policy, Policy):
            raise ValueError('persistent path and explicit policy required')
        if type(policy.chain) is not int or policy.chain <= 0:
            raise ValueError('chain required')
        if type(policy.confirmations) is not int or policy.confirmations < 1:
            raise ValueError('confirmation depth required')
        if not Path(path).is_file() and not initialize:
            raise ValueError('missing durable ledger; explicit initialization required')
        self.policy, self.reader = policy, reader
        config = asdict(policy)
        config['pool'], config['token'] = address(policy.pool), address(policy.token)
        for name in ('net_total','net_controller','net_group','gross_total','gross_controller','gross_group'):
            config[name] = units(config[name])
            if not config[name]: raise ValueError('positive caps required')
        self.config = config
        self.db = sqlite3.connect(Path(path), timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA foreign_keys=ON')
        with self.atomic():
            self.db.execute('CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY CHECK(id=1), config TEXT NOT NULL)')
            self.db.execute('''CREATE TABLE IF NOT EXISTS loans (
                intent TEXT PRIMARY KEY, payload TEXT NOT NULL, controller TEXT NOT NULL,
                grp TEXT NOT NULL, evidence TEXT UNIQUE NOT NULL, borrower TEXT NOT NULL,
                loan TEXT UNIQUE NOT NULL, principal INTEGER NOT NULL CHECK(principal>0),
                recovered INTEGER NOT NULL DEFAULT 0 CHECK(recovered>=0 AND recovered<=principal),
                state TEXT NOT NULL CHECK(state IN ('RESERVED','PENDING','ACTIVE','DEFAULTED','REPAID','REVERTED')),
                funding_tx TEXT UNIQUE, funding_block INTEGER, funding_hash TEXT)''')
            self.db.execute('''CREATE TABLE IF NOT EXISTS receipts (
                tx TEXT NOT NULL, event_index INTEGER NOT NULL, transfer_index INTEGER NOT NULL,
                intent TEXT NOT NULL REFERENCES loans(intent), principal INTEGER NOT NULL,
                observation TEXT NOT NULL, PRIMARY KEY(tx,event_index), UNIQUE(tx,transfer_index))''')
            self.db.execute('CREATE TABLE IF NOT EXISTS incidents (reason TEXT PRIMARY KEY)')
            frozen = json.dumps({'schema':1, **config}, sort_keys=True)
            old = self.db.execute('SELECT config FROM metadata WHERE id=1').fetchone()
            if old is None:
                if not initialize: raise ValueError('missing ledger metadata; hold')
                self.db.execute('INSERT INTO metadata VALUES(1,?)', (frozen,))
            elif old['config'] != frozen: raise ValueError('policy change needs reviewed migration; no epoch reset')

    @contextmanager
    def atomic(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def close(self):
        self.db.close()

    def execution_permission(self):
        return {'allowed':False, 'reason':'OFFLINE_ONLY_NO_ACCEPTED_LIVE_ADAPTER'}

    def row(self, intent):
        row = self.db.execute('SELECT * FROM loans WHERE intent=?', (intent,)).fetchone()
        if row is None: raise ValueError('unknown intent')
        return dict(row)

    def totals(self):
        rows = self.db.execute('SELECT * FROM loans').fetchall()
        return {'net':sum(r['principal']-r['recovered'] for r in rows if r['state']!='REVERTED'),
                'gross':sum(r['principal'] for r in rows)}

    def has_chain_history(self):
        if self.db.execute('SELECT 1 FROM loans WHERE funding_block IS NOT NULL LIMIT 1').fetchone(): return True
        if self.db.execute('SELECT 1 FROM receipts LIMIT 1').fetchone(): return True
        for table in ('draws','backing_anchors','backing_attempts'):
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                query='SELECT 1 FROM '+table+(' WHERE funding_block IS NOT NULL' if table=='draws' else '')+' LIMIT 1'
                if self.db.execute(query).fetchone(): return True
        return False

    def reserve(self, intent, case, borrower, loan, principal, now):
        if self.has_chain_history():
            if not self.audit_canonical(): raise ValueError('canonical audit failed; hold')
        intent, loan = identifier(intent), identifier(loan)
        borrower, principal = address(borrower), units(principal)
        if (not isinstance(case, VerifiedCase) or not principal or
            case.consent is not True or case.independently_reviewed is not True or
            type(now) is not int or type(case.expires) is not int or now >= case.expires):
            raise ValueError('ineligible or expired case')
        for value in (case.controller, case.group, case.evidence_id): identifier(value)
        payload = json.dumps([asdict(case),borrower,loan,principal], sort_keys=True)
        with self.atomic():
            if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book_mode'").fetchone() and not loan.startswith('commitment:'):
                raise ValueError('commitment-book database cannot mix direct loan accounting')
            if self.db.execute('SELECT 1 FROM incidents LIMIT 1').fetchone():
                raise ValueError('reconciliation incident; issuance held')
            old = self.db.execute('SELECT payload FROM loans WHERE intent=?', (intent,)).fetchone()
            if old:
                if old['payload'] != payload: raise ValueError('changed intent replay')
                return False
            rows = self.db.execute('SELECT * FROM loans').fetchall()
            for suffix, field, value in [('total',None,None),('controller','controller',case.controller),('group','grp',case.group)]:
                subset = [r for r in rows if field is None or r[field]==value]
                net = sum(r['principal']-r['recovered'] for r in subset if r['state']!='REVERTED')
                gross = sum(r['principal'] for r in subset)
                if net+principal > self.config['net_'+suffix] or gross+principal > self.config['gross_'+suffix]:
                    raise ValueError('net or lifetime gross cap exceeded')
            self.db.execute('''INSERT INTO loans
                (intent,payload,controller,grp,evidence,borrower,loan,principal,state)
                VALUES(?,?,?,?,?,?,?,?, 'RESERVED')''',
                (intent,payload,case.controller,case.group,case.evidence_id,borrower,loan,principal))
            return True

    def prepare_attempt(self, intent, funding_tx, now):
        """Persist exact anticipated tx hash BEFORE any hypothetical submission.
        No signing/broadcast here. Repeated calls never authorize another send.
        """
        funding_tx = txhash(funding_tx)
        if self.has_chain_history():
            if not self.audit_canonical(): raise ValueError('canonical audit failed; hold')
        with self.atomic():
            if self.db.execute('SELECT 1 FROM incidents LIMIT 1').fetchone():
                raise ValueError('reconciliation incident; issuance held')
            r=self.row(intent)
            if r['funding_tx']:
                if r['funding_tx']!=funding_tx: raise ValueError('changed transaction')
                return False
            if r['loan'].startswith('commitment:'): raise ValueError('backing commitment is not a funding transaction')
            evidence=json.loads(r['payload'])[0]
            if type(now) is not int or now>=evidence['expires']:
                raise ValueError('expired case; no new attempt')
            if r['state']!='RESERVED': raise ValueError('invalid state')
            self.db.execute("UPDATE loans SET state='PENDING',funding_tx=? WHERE intent=?", (funding_tx,intent))
            return True

    def _observation(self, tx, index):
        if self.reader is None: raise ValueError('no independent reader; hold')
        if type(index) is not int or index<0: raise ValueError('invalid log index')
        obs=self.reader.observe(tx,index)
        if obs is None: return None
        if not isinstance(obs,Observation): raise ValueError('typed reader observation required')
        if (self.reader.chain_id()!=self.policy.chain or obs.chain!=self.policy.chain or
            txhash(obs.tx)!=tx or obs.event_index!=index or type(obs.event_index) is not int or
            type(obs.transfer_index) is not int or obs.transfer_index<0 or
            type(obs.status) is not int or obs.status not in (0,1) or
            type(obs.block) is not int or obs.block<0 or
            address(obs.pool)!=self.config['pool'] or address(obs.token)!=self.config['token']):
            raise ValueError('wrong chain or observation binding')
        head=self.reader.head()
        if type(head) is not int or head-obs.block+1<self.policy.confirmations:
            raise ValueError('insufficient confirmations')
        if txhash(self.reader.block_hash(obs.block))!=txhash(obs.block_hash):
            raise ValueError('noncanonical observation')
        return obs

    def reconcile_funding(self, intent, event_index):
        r=self.row(intent)
        if not r['funding_tx']: raise ValueError('no persisted attempt')
        obs=self._observation(r['funding_tx'],event_index)
        if obs is None: return 'HOLD_UNKNOWN'  # never release or submit again
        with self.atomic():
            r=self.row(intent)
            if r['state']!='PENDING': return r['state']
            if obs.status==0:
                self.db.execute("UPDATE loans SET state='REVERTED',funding_block=?,funding_hash=? WHERE intent=?",
                                (obs.block,txhash(obs.block_hash),intent))
                return 'REVERTED'
            if (obs.kind!='funding' or obs.loan!=r['loan'] or address(obs.borrower)!=r['borrower'] or
                units(obs.principal)!=r['principal'] or address(obs.transfer_from)!=self.config['pool'] or
                address(obs.transfer_to)!=r['borrower'] or
                units(obs.transfer_amount)!=r['principal']):
                raise ValueError('funding does not match exact intent')
            self.db.execute("UPDATE loans SET state='ACTIVE',funding_block=?,funding_hash=? WHERE intent=?",
                            (obs.block,txhash(obs.block_hash),intent))
            return 'ACTIVE'

    def apply_repayment(self, intent, repayment_tx, event_index):
        """Claim supplies only a lookup key. All amounts come from the reader.
        Unique repayment AND transfer log prevent allocation to multiple loans.
        Gross caps never grow or reset on repayment; no score is updated.
        """
        if not self.audit_canonical(): raise ValueError('canonical audit failed; hold')
        repayment_tx=txhash(repayment_tx)
        obs=self._observation(repayment_tx,event_index)
        if obs is None: raise ValueError('unknown repayment; hold')
        principal=units(obs.principal)
        if (obs.status!=1 or obs.kind!='repayment' or principal<=0 or
            address(obs.transfer_to)!=self.config['pool'] or address(obs.transfer_from)==self.config['pool'] or
            units(obs.transfer_amount)<principal):
            raise ValueError('not a successful principal recovery to the pool')
        encoded=json.dumps(asdict(obs),sort_keys=True)
        with self.atomic():
            old=self.db.execute('SELECT * FROM receipts WHERE tx=? AND event_index=?',(repayment_tx,event_index)).fetchone()
            if old:
                if old['intent']!=intent or old['observation']!=encoded: raise ValueError('receipt allocation mismatch')
                return False
            r=self.row(intent)
            if (r['state'] not in ('ACTIVE','DEFAULTED') or obs.loan!=r['loan'] or
                address(obs.borrower)!=r['borrower'] or obs.block<r['funding_block'] or
                r['recovered']+principal>r['principal']):
                raise ValueError('repayment loan binding or principal cap mismatch')
            recovered=r['recovered']+principal
            state='REPAID' if recovered==r['principal'] else r['state']
            self.db.execute('UPDATE loans SET recovered=?,state=? WHERE intent=?',(recovered,state,intent))
            self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',
                            (repayment_tx,event_index,obs.transfer_index,intent,principal,encoded))
            return True

    def mark_default(self, intent):
        with self.atomic():
            if self.row(intent)['state'] not in ('ACTIVE','DEFAULTED'): raise ValueError('invalid default state')
            self.db.execute("UPDATE loans SET state='DEFAULTED' WHERE intent=?",(intent,))

    def audit_canonical(self):
        """Detect reorg of previously accepted observations, persist an issuance hold.
        Never erase loss/intent/evidence or automatically retry a transaction.
        Deployment requires this reconciliation before enabling ANY executor.
        """
        if self.reader is None: raise ValueError('no independent reader; hold')
        with self.atomic():
            bad=[]
            if self.reader.chain_id()!=self.policy.chain: bad.append('chain mismatch')
            for r in self.db.execute('SELECT * FROM loans WHERE funding_block IS NOT NULL').fetchall():
                if self.reader.block_hash(r['funding_block'])!=r['funding_hash']: bad.append('funding reorg:'+r['intent'])
            for r in self.db.execute('SELECT observation FROM receipts').fetchall():
                o=json.loads(r['observation'])
                if self.reader.block_hash(o['block'])!=o['block_hash']: bad.append('repayment reorg:'+o['tx'])
            for table,query in [('draws','SELECT funding_block AS block,funding_hash AS hash,loan AS name FROM draws WHERE funding_block IS NOT NULL'),
                                ('backing_anchors','SELECT block,hash,intent AS name FROM backing_anchors'),
                                ('backing_attempts','SELECT block,block_hash AS hash,binding AS name FROM backing_attempts WHERE block IS NOT NULL')]:
                if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                    for r in self.db.execute(query).fetchall():
                        if self.reader.block_hash(r['block'])!=r['hash']: bad.append(table+' reorg:'+r['name'])
            for reason in bad: self.db.execute('INSERT OR IGNORE INTO incidents VALUES(?)',(reason,))
            return not bad and not self.db.execute('SELECT 1 FROM incidents LIMIT 1').fetchone()
