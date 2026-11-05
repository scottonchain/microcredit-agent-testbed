"""Durable backing-change intent journal; no signer, sender or release authority.
Reader observations are an authenticated integration dependency, not user input.
All ambiguous/noncanonical outcomes retain exposure and block the nonce.
"""
import json
from durable import txhash


class PendingJournal:
    def __init__(self, bindings, reader):
        self.bindings,self.ledger,self.reader=bindings,bindings.ledger,reader
        with self.ledger.atomic():
            self.ledger.db.execute('''CREATE TABLE IF NOT EXISTS backing_attempts (
                binding TEXT PRIMARY KEY REFERENCES reply_bindings(id),
                hash TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','CONFIRMED','REVERTED')),
                block INTEGER, block_hash TEXT, observation TEXT)''')

    def prepare(self,binding,transaction,transaction_hash,now):
        """Persist before hypothetical sending. Hash is never permission to send.
        The final executor must independently derive it from the verified envelope.
        """
        transaction_hash=txhash(transaction_hash)
        self.bindings.validate(binding,transaction,now)
        encoded=json.dumps(transaction,sort_keys=True)
        with self.ledger.atomic():
            b=self.ledger.db.execute('SELECT * FROM reply_bindings WHERE id=?',(binding,)).fetchone()
            c=self.bindings._consent(b['subject'],now)
            self.bindings._reservation(b['reservation'],b['subject'],now)
            if c['revision']!=b['revision'] or now>=b['expires'] or encoded!=b['payload']:
                raise ValueError('binding changed before persistence')
            old=self.ledger.db.execute('SELECT * FROM backing_attempts WHERE binding=?',(binding,)).fetchone()
            if old:
                if (old['hash'],old['payload'])!=(transaction_hash,encoded): raise ValueError('replacement needs explicit reconciliation')
                return False
            self.ledger.db.execute("INSERT INTO backing_attempts(binding,hash,payload,state) VALUES(?,?,?,'PENDING')",(binding,transaction_hash,encoded))
            return True

    def reconcile(self,binding):
        row=self.ledger.db.execute('SELECT * FROM backing_attempts WHERE binding=?',(binding,)).fetchone()
        if not row: raise ValueError('unknown attempt')
        if self.reader is None: return 'HOLD'
        o=self.reader.observe(row['hash'])
        if o is None: return 'HOLD'
        expected=json.loads(row['payload'])
        # A nonce count, missing tx, expiry or another tx with this nonce is never
        # evidence that this intended backing change executed or reverted.
        if (o.get('hash')!=row['hash'] or o.get('transaction')!=expected or
            type(o.get('status')) is not int or o['status'] not in (0,1) or
            type(o.get('block')) is not int or o['block']<0 or
            self.reader.head()-o['block']+1<self.ledger.policy.confirmations or
            self.reader.block_hash(o['block'])!=txhash(o.get('block_hash'))):
            raise ValueError('unconfirmed or mismatched outcome; retain exposure')
        encoded=json.dumps(o,sort_keys=True)
        with self.ledger.atomic():
            current=self.ledger.db.execute('SELECT * FROM backing_attempts WHERE binding=?',(binding,)).fetchone()
            if current['state']!='PENDING':
                if current['observation']!=encoded: raise ValueError('changed terminal observation; audit required')
                return current['state']
            state='CONFIRMED' if o['status']==1 else 'REVERTED'
            self.ledger.db.execute('UPDATE backing_attempts SET state=?,block=?,block_hash=?,observation=? WHERE binding=?',
                                   (state,o['block'],o['block_hash'],encoded,binding))
            # No parent reservation is released, even on revert. Prior usable
            # backing and any other accepted/pending grant need reconciliation.
            return state

    def audit(self):
        if self.reader is None: return False
        with self.ledger.atomic():
            for r in self.ledger.db.execute('SELECT * FROM backing_attempts WHERE block IS NOT NULL').fetchall():
                if self.reader.block_hash(r['block'])!=r['block_hash']:
                    self.ledger.db.execute('INSERT OR IGNORE INTO incidents VALUES(?)',('backing transaction reorg:'+r['binding'],))
            return not bool(self.ledger.db.execute('SELECT 1 FROM incidents LIMIT 1').fetchone())

    def barrier(self):
        # A journal is necessary but not sufficient: no installation attests that
        # it captures ALL officer writes or excludes direct borrower pool calls.
        return {'release_allowed':False,'execution_allowed':False,
                'reason':'NO_COMPLETE_WRITE_BOUNDARY_OR_SCOPED_POOL_AUTHORIZATION'}
