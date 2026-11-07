"""Private role-separated staging boundary. No sender or live signing authority.
Consent UID is a trusted controller, not an applicant or assessment agent. The
runtime supervisor supplies kernel peer credentials; JSON cannot choose a role.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
from authenticated_reader import strict_json
from durable import txhash


def private_ledger(ledger):
    db=Path(ledger.db.execute('PRAGMA database_list').fetchone()[2])
    for path in (db,db.parent):
        st=path.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:
            raise ValueError('private owned nonsymlink ledger/directory required')


def node_environment():
    """The ONLY environment a Node child receives: nothing is inherited from the service. PATH, NODE_PATH,
    NODE_OPTIONS, LD_PRELOAD and any secret in the service's environment never reach a child, and module
    resolution is the script's own directory, not an inherited search path."""
    return {'NODE_NO_WARNINGS':'1'}


class PinnedNode:
    """An absolute Node executable pinned by the reviewed configuration.

    The path must be absolute and contain no symlink, name a regular executable owned by root or the service
    user that is not group- or world-writable, and match the pinned SHA-256. It is hashed once, here; every use
    re-checks inode, size and mtime so a replacement after pinning is refused. Nothing is looked up through PATH.
    """
    def __init__(self,path,expected_sha256):
        p=Path(path)
        if not p.is_absolute() or p.resolve()!=p:raise ValueError('absolute node path without symlinks required')
        st=p.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid not in (0,os.getuid()) or st.st_mode&0o022 or not st.st_mode&0o111):
            raise ValueError('owner-controlled executable node required')
        if type(expected_sha256) is not str or len(expected_sha256)!=64:raise ValueError('node executable pin required')
        digest=hashlib.sha256()
        with open(p,'rb') as handle:
            for chunk in iter(lambda:handle.read(1<<20),b''):digest.update(chunk)
        if digest.hexdigest()!=expected_sha256.lower():raise ValueError('node executable pin mismatch')
        self.path=str(p);self._identity=(st.st_ino,st.st_size,st.st_mtime_ns)
    def command(self,*args):
        st=Path(self.path).lstat()
        if (st.st_ino,st.st_size,st.st_mtime_ns)!=self._identity:raise ValueError('node executable changed since pinning')
        return [self.path,*args]


class NodeSignatureVerifier:
    def __init__(self,bridge,node):
        if not isinstance(node,PinnedNode):raise ValueError('pinned node executable required')
        self.bridge=str(Path(bridge).resolve());self.node=node
    def __call__(self,serialized,transaction,limits,now):
        data=json.dumps({'serialized':serialized,'transaction':transaction,'limits':limits,'now':now},allow_nan=False)
        if len(data)>100000:raise ValueError('signature request too large')
        result=subprocess.run(self.node.command(self.bridge),env=node_environment(),input=data,text=True,capture_output=True,timeout=10,check=False)
        if result.returncode or len(result.stdout)>4096:raise ValueError('signature verification failed')
        return strict_json(result.stdout)


