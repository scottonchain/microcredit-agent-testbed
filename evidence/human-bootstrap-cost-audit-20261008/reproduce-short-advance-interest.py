#!/usr/bin/env python3
"""Offline source-formula arithmetic; no keys, network, signing or chain access."""
from decimal import Decimal, getcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path

getcontext().prec = 50
ROOT = Path(__file__).resolve().parent
SOURCE = Path('/workspace/work/relayer-recheck/packages/foundry/contracts/DecentralizedMicrocredit.sol')
YEAR = 365 * 24 * 60 * 60
DAY = 86400
BPS = 10000
CENT = 10000
RESERVE_BPS = 4500
PROTOCOL_FEE_BPS = 0


def amount(micro):
    return f'{Decimal(micro) / Decimal(1000000):.6f}'


def rational(value):
    return {
        'numerator': str(value.numerator),
        'denominator': str(value.denominator),
        'decimal': str(Decimal(value.numerator) / Decimal(value.denominator)),
    }


def accrued(principal_micro, apr_bps, elapsed_seconds):
    if elapsed_seconds < DAY:
        return 0
    return ((principal_micro * apr_bps // BPS) * elapsed_seconds) // YEAR


scenarios = []
for label, premium, verification in [
    ('documented_testnet_933_bps', 500, 'Historical deployment documentation; no fresh RPC read'),
    ('calibrated_risk_case_1833_bps', 1400, 'Calibration scenario; not asserted deployed/current'),
]:
    apr = 433 + premium
    rows = []
    thresholds = []
    for principal_usdc in [1, 5, 25]:
        p = principal_usdc * 1000000
        annual_base = p * apr // BPS
        assert p * apr % BPS == 0  # First source floor is exact for these selected principals.
        for elapsed_days in [0, 1, 7, 30]:
            elapsed_seconds = elapsed_days * DAY
            i = accrued(p, apr, elapsed_seconds)
            dues = i * RESERVE_BPS // BPS
            fee = i * PROTOCOL_FEE_BPS // BPS
            closes = i < CENT
            rows.append({
                'principal_usdc': amount(p),
                'principal_micro_usdc': p,
                'elapsed_days': elapsed_days,
                'elapsed_seconds': elapsed_seconds,
                'annual_interest_micro_before_time_scaling': annual_base,
                'accrued_interest_micro_usdc': i,
                'accrued_interest_usdc': amount(i),
                'full_outstanding_micro_usdc': p + i,
                'full_outstanding_usdc': amount(p + i),
                'full_repayment': {
                    'cash_paid_micro_usdc': p + i,
                    'interest_allocation_micro_usdc': i,
                    'principal_allocation_micro_usdc': p,
                    'dues_credit_micro_usdc_at_45pct': dues,
                    'protocol_fee_micro_usdc_at_0pct': fee,
                    'lender_interest_micro_usdc_after_reserve_and_fee': i - dues - fee,
                    'forgiven_principal_micro_usdc': 0,
                },
                'principal_only_repayment_current_source': {
                    'cash_paid_micro_usdc': p,
                    'cash_paid_above_original_principal_micro_usdc': 0,
                    'interest_allocation_micro_usdc': i,
                    'principal_allocation_micro_usdc': p - i,
                    'principal_remaining_before_closure_micro_usdc': i,
                    'dues_credit_micro_usdc_at_45pct': dues,
                    'closes_under_cent_rule': closes,
                    'forgiven_principal_micro_usdc': i if closes else 0,
                    'outstanding_after_call_micro_usdc': 0 if closes else i,
                    'reserve_added_before_closure_micro_usdc': dues,
                    'reserve_burned_at_closure_micro_usdc_assuming_preexisting_reserve_zero': dues if closes else 0,
                    'reserve_remaining_micro_usdc_assuming_preexisting_reserve_zero': 0 if closes else dues,
                    'economic_interest_income_above_principal': 'none; ledger allocates part of principal-sized cash payment to interest',
                },
            })
        if principal_usdc in [1, 5]:
            unrounded_seconds = Fraction(CENT * BPS * YEAR, p * apr)
            unrounded_days = unrounded_seconds / DAY
            ceil_seconds = -(-unrounded_seconds.numerator // unrounded_seconds.denominator)
            source_seconds = -(-(CENT * YEAR) // annual_base)
            first_source_second = max(DAY, source_seconds)
            assert first_source_second == ceil_seconds
            assert accrued(p, apr, first_source_second - 1) < CENT
            assert accrued(p, apr, first_source_second) >= CENT
            thresholds.append({
                'principal_usdc': amount(p),
                'target_interest_micro_usdc': CENT,
                'unrounded_simple_interest_time_days': rational(unrounded_days),
                'unrounded_simple_interest_time_seconds': rational(unrounded_seconds),
                'ceil_seconds_to_unrounded_cent': ceil_seconds,
                'first_source_second_with_accrued_interest_at_least_cent': first_source_second,
                'source_interest_one_second_before_micro_usdc': accrued(p, apr, first_source_second - 1),
                'source_interest_at_threshold_micro_usdc': accrued(p, apr, first_source_second),
            })
    scenarios.append({
        'scenario': label,
        'effr_bps': 433,
        'risk_premium_bps': premium,
        'apr_bps': apr,
        'apr_percent': str(Decimal(apr) / 100),
        'verification': verification,
        'rows': rows,
        'cent_thresholds': thresholds,
    })

document = {
    'artifact': 'short-advance-interest-rows',
    'prepared_date_utc': '2026-10-08',
    'mode': 'offline_read_only_source_arithmetic',
    'chain_reads': 0,
    'transactions': 0,
    'source': {
        'local_path': str(SOURCE),
        'checkout_commit': '460875c897241d6b9d09877ca36da9fb696f2bf9',
        'git_blob': 'd06ebd2d8397d62840269314e87710d3c43bb89b',
        'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'canonical_source_url': 'https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol',
        'formulas_verified': {
            'loan_rate': 'effrRate + riskPremium, captured at origination',
            'annual_micro_floor': 'floor(principal_micro_usdc * loan_apr_bps / 10000)',
            'interest': '0 if disbursedAt==0 or elapsed_seconds<86400; otherwise floor(annual_micro_floor * elapsed_seconds / 31536000)',
            'outstanding': 'max(principal + accrued_interest - previous_payments, 0) while open',
            'repayment_allocation': 'interest first, then principal',
            'dues': 'floor(actual_interest_allocation * reserveBps / 10000)',
            'short_closure': 'owed - paid < 10000; closes and writes off unpaid principal, consuming reserve first',
        },
        'source_lines': {'constants': 36, 'rate': 1017, 'origination': 1255, 'repayment': 1300, 'closure': 1336, 'interest': 1412},
    },
    'assumptions': [
        'Active loan with nonzero disbursedAt and no previous payments',
        'Loan interestRate equals selected scenario APR at origination',
        'Reserve share4500bps and protocol fee0bps only for allocation columns',
        'USDC uses six decimal base units; no cents rounding in core accrued-interest calculation',
        'No compounding; original principal remains interest base until closure',
        'Rows and principal-only demonstrations are arithmetic, not instructions to exploit CI30',
    ],
    'scenarios': scenarios,
    'hypothetical_one_cent_flat_fee_on_one_usdc_for_one_day': {
        'implemented_by_current_source': False,
        'principal_usdc': '1.000000',
        'fee_usdc': '0.010000',
        'one_day_fee_as_principal_percent': '1',
        'simple_nominal_365_day_annualized_fee_percent': '365',
        'nominal_formula': '0.01 / 1 * 365 / 1 * 100',
        'hypothetical_daily_compounded_effective_annual_rate_percent': str(((Decimal('1.01') ** 365) - 1) * 100),
        'compounding_formula': '((1 + 0.01 / 1) ** 365 - 1) * 100',
        'limitation': 'Effective annual figure assumes365 consecutive identical daily rollovers and compounding; no such mechanism exists in this pool. Not a jurisdiction-specific legal APR disclosure.',
    },
    'verification_checks': [
        'Selected principal timesAPR exactly divisible by10000 before time scaling',
        'Threshold-1second source interest<10000 and threshold source interest>=10000 for1/5USDC under both APRs',
        '1833 and933 distinguished as calibration versus historical deployed documentation, not fresh live rate evidence',
    ],
}

destination = ROOT / 'short-advance-interest-rows.json'
destination.write_text(json.dumps(document, indent=2) + '\n')
print(json.dumps({'artifact': str(destination), 'rows': sum(len(s['rows']) for s in scenarios), 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'cent_thresholds': [{'apr_bps': s['apr_bps'], 'thresholds': s['cent_thresholds']} for s in scenarios]}))
