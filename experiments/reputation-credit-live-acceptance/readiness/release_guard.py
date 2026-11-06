"""Pinned owner-installed release decision plus fresh runtime probes.
No manifest is installed here. An approval file is never accepted from IPC.
The trusted runtime owner/supervisor must provision the exact reviewed hash;
root/service compromise is outside this local isolation boundary.
"""
import hashlib
import os
from pathlib import Path
import stat
from authenticated_reader import strict_json


class InstalledReleaseGuard:
    def __init__(self,path,expected_sha256,*,source_revision,code_pins,clock,code_probe,lease_probe):
        self.path=Path(path);self.digest=expected_sha256;self.revision=source_revision
        self.pins=dict(code_pins);self.clock,self.code_probe,self.lease_probe=clock,code_probe,lease_probe
    def __call__(self):
        try:
            # No following symlinks; inspect the SAME opened object read below.
            fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,'rb') as handle:
                st=os.fstat(handle.fileno())
                if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode&0o077:return False
                raw=handle.read(32769)
            if len(raw)>32768 or hashlib.sha256(raw).hexdigest()!=self.digest:return False
            m=strict_json(raw);now=self.clock()
            keys={'schema','enabled','chain_id','source_revision','code_pins','issued_at','expires_at',
                  'drain_receipt','wallet_review_receipt','service_review_receipt'}
            if not isinstance(m,dict) or set(m)!=keys:return False
            if (type(m['schema']) is not int or m['schema']!=1 or m['enabled'] is not True or
                type(m['chain_id']) is not int or m['chain_id']!=84532 or m['source_revision']!=self.revision or
                m['code_pins']!=self.pins or type(now) is not int or type(m['issued_at']) is not int or
                type(m['expires_at']) is not int or not m['issued_at']<=now<m['expires_at']):return False
            for key in ('drain_receipt','wallet_review_receipt','service_review_receipt'):
                if not isinstance(m[key],str) or not m[key].startswith('https://github.com/scottonchain/'):return False
            # Receipt URLs are reviewed references, not proof fetched here.
            # Probes must check actual current code/proxy/budget wiring and
            # authoritative drain/lease/single-writer state; no cached True flag.
            return self.code_probe() is True and self.lease_probe() is True
        except Exception:return False
