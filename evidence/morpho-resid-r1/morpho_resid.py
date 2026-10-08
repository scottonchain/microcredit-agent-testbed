#!/usr/bin/env python3
"""ETH-USDC-MORPHO-20261008-residual-read: read-only, <=30 RPC, no retries. Position+market+oracle at one fixed Base block for each unique borrower in r15 morpho_logs.json."""
import json, urllib.request, subprocess, datetime
CAST = '/root/.foundry/versions/foundry-rs/foundry/v1.8.4/cast'
URL = 'https://base-rpc.publicnode.com'
BLUE = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb'
L = json.load(open('/root/work/tb_ptv5_r1/evidence/ptv5-r15/morpho_logs.json'))
N = 0; LOG = []
def rpc(m, p):
    global N
    N += 1
    if N > 30: raise SystemExit('budget')
    req = urllib.request.Request(URL, data=json.dumps({"jsonrpc": "2.0", "id": N, "method": m, "params": p}).encode(), headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
    try: r = json.load(urllib.request.urlopen(req, timeout=15))
    except Exception as e: r = {'error': 'EXC ' + str(e)[:100]}
    LOG.append({'m': m, 'p': p, 'r': r}); return r
def sig(s): return subprocess.run([CAST, 'sig', s], capture_output=True, text=True).stdout.strip()
def words(h): h = h[2:]; return [int(h[i:i+64], 16) for i in range(0, len(h), 64)]
def call(to, data, blk): 
    r = rpc('eth_call', [{'to': to, 'data': data}, blk]); return r.get('result') or ('ERR ' + json.dumps(r.get('error')))
# unique (market, borrower) pairs, last 10 logs
pairs = []
for l in L['logs']:
    k = (l['marketId'], l['borrower'])
    if k not in pairs: pairs.append(k)
head = rpc('eth_getBlockByNumber', ['latest', False])['result']
blk = head['number']
out = {'block': int(blk, 16), 'hash': head['hash'], 'timestamp': int(head['timestamp'], 16), 'observedAt': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'pairs': len(pairs)}
mk = {}
for mid in sorted({p[0] for p in pairs}):
    prm = words(call(BLUE, sig('idToMarketParams(bytes32)') + mid[2:], blk))
    mkt = words(call(BLUE, sig('market(bytes32)') + mid[2:], blk))
    oracle = '0x' + hex(prm[2])[2:].zfill(40)
    pr = call(oracle, sig('price()'), blk)
    mk[mid] = {'loan': '0x%040x' % prm[0], 'coll': '0x%040x' % prm[1], 'oracle': oracle, 'lltv': prm[4], 'totalBorrowAssets': mkt[2], 'totalBorrowShares': mkt[3], 'lastUpdate': mkt[4], 'price': int(pr, 16) if pr.startswith('0x') else pr}
out['markets'] = mk
res = []
for mid, u in pairs:
    pos = words(call(BLUE, sig('position(bytes32,address)') + mid[2:] + '0' * 24 + u[2:], blk))
    m = mk[mid]; bs, coll = pos[1], pos[2]
    row = {'market': mid, 'borrower': u, 'borrowShares': bs, 'collateral': coll}
    if bs and isinstance(m['price'], int):
        debt = (bs * (m['totalBorrowAssets'] + 1) + (m['totalBorrowShares'] + 10**6) - 1) // (m['totalBorrowShares'] + 10**6)  # stored (not accrued), rounded up
        maxb = coll * m['price'] // 10**36 * m['lltv'] // 10**18
        row.update({'debtAssetsStoredRoundUp': debt, 'maxBorrow': maxb, 'unhealthyStored': debt > maxb})
    else:
        row['empty'] = (bs == 0)
    res.append(row)
out['positions'] = res
out['rpcCount'] = N
out['summary'] = {'checked': len(res), 'empty': sum(1 for r in res if r.get('empty')), 'healthy': sum(1 for r in res if r.get('unhealthyStored') is False), 'unhealthy': sum(1 for r in res if r.get('unhealthyStored'))}
json.dump(out, open('/root/work/c46/morpho_resid.json', 'w'), indent=1)
json.dump(LOG, open('/root/work/c46/morpho_resid_raw.json', 'w'))
print(json.dumps(out, indent=1)[:5000])
