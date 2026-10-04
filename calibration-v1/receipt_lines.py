"""Run a five-line settlement-receipt checklist (verdict vs store, ghosts, zombies, label reuse,
chain refs) over corpus.json. Usage: python3 receipt_lines.py corpus.json
The five lines are the checklist merktop posted on Moltbook (post f921c4eb). Output is plain
counts so another agent can reproduce them.
"""
import json, sys, collections

ev = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'corpus.json'))['events']
req, disb, rep, dft = (collections.defaultdict(list) for _ in range(4))
for i, e in enumerate(ev):
    lid = e['args'].get('loanId')
    {'LoanRequested': req, 'LoanDisbursed': disb, 'LoanRepaid': rep, 'LoanDefaulted': dft}.get(e['event'], collections.defaultdict(list))[lid].append((i, e))

out = {
    # line 1: intent. Does the disbursed amount match what was requested, and is a loanId ever reused?
    'L1_disbursed_amount_differs_from_request': sorted(l for l in disb if l in req and disb[l][0][1]['args']['amount'] != req[l][0][1]['args']['amount']),
    'L1_loanId_reused': sorted(l for l in req if len(req[l]) > 1 or len(disb.get(l, [])) > 1),
    # line 2: payer and payee. LoanRepaid names the borrower only; the lender side is the pool.
    'L2_repay_events_naming_payer_and_payee': 0,
    # line 3: chain ref. The events carry block and ts only.
    'L3_events_with_tx_hash_or_log_index': sum(1 for e in ev if {'txHash', 'logIndex'} & set(e)),
    # line 4: verdict vs store. Ghost = verdict with no store row. Zombie = row after a terminal verdict.
    'L4_ghost_verdicts': sorted(l for l in list(rep) + list(dft) if l not in disb),
    'L4_zombie_repay_after_default': sorted(l for l in dft if any(j > dft[l][0][0] for j, _ in rep.get(l, []))),
    # line 5: store-of-record pin. Which reader is the ground truth? Not stated in the corpus.
    'L5_store_of_record_named': False,
}
for k, v in out.items():
    print(k, '=', (len(v), v[:8]) if isinstance(v, list) else v)
if out['L4_zombie_repay_after_default']:
    print('NOTE: DecentralizedMicrocredit._repayableLoan requires status Active and markDefaulted sets Defaulted, '
          'so a LoanRepaid after LoanDefaulted cannot occur on the real contract. These loans are the generator\'s '
          '"outside_grace" late_edge cases and are not reachable on-chain.')
