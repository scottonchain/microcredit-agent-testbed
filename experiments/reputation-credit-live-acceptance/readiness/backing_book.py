"""Offline authoritative commitment book on the SAME Ledger database.
A pledge stays reserved across loan repayments. Release is disabled until a
backing-change transaction journal and final reconciliation barrier exist. No sender, live snapshot provider or deployment.
"""
import json
from durable import address, identifier, units, txhash


class BackingBook:
    def __init__(self,ledger,source):
        self.ledger,self.source=ledger,source
        with ledger.atomic():
            rows=ledger.db.execute('SELECT loan,state FROM loans').fetchall()
            if any(not r['loan'].startswith('commitment:') for r in rows):
                raise ValueError('dedicated commitment ledger required; no mixed accounting')
            ledger.db.execute('CREATE TABLE IF NOT EXISTS book_mode (id INTEGER PRIMARY KEY CHECK(id=1))')
            ledger.db.execute('INSERT OR IGNORE INTO book_mode VALUES(1)')
            ledger.db.execute('''CREATE TABLE IF NOT EXISTS pledges (
                intent TEXT PRIMARY KEY REFERENCES loans(intent),desk TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('HELD','RELEASED')))''')
            ledger.db.execute('CREATE TABLE IF NOT EXISTS backing_anchors (intent TEXT PRIMARY KEY,block INTEGER NOT NULL,hash TEXT NOT NULL)')
            ledger.db.execute('''CREATE TABLE IF NOT EXISTS draws (
                loan TEXT PRIMARY KEY, pledge TEXT NOT NULL REFERENCES pledges(intent),
                principal INTEGER NOT NULL CHECK(principal>0), recovered INTEGER NOT NULL DEFAULT 0,
                state TEXT NOT NULL CHECK(state IN ('RESERVED','FUNDED','REPAID')),
                funding_tx TEXT, funding_event INTEGER, funding_block INTEGER, funding_hash TEXT,
                UNIQUE(funding_tx,funding_event),CHECK(recovered>=0 AND recovered<=principal))''')

    def register(self,intent,desk):
        desk=address(desk)
        with self.ledger.atomic():
            r=self.ledger.row(intent)
            if not r['loan'].startswith('commitment:') or r['state']!='RESERVED': raise ValueError('not a held commitment')
            old=self.ledger.db.execute('SELECT * FROM pledges WHERE intent=?',(intent,)).fetchone()
            if old:
                if old['desk']!=desk: raise ValueError('changed desk')
                return False
            self.ledger.db.execute("INSERT INTO pledges VALUES(?,?,'HELD')",(intent,desk))
            return True

    def _audit(self):
        if self.source is None or not self.ledger.audit_canonical(): raise ValueError('canonical hold')
        with self.ledger.atomic():
            bad=False
            for r in self.ledger.db.execute('SELECT * FROM draws WHERE funding_block IS NOT NULL').fetchall():
                if self.source.block_hash(r['funding_block'])!=r['funding_hash']:
                    self.ledger.db.execute('INSERT OR IGNORE INTO incidents VALUES(?)',('draw reorg:'+r['loan'],));bad=True
        if bad: raise ValueError('draw funding reorg; hold')

    def _state(self,intent,now):
        if type(now) is not int: raise ValueError('clock required')
        self._audit()
        root=self.ledger.row(intent)
        pledge=self.ledger.db.execute('SELECT * FROM pledges WHERE intent=?',(intent,)).fetchone()
        if not pledge or pledge['status']!='HELD': raise ValueError('not a held pledge')
        s=self.source.backing_snapshot(pledge['desk'],root['borrower'])
        if (s['chain']!=self.ledger.policy.chain or address(s['pool'])!=self.ledger.config['pool'] or
            address(s['desk'])!=pledge['desk'] or address(s['borrower'])!=root['borrower'] or
            type(s['timestamp']) is not int or type(s['block']) is not int or not -120<=now-s['timestamp']<=900 or
            self.source.head()-s['block']+1<self.ledger.policy.confirmations or
            txhash(self.source.block_hash(s['block']))!=txhash(s['hash'])):
            raise ValueError('backing snapshot binding mismatch')
        for key in ('secured','unsecured','otherBacking','grantedCredit'):
            if type(s[key]) is not int or s[key]<0: raise ValueError('exact backing state required')
        if s['unsecured'] or s['otherBacking'] or s['grantedCredit'] or s['secured']>root['principal']:
            raise ValueError('unsupported additional or unsecured capacity')
        # Provider must establish complete canonical borrower loan inventory;
        # this marker is a trust-boundary assertion, not a cryptographic proof.
        if s.get('inventory_complete') is not True or not isinstance(s['loans'],dict):
            raise ValueError('complete borrower loan inventory required')
        return root,s

    def _hold_locked(self):
        if self.ledger.db.execute('SELECT 1 FROM incidents LIMIT 1').fetchone(): raise ValueError('incident hold')

    def reserve_draw(self,intent,loan,principal,now):
        loan=identifier(loan); principal=units(principal)
        root,s=self._state(intent,now)
        if not principal or now>=json.loads(root['payload'])[0]['expires']: raise ValueError('expired or empty draw')
        observed=s['loans'].get(loan)
        if observed!={'state':'REQUESTED','principal':principal,'recovered':0}:
            raise ValueError('draw must match actual requested-loan state')
        with self.ledger.atomic():
            self._hold_locked()
            current=self.ledger.row(intent)
            held=self.ledger.db.execute('SELECT status FROM pledges WHERE intent=?',(intent,)).fetchone()
            if not held or held['status']!='HELD' or current['state']!='RESERVED' or current['recovered']:
                raise ValueError('commitment no longer fully held')
            old=self.ledger.db.execute('SELECT * FROM draws WHERE loan=?',(loan,)).fetchone()
            if old:
                if (old['pledge'],old['principal'])!=(intent,principal): raise ValueError('changed draw')
                return False
            own=self.ledger.db.execute('SELECT * FROM draws WHERE pledge=?',(intent,)).fetchall()
            if set(s['loans'])-({r['loan'] for r in own}|{loan}): raise ValueError('untracked borrower loan; reconciliation required')
            for r in own:
                remote=s['loans'].get(r['loan'])
                expected='ACTIVE' if r['state']=='FUNDED' else ('REQUESTED' if r['state']=='RESERVED' else 'REPAID')
                if remote!={'state':expected,'principal':r['principal'],'recovered':r['recovered']}:
                    raise ValueError('tracked loan diverges from current canonical inventory')
            if sum(r['principal']-r['recovered'] for r in own)+principal>s['secured']:
                raise ValueError('same backing cannot cover concurrent draws twice')
            allrows=self.ledger.db.execute('SELECT d.principal,l.controller,l.grp FROM draws d JOIN loans l ON l.intent=d.pledge').fetchall()
            for suffix,key,value in [('total',None,None),('controller','controller',root['controller']),('group','grp',root['grp'])]:
                gross=sum(r['principal'] for r in allrows if key is None or r[key]==value)
                if gross+principal>self.ledger.config['gross_'+suffix]: raise ValueError('cumulative draw cap')
            self.ledger.db.execute("INSERT INTO draws(loan,pledge,principal,state) VALUES(?,?,?,'RESERVED')",(loan,intent,principal))
            return True

    def funding(self,loan,transaction,event):
        self._audit()
        o=self.ledger._observation(txhash(transaction),event)
        if o is None: return 'HOLD_UNKNOWN'
        if o.kind!='funding' or o.status!=1: raise ValueError('funding required')
        with self.ledger.atomic():
            d=self.ledger.db.execute('SELECT * FROM draws WHERE loan=?',(loan,)).fetchone()
            if not d: raise ValueError('unreserved loan; incident investigation required')
            root=self.ledger.row(d['pledge'])
            if (o.loan!=loan or address(o.borrower)!=root['borrower'] or units(o.principal)!=d['principal'] or
                address(o.transfer_from)!=self.ledger.config['pool'] or address(o.transfer_to)!=root['borrower'] or
                units(o.transfer_amount)!=d['principal']): raise ValueError('wrong loan funding')
            if d['funding_tx']:
                if (d['funding_tx'],d['funding_event'])!=(txhash(transaction),event): raise ValueError('changed funding receipt')
                return False
            self.ledger.db.execute("UPDATE draws SET state='FUNDED',funding_tx=?,funding_event=?,funding_block=?,funding_hash=? WHERE loan=?",
                                   (txhash(transaction),event,o.block,txhash(o.block_hash),loan))
            return True

    def repayment(self,loan,transaction,event):
        self._audit()
        o=self.ledger._observation(txhash(transaction),event)
        if o is None or o.kind!='repayment' or o.status!=1: raise ValueError('verified repayment required')
        principal=units(o.principal)
        encoded=json.dumps(o.__dict__,sort_keys=True)
        with self.ledger.atomic():
            d=self.ledger.db.execute('SELECT * FROM draws WHERE loan=?',(loan,)).fetchone()
            if not d: raise ValueError('unknown draw')
            root=self.ledger.row(d['pledge'])
            if (o.loan!=loan or address(o.borrower)!=root['borrower'] or principal<=0 or
                address(o.transfer_to)!=self.ledger.config['pool'] or address(o.transfer_from)==self.ledger.config['pool'] or
                units(o.transfer_amount)<principal): raise ValueError('wrong repayment binding')
            old=self.ledger.db.execute('SELECT * FROM receipts WHERE tx=? AND event_index=?',(txhash(transaction),event)).fetchone()
            if old:
                if old['intent']!=d['pledge'] or old['observation']!=encoded: raise ValueError('allocation conflict')
                return False
            if d['state']!='FUNDED' or o.block<d['funding_block'] or d['recovered']+principal>d['principal']:
                raise ValueError('repayment exceeds or precedes funded draw')
            recovered=d['recovered']+principal
            state='REPAID' if recovered==d['principal'] else 'FUNDED'
            self.ledger.db.execute('UPDATE draws SET recovered=?,state=? WHERE loan=?',(recovered,state,loan))
            self.ledger.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',
                                  (txhash(transaction),event,o.transfer_index,d['pledge'],principal,encoded))
            # Deliberately do NOT reduce the parent pledge or recreate gross headroom.
            return True

    def release(self,intent,now):
        # Even a recent zero-backing block can predate an accepted or pending
        # backing grant. No authoritative journal/barrier is installed yet.
        # Retain all exposure instead of treating a snapshot as finality.
        raise ValueError('release disabled: backing-change journal and reconciliation barrier required')
