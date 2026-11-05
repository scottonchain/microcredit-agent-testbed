import unittest
from decimal import Decimal as D
from fractions import Fraction as F
from itertools import product, combinations
from bounds import Budget, VerifiedCase
from stress import default_tail, liquidity_path, identity_attack, report


def case(i):
    return VerifiedCase('same-controller','same-group',f'fresh-proof-{i}',True,True,100)


class Stress(unittest.TestCase):
    def test_binomial_matches_exhaustive_enumeration(self):
        p=F(1,4)
        for threshold in range(6):
            expected=sum((p**sum(b)*(1-p)**(4-sum(b)) for b in product((0,1),repeat=4)
                          if sum(b)>=threshold),F(0))
            self.assertEqual(default_tail(4,p,threshold),expected)

    def test_probability_boundaries_and_invalid_inputs(self):
        self.assertEqual(default_tail(20,F(0),1),0)
        self.assertEqual(default_tail(20,F(1),20),1)
        for args in [(True,F(1,2),1),(20,.05,5),(20,F(2),5),(20,F(1,2),21.0)]:
            with self.assertRaises(ValueError): default_tail(*args)

    def test_common_shock_same_mean_but_over_nineteen_times_tail(self):
        r=report()
        self.assertEqual(20*10*F(1,20),r['same_mean_loss'])
        self.assertGreater(r['tail_ratio'],19)
        self.assertLess(r['independent_tail_probability'],.003)
        self.assertEqual(r['common_shock_tail_probability'],.05)

    def test_dependence_worst_case_attains_markov_bound(self):
        # Enumerate all15504 five-default subsets, not a Monte Carlo sample.
        counts=[0]*20
        total=0
        for subset in combinations(range(20),5):
            total+=1
            for i in subset: counts[i]+=1
        for count in counts: self.assertEqual(F(1,5)*F(count,total),F(1,20))
        self.assertEqual(F(1,5)*50,10)
        self.assertEqual(F(10,50),F(1,5))
        self.assertEqual(report()['worst_dependence_tail_probability'],.2)

    def test_classification_blindness_exposes_different_caps(self):
        for controller,group,accepted,loss in [(True,True,1,'10'),(False,True,3,'30'),(False,False,10,'100')]:
            self.assertEqual(identity_attack(known_controller=controller,known_group=group),
                             {'accepted':accepted,'realized_loss':loss})

    def test_recycled_cash_can_farm_turnover_without_cap_growth(self):
        b=Budget(100,10,30)
        for i in range(100):
            b.reserve(str(i),case(i),10,0)
            b.settle(str(i),10)
        # 100 repayments totaling1000 units: fee-free, no maturity, fresh trusted proofs;
        # this can be the same10 recycled100 times, not1000 independent events.
        self.assertEqual(sum(r['outcome'] for r in b.rows.values()),1000)
        self.assertEqual(b.person,10)
        with self.assertRaises(ValueError): b.reserve('large',case(101),11,0)
        b.reserve('final',case(102),10,0)
        b.settle('final',0)
        self.assertEqual(b.used(),10)

    def test_forged_repayment_not_detected_by_reference_budget(self):
        b=Budget(100,10,30)
        b.reserve('one',case(1),10,0)
        b.settle('one',10)  # unverified claim accepted: counterexample
        self.assertEqual(b.used(),0)
        self.assertTrue(b.reserve('two',case(2),10,0))

    def test_restart_loses_in_memory_reservations(self):
        before=Budget(10,10,10)
        before.reserve('pending',case(1),10,0)
        restarted=Budget(10,10,10)
        self.assertTrue(restarted.reserve('second',case(2),10,0))
        self.assertEqual(before.used()+restarted.used(),20)  # unsafe if both broadcast

    def test_positive_total_surplus_does_not_fix_early_shortfall(self):
        path=liquidity_path(0,[(0,0,0,10),(30,0,0,10)])
        self.assertEqual(path,[D(-10),D(10)])
        self.assertLess(min(path),0)

    def test_income_shock_breaks_positive_cash_path(self):
        self.assertEqual(liquidity_path(0,[(100,70,10,15)]*3),[D(5),D(10),D(15)])
        self.assertEqual(liquidity_path(0,[(80,70,10,15)]*3),[D(-15),D(-30),D(-45)])

    def test_five_clean_observations_cannot_certify_low_pd(self):
        upper=report()['five_zero_defaults_iid_upper95']
        self.assertAlmostEqual((1-upper)**5,.05)
        self.assertGreater(upper,.45)
