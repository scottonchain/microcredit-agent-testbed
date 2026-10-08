#!/usr/bin/env python3
"""Conditional retained-cash allocation; no quotes, keys, network or execution."""
import json
from decimal import Decimal
from pathlib import Path
from admission import service

fixture = json.loads(Path(__file__).with_name('fixtures.json').read_text())
case = next(x for x in fixture['cases'] if x['id'] == 'conditional_service')
working_capital = service(case)['principal_micros']
balance = 0
rows = []
for cycle in range(1, 5):
    result = service(dict(case, worker_cash=str(Decimal(balance) / 1_000_000)))
    balance += result['borrower_net_micros']
    rows.append({'cycle': cycle, 'loan_micros': result['principal_micros'],
        'earned_net_micros': result['borrower_net_micros'],
        'retained_cash_micros': balance})

stake = 1_000_000
uncommitted = balance - working_capital - stake
assert sum(x['earned_net_micros'] for x in rows) == balance
assert working_capital + stake + uncommitted == balance
print(json.dumps({'scope': 'UNQUALIFIED STRUCTURAL ASSUMPTIONS, not earnings',
    'cycles': rows, 'next_job_cash_micros': working_capital,
    'minimum_new_secured_edge_stake_micros': stake,
    'uncommitted_before_human_fees_micros': uncommitted,
    'notes': ['All earnings retained; cannot also count human payouts.',
        'Actual contract needs separately verified liquidity, secured edge and configuration.',
        'Finance/ramp fees and commercial demand remain unqualified.']}, indent=2))
