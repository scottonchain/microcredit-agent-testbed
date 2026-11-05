"""Offline regressions; all chain/provider values below are synthetic."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from metrics import lending_dashboard as ld
from metrics.test_lending_dashboard import synthetic_events, synthetic_terms, block_time

POOL = '0x' + '11' * 20
TOKEN = '0x' + '22' * 20
DEPLOYMENT = dict(chain_id=84532, pool=POOL, lens=POOL, network='base-sepolia',
                  token={'address': TOKEN}, explorer_url='https://sepolia.basescan.org')


def fixture():
    events = synthetic_events()
    records = {}
    for i, terms in synthetic_terms().items():
        request = next(e['args'] for e in events if e['event'] == 'LoanRequested' and e['args']['loanId'] == i)
        status, term, req, disb, due = terms
        records[i] = [request['amount'], 10_100_000 if i == 1 else 0, 10_000_000 if i == 1 else 0,
                      request['borrower'], 933, term, req, disb, status, 0]
    # Default: 15 principal written off, 5 reserve recovered; loan 2 has 5 principal repaid first.
    records[2][1:3] = [5_000_000, 5_000_000]
    for name, args in [('RepaymentApplied', dict(interest=0, principal=5_000_000, fee=0)),
                       ('LoanRepaid', dict(borrower=records[2][3], amount=5_000_000))]:
        events.append(dict(event=name, args=dict(loanId=2, **args), block=125, logIndex=len(events), tx='0x125', address=POOL))
    events.append(dict(event='ReserveFunded', args=dict(amount=5_000_000), block=100, logIndex=2, tx='0x100', address=POOL))
    events.sort(key=lambda e: (e['block'], e['logIndex']))
    pool = {k: 0 for k in ld.POOL_FIELDS}
    pool.update(totalAssets=90_055_000, lenderCash=78_100_000, totalLentOut=12_000_000,
                totalShares=1, totalStaked=5_000_000, firstLossReserve=45_000, totalDuesPaid=45_000)
    return events, records, pool


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.events, self.records, self.pool = fixture()

    def reconcile(self):
        times = {e['block']: block_time(e['block']) for e in self.events}
        loans = ld.build_loans(self.events, times, synthetic_terms())
        ld.reconcile(self.events, loans, self.records, self.pool)

    def test_complete_synthetic_ledger(self):
        self.reconcile()

    def test_missing_each_financial_event_fails(self):
        original = copy.deepcopy(self.events)
        for index, e in enumerate(original):
            if e['event'] not in ('Deposited', 'Staked', 'LoanRequested', 'LoanDisbursed',
                                  'LoanRepaid', 'RepaymentApplied', 'LoanDefaulted', 'ReserveFunded'):
                continue
            with self.subTest(event=e['event'], index=index):
                self.events = original[:index] + original[index+1:]
                with self.assertRaises(ld.RpcError):
                    self.reconcile()

    def test_empty_logs_with_actual_inventory_fails(self):
        with self.assertRaises(ld.RpcError):
            ld.reconcile([], [], self.records, self.pool)

    def test_wrong_borrower_amount_time_and_paid_state_fail(self):
        original = copy.deepcopy(self.records)
        for field, value in [(0, 99), (1, 99), (2, 99), (3, POOL), (4, 99), (6, 99), (7, 99)]:
            with self.subTest(field=field):
                self.records = copy.deepcopy(original)
                self.records[1][field] = value
                with self.assertRaises(ld.RpcError):
                    self.reconcile()

    def test_pool_stock_mismatches_fail(self):
        original = self.pool.copy()
        for name in ('totalAssets', 'totalLentOut', 'reservedLiquidity', 'totalImpaired',
                     'lenderCash', 'totalShares', 'totalStaked', 'firstLossReserve'):
            with self.subTest(name=name):
                self.pool = original.copy()
                self.pool[name] += 1
                with self.assertRaises(ld.RpcError):
                    self.reconcile()

    def test_forgiven_dust_holds_instead_of_guessing_reserve(self):
        self.records[1][0] += 1
        for e in self.events:
            if e['event'] in ('LoanRequested', 'LoanDisbursed') and e['args'].get('loanId') == 1:
                e['args']['amount'] += 1
        with self.assertRaises(ld.RpcError): self.reconcile()

    def test_profile_ingestion_never_calls_provider(self):
        bomb = unittest.mock.Mock()
        bomb.logs.side_effect = AssertionError('profile fetch')
        bomb.call.side_effect = AssertionError('profile fetch')
        for schema in ({'registered': True}, {'registered': False}, {'uid': 'malformed'}):
            self.assertEqual(ld.read_attestations(bomb, bomb, 1, 0, POOL, schema), [])
        bomb.logs.assert_not_called(); bomb.call.assert_not_called()


class Provider:
    def __init__(self):
        self.chain = 84532
        self.hash = '0x' + 'ab' * 32
        self.calls = 0
        self.url = 'fake://'
        self.ids = []
        self.finalized = ld.DEPLOYMENT_BLOCK + 100
        self.pool = {name: 0 for name in ld.POOL_FIELDS}
    def request(self, method, params):
        assert method == 'eth_chainId'
        return hex(self.chain)
    def block(self, n):
        n = self.finalized if n == 'finalized' else n
        return dict(number=hex(n), hash=self.hash, timestamp=hex(block_time(n)))
    def call(self, to, sig, *args, **kw):
        if sig == 'usdc()': return [TOKEN]
        if sig == 'getAllLoanIds()': return [self.ids]
        if sig in ('getLenders()', 'getBorrowers()'): return [[]]
        return [self.pool.get(sig[:-2], 0)]
    def logs(self, *args, **kwargs): return []


class CollectionTests(unittest.TestCase):
    def setUp(self): self.state, self.logs = Provider(), Provider()
    def collect(self, **kwargs): return ld.collect(DEPLOYMENT, self.state, self.logs, **kwargs)
    def test_empty_inventory_and_zero_pool_is_valid(self):
        report = self.collect()
        self.assertEqual(report['snapshot']['verification'], 'reconciled-finalized-v1')
        self.assertTrue(report['snapshot']['collectedAt'])
        self.assertEqual(report['profiles'], [])
    def test_inventory_one_empty_history_fails(self):
        self.state.ids = [1]
        with self.assertRaisesRegex(ld.RpcError, 'inventory'): self.collect()
    def test_either_wrong_chain_fails(self):
        for provider in (self.state, self.logs):
            provider.chain = 1
            with self.assertRaises(ld.RpcError): self.collect()
            provider.chain = 84532
    def test_boundary_mismatch_fails(self):
        self.logs.hash = '0x' + 'cd' * 32
        with self.assertRaises(ld.RpcError): self.collect()
    def test_final_hash_change_on_either_provider_fails(self):
        for provider in (self.state, self.logs):
            original = provider.block
            def changed(n):
                result = original(n)
                if self.state.calls: result['hash'] = '0x' + 'cd' * 32
                return result
            with patch.object(provider, 'block', side_effect=changed), patch.object(self.logs, 'logs', side_effect=lambda *a: setattr(self.state, 'calls', 1) or []):
                with self.assertRaises(ld.RpcError): self.collect()
            self.state.calls = 0
    def test_incomplete_start_or_unfinalized_block_fails(self):
        for kwargs in ({'from_block': ld.DEPLOYMENT_BLOCK + 1}, {'block': self.state.finalized + 1}):
            with self.assertRaises(ld.RpcError): self.collect(**kwargs)
    def test_unchanged_ledger_gets_new_success_time(self):
        a, b = self.collect(), self.collect()
        self.assertEqual(a['loans'], b['loans'])
        self.assertEqual(a['snapshot']['blockHash'], b['snapshot']['blockHash'])
        self.assertNotEqual(a['snapshot']['collectedAt'], b['snapshot']['collectedAt'])
    def test_failure_preserves_snapshot_and_records_only_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            ld.write_outputs(self.collect(), p)
            before = {name: (p / name).read_bytes() for name in ('snapshot.js', 'snapshot.json')}
            with patch.object(ld, 'load_deployment', return_value=DEPLOYMENT), patch.object(ld, 'collect', side_effect=ld.RpcError('private provider error')):
                self.assertEqual(ld.main(['--out', d]), 1)
            for name, data in before.items(): self.assertEqual((p / name).read_bytes(), data)
            status = json.loads((p / 'refresh-status.json').read_text())
            self.assertEqual(status['status'], 'failed')
            self.assertNotIn('private', str(status))
    def test_profile_publication_rejected(self):
        report = self.collect(); report['profiles'] = [{'country': 'private'}]
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            ld.write_outputs(report, Path(d))


class LogTests(unittest.TestCase):
    def raw(self):
        ev = ld.parse_event('ReserveFunded(address indexed from,uint256 amount)')
        return dict(address=POOL, topics=[ev['topic'], '0x' + '0' * 64], data='0x' + format(1, '064x'),
                    blockNumber='0xa', logIndex='0x1', transactionHash='0x'+'ab'*32, blockHash='0x'+'cd'*32)
    def read(self, logs):
        rpc = unittest.mock.Mock(); rpc.logs.return_value = logs
        return ld.read_pool_logs(rpc, POOL, 0, 10)
    def test_duplicates_count_once(self):
        log = self.raw(); self.assertEqual(len(self.read([log, log.copy()])), 1)
    def test_conflicting_duplicate_fails(self):
        log = self.raw()
        with self.assertRaises(ld.RpcError): self.read([log, dict(log, data='0x'+'0'*64)])
    def test_wrong_address_range_or_removed_fails(self):
        for changes in ({'address': TOKEN}, {'blockNumber': '0xb'}, {'removed': True}):
            with self.subTest(changes=changes), self.assertRaises(ld.RpcError): self.read([dict(self.raw(), **changes)])

class FullProvider(Provider):
    """Only implements real deployed public getters; rejects invented selectors."""
    def __init__(self):
        super().__init__()
        self.events, self.records, self.pool = fixture()
        self.ids = list(self.records)
        self.finalized = ld.DEPLOYMENT_BLOCK + 200
    def block(self, n):
        n = self.finalized if n == 'finalized' else n
        return dict(number=hex(n), hash=self.hash, timestamp=hex(block_time(n - ld.DEPLOYMENT_BLOCK)))
    def call(self, to, sig, *args, **kw):
        if sig == 'getLoan(uint256)':
            r = self.records[args[0]]
            return [r[0], r[0]-r[1] if r[8] in (1,2) else 0, r[3], r[4], r[8] in (1,2)]
        if sig == 'getLoanTerms(uint256)': return synthetic_terms()[args[0]]
        if sig in ('sharePrice()', 'getUtilisation()'): return [0]
        if sig in {k+'()' for k in ld.POOL_FIELDS} or sig in ('usdc()', 'getAllLoanIds()', 'getLenders()', 'getBorrowers()'):
            return super().call(to, sig, *args, **kw)
        raise AssertionError('not a deployed getter: ' + sig)
    def logs(self, *args, **kw):
        specs = {ld.parse_event(s)['name']: ld.parse_event(s) for s in ld.POOL_EVENTS}
        result = []
        for e in self.events:
            spec = specs[e['event']]
            values = dict(e['args']); values.setdefault('from', TOKEN)
            topics = [spec['topic']] + ['0x'+ld.encode_word(p['type'],values[p['name']]) for p in spec['params'] if p['indexed']]
            data = '0x' + ''.join(ld.encode_word(p['type'],values[p['name']]) for p in spec['params'] if not p['indexed'])
            result.append(dict(address=POOL, topics=topics, data=data, blockNumber=hex(ld.DEPLOYMENT_BLOCK+e['block']),
                               logIndex=hex(e['logIndex']), transactionHash='0x'+format(e['block'],'064x'), blockHash=self.hash))
        return result


class EndToEndCollectionTests(unittest.TestCase):
    def test_nonempty_full_collection_actual_public_abi(self):
        result = ld.collect(DEPLOYMENT, FullProvider(), FullProvider())
        self.assertEqual(len(result['loans']), 3)
        self.assertEqual(result['pool']['totalAssets'], 90_055_000)
        self.assertEqual(result['flows']['interest'], 100_000)
    def test_missing_repayment_fails_full_collection(self):
        logs = FullProvider()
        logs.events = [e for e in logs.events if not (e['block'] == 125)]
        with self.assertRaises(ld.RpcError): ld.collect(DEPLOYMENT, FullProvider(), logs)
    def test_wrong_event_block_hash_fails(self):
        logs = FullProvider()
        original = logs.logs
        with patch.object(logs, 'logs', side_effect=lambda *a: [dict(e, blockHash='0x'+'ee'*32) for e in original()]):
            with self.assertRaises(ld.RpcError): ld.collect(DEPLOYMENT, FullProvider(), logs)
    def test_meta_repayment_normalizes_once(self):
        logs = FullProvider()
        for e in logs.events:
            if e['event'] == 'LoanRepaid': e['event'] = 'MetaLoanRepaid'
        result = ld.collect(DEPLOYMENT, FullProvider(), logs)
        self.assertEqual(result['flows']['repaid'], 15_100_000)
