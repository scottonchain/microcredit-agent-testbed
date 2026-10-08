#!/usr/bin/env python3
"""Human pricing sensitivity, not a partner quote or borrowing authorization."""
import json
from decimal import Decimal, getcontext
getcontext().prec = 32

P = 25_000_000
DAYS = 30
BPS = 10_000
RATE = 433 + 1400  # EFFR plus risk PREMIUM, not 14% total APR.
YEAR = 365 * 86400
I = ((P * RATE) // BPS) * (DAYS * 86400) // YEAR
assert I == 376_643
reserve = I * 4500 // BPS  # Recorded reserve split; pilot configuration unchosen.

rows = []
for p_bps in (0, 300, 600, 1000):
    # Structural full principal loss, no recovery, no collectible interest on default.
    collectible_num = (BPS - p_bps) * I
    loss_num = p_bps * P
    shortage_num = max(0, loss_num - collectible_num)
    rows.append({'cycle_default_bps_assumption': p_bps, 'lgd_bps_assumption': BPS,
        'collectible_interest_micros_floor': collectible_num // BPS,
        'expected_principal_loss_micros': loss_num // BPS,
        'minimum_external_loss_support_micros_ceiling': (shortage_num + BPS - 1) // BPS,
        'servicing_and_other_costs': 'UNKNOWN, excluded from this lower bound'})

# Published Philippine physical cashout rate; FX/parity and selected route are assumptions.
exit_fee = P * 200 // BPS
net_received = P - exit_fee
annualized = Decimal(I + exit_fee) / Decimal(net_received) * Decimal(365) / DAYS * 100
result = {'scope': 'Structural sensitivity; no human loan, quotes or spendable payout',
    'loss_support_scope': 'Optimistic ecosystem lower bound: all collectible gross interest allocated to losses; not proof of configured reserve sufficiency',
    'principal_micros': P, 'elapsed_days': DAYS, 'premium_bps': 1400,
    'benchmark_bps': 433, 'total_apr_bps': RATE, 'contract_interest_micros': I,
    'recorded_reserve_bps_example': 4500,
    'successful_interest_to_reserve_micros': reserve,
    'successful_interest_remainder_micros': I - reserve,
    'no_cost_no_recovery_cycle_default_break_even_percent': str(Decimal(I) / (P + I) * 100),
    'loss_rows': rows,
    'borrower_paid_2pct_cashout_example': {'exit_fee_micros': exit_fee,
        'net_received_micros': net_received, 'repayment_micros': P + I,
        'simple_annualized_all_in_cost_percent': str(annualized),
        'not_legal_apr_or_quote': True,
        'repayment_spread_network_servicing_costs': 'UNKNOWN and not included'},
    'partner_servicing_cashout_repayment_costs': 'UNKNOWN, never zero',
    'human_eligible_or_launch_qualified': False}
assert reserve + (I - reserve) == I
assert net_received + exit_fee == P
assert all(x['minimum_external_loss_support_micros_ceiling'] >= 0 for x in rows)
print(json.dumps(result, indent=2))
