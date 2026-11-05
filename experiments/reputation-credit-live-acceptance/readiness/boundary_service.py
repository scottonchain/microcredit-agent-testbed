"""Explicit, closed-by-default sidecar assembly. No import-time network/action.
The retained supervisor supplies its existing lease and full-inventory probes;
missing probes close the release gate. This does not replace or start D7 itself.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from authenticated_reader import AuthenticatedSnapshots,HTTPSReadRPC,DeskSnapshots,strict_json
from canonical_adapter import CanonicalReader
from durable import Ledger,Policy
from service_binding import ReplyBindings
from pending_journal import PendingJournal
from local_boundary import LocalBoundary,NodeSignatureVerifier,serve_unix
from release_guard import InstalledReleaseGuard
from submission import SubmissionCoordinator,InheritedFDSigner,HTTPSBroadcast


def assemble(config_path,expected_sha256,*,lease_probe=None,inventory_probe=None,key_fd=None,clock=lambda:int(time.time())):
    fd=os.open(config_path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as handle:
        st=os.fstat(handle.fileno());raw=handle.read(100001)
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077 or len(raw)>100000:
        raise ValueError('private supervisor configuration required')
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('configuration revision mismatch')
    c=strict_json(raw)
    required={'policy','ledger_path','rpc','code_pins','proxy_bindings','desk','officer','approved_messages','fees',
              'consent_uid','executor_uid','socket_path','socket_group','source_revision','source_hashes','release_path','release_sha256'}
    if set(c)!=required:raise ValueError('exact deployment configuration required')
    root=Path(__file__).parent.resolve()
    for directory in (root,*root.parents,root/'signed-validator'):
        st=directory.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid not in (0,os.getuid()) or st.st_mode&0o022:
            raise ValueError('installed source directories must exclude client writes')
    # Boundary source files are pinned by the reviewed installation config.
    # The supervisor separately authenticates Node/Python and installed dependencies.
    # No caller-provided script/module path.
    code_files=['authenticated_reader.py','boundary_service.py','canonical_adapter.py','durable.py','bounds.py','service_binding.py',
                'pending_journal.py','local_boundary.py','release_guard.py','submission.py',
                'signed-validator/bridge.cjs','signed-validator/verify.cjs','signed-validator/sign-fd.cjs','signed-validator/package-lock.json']
    if set(c['source_hashes'])!=set(code_files):raise ValueError('complete source pins required')
    for name in code_files:
        path=root/name;st=path.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_uid not in (0,os.getuid()) or st.st_mode&0o022 or hashlib.sha256(path.read_bytes()).hexdigest()!=c['source_hashes'][name]:
            raise ValueError('installed source integrity mismatch')
    policy=Policy(**c['policy'])
    if policy.chain!=84532:raise ValueError('Base Sepolia only')
    primary=HTTPSReadRPC(c['rpc']['primary'],approved_origins=c['rpc']['approved_origins'])
    witness=HTTPSReadRPC(c['rpc']['witness'],approved_origins=c['rpc']['approved_origins']) if c['rpc']['witness'] else None
    if witness is not None and witness.endpoint==primary.endpoint:raise ValueError('duplicate witness is not independence')
    provider=AuthenticatedSnapshots(primary,policy,c['code_pins'],witness=witness,proxy_bindings=c['proxy_bindings'])
    reader=CanonicalReader(provider,policy,clock)
    ledger=Ledger(c['ledger_path'],policy,reader)  # never silently initializes or resets
    try:
        service=DeskSnapshots(provider,c['desk'],c['officer'])
        bindings=ReplyBindings(ledger,c['desk'],c['officer'],service,c['approved_messages'])
        journal=PendingJournal(bindings,provider)
        verifier=NodeSignatureVerifier(root/'signed-validator/bridge.cjs')
        def code_probe():
            n=provider.head()-policy.confirmations+1
            provider._pins(provider.block_hash(n))
            # Complete inventory/budget wiring probe is a REQUIRED installed
            # dependency, not a manifest boolean or a request-controlled claim.
            return inventory_probe is not None and inventory_probe() is True
        guard=InstalledReleaseGuard(c['release_path'],c['release_sha256'],source_revision=c['source_revision'],
             code_pins=c['code_pins'],clock=clock,code_probe=code_probe,lease_probe=lease_probe or (lambda:False))
        signer=InheritedFDSigner(key_fd,root/'signed-validator/sign-fd.cjs') if key_fd is not None else None
        sender=HTTPSBroadcast(primary,guard)
        submitter=SubmissionCoordinator(bindings,journal,verifier,clock=clock,fee_limits=c['fees'],signer=signer,sender=sender,release_guard=guard)
        boundary=LocalBoundary(bindings,journal,verifier,consent_uid=c['consent_uid'],executor_uid=c['executor_uid'],
                  fee_limits=c['fees'],clock=clock,submitter=submitter)  # external signed staging remains disabled
        return boundary,c,ledger
    except BaseException:
        ledger.close();raise


def main():
    import argparse
    import signal
    parser=argparse.ArgumentParser(description='Start the read/consent boundary with broadcast CLOSED; retained supervisor integrates submission ports separately.')
    parser.add_argument('--config',required=True);parser.add_argument('--config-sha256',required=True)
    args=parser.parse_args();boundary,c,ledger=assemble(args.config,args.config_sha256)
    stopped=[False]
    def stop(*_):stopped[0]=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    try:serve_unix(boundary,c['socket_path'],socket_group=c['socket_group'],stop=lambda:stopped[0])
    finally:ledger.close()


if __name__=='__main__':main()
