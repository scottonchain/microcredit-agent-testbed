#!/usr/bin/env python3
"""Deliberately corrupt real public artifacts; never read a key or use a network."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('coldstart_evidence_audit', HERE / 'verify-evidence.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
REPO = HERE.parents[1]
RELATIVE = 'evidence/coldstart-fork-run-001'

def fixture(target):
    manifest = module.load(HERE / 'reproducibility-manifest.json')
    for item in manifest['files']:
        dest = target / item['path']; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / item['path'], dest)
    shutil.copyfile(HERE / 'reproducibility-manifest.json', target / RELATIVE / 'reproducibility-manifest.json')

def rehash_manifest(repo):
    path = repo / RELATIVE / 'reproducibility-manifest.json'
    manifest = module.load(path)
    for item in manifest['files']:
        data = (repo / item['path']).read_bytes()
        item.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    path.write_text(json.dumps(manifest, indent=2) + '\n')

def mutate(case, repo):
    passed = repo / RELATIVE / 'attempt-3-passed'
    if case == 'file_byte_changed':
        with (passed / 'initial.json').open('a') as f: f.write(' ')
    elif case == 'journal_payload_changed_and_file_rehashed':
        path = passed / 'journal.jsonl'
        records = [json.loads(line) for line in path.read_text().splitlines()]
        records[0]['payload']['source_chain_id'] = 1
        path.write_text('\n'.join(json.dumps(r, sort_keys=True) for r in records) + '\n')
        rehash_manifest(repo)
    elif case == 'boundary_changed_and_file_rehashed':
        path = passed / 'scenario1-after.json'; value = module.load(path)
        value['root_aggregate_usdc_units'] -= 1
        path.write_text(json.dumps(value, indent=2) + '\n'); rehash_manifest(repo)
    elif case == 'short_repay_with_recomputed_journal_and_file_hashes':
        path = passed / 'journal.jsonl'
        records = [json.loads(line) for line in path.read_text().splitlines()]
        for record in records:
            p = record['payload']
            if p.get('label') == 'full principal repayment' and record['kind'] in ('transaction_intent', 'mined_transaction'):
                tx = p['transaction']; key = 'data' if record['kind'] == 'transaction_intent' else 'input'
                tx[key] = tx[key][:-64] + ('%064x' % 999999)
                # Alter exactly one matched repayment pair.
                if record['kind'] == 'mined_transaction': break
        previous = '0' * 64
        for record in records:
            record['previous_sha256'] = previous
            unsigned = {k: v for k, v in record.items() if k != 'record_sha256'}
            previous = hashlib.sha256(module.canonical(unsigned)).hexdigest()
            record['record_sha256'] = previous
        path.write_text('\n'.join(json.dumps(r, sort_keys=True) for r in records) + '\n')
        rehash_manifest(repo)

if __name__ == '__main__':
    result = module.audit(REPO)
    cases = ['file_byte_changed', 'journal_payload_changed_and_file_rehashed',
             'boundary_changed_and_file_rehashed', 'short_repay_with_recomputed_journal_and_file_hashes']
    rejected = []
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='coldstart-public-tamper-') as temp:
            repo = Path(temp); fixture(repo); mutate(case, repo)
            try:
                module.audit(repo)
            except (ValueError, KeyError, OSError, TypeError) as exc:
                rejected.append({'case': case, 'rejected': True, 'reason': str(exc)})
            else:
                raise AssertionError('Corruption accepted: ' + case)
    print(json.dumps({'status': 'passed', 'original': result['status'], 'corruption_cases': rejected,
                      'network_calls': 0, 'private_keys_read': 0, 'signatures_created': 0}, indent=2))
