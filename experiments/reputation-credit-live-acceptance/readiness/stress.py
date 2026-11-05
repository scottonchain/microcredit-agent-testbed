"""Exact synthetic stress calculations; NOT a PD model or production policy.
No fitting, network, random sampling or human records. Run to reproduce report.
"""
from fractions import Fraction as F
from math import comb
import json
from bounds import Budget, VerifiedCase, amount


def default_tail(n, p, minimum_defaults):
    """Exact binomial tail: independent, identical Bernoulli defaults only."""
    if type(n) is not int or not 1 <= n <= 1000:
        raise ValueError('bounded integer cohort required')
    if type(minimum_defaults) is not int or not 0 <= minimum_defaults <= n + 1:
        raise ValueError('invalid threshold')
    if not isinstance(p, F) or not 0 <= p <= 1:
        raise ValueError('exact probability required')
    return sum((F(comb(n,k))*p**k*(1-p)**(n-k)
                for k in range(minimum_defaults,n+1)), F(0))


def liquidity_path(opening, periods):
    """End-period cash; receipts must be usable BEFORE that period's debts.
    Rows: receipts, essentials, existing debt, proposed debt. Negative cash is
    timing insufficiency, not fraud. Within-period timing/provenance excluded.
    """
    balance=amount(opening)
    path=[]
    for row in periods:
        if len(row)!=4: raise ValueError('four period cash flows required')
        receipts,essential,existing,proposed=map(amount,row)
        balance+=receipts-essential-existing-proposed
        path.append(balance)
    if not path: raise ValueError('at least one period required')
    return path


def identity_attack(*, known_controller, known_group):
    """20 colluding aliases ask10 each then default; caps100/person10/group30.
    Classification is an oracle assumption, NOT inferred from wallets or trust.
    """
    budget=Budget(100,10,30)
    accepted=0
    for i in range(20):
        case=VerifiedCase('same' if known_controller else f'person-{i}',
                          'same' if known_group else f'group-{i}',
                          f'proof-{i}',True,True,100)
        try: budget.reserve(f'intent-{i}',case,10,0)
        except ValueError: continue
        budget.settle(f'intent-{i}',0)
        accepted+=1
    return {'accepted':accepted,'realized_loss':str(budget.used())}


def report():
    p,n=F(1,20),20
    independent=default_tail(n,p,5)  # exposure10,LGD1: loss>=50 iff defaults>=5
    common_shock=p  # all20 default together with probability p, else none
    return {
        'kind':'ILLUSTRATIVE_OFFLINE_STRESS_NOT_CALIBRATION',
        'assumptions':{'borrowers':n,'exposure_each':10,'marginal_pd':str(p),'lgd':1,'loss_tail_threshold':50},
        'same_mean_loss':10,
        'independent_tail_probability_exact':str(independent),
        'independent_tail_probability':float(independent),
        'common_shock_tail_probability':float(common_shock),
        'tail_ratio':float(common_shock/independent),
        'worst_dependence_tail_probability':float(F(1,5)),
        'worst_dependence_to_iid_ratio':float(F(1,5)/independent),
        'worst_dependence_construction':'With probability1/5 choose exactly5 of20 uniformly to default; otherwise none. Marginal PD=(1/5)*(5/20)=1/20. Tail attains Markov mean10/threshold50=1/5.',
        'identity_classification_sensitivity':{
            'controller_known':identity_attack(known_controller=True,known_group=True),
            'group_only_known':identity_attack(known_controller=False,known_group=True),
            'both_missed':identity_attack(known_controller=False,known_group=False)},
        'timing_shortfall':[str(x) for x in liquidity_path(0,[(0,0,0,10),(30,0,0,10)])],
        'five_zero_defaults_iid_upper95':1-.05**(1/5),
        'warning':'Five usability sessions are not five repayment observations; IID bound does not apply to them.'}


if __name__=='__main__': print(json.dumps(report(),indent=2))
