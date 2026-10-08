import json, subprocess
R = json.load(open('/root/work/live-sim-20261008/results.json'))
print('txs', len(R['txs']), 'gas_cost_wei', R['gas_wei'])
for n, c in sorted(R['cases'].items()):
    txs = [t for t in R['txs']]
    print('case', n, c['status'], 'loan', c['loan_id'], 'agg_before', c['aggregate_before_micro'], 'agg_after', c['aggregate_after_micro'],
          'blocks', c['disbursed_block'], c['repaid_block'], c['final_block'])
    print('  pool diffs', c['reconcile']['pool_state_diffs'], 'completed', c['reconcile']['borrower_completed'], 'dues', c['reconcile']['borrower_dues'])
    for r in c.get('refusals', []):
        print('  refusal', r['label'], r['revert_data'][:10], r['match'])
    print('  first/last', c['pool_before']['block'], c['pool_after']['block'])
print('--- per-case tx hashes')
import collections
for t in R['txs']:
    print(t['hash'], t['block'], t['gasUsed'], t['label'])
