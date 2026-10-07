#!/usr/bin/env python3
"""Read-only, standard-library audit of the published cold-start fork packet."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

POOL = '0x73872b8fb7f1771c67911f03edc75abdc9514973'
TOKEN = '0x036cbd53842c5426634e7929541ec2318f3dcf7e'
HERMES = '0x5e4dc7639d2b94006c51ad5373173f5e01c248f9'
AVERY = '0xc5e42b0fb0c109e55f4a40cccfcf3fed1fc39009'
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
LOAN_REQUESTED = '0x470e775e4fa2bd975947314dc912d0dd85338d809a6b967e36382e32a3b6f2bb'
BLOCK = 47820167
BLOCK_HASH = '0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078'
EVIDENCE = 'evidence/coldstart-fork-run-001'

def require(condition, message):
    if not condition:
        raise ValueError(message)

def number(value):
    if isinstance(value, str):
        return int(value, 16 if value.startswith('0x') else 10)
    return int(value)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def load(path):
    return json.loads(path.read_text())

def journal(path):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    previous = '0' * 64
    for index, record in enumerate(records, 1):
        require(record['sequence'] == index, 'Journal sequence gap: ' + str(path))
        require(record['previous_sha256'] == previous, 'Journal predecessor mismatch')
        unsigned = {k: v for k, v in record.items() if k != 'record_sha256'}
        digest = hashlib.sha256(canonical(unsigned)).hexdigest()
        require(digest == record['record_sha256'], 'Journal digest mismatch')
        previous = digest
    return records

def audit(repo):
    manifest = load(repo / EVIDENCE / 'reproducibility-manifest.json')
    require(manifest['schema'] == 'coldstart-reproduction/1', 'Unknown manifest schema')
    require(manifest['source_block'] == BLOCK and manifest['source_block_hash'] == BLOCK_HASH,
            'Manifest source identity differs from original run')
    files = manifest['files']
    require(len({item['path'] for item in files}) == len(files), 'Duplicate manifest path')
    for item in files:
        relative = Path(item['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe manifest path')
        path = (repo / relative).resolve()
        path.relative_to(repo.resolve())
        content = path.read_bytes()
        require(len(content) == item['bytes'], 'File size mismatch: ' + item['path'])
        require(hashlib.sha256(content).hexdigest() == item['sha256'], 'File hash mismatch: ' + item['path'])

    root = repo / EVIDENCE
    failed = []
    for name in ('attempt-1-stopped-gas-guard', 'attempt-2-stopped-gas-guard'):
        records = journal(root / name / 'journal.jsonl')
        require(not any(r['kind'] in ('transaction_receipt', 'mined_transaction') for r in records),
                'Stopped attempt contains a mined transaction')
        failure = load(root / name / 'failure.json')
        require('Gas price above one gwei' in failure['error'], 'Wrong stopped-at-guard reason')
        require(any(r['kind'] == 'failure' and r['payload'] == failure for r in records),
                'Failure file differs from journal')
        failed.append({'attempt': name, 'records': len(records), 'mined_transactions': 0})

    passed = root / 'attempt-3-passed'
    records = journal(passed / 'journal.jsonl')
    evidence = load(passed / 'evidence.json')
    initial = load(passed / 'initial.json')
    final = load(passed / 'final.json')
    guard = records[0]['payload']
    require(records[0]['kind'] == 'fork_guard' and guard['chain_id'] == 31337 and
            guard['source_chain_id'] == 84532 and guard['fork_block_target'] == BLOCK and
            guard['source_block_hash'] == BLOCK_HASH, 'Wrong fork guard/source')
    require(initial['block_number'] == BLOCK and initial['block_hash'] == BLOCK_HASH, 'Wrong initial source block')
    require(evidence['status'] == 'passed' and evidence['mode'] == 'fork' and
            evidence['chain_id'] == 31337 and evidence['source_chain_id'] == 84532 and
            evidence['fork_block_target'] == BLOCK and evidence['fork_block_hash'] == BLOCK_HASH and
            evidence['no_live_fund_moves'] is True, 'Wrong evidence scope')
    require(load(passed / 'runtime-code-hashes.json') == guard['code_hashes'] == evidence['runtime_code_hashes'],
            'Runtime fingerprint records disagree')
    require(all(item.get('artifact_normalized_runtime_matches', True) for item in guard['code_hashes'].values()),
            'Compiled runtime normalization failed')
    source = load(root / 'source-code-hashes.json')
    require(source['fork_block_number'] == BLOCK and source['fork_block_hash'] == BLOCK_HASH,
            'Source fingerprints use another block')
    for name, item in source['contracts'].items():
        observed = guard['code_hashes'][name]
        require(all(item[k].lower().removeprefix('0x') == observed[k].lower().removeprefix('0x')
                    for k in ('address', 'sha256', 'keccak256')), 'Source runtime fingerprint mismatch')

    intents, submitted, receipts, mined = {}, {}, {}, {}
    pending_intent = None
    complete = None
    balances = {v['address'].lower(): v['usdc_units'] for v in initial['wallets'].values()}
    balances[POOL] = initial['pool']['token_balance']
    transfers = []
    snapshot_count = 0
    negative_count = 0
    loans, disbursements, repayments, withdrawers, nonces = {}, {}, {}, [], {}
    selectors = {k: '0x' + v.lower().removeprefix('0x') for k, v in
                 load(repo / 'scenarios/cold-start-three-communities/manifest.json')['contracts']['DecentralizedMicrocredit']['selectors'].items()}
    for record in records:
        kind, payload = record['kind'], record['payload']
        if kind == 'transaction_intent':
            require(pending_intent is None, 'Unsubmitted preceding intent')
            pending_intent = payload
        elif kind == 'transaction_submitted':
            txhash = payload['hash'].lower()
            require(pending_intent is not None and txhash not in submitted, 'Duplicate or unpaired submission')
            require(pending_intent['label'] == payload['label'], 'Intent/submission label mismatch')
            intents[txhash], submitted[txhash] = pending_intent['transaction'], payload
            pending_intent = None
        elif kind == 'transaction_receipt':
            txhash = payload['hash'].lower(); receipt = payload['receipt']
            require(txhash in submitted and txhash not in receipts, 'Duplicate/unsubmitted receipt')
            require(receipt['transactionHash'].lower() == txhash and number(receipt['status']) == 1,
                    'Failed or mismatched receipt')
            require(receipt.get('contractAddress') is None, 'Unexpected deployment receipt')
            receipts[txhash] = receipt
            for log in receipt['logs']:
                if log['address'].lower() != TOKEN or not log['topics'] or log['topics'][0].lower() != TRANSFER:
                    continue
                require(len(log['topics']) == 3 and log.get('removed', False) is False, 'Malformed token transfer')
                sender, recipient = ['0x' + topic[-40:].lower() for topic in log['topics'][1:]]
                require(sender in balances and recipient in balances, 'Transfer leaves tracked root/pool scope')
                amount = number(log['data'])
                require(balances[sender] >= amount, 'Negative replayed USDC balance')
                balances[sender] -= amount; balances[recipient] += amount
                transfers.append({'hash': txhash, 'from': sender, 'to': recipient, 'units': amount})
            require(sum(balances.values()) == 35000000, 'Token ledger does not conserve35 USDC')
        elif kind == 'mined_transaction':
            tx = payload['transaction']; txhash = tx['hash'].lower()
            require(txhash in receipts and txhash not in mined, 'Duplicate/unreceipted mined transaction')
            receipt, intent = receipts[txhash], intents[txhash]
            require(number(tx['chainId']) == 31337 and tx['blockHash'] == receipt['blockHash'] and
                    number(tx['blockNumber']) == number(receipt['blockNumber']), 'Wrong mined chain/block')
            for key in ('from', 'to'):
                require(tx[key].lower() == receipt[key].lower() == intent[key].lower(), 'Mined sender/target mismatch')
            require(tx['input'].lower() == intent.get('data', '0x').lower(), 'Mined calldata mismatch')
            for key in ('value', 'gas', 'gasPrice'):
                require(number(tx[key]) == number(intent.get(key, '0x0')), 'Mined intent quantity mismatch: ' + key)
            if 'nonce' in intent:
                require(number(tx['nonce']) == number(intent['nonce']), 'Mined intent nonce mismatch')
            sender = tx['from'].lower()
            if sender in nonces:
                require(number(tx['nonce']) == nonces[sender] + 1, 'Nonsequential sender nonce')
            nonces[sender] = number(tx['nonce'])
            if tx['to'].lower() == POOL:
                encoded = tx['input'].lower()
                words = [int(encoded[start:start+64], 16) for start in range(10, len(encoded), 64)]
                if encoded[:10] == selectors['disburseLoan(uint256)']:
                    require(len(words) == 1 and words[0] in loans and words[0] not in disbursements,
                            'Disbursement has no unique mined request')
                    disbursements[words[0]] = payload['block_timestamp']
                elif encoded[:10] == selectors['repayLoan(uint256,uint256)']:
                    require(len(words) == 2 and words[0] in disbursements and words[0] not in repayments and
                            words[1] == 1000000, 'Repayment is not the complete one-USDC principal')
                    require(0 <= payload['block_timestamp'] - disbursements[words[0]] < 86400,
                            'Repayment is outside the interest-free grace')
                    repayments[words[0]] = payload['block_timestamp']
                elif encoded[:10] == selectors['withdrawFunds(uint256)']:
                    require(words == [2**256 - 1], 'Withdrawal is not the full-share sentinel')
                    withdrawers.append(sender)
            mined[txhash] = payload
        elif kind == 'receipt_derived_loan':
            txhash, event, loan_id = payload['transaction_hash'].lower(), payload['log'], payload['loan_id']
            require(txhash in receipts and event in receipts[txhash]['logs'] and loan_id not in loans,
                    'Loan identifier is not derived from a unique matching mined receipt')
            require(event['address'].lower() == POOL and len(event['topics']) == 3 and
                    event['topics'][0].lower() == LOAN_REQUESTED and number(event['topics'][2]) == loan_id and
                    ('0x' + event['topics'][1][-40:]).lower() == payload['borrower'].lower() and
                    int(event['data'][2:66], 16) == 1000000 and not event.get('removed', False),
                    'LoanRequested event fields mismatch')
            loans[loan_id] = payload
        elif kind == 'snapshot':
            snapshot_count += 1
            require(load(passed / (payload['label'] + '.json')) == payload, 'Snapshot file/journal mismatch')
            require(payload['pool']['token_balance'] == balances[POOL], 'Pool cash differs from transfer replay')
            for wallet in payload['wallets'].values():
                require(wallet['usdc_units'] == balances[wallet['address'].lower()], 'Actor cash differs from transfer replay')
            require(sum(w['usdc_units'] for w in payload['wallets'].values()) == payload['root_aggregate_usdc_units'],
                    'Snapshot aggregate differs from wallet sum')
        elif kind == 'expected_revert':
            negative_count += 1
            require(payload['mode'] == 'read_only_eth_call' and payload['actual_selector'] == payload['expected_selector'],
                    'Negative control differs from expected read-only rejection')
        elif kind == 'complete':
            require(complete is None, 'Multiple completion checkpoints')
            complete = record

    require(pending_intent is None and len(intents) == len(submitted) == len(receipts) == len(mined) == 59,
            'Transaction lifecycle/count mismatch')
    require(len(records) == 292 and snapshot_count == 8 and negative_count == 8, 'Unexpected trace counts')
    require(complete is not None and complete['payload'] == {k: v for k, v in evidence.items() if k != 'journal_tip_sha256'} and
            complete['record_sha256'] == evidence['journal_tip_sha256'], 'Completion checkpoint differs from evidence')
    cleanup = records[complete['sequence']:]
    require(len(cleanup) == 14 and all(r['kind'] == 'stop_local_impersonation' for r in cleanup), 'Missing post-completion cleanup')

    scenario_ids = []
    zero_fields = ('activeLoanCount', 'available_credit', 'borrow_limit', 'budget_held', 'creditCommitted',
                   'creditLoss', 'defaultedLoans', 'duesPaid', 'getCreditScore', 'grantedCredit', 'lenderBalance',
                   'lenderPrincipal', 'provider_score', 'queuedShares', 'queuedWithdrawals', 'scoreOverrides',
                   'sharesOf', 'stakeCommitted', 'stakeOf', 'unclaimedPayouts')
    for scenario in (1, 2, 3):
        boundary = load(passed / ('scenario%d-after.json' % scenario))
        result = load(passed / ('scenario%d-result.json' % scenario))
        require(result['scenario'] == scenario and result['status'] == 'passed' and result['mode'] == 'fork', 'Wrong scenario result')
        scenario_ids.append(result['loan_id_from_mined_receipt'])
        loan_id = result['loan_id_from_mined_receipt']
        borrower = initial['wallets'][result['borrower_role']]['address'].lower()
        require(loan_id in loans and loans[loan_id]['borrower'].lower() == borrower and loan_id in repayments,
                'Scenario does not bind to the actual borrowed/repaid loan')
        terminal_loan = boundary['loans'][str(loan_id)]
        require(terminal_loan['getLoan'][1] == 0 and terminal_loan['getLoan'][4] == 0 and
                terminal_loan['getLoanTerms'][0] == 3, 'Terminal loan is not fully repaid/closed')
        require(boundary['root_aggregate_usdc_units'] == 20000000 and boundary['pool'] == initial['pool'],
                'Boundary does not restore exact root/pool funds')
        require(boundary['provider']['totalHeld'] == 920000 and boundary['provider']['scores'][AVERY] == initial['provider']['scores'][AVERY],
                'Original provider budget/Avery changed')
        for wallet in boundary['wallets'].values():
            require(all(wallet['position'][key] == 0 for key in zero_fields) and not wallet['position']['backings_received'],
                    'Terminal actor financial position remains open')
    require(scenario_ids == [18, 19, 20], 'Wrong receipt-derived scenario loan IDs')
    require(set(loans) == set(disbursements) == set(repayments) == {18, 19, 20} and
            sorted(withdrawers) == sorted(initial['wallets']['s%d-funder' % i]['address'].lower() for i in (1, 2, 3)),
            'Loans or full-share withdrawals do not cover exactly the three scenarios')
    require(initial['root_aggregate_usdc_units'] == final['root_aggregate_usdc_units'] == 20000000 and
            final['pool'] == initial['pool'], 'Final baseline/pool mismatch')
    gas = sum(number(r['gasUsed']) * number(r['effectiveGasPrice']) for r in receipts.values())
    require(gas == evidence['gas_spent_wei'], 'Recorded fork gas differs from receipts')
    return {'status': 'passed', 'mode': 'offline_artifact_verification', 'network_calls': 0,
            'manifest_files': len(files), 'journal_records': len(records), 'mined_local_transactions': len(receipts),
            'token_transfer_logs_replayed': len(transfers), 'snapshots_reconciled': snapshot_count,
            'read_only_rejections': negative_count, 'loan_ids': scenario_ids,
            'repay_seconds_after_disbursement': [repayments[i] - disbursements[i] for i in scenario_ids],
            'root_initial_final_usdc_units': 20000000, 'existing_pool_usdc_units': 15000000,
            'journal_completion_sha256': complete['record_sha256'], 'journal_final_sha256': records[-1]['record_sha256'],
            'failed_attempts': failed,
            'limits': ['File integrity and internal consistency, not independent proof of execution or source provenance.',
                       'No live recovery/source settlement, outside income, autonomous reliability or general fraud-resistance proof.']}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.repo.resolve()), indent=2))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({'status': 'failed', 'mode': 'offline_artifact_verification', 'error': str(exc)}), file=sys.stderr)
        sys.exit(1)
