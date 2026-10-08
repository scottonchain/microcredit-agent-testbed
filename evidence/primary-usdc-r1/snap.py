#!/usr/bin/env python3
"""PRIMARY-USDC-RESUME-20261008-r1: read-only full-state + first approval preflight on Base Sepolia.
No signing, no broadcast. Counts every RPC request."""
import json, urllib.request, time, datetime, hashlib, sys
sys.path.insert(0, '/root/work/c46')
R = 'https://sepolia.base.org'
H = json.load(open('/root/work/c46/handoff.json'))
POOL = H['chain']['contracts']['pool']; USDC = H['chain']['contracts']['usdc']; PROV = H['chain']['contracts']['provider']
WM = H['requiredReads']['actors']['walletMap']
HERMES = H['requiredReads']['hermes']['address']
AVERY = H['requiredReads']['provider']['averyAddress']
N = 0
LOG = []
def rpc(m, p):
    global N
    N += 1
    req = urllib.request.Request(R, data=json.dumps({"jsonrpc": "2.0", "id": N, "method": m, "params": p}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=10))
    except Exception as e:
        return {'error': 'EXC ' + str(e)[:120]}
    return r
SEL = {}
import subprocess, os
CAST = '/root/.foundry/versions/foundry-rs/foundry/v1.8.4/cast'
def sel(sig):
    if sig not in SEL:
        SEL[sig] = subprocess.run([CAST, 'sig', sig], capture_output=True, text=True).stdout.strip()
    return SEL[sig]
def a32(a): return '0' * 24 + a[2:].lower()
BLK = None
def call(to, sig, *args):
    data = sel(sig) + ''.join(a32(a) if isinstance(a, str) else '%064x' % a for a in args)
    r = rpc('eth_call', [{'to': to, 'data': data}, BLK])
    if 'result' in r: return r['result']
    return 'ERR ' + json.dumps(r.get('error'))[:150]
def u(h):
    try: return int(h, 16)
    except Exception: return h
def words(h):
    h = h[2:]
    return [h[i:i + 64] for i in range(0, len(h), 64)]

