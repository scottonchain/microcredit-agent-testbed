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

class AccountingProvider(FullProvider):
    """Hand-specified 1812e7d accounting, exposed ONLY through public getters.

    No cumulative repayment or principalRepaid getter is provided. FullProvider's
    old populated records are useful unit oracles, not production observations.
    """
    borrower = '0x' + 'aa' * 20
    backer = '0x' + 'cc' * 20
    day = 86400
    epoch = 1_700_000_000

    def __init__(self, principal=10_000_000, rate=1000, final_days=2):
        Provider.__init__(self)
        self.ids = [1]
        self.principal, self.rate = principal, rate
        self.status, self.term = 2, 365 * self.day
        self.finalized = ld.DEPLOYMENT_BLOCK + 200
        self.final_days = final_days
        # Expected public outstanding is set explicitly by each repayment fixture.
        self.outstanding = principal + (principal * rate // 10000) * final_days // 365
        self.events = []
        self.add('Deposited', 100, lender=self.backer, assets=100_000_000, shares=100_000_000_000_000)
        self.add('ReserveFunded', 100, amount=10_000_000)
        self.add('Staked', 100, account=self.backer, amount=10_000_000)
        self.add('LoanRequested', 110, borrower=self.borrower, loanId=1, amount=principal, interestRate=rate)
        self.add('LoanDisbursed', 111, borrower=self.borrower, loanId=1, to=self.borrower, amount=principal)
        self.pool.update(totalAssets=100_000_000, lenderCash=110_000_000-principal,
                         totalLentOut=principal, totalShares=100_000_000_000_000,
                         totalStaked=10_000_000, firstLossReserve=10_000_000)

    def add(self, name, block, **args):
        self.events.append(dict(event=name, block=block, logIndex=len(self.events),
                                tx='0x'+format(block,'064x'), address=POOL, args=args))

    def timestamp(self, n):
        elapsed = {100: -2, 110: -1, 111: 0, 120: 2*self.day,
                   121: 31*self.day, 122: 32*self.day, 130: 61*self.day,
                   200: self.final_days*self.day}[n]
        return self.epoch + elapsed

    def block(self, n):
        n = self.finalized if n == 'finalized' else n
        offset = n - ld.DEPLOYMENT_BLOCK
        # Deployment boundary precedes the first event.
        ts = self.epoch - 100 if offset == 0 else self.timestamp(offset)
        return dict(number=hex(n), hash=self.hash, timestamp=hex(ts))

    def call(self, to, sig, *args, **kw):
        if sig == 'getLoan(uint256)':
            return [self.principal, self.outstanding, self.borrower, self.rate, self.status in (1,2)]
        if sig == 'getLoanTerms(uint256)':
            return [self.status, self.term, self.epoch-1, self.epoch, self.epoch+self.term]
        if sig in ('sharePrice()', 'getUtilisation()'): return [0]
        if sig in {k+'()' for k in ld.POOL_FIELDS} or sig in ('usdc()', 'getAllLoanIds()', 'getLenders()', 'getBorrowers()'):
            return Provider.call(self, to, sig, *args, **kw)
        raise AssertionError('unavailable public getter: '+sig)


class AccountingAndTrustBoundaryTests(unittest.TestCase):
    def collect(self, p, logs=None):
        return ld.collect(DEPLOYMENT, p, copy.deepcopy(p) if logs is None else logs)

    def test_nonzero_fee_and_reserve_allocation(self):
        p = AccountingProvider()
        # 10 USDC, 10% APR, 2 days: floor(1_000_000 * 2 / 365) = 5479.
        # Fee 10% = 547; reserve 45% = 2465; 2 USDC principal repaid.
        p.add('RepaymentApplied', 120, loanId=1, interest=5479, principal=2_000_000, fee=547)
        p.add('LoanRepaid', 120, loanId=1, borrower=p.borrower, amount=2_005_479)
        p.outstanding = 8_000_000
        p.pool.update(lenderCash=102_004_932, totalLentOut=8_000_000,
                      protocolFees=547, totalDuesPaid=2465, firstLossReserve=10_002_465,
                      totalAssets=100_002_467)
        s = self.collect(p)
        self.assertEqual(s['flows']['fees'], 547)
        self.assertEqual(s['flows']['interest'], 5479)
        self.assertEqual(s['pool']['totalAssets']-100_000_000, 2467)

    def test_reserve_release_changes_nav_not_cash(self):
        p = AccountingProvider()
        p.add('ReserveReleased', 120, amount=2_000_000)
        p.pool.update(firstLossReserve=8_000_000, totalAssets=102_000_000)
        s = self.collect(p)
        self.assertEqual(s['flows']['reserveReleased'], 2_000_000)
        self.assertEqual(s['pool']['lenderCash'], 100_000_000)

    def test_backer_slashing_and_reserve_default_recovery(self):
        p = AccountingProvider(final_days=62)
        p.term = 30*p.day  # default at 61 days, after term plus 30-day late period
        p.add('Backed', 110, backer=p.backer, borrower=p.borrower, secured=4_000_000, unsecured=0)
        p.add('BackerCharged', 130, backer=p.backer, loanId=1, slashed=4_000_000, charged=0)
        p.add('LoanDefaulted', 130, borrower=p.borrower, loanId=1, writtenOff=10_000_000, recovered=10_000_000)
        p.status, p.outstanding = 4, 0
        p.pool.update(lenderCash=104_000_000, totalLentOut=0, totalStaked=6_000_000,
                      firstLossReserve=4_000_000, totalAssets=100_000_000)
        s = self.collect(p)
        self.assertEqual(s['stake'][p.backer], 6_000_000)
        self.assertEqual(s['flows']['writtenOff'], 10_000_000)
        self.assertEqual(s['loans'][0]['recovered'], 10_000_000)

    def test_active_impairment_reduces_by_principal_not_interest(self):
        p = AccountingProvider(final_days=32)
        p.term = 30*p.day
        p.add('LoanImpaired', 121, loanId=1, impaired=10_000_000)
        # 32 days at 10% => 87671 interest. Repayment reduces impairment by 2 USDC only.
        p.add('RepaymentApplied', 122, loanId=1, interest=87671, principal=2_000_000, fee=8767)
        p.add('LoanRepaid', 122, loanId=1, borrower=p.borrower, amount=2_087_671)
        p.outstanding = 8_000_000
        p.pool.update(lenderCash=102_078_904, totalLentOut=8_000_000, totalImpaired=8_000_000,
                      protocolFees=8767, totalDuesPaid=39451, firstLossReserve=10_039_451,
                      totalAssets=100_039_453)
        s = self.collect(p)
        self.assertEqual(s['loans'][0]['impaired'], 8_000_000)
        self.assertEqual(s['pool']['totalAssets'], 100_039_453)

    def test_interest_after_first_day_uses_contract_integer_order(self):
        p = AccountingProvider(principal=10_000_009, rate=933, final_days=364)
        # Contract floors principal*rate/10000 BEFORE multiplying elapsed time:
        # floor(933000*364/365)=930443; a combined division would produce 930444.
        p.outstanding = 10_930_452
        s = self.collect(p)
        self.assertEqual(s['flows']['interest'], 0)  # accrued is not collected
        self.assertEqual(s['loans'][0]['status'], 'Active')
        p.outstanding += 1
        with self.assertRaises(ld.RpcError): self.collect(p)

    def test_balanced_omitted_deposit_withdrawal_evades_stock_reconciliation(self):
        p = AccountingProvider()
        # Before any lending/interest, same share price, existing lender: stocks
        # and lender inventory end unchanged, while gross flows differ by 1 USDC.
        p.add('Deposited', 100, lender=p.backer, assets=1_000_000, shares=1_000_000_000_000)
        p.add('Withdrawn', 100, lender=p.backer, to=p.backer, assets=1_000_000, shares=1_000_000_000_000)
        complete = self.collect(p)
        omitted = copy.deepcopy(p)
        omitted.events = omitted.events[:-2]
        reduced = self.collect(p, omitted)
        self.assertEqual(complete['pool'], reduced['pool'])
        self.assertEqual(complete['loans'], reduced['loans'])
        self.assertEqual(complete['flows']['deposited']-reduced['flows']['deposited'], 1_000_000)
        self.assertEqual(complete['flows']['withdrawn']-reduced['flows']['withdrawn'], 1_000_000)
        # Both pass with production public getters (no populated repayment fields).
        # Passing is the documented trust-boundary counterexample, NOT completeness.
        self.assertEqual(reduced['snapshot']['verification'], 'reconciled-finalized-v1')

    def test_forgiven_principal_blocks_every_subsequent_full_history_collection(self):
        p = AccountingProvider()
        p.add('RepaymentApplied', 120, loanId=1, interest=5479, principal=9_999_999, fee=547)
        p.add('LoanRepaid', 120, loanId=1, borrower=p.borrower, amount=10_005_478)
        p.status, p.outstanding = 3, 0
        # One micro-unit is forgiven and charged to the reserve, not paid cash.
        p.pool.update(lenderCash=110_004_931, totalLentOut=0, protocolFees=547,
                      totalDuesPaid=2465, firstLossReserve=10_002_464, totalAssets=100_002_467)
        for days in (2, 3, 30, 365):
            p.final_days = days
            with self.subTest(days=days), self.assertRaises(ld.RpcError): self.collect(p)
