"""At-most-one broadcast attempt coordinator, inactive without installed ports.
The signer/custody, sender and authoritative release/lease guard are trusted
runtime dependencies. No credential is loaded here. Public caller chooses only
an existing binding ID, never a key, destination, nonce, fee or approval flag.
"""
import json
from durable import txhash
from local_boundary import PinnedNode,node_environment,private_ledger


class SubmissionCoordinator:
    def __init__(self,bindings,journal,verifier,*,clock,fee_limits,signer=None,sender=None,release_guard=None):
        self.bindings,self.journal,self.ledger=bindings,journal,bindings.ledger
        self.verifier,self.clock,self.limits=verifier,clock,dict(fee_limits)
        self.signer,self.sender,self.guard=signer,sender,release_guard
        private_ledger(self.ledger)
        with self.ledger.atomic():
            self.ledger.db.execute('''CREATE TABLE IF NOT EXISTS submission_attempts (
                binding TEXT PRIMARY KEY REFERENCES reply_bindings(id),
                state TEXT NOT NULL,hash TEXT,raw TEXT)''')
    def _permit(self):
        if self.signer is None or self.sender is None or self.guard is None or self.guard() is not True:
            raise ValueError('release/drain/lease/custody gate closed')
    def _current_locked(self,b,now):
        c=self.bindings._consent(b['subject'],now)
        self.bindings._reservation(b['reservation'],b['subject'],now)
        if c['revision']!=b['revision'] or now>=b['expires'] or b['fingerprint']!=self.bindings.fingerprint:
            raise ValueError('consent/policy/expiry changed')
    def _status(self,binding,state):
        return {'state':state,'retry_allowed':False,'binding_id':binding}
    def submit(self,binding):
        self._permit()
        b=self.ledger.db.execute('SELECT * FROM reply_bindings WHERE id=?',(binding,)).fetchone()
        if not b:raise ValueError('unknown binding')
        b=dict(b);transaction=json.loads(b['payload']);now=self.clock()
        # This validates evidence only; the separately installed release guard
        # supplies execution authority. Default reference APIs grant none.
        self.bindings.validate(binding,transaction,now)
        with self.ledger.atomic():
            self._permit();self._current_locked(b,self.clock())
            old=self.ledger.db.execute('SELECT state FROM submission_attempts WHERE binding=?',(binding,)).fetchone()
            if old:return self._status(binding,old['state'])
            # Commit BEFORE invoking even the signer. Crash/retry never signs
            # again or creates another nonce; operator reconciliation is required.
            self.ledger.db.execute("INSERT INTO submission_attempts(binding,state) VALUES(?,'SIGNING')",(binding,))
        limits=dict(self.limits,expires=b['expires'])
        try:
            raw=self.signer(transaction,limits)
            checked=self.verifier(raw,transaction,limits,self.clock())
            if checked.get('signatureValid') is not True:raise ValueError('bad signature')
            h=txhash(checked['transactionHash'])
            self.journal.prepare(binding,transaction,h,self.clock())
            with self.ledger.atomic():
                self._permit();self._current_locked(b,self.clock())
                self.ledger.db.execute("UPDATE submission_attempts SET state='SEND_STARTED',hash=?,raw=? WHERE binding=?",(h,raw,binding))
        except Exception:
            with self.ledger.atomic():
                self.ledger.db.execute("UPDATE submission_attempts SET state='HELD' WHERE binding=?",(binding,))
            return self._status(binding,'HELD')
        # Durable SEND_STARTED precedes network. Hold the same consent DB write
        # lock through the single send; accepted withdrawals serialize against it.
        # Withdrawal after send cannot recall an already signed/submitted tx.
        with self.ledger.atomic():
            try:self._permit();self._current_locked(b,self.clock())
            except Exception:
                self.ledger.db.execute("UPDATE submission_attempts SET state='HELD' WHERE binding=?",(binding,))
                return self._status(binding,'HELD')
            try:
                sent=txhash(self.sender(raw))
                if sent!=h:raise ValueError('sender hash mismatch')
                state='BROADCAST'
            except Exception:
                state='UNKNOWN'
                self.ledger.db.execute('INSERT OR IGNORE INTO incidents VALUES(?)',('uncertain submission:'+binding,))
            self.ledger.db.execute('UPDATE submission_attempts SET state=? WHERE binding=?',(state,binding))
        return self._status(binding,state)

    def reconcile(self,binding):
        state=self.journal.reconcile(binding)
        if state in ('CONFIRMED','REVERTED'):
            with self.ledger.atomic():
                attempt=self.ledger.db.execute('SELECT hash FROM submission_attempts WHERE binding=?',(binding,)).fetchone()
                receipt=self.ledger.db.execute('SELECT hash FROM backing_attempts WHERE binding=?',(binding,)).fetchone()
                if attempt and receipt and attempt['hash']==receipt['hash']:
                    self.ledger.db.execute('UPDATE submission_attempts SET state=? WHERE binding=?',(state,binding))
        return state


class HTTPSBroadcast:
    """Single send port, never installed by default. No retry, fallback or key.
    Release guard is checked again even when called outside the coordinator.
    """
    def __init__(self,transport,release_guard=None):
        self.transport,self.guard=transport,release_guard
    def __call__(self,raw):
        import re
        if self.guard is None or self.guard() is not True:raise ValueError('broadcast gate closed')
        if not isinstance(raw,str) or not re.fullmatch(r'0x02(?:[0-9a-fA-F]{2})+',raw) or len(raw)>32768:
            raise ValueError('bounded signed EIP1559 envelope required')
        return txhash(self.transport._exchange('eth_sendRawTransaction',[raw]))


class InheritedFDSigner:
    """Owner-held sealed/memory key descriptor, supplied only at accepted launch.
    Never opens a key file, reads an environment secret or creates credentials.
    Node child consumes FD privately and returns a signature to this service only.
    """
    def __init__(self,key_fd,script,node):
        import os
        from pathlib import Path
        if not isinstance(node,PinnedNode):raise ValueError('pinned node executable required')
        if type(key_fd) is not int or key_fd<3:raise ValueError('inherited private descriptor required')
        os.fstat(key_fd)
        import fcntl
        import sys
        if sys.platform!='linux':raise ValueError('Linux sealed descriptor required')
        # Linux UAPI linux/fcntl.h: GET_SEALS=1024+10; seal/shrink/grow/write bits1/2/4/8.
        # Some Python builds omit the symbolic constants despite kernel support.
        seals=0x0f
        if fcntl.fcntl(key_fd,getattr(fcntl,'F_GET_SEALS',1034))&seals!=seals:raise ValueError('sealed immutable memory descriptor required')
        self.fd,self.script,self.node=key_fd,str(Path(script).resolve()),node
    def __call__(self,transaction,limits):
        import subprocess
        result=subprocess.run(self.node.command(self.script,str(self.fd)),env=node_environment(),input=json.dumps({'transaction':transaction,'limits':limits}),
             text=True,capture_output=True,pass_fds=(self.fd,),timeout=10,check=False)
        if result.returncode or len(result.stdout)>40000:raise ValueError('private signer rejected')
        from authenticated_reader import strict_json
        value=strict_json(result.stdout)
        if set(value)!={'serialized'}:raise ValueError('invalid signer result')
        return value['serialized']
