"""Read one LOCAL EVM RPC tape from stdin; no network or credentials."""
import copy
import hashlib
import json
import sys
from authenticated_reader import AuthenticatedSnapshots
from durable import Policy
from runtime_inventory import CanonicalInventory,digest


def replay(tape):
    class Port:
        def call(self,method,params):
            key=json.dumps([method,params],sort_keys=True,separators=(',',':'))
            if key not in tape['responses']:raise ValueError('unexpected RPC request')
            return copy.deepcopy(tape['responses'][key])
    p=Policy(31337,tape['pool'],tape['token'],'100','20','40','100','20','40',confirmations=1)
    provider=AuthenticatedSnapshots(Port(),p,tape['pins'])
    return CanonicalInventory(provider,tape['budget'],[tape['borrower']]).snapshot()

if __name__=='__main__':
    tape=json.load(sys.stdin);s=replay(tape)
    if tape.get('snapshot_only') is True:
        print(json.dumps({'digest':digest(s['state']),'state':s['state']}));sys.exit(0)
    assert s['state']['budget']['totalUsed']==5_000_000
    assert s['state']['loans']['1']['open']==0
    assert s['state']['lent']==s['state']['reserved']==0
    # Canonical acquisition must reject a registry omitting an existing borrower.
    bad=copy.deepcopy(tape);bad['borrower']='0x'+'f'*40
    try:replay(bad)
    except ValueError:pass
    else:raise AssertionError('unknown borrower accepted')
    # Mutate actual ABI responses, not a second invented inventory model.
    for selector in ('0xb2e2c75f','0x5c1bf865','0x0634612f'):
        bad=copy.deepcopy(tape)
        key=next(k for k in bad['responses'] if selector in k)
        bad['responses'][key]='0x'+'0'*64
        try:replay(bad)
        except ValueError:pass
        else:raise AssertionError('malformed/inconsistent ABI accepted: '+selector)
    print(json.dumps({'inventory_digest':digest(s['state']),'block':s['block'],'hash':s['hash'],'unknown_borrower_rejected':True}))