class LocalBoundary:
    def __init__(self,bindings,journal,verifier,*,consent_uid,executor_uid,fee_limits,clock,submitter=None,allow_external_staging=False):
        if (type(consent_uid) is not int or type(executor_uid) is not int or min(consent_uid,executor_uid)<=0 or os.getuid() in (consent_uid,executor_uid) or
            consent_uid==executor_uid):raise ValueError('non-root clients distinct from each other and service UID required')
        self.bindings,self.journal,self.verifier=bindings,journal,verifier
        self.consent_uid,self.executor_uid,self.limits,self.clock=consent_uid,executor_uid,dict(fee_limits),clock
        self.ledger=bindings.ledger
        self.submitter=submitter
        self.allow_external_staging=allow_external_staging
        private_ledger(self.ledger)
        with self.ledger.atomic():
            self.ledger.db.execute('''CREATE TABLE IF NOT EXISTS signed_staging (
                binding TEXT PRIMARY KEY REFERENCES backing_attempts(binding),
                hash TEXT UNIQUE NOT NULL,raw TEXT NOT NULL,state TEXT NOT NULL CHECK(state='STAGED'))''')
    def dispatch(self,peer_uid,raw):
        if not isinstance(raw,bytes) or len(raw)>100000:raise ValueError('bounded local JSON required')
        p=strict_json(raw)
        if not isinstance(p,dict) or set(p)!={'method','params'} or not isinstance(p['params'],dict):raise ValueError('request schema')
        method,args=p['method'],p['params']
        if method=='consent':
            if peer_uid!=self.consent_uid:raise ValueError('consent role required')
            if set(args)!={'subject','revision','allowed','purpose','expires'}:raise ValueError('consent schema')
            return {'updated':self.bindings.record_consent(**args)}
        if peer_uid!=self.executor_uid:raise ValueError('executor role required')
        if method=='submit':
            if set(args)!={'binding_id'} or self.submitter is None:raise ValueError('no accepted submission adapter')
            return self.submitter.submit(args['binding_id'])
        if method=='bind':
            if set(args)!={'binding_id','reservation','borrower','backing','message_id','expires'}:raise ValueError('binding schema')
            return self.bindings.bind(**args,now=self.clock())
        if method=='reconcile':
            if set(args)!={'binding_id'}:raise ValueError('reconcile schema')
            return {'state':self.submitter.reconcile(args['binding_id']) if self.submitter is not None else self.journal.reconcile(args['binding_id']),'execution_allowed':False}
        if not self.allow_external_staging:raise ValueError('external signed staging disabled; custody must remain inside submission gate')
        if method!='stage' or set(args)!={'binding_id','transaction','serialized'}:raise ValueError('unknown method or schema')
        now=self.clock();binding=args['binding_id'];transaction=args['transaction'];serialized=args['serialized']
        b=self.ledger.db.execute('SELECT * FROM reply_bindings WHERE id=?',(binding,)).fetchone()
        if not b:raise ValueError('unknown binding')
        self.bindings.validate(binding,transaction,now)
        limits=dict(self.limits,expires=b['expires'])
        checked=self.verifier(serialized,transaction,limits,now)
        if checked.get('signatureValid') is not True:raise ValueError('signature invalid')
        h=txhash(checked['transactionHash'])
        # Journal validation reacquires canonical state after verifier completion.
        self.journal.prepare(binding,transaction,h,self.clock())
        with self.ledger.atomic():
            now=self.clock();c=self.bindings._consent(b['subject'],now)
            self.bindings._reservation(b['reservation'],b['subject'],now)
            if c['revision']!=b['revision'] or now>=b['expires']:raise ValueError('consent expired/changed during staging')
            old=self.ledger.db.execute('SELECT * FROM signed_staging WHERE binding=?',(binding,)).fetchone()
            if old and (old['hash'],old['raw'])!=(h,serialized):raise ValueError('changed signed staging replay')
            if not old:self.ledger.db.execute("INSERT INTO signed_staging VALUES(?,?,?,'STAGED')",(binding,h,serialized))
        # Raw signed bytes are private and never returned to an IPC caller.
        return {'state':'STAGED','transaction_hash':h,'execution_allowed':False,
                'reason':'RETAINED_RUNTIME_DRAIN_AND_COMPLETE_RELEASE_GATE_REQUIRED'}


def serve_unix(boundary,path,*,socket_group,stop,ready=None):
    """Supervised entrypoint; never auto-started. Private ledger is separate.
    Existing sockets require drain, never automatic unlink/replacement.
    """
    import socket
    import struct
    path=Path(path)
    if not path.is_absolute() or path.exists() or path.is_symlink():raise ValueError('new absolute socket path required')
    parent=path.parent.lstat()
    if stat.S_ISLNK(parent.st_mode) or parent.st_uid!=os.getuid() or parent.st_mode&0o027:
        raise ValueError('owned socket directory without group-write/other access required')
    if not hasattr(socket,'SO_PEERCRED'):raise ValueError('kernel peer credentials required')
    def exact(conn,n):
        chunks=[]
        while n:
            data=conn.recv(n)
            if not data:raise ValueError('truncated request')
            chunks.append(data);n-=len(data)
        return b''.join(chunks)
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(str(path));os.chown(path,-1,socket_group);os.chmod(path,0o660)
        socket_inode=path.lstat().st_ino
        try:
            server.listen(8);server.settimeout(1)
            if ready is not None:ready()
            while not stop():
                try:conn,_=server.accept()
                except socket.timeout:continue
                with conn:
                    conn.settimeout(5)
                    try:
                        _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                        n=struct.unpack('!I',exact(conn,4))[0]
                        if n>100000:raise ValueError('oversized request')
                        answer={'ok':True,'result':boundary.dispatch(uid,exact(conn,n))}
                    except Exception:answer={'ok':False,'error':'REQUEST_REJECTED'}
                    out=json.dumps(answer,allow_nan=False).encode()
                    try:conn.sendall(struct.pack('!I',len(out))+out)
                    except OSError:pass
        finally:
            if path.exists() and path.lstat().st_ino==socket_inode:path.unlink()


def unix_request(path,expected_service_uid,request,timeout=10):
    """Client helper authenticates the server's kernel UID, not JSON claims."""
    import socket
    import struct
    raw=json.dumps(request,allow_nan=False).encode()
    if len(raw)>100000:raise ValueError('request too large')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
        conn.settimeout(timeout);conn.connect(str(path))
        _,uid,_=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid!=expected_service_uid:raise ValueError('server identity mismatch')
        conn.sendall(struct.pack('!I',len(raw))+raw)
        def exact(n):
            out=b''
            while len(out)<n:
                data=conn.recv(n-len(out))
                if not data:raise ValueError('truncated response')
                out+=data
            return out
        size=struct.unpack('!I',exact(4))[0]
        if size>100000:raise ValueError('oversized response')
        return strict_json(exact(size))
