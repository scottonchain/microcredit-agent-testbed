#!/usr/bin/env python3
import json
from pathlib import Path
from admission import micros,service,keeper
p=Path(__file__).parent;f=json.loads((p/'fixtures.json').read_text());s=f['cases'][1];a=service(s)
# Decimal input cannot silently discard value beyond token precision.
try:micros('.0000001');raise AssertionError('fractional token accepted')
except ValueError:pass
assert micros('0.485000')==485000
# A profitable job cannot create loan necessity after all upfront costs are prepaid.
assert service(dict(s,spendable_prepayment='.485'))['principal_micros']==0
# Added operating expense cannot improve borrower net/human proceeds.
for x in ['input','compute','work','gas','platform','refund_reserve','default_reserve']:
 from decimal import Decimal
 b=service(dict(s,**{x:str(Decimal(s[x])+Decimal('.000001'))}));assert b['borrower_net_micros']<=a['borrower_net_micros'] and b['human_spendable_micros']<=a['human_spendable_micros']
# More default probability or less recovery cannot increase lender margin.
assert service(dict(s,default_probability_bps=200))['lender_expected_margin_numerator']<=a['lender_expected_margin_numerator']
assert service(dict(s,default_recovery='.10'))['lender_expected_margin_numerator']<a['lender_expected_margin_numerator']
# Native principal is return of funding, never revenue; complete cost split conserved.
k=keeper(f['cases'][0]);t={z:int(v)for z,v in f['cases'][0]['terms'].items()};assert k['total_margin_wei']==t['expectedExternalRewardWei']-t['totalGasReservedWei']-t['workCostWei'];assert k['borrower_margin_wei']<0
# Human fee rounding always conserves surplus and cannot manufacture micros.
assert a['human_spendable_micros']+sum(a['human_fees'].values())==a['borrower_net_micros']
# Retained capital exit and human payout are mutually exclusive allocations.
assert a['retained_earnings_jobs_to_no_loan']==2

# A nonrepayable gift changes borrower cash but creates no earned resource profit.
g=service(dict(s,sponsor_advance='.485'));assert g['borrower_actual_cash_delta_micros']==920000 and g['borrower_net_micros']==435000 and g['success_conservation']['sponsor_delta_micros']==-485000
assert g['borrower_actual_cash_delta_micros']-g['non_earned_subsidy_ringfenced_micros']==g['borrower_net_micros']
# Sponsor cash cannot protect lender without an equal sponsor debit on default.
assert sum(a['success_conservation'].values())==sum(a['default_conservation'].values())==0
assert a['default_conservation']['sponsor_delta_micros']==-485000 and a['sponsor_expected_loss_micros_ceiling']==4850
try:service(dict(s,stake_capacity='.10'));raise AssertionError('unfunded recovery accepted')
except ValueError:pass
assert not a['conditional_human_spendability']

# Mixed default financing uses actual buyer/grant cash, not fictitious negative borrower funding.
m=service(dict(f['cases'][1],worker_cash='.10',spendable_prepayment='.10',sponsor_advance='.10'))
assert m['principal_micros']==185000
assert m['default_conservation']['buyer_delta_micros']==-100000
assert m['default_conservation']['sponsor_delta_micros']==-285000
assert m['default_conservation']['borrower_delta_micros']==-100000
assert sum(m['default_conservation'].values())==0
try:service(dict(f['cases'][1],spendable_prepayment='1.000001'));raise AssertionError('prepayment exceeds price')
except ValueError:pass
z=service(dict(f['cases'][1],ramp_fixed='1'));assert z['human_spendable_micros']<0 and not z['human_route_economically_viable']
print(json.dumps({'passed':True,'checks':['exact sixdecimal precision','prepayment removes necessity','operating cost monotonicity','default probability/recovery monotonicity','native cycle conservation excludes principal','human quoted fee conservation','retained earnings exit','grant exclusion from earnings','success/default party conservation','sponsor-funded recovery and stake capacity','human eligibility unverified','mixed cash/prepayment/grant default conservation','prepayment bounded by total price','negative human surplus rejects payout route']},indent=2))