t0 = time.time()
obs = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
out = {'observedAtStart': obs, 'rpc': R}
cid = rpc('eth_chainId', [])['result']; out['chainId'] = int(cid, 16)
b = rpc('eth_getBlockByNumber', ['latest', False])['result']
BLK = b['number']
out['block'] = {'number': int(BLK, 16), 'hash': b['hash'], 'timestamp': int(b['timestamp'], 16),
                'timestampIso': datetime.datetime.fromtimestamp(int(b['timestamp'], 16), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'baseFeePerGas': int(b.get('baseFeePerGas', '0x0'), 16)}
# runtime code
rt = {}
for k, a in (('pool', POOL), ('provider', PROV), ('usdc', USDC)):
    c = rpc('eth_getCode', [a, BLK])['result']
    from_k = subprocess.run([CAST, 'keccak', c], capture_output=True, text=True).stdout.strip()
    rt[k] = {'address': a, 'keccak': from_k, 'expected': H['chain']['runtimeKeccakExpected'][k], 'match': from_k == H['chain']['runtimeKeccakExpected'][k], 'codeBytes': (len(c) - 2) // 2}
out['runtime'] = rt
actors = {}
for role, a in WM.items():
    d = {'address': a}
    d['ethWei'] = str(u(rpc('eth_getBalance', [a, BLK])['result']))
    d['nonceLatest'] = u(rpc('eth_getTransactionCount', [a, 'latest'])['result'])
    d['noncePending'] = u(rpc('eth_getTransactionCount', [a, 'pending'])['result'])
    d['usdcUnits'] = str(u(call(USDC, 'balanceOf(address)', a)))
    d['allowanceUnits'] = str(u(call(USDC, 'allowance(address,address)', a, POOL)))
    d['poolShares'] = str(u(call(POOL, 'sharesOf(address)', a)))
    d['lenderBalanceUnits'] = str(u(call(POOL, 'lenderBalance(address)', a)))
    d['activeLoanCount'] = str(u(call(POOL, 'activeLoanCount(address)', a)))
    d['grantedCreditUnits'] = str(u(call(POOL, 'grantedCredit(address)', a)))
    d['duesPaidUnits'] = str(u(call(POOL, 'duesPaid(address)', a)))
    d['creditCommittedUnits'] = str(u(call(POOL, 'creditCommitted(address)', a)))
    d['providerBudgetHeldScore'] = str(u(call(PROV, 'budgetHeld(address)', a)))
    bl = call(POOL, 'getBorrowLimit(address)', a)
    d['getBorrowLimit_raw'] = [str(int(w, 16)) for w in words(bl)] if bl.startswith('0x') else bl
    d['availableCreditUnits'] = d['getBorrowLimit_raw'][1] if isinstance(d['getBorrowLimit_raw'], list) and len(d['getBorrowLimit_raw']) > 1 else None
    actors[role] = d
out['actors'] = actors
# getScores
gs = call(PROV, 'getScores()')
sc = {}
if gs.startswith('0x'):
    w = words(gs)
    # (address[] , uint256[]): offsets
    o1 = int(w[0], 16) // 32; o2 = int(w[1], 16) // 32
    n1 = int(w[o1], 16); addrs = ['0x' + w[o1 + 1 + i][-40:] for i in range(n1)]
    n2 = int(w[o2], 16); vals = [int(w[o2 + 1 + i], 16) for i in range(n2)]
    sc = {a: v for a, v in zip(addrs, vals)}
out['providerScoresRaw'] = sc if gs.startswith('0x') else gs
for role, d in actors.items():
    d['providerScore'] = str(sc.get(d['address'].lower(), 0)) if gs.startswith('0x') else None
out['avery'] = {'address': AVERY, 'rawScore': str(sc.get(AVERY.lower(), 0)), 'budgetHeld': str(u(call(PROV, 'budgetHeld(address)', AVERY))),
                'creditScore': call(PROV, 'creditScore(address)', AVERY)}
# pool
pool = {}
for name, sig in [('paused', 'paused()'), ('token', 'usdc()'), ('scoreProvider', 'scoreProvider()'), ('maxLoanUnits', 'maxLoanAmount()'), ('aprBps', 'getLoanRate()'),
                  ('reserveBps', 'reserveBps()'), ('assetsUnits', 'totalAssets()'), ('cashUnits', 'lenderCash()'), ('totalShares', 'totalShares()'),
                  ('lentUnits', 'totalLentOut()'), ('reservedUnits', 'reservedLiquidity()'), ('queueUnits', 'totalQueuedWithdrawals()'),
                  ('firstLossReserveUnits', 'firstLossReserve()'), ('duesPaidUnits', 'totalDuesPaid()'), ('impairedUnits', 'totalImpaired()'),
                  ('feesUnits', 'protocolFees()'), ('owner', 'owner()'), ('oracle', 'oracle()'), ('guardian', 'guardian()'), ('protocolFeeBps', 'protocolFeeBps()'),
                  ('totalUnclaimedPayouts', 'totalUnclaimedPayouts()'), ('totalQueuedShares', 'totalQueuedShares()')]:
    v = call(POOL, sig)
    pool[name] = v if not v.startswith('0x') else (('0x' + v[-40:]) if name in ('token', 'scoreProvider', 'owner', 'oracle', 'guardian') else str(int(v, 16)))
pool['tokenBalanceUnits'] = str(u(call(USDC, 'balanceOf(address)', POOL)))
pool['stakeOf'] = {r: str(u(call(POOL, 'stakeOf(address)', a))) for r, a in WM.items()}
pool['stakeCommitted'] = {r: str(u(call(POOL, 'stakeCommitted(address)', a))) for r, a in WM.items()}
pool['creditLoss'] = {r: str(u(call(POOL, 'creditLoss(address)', a))) for r, a in WM.items()}
ids = call(POOL, 'getAllLoanIds()'); lend = call(POOL, 'getLenders()')
def arr(h):
    if not h.startswith('0x'): return h
    w = words(h); n = int(w[1], 16); return ['0x' + x[-40:] if False else x for x in w[2:2 + n]]
lid = arr(ids); pool['getAllLoanIds'] = [str(int(x, 16)) for x in lid] if isinstance(lid, list) else lid
ll = arr(lend); pool['getLenders'] = ['0x' + x[-40:] for x in ll] if isinstance(ll, list) else ll
out['pool'] = pool
# hermes
out['hermes'] = {'address': HERMES, 'poolShares': str(u(call(POOL, 'sharesOf(address)', HERMES))), 'lenderBalanceUnits': str(u(call(POOL, 'lenderBalance(address)', HERMES))),
                 'usdcUnits': str(u(call(USDC, 'balanceOf(address)', HERMES))), 'ethWei': str(u(rpc('eth_getBalance', [HERMES, BLK])['result'])),
                 'nonceLatest': u(rpc('eth_getTransactionCount', [HERMES, 'latest'])['result']), 'noncePending': u(rpc('eth_getTransactionCount', [HERMES, 'pending'])['result'])}
# provider
prov = {}
for name, sig in [('fresh', 'isFresh()'), ('owner', 'owner()'), ('reporter', 'reporter()'), ('lending', 'lending()'), ('epoch', 'epoch()'), ('lastReportAt', 'lastReportAt()'),
                  ('maxScoreAge', 'maxScoreAge()'), ('maxTotalScore', 'maxTotalScore()'), ('maxIncreasePerReport', 'maxIncreasePerReport()'), ('totalScore', 'totalScore()'), ('totalHeld', 'totalHeld()')]:
    v = call(PROV, sig)
    prov[name] = v if not v.startswith('0x') else (('0x' + v[-40:]) if name in ('owner', 'reporter', 'lending') else str(int(v, 16)))
out['providerState'] = prov
# approval preflight
F = H['exactSmallestOperation']
tx = {'from': F['from'], 'to': F['to'], 'value': '0x0', 'data': F['data']}
out['approval'] = {'tx': tx}
r = rpc('eth_call', [tx, BLK]); out['approval']['eth_call'] = r.get('result', r.get('error'))
out['approval']['eth_call_required'] = H['requiredReads']['actors'] and '0x' + '0' * 63 + '1'
r = rpc('eth_estimateGas', [tx, BLK]); out['approval']['estimateGas'] = u(r['result']) if 'result' in r else r.get('error')
gp = rpc('eth_gasPrice', []); out['approval']['gasPriceWei'] = u(gp['result']) if 'result' in gp else gp.get('error')
out['approval']['pendingNonce'] = actors['s1-funder']['noncePending']
out['approval']['ethWei'] = actors['s1-funder']['ethWei']
# ledger
tot = sum(int(a['usdcUnits']) for a in actors.values()) + int(pool['tokenBalanceUnits'])
out['ledger'] = {'rootWalletUsdcUnits': str(sum(int(a['usdcUnits']) for a in actors.values())), 'poolTokenBalanceUnits': pool['tokenBalanceUnits'], 'aggregateUnits': str(tot), 'expectedAggregate': '35000000'}
out['rpcRequests'] = N
out['elapsedSeconds'] = round(time.time() - t0, 1)
out['observedAtEnd'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
json.dump(out, open('/root/work/c46/snapshot.json', 'w'), indent=1, sort_keys=True)
print(json.dumps({k: out[k] for k in ('block', 'runtime', 'ledger', 'rpcRequests', 'elapsedSeconds', 'observedAtEnd')}, indent=1))
print(json.dumps(out['approval'], indent=1)); print(json.dumps(out['pool'], indent=0)[:2500]); print(json.dumps(out['providerState'])); print(json.dumps(out['hermes']))
for r, a in actors.items(): print(r, a['usdcUnits'], a['ethWei'], a['nonceLatest'], a['noncePending'], a['allowanceUnits'], a['poolShares'], a['activeLoanCount'], a['grantedCreditUnits'], a['providerScore'], a['availableCreditUnits'])
