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


SECRET = 'https://user:hunter2@rpc.example/v2/APIKEY123?token=s3cr3t Authorization: Bearer abc /home/runner/.key Traceback'


class FailureDiagnosticsTests(unittest.TestCase):
    """Published failure diagnostics come from fixed lists only and never carry error text."""
    def run_main(self, error, stage=None, out=None):
        """Run main() with collect raising `error` after marking `stage`; return (rc, status, stderr)."""
        import contextlib, io
        def fake(deployment, rpc, logs_rpc, block, from_block, progress=None):
            if stage: progress.mark(stage)
            raise error
        with tempfile.TemporaryDirectory() as d:
            err = io.StringIO()
            with patch.object(ld, 'load_deployment', return_value=dict(DEPLOYMENT, rpc_url='https://rpc.example/')), \
                    patch.object(ld, 'collect', side_effect=fake), contextlib.redirect_stderr(err):
                rc = ld.main(['--out', d])
            status = json.loads((Path(d) / 'refresh-status.json').read_text())
            return rc, status, err.getvalue()

    def test_secret_like_messages_never_reach_status_or_stderr(self):
        errors = [ld.RpcError(SECRET), ld.RpcError('block ' + SECRET + ' not found'), ValueError(SECRET), OSError(SECRET),
                  KeyError(SECRET), IndexError(SECRET), TypeError(SECRET), ld.RpcError('x', SECRET)]
        for error in errors:
            error.role = SECRET
            rc, status, err = self.run_main(error, stage=SECRET)
            self.assertEqual(rc, 1)
            blob = json.dumps(status) + err
            for fragment in ('hunter2', 'APIKEY123', 's3cr3t', 'Bearer', '/home/runner', 'Traceback', 'rpc.example', 'https://'):
                self.assertNotIn(fragment, blob)
            self.assertEqual(status['failureStage'], 'unknown')
            self.assertIn(status['failureCode'], ld.FAILURE_CODES)
            self.assertNotIn('failureProvider', status)

    def test_failure_categories_stay_distinguishable(self):
        cases = [(ld.RpcError('provider chain mismatch'), 'chain_check', 'chain_mismatch'),
                 (ld.RpcError('provider block mismatch'), 'state_boundary', 'finality_boundary'),
                 (ld.RpcError('pool token wiring mismatch'), 'pool_state', 'wiring_mismatch'),
                 (ld.RpcError('conflicting duplicate log'), 'logs', 'log_inconsistent'),
                 (ld.RpcError('loan inventory mismatch'), 'loans', 'inventory_mismatch'),
                 (ld.RpcError('incomplete or inconsistent ledger'), 'reconcile', 'reconciliation_failed'),
                 (ld.RpcError('block 0x1 not found'), 'block_times', 'block_missing'),
                 (ld.RpcError('collection time budget exceeded'), 'logs', 'time_budget'),
                 (ld.RpcError('some new unlisted message'), 'loans', 'rpc_other'),
                 (ValueError('bad'), 'setup', 'invalid_data'),
                 (OSError('disk'), 'setup', 'local_io'),
                 (KeyError('k'), 'pool_state', 'unexpected_shape')]
        seen = set()
        for error, stage, code in cases:
            rc, status, err = self.run_main(error, stage=stage)
            self.assertEqual((status['failureStage'], status['failureCode']), (stage, code))
            self.assertEqual(status['status'], 'failed')
            self.assertIn(f'stage {stage} (code {code})', err)
            seen.add(code)
        self.assertEqual(len(seen), len({c for _, _, c in cases}))

    def test_stage_is_recorded_by_the_real_collection(self):
        state, logs = Provider(), Provider()
        for attribute, stage, code in (('chain', 'chain_check', 'chain_mismatch'), ('hash', 'state_boundary', 'finality_boundary')):
            progress = ld.Progress()
            target = state if attribute == 'chain' else logs
            original = getattr(target, attribute)
            setattr(target, attribute, 1 if attribute == 'chain' else '0x' + 'cd' * 32)
            with self.assertRaises(ld.RpcError) as caught:
                ld.collect(DEPLOYMENT, state, logs, progress=progress)
            self.assertEqual(ld.classify_failure(caught.exception, progress)[:2], (stage, code))
            setattr(target, attribute, original)
        state.ids = [1]
        progress = ld.Progress()
        with self.assertRaises(ld.RpcError) as caught:
            ld.collect(DEPLOYMENT, state, logs, progress=progress)
        self.assertEqual(ld.classify_failure(caught.exception, progress)[:2], ('loans', 'inventory_mismatch'))
        progress = ld.Progress()
        with self.assertRaises(ld.RpcError) as caught:
            ld.collect(DEPLOYMENT, state, logs, from_block=ld.DEPLOYMENT_BLOCK + 1, progress=progress)
        self.assertEqual(ld.classify_failure(caught.exception, progress)[:2], ('setup', 'bad_range'))

    def test_transport_failures_get_fixed_codes_and_a_provider_role(self):
        import io, socket, urllib.error
        def failing(exc):
            def opener(request, timeout=None): raise exc
            return opener
        cases = [(urllib.error.HTTPError(SECRET, 403, SECRET, {}, io.BytesIO(b'body ' + SECRET.encode())), 'http_403'),
                 (urllib.error.HTTPError(SECRET, 429, SECRET, {}, None), 'http_429'),
                 (urllib.error.HTTPError(SECRET, 404, SECRET, {}, None), 'http_4xx'),
                 (urllib.error.HTTPError(SECRET, 503, SECRET, {}, None), 'http_5xx'),
                 (urllib.error.URLError(SECRET), 'connection'),
                 (socket.timeout(SECRET), 'timeout'),
                 (json.JSONDecodeError(SECRET, SECRET, 0), 'bad_response')]
        for exc, code in cases:
            for role in ('state', 'logs'):
                rpc = ld.Rpc('https://rpc.example/' + SECRET, role=role)
                with patch.object(ld.urllib.request, 'urlopen', side_effect=failing(exc)), patch.object(ld.time, 'sleep'):
                    with self.assertRaises(ld.RpcError) as caught:
                        rpc.request('eth_chainId', [])
                self.assertEqual(ld.classify_failure(caught.exception)[1:], (code, role))
        self.assertIsNone(ld.Rpc('x', role=SECRET).role)

    def test_provider_rejection_and_time_budget_codes(self):
        rpc = ld.Rpc('https://rpc.example/', role='logs')
        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self, *a): return json.dumps({'jsonrpc': '2.0', 'id': 1, 'error': {'message': SECRET}}).encode()
        with patch.object(ld.urllib.request, 'urlopen', return_value=Response()):
            with self.assertRaises(ld.RpcError) as caught: rpc.request('eth_call', [])
        self.assertEqual(ld.classify_failure(caught.exception)[1:], ('provider_rejected', 'logs'))
        rpc.deadline = 0
        with self.assertRaises(ld.RpcError) as caught: rpc.request('eth_call', [])
        self.assertEqual(ld.classify_failure(caught.exception)[1:], ('time_budget', 'logs'))

    def test_every_published_name_is_on_the_fixed_lists(self):
        for message, code in ld.MESSAGE_CODES.items(): self.assertIn(code, ld.FAILURE_CODES)
        self.assertEqual(ld.classify_failure(RuntimeError(SECRET))[1], 'unknown')
        with tempfile.TemporaryDirectory() as d:
            ld.write_attempt(Path(d), 'failed', (SECRET, SECRET, SECRET))
            status = json.loads((Path(d) / 'refresh-status.json').read_text())
        self.assertEqual(status['failureStage'], 'unknown'); self.assertEqual(status['failureCode'], 'unknown')
        self.assertNotIn('failureProvider', status); self.assertNotIn('hunter2', json.dumps(status))

    def test_success_status_format_is_unchanged_and_failure_keeps_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            ld.write_attempt(Path(d), 'success', ('chain_check', 'chain_mismatch', 'state'))
            self.assertEqual(set(json.loads((Path(d) / 'refresh-status.json').read_text())), {'attemptedAt', 'status'})
            for name in ('snapshot.json', 'snapshot.js'): (Path(d) / name).write_text('keep')
            with patch.object(ld, 'load_deployment', return_value=dict(DEPLOYMENT, rpc_url='https://rpc.example/')), patch.object(ld, 'collect', side_effect=ld.RpcError('x')):
                self.assertEqual(ld.main(['--out', d]), 1)
            for name in ('snapshot.json', 'snapshot.js'): self.assertEqual((Path(d) / name).read_text(), 'keep')
            self.assertEqual(json.loads((Path(d) / 'refresh-status.json').read_text())['status'], 'failed')

    def test_no_write_leaves_no_status_file(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(ld, 'load_deployment', return_value=dict(DEPLOYMENT, rpc_url='https://rpc.example/')), patch.object(ld, 'collect', side_effect=ld.RpcError('x')):
                self.assertEqual(ld.main(['--out', d, '--no-write']), 1)
            self.assertFalse((Path(d) / 'refresh-status.json').exists())


PATH_MARKER = '/private/PATHMARKER/status.json'


class FailureHandlingRegressionTests(unittest.TestCase):
    """Review amendments: malformed metadata, failure to save the record, the write stage, real stderr."""
    MALFORMED = [{}, [], ['timeout'], {'timeout'}, 5, 1.5, None, b'timeout', ('timeout',), object()]

    def test_malformed_codes_roles_and_stages_fall_back_without_raising(self):
        for value in self.MALFORMED:
            error = ld.RpcError('fixture', value)
            error.role = value
            progress = ld.Progress(); progress.stage = value
            self.assertEqual(ld.classify_failure(error, progress), ('unknown', 'rpc_other', None))
            with tempfile.TemporaryDirectory() as d:
                ld.write_attempt(Path(d), 'failed', (value, value, value))
                status = json.loads((Path(d) / 'refresh-status.json').read_text())
            self.assertEqual((status['failureStage'], status['failureCode']), ('unknown', 'unknown'))
            self.assertNotIn('failureProvider', status)

    def test_malformed_code_through_main_still_records_a_fixed_failure(self):
        for value in self.MALFORMED:
            with tempfile.TemporaryDirectory() as d:
                with patch.object(ld, 'load_deployment', side_effect=ld.RpcError('fixture', value)):
                    self.assertEqual(ld.main(['--out', d]), 1)
                status = json.loads((Path(d) / 'refresh-status.json').read_text())
            self.assertEqual((status['status'], status['failureStage'], status['failureCode']), ('failed', 'setup', 'rpc_other'))

    def test_write_stage_is_marked_and_classified(self):
        report = {'snapshot': {}}
        for error, code in ((OSError(SECRET + PATH_MARKER), 'local_io'), (ValueError(SECRET), 'invalid_data')):
            with tempfile.TemporaryDirectory() as d:
                with patch.object(ld, 'load_deployment', return_value=dict(DEPLOYMENT, rpc_url='https://rpc.example/')), \
                        patch.object(ld, 'collect', return_value=report), patch.object(ld, 'write_outputs', side_effect=error):
                    self.assertEqual(ld.main(['--out', d]), 1)
                status = json.loads((Path(d) / 'refresh-status.json').read_text())
            self.assertEqual((status['status'], status['failureStage'], status['failureCode']), ('failed', 'write', code))
            self.assertNotIn('hunter2', json.dumps(status)); self.assertNotIn('PATHMARKER', json.dumps(status))

    def run_subprocess(self, script):
        import subprocess, sys
        root = Path(ld.__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, '-c', script], cwd=root, capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout, result.stderr

    def assert_clean(self, stderr):
        for fragment in ('Traceback', 'hunter2', 'APIKEY123', 's3cr3t', 'PATHMARKER', 'rpc.example', 'Bearer', 'During handling', 'File "'):
            self.assertNotIn(fragment, stderr)

    PRELUDE = (
        "import sys, tempfile\nfrom unittest.mock import patch\nfrom metrics import lending_dashboard as ld\n"
        "SECRET = %r\nPATH = %r\nd = tempfile.mkdtemp()\n" % (SECRET, PATH_MARKER))

    def test_subprocess_stderr_when_saving_the_failed_record_also_fails(self):
        script = self.PRELUDE + (
            "with patch.object(ld, 'load_deployment', side_effect=ld.RpcError(SECRET)), "
            "patch.object(ld, 'write_attempt', side_effect=OSError(PATH)):\n"
            "    sys.exit(ld.main(['--out', d]))\n")
        code, out, err = self.run_subprocess(script)
        self.assertEqual(code, 1)
        self.assert_clean(err)
        self.assertIn('Collection failed at stage setup (code rpc_other)', err)
        self.assertIn('could not be saved (code local_io)', err)

    def test_subprocess_stderr_when_output_and_status_writes_both_fail(self):
        script = self.PRELUDE + (
            "with patch.object(ld, 'load_deployment', return_value=dict(rpc_url='https://rpc.example/')), "
            "patch.object(ld, 'collect', return_value={}), "
            "patch.object(ld, 'write_outputs', side_effect=OSError(SECRET + PATH)), "
            "patch.object(ld, 'write_attempt', side_effect=OSError(PATH)):\n"
            "    sys.exit(ld.main(['--out', d]))\n")
        code, out, err = self.run_subprocess(script)
        self.assertEqual(code, 1)
        self.assert_clean(err)
        self.assertIn('Collection failed at stage write (code local_io)', err)

    def test_subprocess_stderr_for_a_secret_collection_error_with_a_malformed_code(self):
        script = self.PRELUDE + (
            "error = ld.RpcError(SECRET, {})\nerror.role = SECRET\n"
            "with patch.object(ld, 'load_deployment', side_effect=error):\n"
            "    sys.exit(ld.main(['--out', d]))\n")
        code, out, err = self.run_subprocess(script)
        self.assertEqual(code, 1)
        self.assert_clean(err)
        self.assertIn('stage setup (code rpc_other)', err)


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


# ---------------------------------------------------------------- transport: rate limits, retries, range splitting, header reuse
import email.utils
import http.client
import io
import socket
import ssl
import urllib.error
from datetime import datetime, timedelta, timezone


class Reply:
    """A urlopen result carrying one JSON-RPC payload."""
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def read(self, *a): return json.dumps(self.payload).encode()


def http_error(status, retry_after=None, headers=None):
    h = dict(headers or {})
    if retry_after is not None: h['Retry-After'] = retry_after
    return urllib.error.HTTPError(SECRET, status, SECRET, h, io.BytesIO(b'body ' + SECRET.encode()))


class Script:
    """urlopen stand-in: yields each scripted outcome in turn (an exception is raised, anything else is returned)."""
    def __init__(self, *outcomes): self.outcomes, self.calls = list(outcomes), 0
    def __call__(self, request, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, BaseException): raise outcome
        return outcome


def make_rpc(**kw):
    kw.setdefault('jitter', lambda: 0.0)
    return ld.Rpc('https://rpc.example/' + SECRET, **kw)


def run_request(rpc, script, sleeps):
    with patch.object(ld.urllib.request, 'urlopen', side_effect=script), patch.object(ld.time, 'sleep', side_effect=sleeps.append):
        return rpc.request('eth_chainId', [])


class RetryAfterParsingTests(unittest.TestCase):
    def test_valid_seconds_and_case_insensitive_name(self):
        self.assertEqual(ld.retry_after_seconds({'Retry-After': '120'}), 120)
        self.assertEqual(ld.retry_after_seconds({'retry-after': ' 7 '}), 7)
        self.assertEqual(ld.retry_after_seconds({'RETRY-AFTER': '0'}), 0)
        self.assertEqual(ld.retry_after_seconds({'Retry-After': '00000120'}), 120)  # leading zeros do not change the value
        self.assertEqual(ld.retry_after_seconds({'Retry-After': '0000000000'}), 0)
        self.assertEqual(ld.retry_after_seconds({'Retry-After': '12345678'}), 12_345_678)  # a long but representable delay is a delay, not noise
        self.assertEqual(ld.retry_after_seconds({'Retry-After': '999999999'}), 999_999_999)
        self.assertEqual(ld.retry_after_seconds({'Retry-After': '0' * 50 + '45'}), 45)
        msg = http.client.HTTPMessage(); msg['retry-AFTER'] = '30'
        self.assertEqual(ld.retry_after_seconds(msg), 30)

    def test_unrepresentable_delays_come_back_as_infinity_not_as_no_delay(self):
        for value in ['1000000000', '9' * 12, '1' + '0' * 30, '9' * 5000, '0' * 4000 + '1' + '0' * 12]:
            self.assertEqual(ld.retry_after_seconds({'Retry-After': value}), float('inf'), value[:12])

    def test_http_date_in_the_future_and_the_past(self):
        now = datetime.now(timezone.utc)
        future = email.utils.format_datetime(now + timedelta(seconds=90), usegmt=True)
        past = email.utils.format_datetime(now - timedelta(seconds=90), usegmt=True)
        self.assertTrue(85 <= ld.retry_after_seconds({'Retry-After': future}) <= 90)
        self.assertEqual(ld.retry_after_seconds({'Retry-After': past}), 0.0)
        fixed = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(ld.retry_after_seconds({'Retry-After': 'Sun, 15 Nov 2026 12:02:00 GMT'}, now=fixed), 120.0)

    def test_malformed_repeated_or_missing_values_are_not_a_delay(self):
        for value in ['', ' ', '-5', '1.5', '1e3', 'abc', '0x10', '٣٠', 'Sun, 99 Nov 2026 12:00:00 GMT',
                      'Sun, 15 Nov 2026 12:00:00', 'tomorrow', None, 120, ['30'], b'30']:
            self.assertIsNone(ld.retry_after_seconds({'Retry-After': value}), repr(value))
        self.assertIsNone(ld.retry_after_seconds({}))
        self.assertIsNone(ld.retry_after_seconds(None))
        self.assertIsNone(ld.retry_after_seconds(object()))
        msg = http.client.HTTPMessage(); msg['Retry-After'] = '10'; msg['Retry-After'] = '20'
        self.assertIsNone(ld.retry_after_seconds(msg))  # two values: ambiguous, so not trusted


class BackoffTests(unittest.TestCase):
    def test_429_with_retry_after_waits_at_least_that_long_not_the_fixed_backoff(self):
        sleeps = []; script = Script(http_error(429, '120'), Reply({'result': '0x14a34'}))
        self.assertEqual(run_request(make_rpc(), script, sleeps), '0x14a34')
        self.assertEqual(sleeps, [120.0]); self.assertEqual(script.calls, 2)
        sleeps = []; script = Script(http_error(429, '120'), Reply({'result': '0x1'}))
        run_request(make_rpc(jitter=lambda: 1.0), script, sleeps)
        self.assertEqual(sleeps, [121.0])  # up to one second of jitter on top, never less than asked

    def test_retry_after_date_is_honoured(self):
        when = email.utils.format_datetime(datetime.now(timezone.utc) + timedelta(seconds=45), usegmt=True)
        sleeps = []; run_request(make_rpc(), Script(http_error(429, when), Reply({'result': '0x1'})), sleeps)
        self.assertEqual(len(sleeps), 1); self.assertTrue(40 <= sleeps[0] <= 45.5, sleeps)

    def test_padded_and_oversized_numeric_retry_after_through_the_request_path(self):
        sleeps = []; run_request(make_rpc(), Script(http_error(429, '00000120'), Reply({'result': '0x1'})), sleeps)
        self.assertEqual(sleeps, [120.0])  # padded 120 waits 120 s, not the 0.5 s fallback it used to get
        for value in ('12345678', '9' * 12, '0' * 40 + '7' * 20, '9' * 5000):
            rpc = make_rpc(); rpc.deadline = ld.time.monotonic() + 600
            sleeps = []; script = Script(http_error(429, value))
            with self.assertRaises(ld.RpcError) as caught: run_request(rpc, script, sleeps)
            self.assertEqual((script.calls, sleeps), (1, []), value[:12])  # an over-budget positive delay is refused: no early retry, no sleep
            self.assertEqual(ld.classify_failure(caught.exception)[1:], ('http_429', 'state'))

    def test_retry_after_longer_than_the_remaining_budget_refuses_without_sleeping(self):
        rpc = make_rpc(); rpc.deadline = ld.time.monotonic() + 60
        sleeps = []; script = Script(http_error(429, '120'))
        with self.assertRaises(ld.RpcError) as caught: run_request(rpc, script, sleeps)
        self.assertEqual(sleeps, []); self.assertEqual(script.calls, 1)  # not retried early, not slept
        self.assertEqual(ld.classify_failure(caught.exception)[1:], ('http_429', 'state'))

    def test_retry_after_that_just_fits_is_honoured_and_one_that_just_misses_is_refused(self):
        with patch.object(ld.time, 'monotonic', return_value=1000.0):
            rpc = make_rpc(); rpc.deadline = 1100.0
            self.assertEqual(rpc.wait_before_retry(http_error(429, '100'), 0), 100.0)
            self.assertIsNone(rpc.wait_before_retry(http_error(429, '101'), 0))

    def test_retry_after_zero_is_not_a_reason_to_retry_at_once(self):
        sleeps = []; run_request(make_rpc(), Script(http_error(429, '0'), Reply({'result': '0x1'})), sleeps)
        self.assertEqual(sleeps, [0.5])  # a provider that says "0" on a 429 still gets the normal backoff, not an immediate retry
        past = email.utils.format_datetime(datetime.now(timezone.utc) - timedelta(seconds=30), usegmt=True)
        sleeps = []; run_request(make_rpc(), Script(http_error(429, past), Reply({'result': '0x1'})), sleeps)
        self.assertEqual(sleeps, [0.5])

    def test_malformed_retry_after_falls_back_to_capped_jittered_backoff(self):
        for bad in ('abc', '-1', '1.5', ''):
            sleeps = []; run_request(make_rpc(), Script(http_error(429, bad), Reply({'result': '0x1'})), sleeps)
            self.assertEqual(sleeps, [0.5], bad)  # attempt 0: ceiling 1, jitter 0 -> half of it
        sleeps = []; run_request(make_rpc(jitter=lambda: 1.0), Script(http_error(503), Reply({'result': '0x1'})), sleeps)
        self.assertEqual(sleeps, [1.0])

    def test_backoff_grows_is_capped_and_always_jittered_inside_its_bounds(self):
        rpc = make_rpc()
        err = urllib.error.URLError('x')
        low = [rpc.wait_before_retry(err, a) for a in range(0, 8)]
        self.assertEqual(low[:4], [0.5, 1.0, 2.0, 4.0]); self.assertTrue(all(v <= ld.MAX_BACKOFF_S for v in low))
        self.assertEqual(low[-1], ld.MAX_BACKOFF_S / 2)  # capped: 8 / 2 at jitter 0
        high = make_rpc(jitter=lambda: 1.0)
        self.assertTrue(all(high.wait_before_retry(err, a) <= ld.MAX_BACKOFF_S for a in range(0, 12)))
        self.assertEqual(high.wait_before_retry(err, 30), ld.MAX_BACKOFF_S)

    def test_a_broken_jitter_source_cannot_shorten_or_lengthen_a_wait(self):
        err = urllib.error.URLError('x')
        for bad in (-1, 5, None, 'x', float('nan'), True, False):
            self.assertEqual(make_rpc(jitter=lambda b=bad: b).wait_before_retry(err, 0), 1.0, repr(bad))

    def test_no_sleep_after_the_last_attempt_and_attempts_are_bounded(self):
        for retries, expected_calls in ((1, 1), (2, 2), (3, 3), (5, 5)):
            sleeps = []; script = Script(http_error(503))
            with self.assertRaises(ld.RpcError): run_request(make_rpc(retries=retries), script, sleeps)
            self.assertEqual((script.calls, len(sleeps)), (expected_calls, expected_calls - 1), retries)
        for bad in (0, -1, 6, 99, True, '3', None, 2.5):
            self.assertEqual(ld.Rpc('https://x/', retries=bad).retries, 2, repr(bad))

    def test_a_wait_that_does_not_fit_stops_the_retries(self):
        rpc = make_rpc(retries=5); rpc.deadline = ld.time.monotonic() + 0.2
        sleeps = []; script = Script(http_error(503))
        with self.assertRaises(ld.RpcError): run_request(rpc, script, sleeps)
        self.assertEqual((script.calls, sleeps), (1, []))  # a 0.5 s backoff does not fit in 0.2 s

    def test_budget_exhausted_between_attempts_is_a_time_budget_failure(self):
        rpc = make_rpc(retries=3); times = iter([0.0, 0.0, 10_000.0])  # attempt 1 starts, its backoff fits, then the budget is gone when attempt 2 would start
        rpc.deadline = 100.0
        with patch.object(ld.time, 'monotonic', side_effect=lambda: next(times)), \
                patch.object(ld.urllib.request, 'urlopen', side_effect=Script(http_error(503))), patch.object(ld.time, 'sleep'):
            with self.assertRaises(ld.RpcError) as caught: rpc.request('eth_chainId', [])
        self.assertEqual(ld.classify_failure(caught.exception)[1:], ('time_budget', 'state'))

    def test_retry_after_value_never_reaches_the_published_failure(self):
        rpc = make_rpc(); rpc.deadline = ld.time.monotonic() + 1
        with self.assertRaises(ld.RpcError) as caught:
            run_request(rpc, Script(http_error(429, '99999', headers={'X-Secret': SECRET})), [])
        stage, code, role = ld.classify_failure(caught.exception)
        self.assertEqual((code, role), ('http_429', 'state'))
        self.assertNotIn('99999', repr((stage, code, role)))
        self.assertTrue(code in ld.FAILURE_CODES)


class SyntheticOSErrorTests(unittest.TestCase):
    """The November 9 hypothesis: a socket error urllib does not wrap in URLError escaped as a bare OSError and was reported as local_io."""
    CASES = [(ConnectionResetError(SECRET), 'connection'), (ConnectionRefusedError(SECRET), 'connection'),
             (ConnectionAbortedError(SECRET), 'connection'), (BrokenPipeError(SECRET), 'connection'),
             (http.client.RemoteDisconnected(SECRET), 'connection'), (ssl.SSLError(SECRET), 'connection'),
             (socket.gaierror(SECRET), 'connection'), (OSError(SECRET), 'connection'),
             (http.client.IncompleteRead(b'part', 10), 'bad_response'), (http.client.BadStatusLine(SECRET), 'bad_response')]

    def test_each_transport_error_becomes_a_fixed_code_with_the_provider_role(self):
        for exc, code in self.CASES:
            for role in ('state', 'logs'):
                with self.assertRaises(ld.RpcError, msg=repr(exc)) as caught:
                    run_request(make_rpc(role=role), Script(exc), [])
                self.assertEqual(ld.classify_failure(caught.exception)[1:], (code, role), repr(exc))
                self.assertNotIn('hunter2', repr(ld.classify_failure(caught.exception)))

    def test_a_reset_is_retried_and_then_succeeds(self):
        sleeps = []; self.assertEqual(run_request(make_rpc(), Script(ConnectionResetError(SECRET), Reply({'result': '0x2'})), sleeps), '0x2')
        self.assertEqual(sleeps, [0.5])

    def test_local_file_errors_are_still_local_io(self):
        self.assertEqual(ld.classify_failure(OSError(SECRET))[1], 'local_io')  # only a failed transport request becomes `connection`
        self.assertEqual(ld.transport_code(OSError(SECRET)), 'connection')


class RangeSplitTests(unittest.TestCase):
    def test_only_a_range_or_result_size_message_is_a_range_limit(self):
        for message in ('block range too large', 'eth_getLogs is limited to a range', 'query returned more than 10000 results',
                        'Log response size exceeded', 'range is too wide', 'max range exceeded', 'query exceeds max results 20000'):
            self.assertTrue(ld.range_limited({'message': message}), message)
        for message in ('rate limit exceeded', 'Too Many Requests', 'request throttled', 'daily quota exceeded', 'over capacity', 'limit exceeded',
                        'rate limit: block range too large', 'Too Many Requests: block range too large', 'request throttled: range too wide',
                        'rate-limit hit, max range', 'daily quota exceeded: block range', 'over capacity, query returned more than 10000 results',
                        'internal error', '', None, 5, ['block range']):
            self.assertFalse(ld.range_limited({'message': message}), repr(message))
        for not_an_error in (None, 'block range', 5, [], {'code': -32005}):
            self.assertFalse(ld.range_limited(not_an_error))
        import collections
        self.assertFalse(ld.range_limited(collections.UserDict({'message': 'block range too large'})))  # only a real JSON object counts

    def logs_rpc(self, outcome):
        class Probe(ld.Rpc):
            def __init__(self): super().__init__('fake://', retries=1); self.widths = []
            def request(self, method, params):
                self.widths.append(int(params[0]['toBlock'], 16) - int(params[0]['fromBlock'], 16) + 1)
                if isinstance(outcome, BaseException): raise outcome
                raise AssertionError('unscripted')
        return Probe()

    def test_range_limit_splits_down_to_the_public_cap_and_stops(self):
        class Limited(ld.Rpc):
            def __init__(self): super().__init__('fake://', retries=1); self.widths = []
            def request(self, method, params):
                self.widths.append(int(params[0]['toBlock'], 16) - int(params[0]['fromBlock'], 16) + 1)
                error = ld.RpcError('provider rejected request', 'provider_rejected'); error.role = 'logs'
                error.range_limited = ld.range_limited({'message': 'block range too large'}); raise error
        limited = Limited()
        with self.assertRaises(ld.RpcError): limited.logs(['0x' + '11' * 20], 0, 99_999)
        self.assertEqual(limited.widths, [10_000, 2_500, 625, 156])

    def test_other_failures_never_shrink_the_range(self):
        def coded(code, **extra):
            e = ld.RpcError('x', code); e.role = 'logs'
            for k, v in extra.items(): setattr(e, k, v)
            return e
        failures = [coded('http_429'), coded('timeout'), coded('connection'), coded('time_budget'), coded('http_5xx'), coded('bad_response'),
                    coded('provider_rejected', range_limited=False), coded('provider_rejected'), ld.RpcError('plain, no code'),
                    coded('provider_rejected', range_limited='yes')]
        for failure in failures:
            rpc = self.logs_rpc(failure)
            with self.assertRaises(ld.RpcError): rpc.logs(['0x' + '11' * 20], 0, 99_999)
            self.assertEqual(rpc.widths, [10_000], f'{failure.code!r} must not shrink the range')

    def test_a_rate_limited_rejection_through_the_real_request_path_does_not_shrink(self):
        class Real(ld.Rpc): pass
        rpc = Real('https://rpc.example/', retries=1, role='logs'); widths = []
        def opener(request, timeout=None):
            body = json.loads(request.data); p = body['params'][0]
            widths.append(int(p['toBlock'], 16) - int(p['fromBlock'], 16) + 1)
            return Reply({'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32005, 'message': 'rate limit exceeded'}})
        with patch.object(ld.urllib.request, 'urlopen', side_effect=opener):
            with self.assertRaises(ld.RpcError) as caught: rpc.logs(['0x' + '11' * 20], 0, 99_999)
        self.assertEqual(widths, [10_000]); self.assertEqual(ld.classify_failure(caught.exception)[1:], ('provider_rejected', 'logs'))

    def test_a_range_rejection_through_the_real_request_path_does_shrink(self):
        rpc = ld.Rpc('https://rpc.example/', retries=1, role='logs'); widths = []
        def opener(request, timeout=None):
            p = json.loads(request.data)['params'][0]
            width = int(p['toBlock'], 16) - int(p['fromBlock'], 16) + 1; widths.append(width)
            if width > 1_000: return Reply({'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32602, 'message': 'block range too large'}})
            return Reply({'jsonrpc': '2.0', 'id': 1, 'result': []})
        with patch.object(ld.urllib.request, 'urlopen', side_effect=opener):
            self.assertEqual(rpc.logs(['0x' + '11' * 20], 0, 2_999), [])
        self.assertEqual(widths, [3_000, 2_500, 625, 625, 625, 625, 500])  # two rejections (range), then 625-block windows over the whole range


class CountingProvider(FullProvider):
    def __init__(self):
        super().__init__(); self.seen = {}
    def block(self, n):
        n = self.finalized if n == 'finalized' else n
        self.seen[n] = self.seen.get(n, 0) + 1
        return super().block(n)


class HeaderReuseTests(unittest.TestCase):
    def collect(self, state=None, logs=None):
        state, logs = state or CountingProvider(), logs or CountingProvider()
        return state, logs, ld.collect(DEPLOYMENT, state, logs)

    def test_event_blocks_are_read_once_per_provider_and_boundaries_are_reread_at_the_end(self):
        state, logs, result = self.collect()
        event_blocks = {ld.DEPLOYMENT_BLOCK + e['block'] for e in state.events}
        boundary = {ld.DEPLOYMENT_BLOCK, ld.DEPLOYMENT_BLOCK + 200}
        self.assertTrue(event_blocks and not (event_blocks & boundary))
        for n in event_blocks:
            self.assertEqual((state.seen[n], logs.seen[n]), (1, 1), 'the state header is reused, the logs header is still read independently')
        # state: finalized + boundary header + early match + final match; logs: finalized + early match + final match
        self.assertEqual(state.seen[ld.DEPLOYMENT_BLOCK + 200], 4)
        self.assertEqual(logs.seen[ld.DEPLOYMENT_BLOCK + 200], 3)
        self.assertEqual(state.seen[ld.DEPLOYMENT_BLOCK], 3); self.assertEqual(logs.seen[ld.DEPLOYMENT_BLOCK], 2)
        self.assertEqual(result['snapshot']['eventCount'], len(state.events))

    def test_a_reused_state_header_must_still_name_the_block_that_was_asked_for(self):
        for delta in (1, -1, 1000):
            state, logs = CountingProvider(), CountingProvider()
            first_event = ld.DEPLOYMENT_BLOCK + state.events[0]['block']
            original = state.block
            def wrong_number(n, original=original, delta=delta, first_event=first_event):
                h = original(n)
                return dict(h, number=hex(n + delta)) if n == first_event else h
            with patch.object(state, 'block', side_effect=wrong_number):
                with self.assertRaises(ld.RpcError, msg=delta) as caught: ld.collect(DEPLOYMENT, state, logs)
            self.assertEqual(str(caught.exception), 'provider block mismatch')
        state, logs = CountingProvider(), CountingProvider()
        first_event = ld.DEPLOYMENT_BLOCK + state.events[0]['block']
        original = state.block
        with patch.object(state, 'block', side_effect=lambda n: {k: v for k, v in original(n).items() if k != 'number'} if n == first_event else original(n)):
            with self.assertRaises((ld.RpcError, KeyError, TypeError, ValueError)): ld.collect(DEPLOYMENT, state, logs)
        state, logs, result = self.collect()  # unchanged headers still collect, one read per provider per event block
        self.assertEqual(result['snapshot']['eventCount'], len(state.events))

    def test_a_logs_provider_that_disagrees_on_an_event_block_still_fails(self):
        state, logs = CountingProvider(), CountingProvider()
        first_event = ld.DEPLOYMENT_BLOCK + state.events[0]['block']
        original = logs.block
        def lie(n):
            h = original(n)
            return dict(h, hash='0x' + 'cc' * 32) if n == first_event else h
        with patch.object(logs, 'block', side_effect=lie):
            with self.assertRaises(ld.RpcError) as caught: ld.collect(DEPLOYMENT, state, logs)
        self.assertEqual(str(caught.exception), 'provider block mismatch')
        timestamp = lambda n: dict(original(n), timestamp=hex(as_int_(original(n)['timestamp']) + 1)) if n == first_event else original(n)
        with patch.object(logs, 'block', side_effect=timestamp):
            with self.assertRaises(ld.RpcError): ld.collect(DEPLOYMENT, CountingProvider(), logs)

    def test_event_block_hash_mismatch_and_end_of_run_change_still_fail(self):
        state, logs = CountingProvider(), CountingProvider()
        original = logs.logs
        with patch.object(logs, 'logs', side_effect=lambda *a: [dict(e, blockHash='0x' + 'ee' * 32) for e in original()]):
            with self.assertRaises(ld.RpcError): ld.collect(DEPLOYMENT, state, logs)
        for provider_name in ('state', 'logs'):
            state, logs = CountingProvider(), CountingProvider()
            target = state if provider_name == 'state' else logs
            real = target.block; boundary = ld.DEPLOYMENT_BLOCK + 200; reads = {'n': 0}
            last_read = 3 if provider_name == 'state' else 2  # state: header, early match, final match; logs: early match, final match
            def changing(n, real=real, reads=reads, last_read=last_read):
                h = real(n)
                if n == boundary:
                    reads['n'] += 1
                    if reads['n'] == last_read: return dict(h, hash='0x' + 'dd' * 32)  # only the LAST read, the end-of-run reread, differs
                return h
            with patch.object(target, 'block', side_effect=changing):
                with self.assertRaises(ld.RpcError, msg=provider_name): ld.collect(DEPLOYMENT, state, logs)


def as_int_(value): return int(value, 16)
