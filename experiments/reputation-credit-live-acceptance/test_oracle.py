"""Independent arithmetic/state vectors; these tests perform no chain calls."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, Inexact, ROUND_HALF_UP
import unittest

from oracle import (Allocation, Cashflow, ReportConflict, ReputationLedger, ReservationTerminal, affordability,
                    break_even_charge, brier_penalty, display_score, margin, root_budget)

D = Decimal


class ArithmeticTests(unittest.TestCase):
    def test_score_reference_vectors(self):
        vectors = [('0.05', '600.00'), ('0.03', '638.35'), ('0.06', '586.08'),
                   ('0', '850.00'), ('1', '300.00'), ('0.000001', '850.00'),
                   ('0.999999', '300.00')]
        for probability, expected in vectors:
            with self.subTest(probability=probability):
                self.assertEqual(display_score(probability).quantize(D('.01'), rounding=ROUND_HALF_UP), D(expected))

    def test_unavailable_score_is_not_zero_risk(self):
        self.assertIsNone(display_score(None))
        for invalid in ['-0.1', '1.1', 'NaN', 'Infinity', .03, True]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                display_score(invalid)

    def test_score_direction(self):
        values = [display_score(p) for p in ['.001', '.01', '.03', '.06', '.1', '.5']]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_expected_margin_and_break_even(self):
        self.assertEqual(margin('.06', '2', '1', '100', '1', '0', '0'), D('-5.12'))
        self.assertEqual(break_even_charge('.06', '1', '100', '1', '0', '0'), D(350)/47)
        self.assertEqual(break_even_charge('.06', '1', '100', '1', '0', '0').quantize(D('.01')), D('7.45'))
        self.assertEqual(margin('0', '2', '1', '100', '1', '.25', '.5'), D('.25'))
        self.assertEqual(break_even_charge('0', '1', '100', '1', '.25', '.5'), D('1.75'))

    def test_break_even_impossible_and_cost_validation(self):
        with self.assertRaises(ValueError):
            break_even_charge('1', '1', '100', '1', '0', '0')
        for values in [('.06', '2', '1', '-100', '1', '0', '0'), ('.06', '2', '1.1', '100', '1', '0', '0')]:
            with self.assertRaises(ValueError):
                margin(*values)

    def test_every_date_affordability_not_final_balance_only(self):
        rows = [Cashflow(D('20'), D('20'), D('0'), D('10')),
                Cashflow(D('100'), D('20'), D('0'), D('10'))]
        self.assertEqual(affordability('5', rows), ((D('-5'), D('65')), False))

    def test_loan_proceeds_never_fund_repayment(self):
        rows = [Cashflow(D('20'), D('20'), D('5'), D('10'), D('1000000'))]
        self.assertEqual(affordability('0', rows), ((D('-15'),), False))

    def test_cumulative_affordability_boundary(self):
        rows = [Cashflow(D('10'), D('5'), D('2'), D('3')),
                Cashflow(D('10'), D('5'), D('2'), D('3.000001'))]
        self.assertEqual(affordability('0', rows), ((D('0'), D('-.000001')), False))
        self.assertEqual(affordability('.000001', rows), ((D('.000001'), D('0')), True))

    def test_root_budget_and_brier_vectors(self):
        self.assertEqual(root_budget('100', '0'), D('20'))
        self.assertEqual(root_budget('10', '0'), D('2'))
        self.assertEqual(root_budget('10', '3'), D('0'))
        self.assertEqual(brier_penalty('15', '.03', True), D('14.1135'))
        self.assertEqual(brier_penalty('15', '.03', False), D('.0135'))
        self.assertEqual(brier_penalty('15', '1', False), D('15'))
        self.assertEqual(brier_penalty('15', '0', False), D('0'))
        with self.assertRaises(ValueError):
            brier_penalty('15', '.03', 1)


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.ledger = ReputationLedger()
        self.ledger.set_target('root', '100')

    def reserve(self, loan='loan', u='15', q='.03', path=('root', 'borrower')):
        return self.ledger.reserve(loan, 'root', u, q, [Allocation(path, D(u))])

    def test_exact_limit_and_one_unit_above(self):
        self.assertTrue(self.reserve(u='20'))
        self.assertEqual(self.ledger.available('root'), D('0'))
        with self.assertRaises(ValueError):
            self.reserve(loan='other', u='.000001')

    def test_concurrent_competing_reservations_cannot_double_spend(self):
        def attempt(loan):
            try:
                return self.reserve(loan=loan)
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, ['loan1', 'loan2']))
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.ledger.locked('root'), D('15'))

    def test_exact_retry_is_idempotent_and_changed_retry_rejected(self):
        self.assertTrue(self.reserve())
        self.assertFalse(self.reserve())
        self.assertEqual(self.ledger.locked('root'), D('15'))
        with self.assertRaises(ValueError):
            self.reserve(u='14')

    def test_drop_grandfathers_existing_lock_and_blocks_new_capacity(self):
        self.reserve()
        self.ledger.set_target('root', '10')
        self.assertEqual(self.ledger.budget('root'), D('2'))
        self.assertEqual(self.ledger.locked('root'), D('15'))
        self.assertEqual(self.ledger.available('root'), D('0'))
        with self.assertRaises(ValueError):
            self.reserve(loan='other', u='.000001')
        self.ledger.settle('loan', 'root', False, 'label1')
        self.assertEqual(self.ledger.available('root'), D('1.9865'))

    def test_default_and_nondefault_penalties_exactly_once(self):
        for defaulted, penalty in [(True, '14.1135'), (False, '.0135')]:
            with self.subTest(defaulted=defaulted):
                self.setUp()
                self.reserve()
                self.assertTrue(self.ledger.settle('loan', 'root', defaulted, 'label1'))
                self.assertFalse(self.ledger.settle('loan', 'root', defaulted, 'label1'))
                self.assertEqual(self.ledger.penalties['root'], D(penalty))
                self.assertEqual(self.ledger.locked('root'), D('0'))
                self.assertEqual(self.ledger.skill_updates[('loan', 'root')], 1)
                with self.assertRaises(ValueError):
                    self.ledger.settle('loan', 'root', not defaulted, 'label2')

    def test_upheld_correction_replaces_prior_penalty_without_new_observation(self):
        self.reserve()
        self.ledger.settle('loan', 'root', True, 'label1')
        self.assertTrue(self.ledger.correct('loan', 'root', False, 'appeal1'))
        self.assertFalse(self.ledger.correct('loan', 'root', False, 'appeal1'))
        self.assertEqual(self.ledger.penalties['root'], D('.0135'))
        self.assertEqual(self.ledger.skill_updates[('loan', 'root')], 1)
        self.assertEqual(self.ledger.available('root'), D('19.9865'))
        with self.assertRaises(ValueError):
            self.ledger.correct('loan', 'root', True, 'appeal1')

    def test_cancellation_does_not_train_or_penalize(self):
        self.reserve()
        self.assertTrue(self.ledger.cancel_before_disbursement('loan', 'root'))
        self.assertFalse(self.ledger.cancel_before_disbursement('loan', 'root'))
        self.assertEqual(self.ledger.available('root'), D('20'))
        self.assertEqual(self.ledger.skill_updates, {})
        self.assertEqual(self.ledger.penalties['root'], D('0'))
        with self.assertRaises(ValueError):
            self.ledger.settle('loan', 'root', False, 'label1')
        with self.assertRaises(ValueError):
            self.ledger.correct('loan', 'root', False, 'appeal1')

    def test_old_reservation_replay_never_relocks_settled_loan(self):
        self.reserve()
        self.ledger.settle('loan', 'root', True, 'label1')
        with self.assertRaises(ReservationTerminal):  # was False before the 433 amendment: indistinguishable from "a lock exists"
            self.reserve()
        self.assertEqual(self.ledger.locked('root'), D('0'))
        self.assertEqual(self.ledger.penalties['root'], D('14.1135'))

    def test_reserve_false_means_only_an_exact_retry_of_an_active_reservation(self):
        self.assertTrue(self.reserve())
        self.assertFalse(self.reserve())                       # active exact retry
        self.assertEqual(self.ledger.locked('root'), D('15'))

    def test_cancelled_identity_is_terminal_and_never_reopened(self):
        self.reserve()
        self.ledger.cancel_before_disbursement('loan', 'root')
        with self.assertRaises(ReservationTerminal):
            self.reserve()                                     # exact retry must not read as an open lock
        with self.assertRaises(ValueError):
            self.reserve(u='14')                               # changed fields
        self.assertEqual(self.ledger.locked('root'), D('0'))
        self.assertNotIn(('loan', 'root'), self.ledger.open)

    def test_settled_identity_retry_after_correction_is_also_terminal(self):
        self.reserve()
        self.ledger.settle('loan', 'root', True, 'label1')
        self.ledger.correct('loan', 'root', False, 'appeal1')
        with self.assertRaises(ReservationTerminal):
            self.reserve()
        self.assertEqual(self.ledger.locked('root'), D('0'))

    def test_late_original_report_after_correction_is_a_noop_preserving_the_corrected_outcome(self):
        self.reserve()
        self.assertTrue(self.ledger.settle('loan', 'root', True, 'rep1'))
        self.assertTrue(self.ledger.correct('loan', 'root', False, 'corr1'))
        corrected = self.ledger.penalties['root']
        self.assertFalse(self.ledger.settle('loan', 'root', True, 'rep1'))   # exact old delivery
        self.assertEqual(self.ledger.penalties['root'], corrected)
        self.assertFalse(self.ledger.outcomes[('loan', 'root')].defaulted)
        self.assertEqual(self.ledger.skill_updates[('loan', 'root')], 1)

    def test_reused_report_identity_with_changed_label_rejects_even_after_a_correction(self):
        self.reserve()
        self.ledger.settle('loan', 'root', True, 'rep1')
        self.ledger.correct('loan', 'root', False, 'corr1')
        with self.assertRaises(ReportConflict):
            self.ledger.settle('loan', 'root', False, 'rep1')              # a bare id set would hide this conflict
        with self.assertRaises(ReportConflict):
            self.ledger.correct('loan', 'root', True, 'corr1')
        with self.assertRaises(ReportConflict):
            self.ledger.correct('loan', 'root', False, 'rep1')             # one namespace: rep1 carried True
        with self.assertRaises(ValueError):
            self.ledger.settle('loan', 'root', True, 'rep2')               # a NEW id still needs an explicit correction
        self.assertFalse(self.ledger.outcomes[('loan', 'root')].defaulted)

    def test_ledger_arithmetic_fails_closed_instead_of_rounding(self):
        sub_precision = D('0.' + '0' * 59 + '1')                          # 1e-60: below what 60 digits can add to 10
        paths = [Allocation(('root', 'borrower'), D('10')), Allocation(('root', 'b2', 'borrower'), sub_precision)]
        with self.assertRaises(Inexact):
            self.ledger.reserve('loan', 'root', D('10'), '.03', paths)     # was accepted as summing to exactly 10
        self.assertEqual(self.ledger.locked('root'), D('0'))
        self.assertNotIn(('loan', 'root'), self.ledger.history)

    def test_trapped_settlement_leaves_the_reservation_open_and_the_penalty_unchanged(self):
        units = D('1.' + '1' * 30)
        pd = '0.' + '3' * 30
        self.ledger.reserve('loan', 'root', units, pd, [Allocation(('root', 'borrower'), units)])
        before = (dict(self.ledger.penalties), dict(self.ledger.open), dict(self.ledger.outcomes))
        for label in (True, False):
            with self.subTest(label=label), self.assertRaises(Inexact):
                self.ledger.settle('loan', 'root', label, 'rep1')
        self.assertEqual((dict(self.ledger.penalties), dict(self.ledger.open), dict(self.ledger.outcomes)), before)
        self.assertEqual(self.ledger.locked('root'), units)
        self.assertEqual(self.ledger.skill_updates, {})

    # ---- PROVISIONAL REFERENCE SEMANTICS (not finalized mechanism or underwriting policy) ----
    def test_provisional_self_path_is_rejected_by_the_reference_ledger(self):
        with self.assertRaises(ValueError):
            self.ledger.reserve('loan', 'root', '5', '.03', [Allocation(('root', 'root'), D('5'))])
        self.assertEqual(self.ledger.locked('root'), D('0'))

    def test_provisional_independent_roots_counts_every_recorded_identity(self):
        self.reserve(loan='cancelled-loan')
        self.ledger.cancel_before_disbursement('cancelled-loan', 'root')
        self.assertEqual(self.ledger.independent_roots('cancelled-loan'), frozenset(['root']))
        self.reserve(loan='settled-loan', u='1')
        self.ledger.settle('settled-loan', 'root', False, 'rep1')
        self.assertEqual(self.ledger.independent_roots('settled-loan'), frozenset(['root']))

    def test_old_correction_retry_never_reapplies_superseded_label(self):
        self.reserve()
        self.ledger.settle('loan', 'root', True, 'label1')
        self.ledger.correct('loan', 'root', False, 'appeal1')
        self.ledger.correct('loan', 'root', True, 'appeal2')
        self.assertFalse(self.ledger.correct('loan', 'root', False, 'appeal1'))
        self.assertEqual(self.ledger.penalties['root'], D('14.1135'))
        self.assertEqual(self.ledger.skill_updates[('loan', 'root')], 1)

    def test_penalty_reduction_does_not_erase_other_loans_penalties(self):
        self.reserve(loan='one', u='10')
        self.reserve(loan='two', u='10')
        self.ledger.settle('one', 'root', True, 'label-one')
        self.ledger.settle('two', 'root', True, 'label-two')
        self.assertEqual(self.ledger.penalties['root'], D('18.818'))
        self.ledger.correct('one', 'root', False, 'appeal-one')
        self.assertEqual(self.ledger.penalties['root'], D('9.418'))
        self.assertEqual(self.ledger.skill_updates, {('one', 'root'): 1, ('two', 'root'): 1})

    def test_split_paths_share_one_original_budget_and_observation(self):
        paths = [Allocation(('root', 'a', 'borrower'), D('8')),
                 Allocation(('root', 'b', 'borrower'), D('7'))]
        self.ledger.reserve('loan', 'root', '15', '.03', paths)
        self.assertEqual(self.ledger.locked('root'), D('15'))
        self.assertEqual(self.ledger.independent_roots('loan'), frozenset(['root']))
        self.ledger.settle('loan', 'root', True, 'label1')
        self.assertEqual(self.ledger.penalties['root'], D('14.1135'))
        self.assertEqual(self.ledger.skill_updates[('loan', 'root')], 1)

    def test_alias_root_cannot_spend_received_influence(self):
        self.reserve(path=('root', 'alias', 'borrower'))
        with self.assertRaises(ValueError):
            self.ledger.reserve('other', 'alias', '1', '.03', [Allocation(('alias', 'b'), D('1'))])

    def test_invalid_paths_and_missing_units(self):
        invalid = [
            [Allocation(('root', 'a', 'b', 'borrower'), D('15'))],
            [Allocation(('root', 'root', 'borrower'), D('15'))],
            [Allocation(('otherroot', 'borrower'), D('15'))],
            [Allocation(('root', 'borrower'), D('14'))],
            [Allocation(('root', 'borrower'), D('10')), Allocation(('root', 'borrower'), D('5'))],
            [Allocation(('root', 'b1'), D('10')), Allocation(('root', 'b2'), D('5'))],
        ]
        for paths in invalid:
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                self.ledger.reserve('loan', 'root', '15', '.03', paths)
        self.assertEqual(self.ledger.locked('root'), D('0'))


if __name__ == '__main__':
    unittest.main()
