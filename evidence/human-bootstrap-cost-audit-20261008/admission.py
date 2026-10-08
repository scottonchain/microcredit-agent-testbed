#!/usr/bin/env python3
"""Structural admission calculator; never quotes, signs or moves funds."""
import json,sys
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
U=1000000

def micros(x):
 d=Decimal(str(x))*U
 if d!=d.to_integral_value(): raise ValueError('USD/USDC inputs must be exact six-decimal values')
 if d<0:raise ValueError('negative monetary input')
 return int(d)
def ceildiv(a,b):return -(-a//b)
def service(s):
 k={x:micros(s.get(x,'0')) for x in ['price','input','compute','work','gas','platform','refund_reserve','default_reserve','finance_fee','lender_cost','default_recovery','worker_cash','spendable_prepayment','sponsor_advance','ramp_fixed','payout_fixed']}
 if k['spendable_prepayment']>k['price']:raise ValueError('prepayment exceeds total buyer price')
 costs=sum(k[x] for x in ['input','compute','work','gas','platform','refund_reserve','default_reserve'])
 upfront=sum(k[x] for x in ['input','compute','work','gas'])
 need=max(0,upfront-k['worker_cash']-k['spendable_prepayment']-k['sponsor_advance'])
 fee=k['finance_fee'] if need else 0
 net=k['price']-costs-fee
 # Credit history does not offset expected loss; recovery must be realizable cash.
 stake=micros(s.get('stake_capacity','0'))
 if k['default_recovery']>stake:raise ValueError('recovery exceeds separate stake capacity')
 recovery=min(need,k['default_recovery']);loss=need-recovery
 p=int(s.get('default_probability_bps',0));assert 0<=p<=10000
 lender_expected_num=(10000-p)*fee-p*loss-10000*k['lender_cost'] if need else 0
 payout=max(0,net);ramp_bps=int(s.get('ramp_bps',0));payout_bps=int(s.get('payout_bps',0));assert 0<=ramp_bps<=10000 and 0<=payout_bps<=10000
 ramp=ceildiv(payout*ramp_bps,10000)+k['ramp_fixed'];transfer=ceildiv(max(0,payout-ramp)*payout_bps,10000)+k['payout_fixed']
 human=payout-ramp-transfer
 mode='NO_LOAN_EXISTING_CASH' if upfront<=k['worker_cash'] else 'NO_LOAN_PREPAYMENT' if need==0 and k['spendable_prepayment'] else 'NO_LOAN_DIRECT_SPONSORSHIP' if need==0 else 'WORKING_CAPITAL_NEEDED'
 admit=need>0 and net>0 and lender_expected_num>0
 subsidy=k['sponsor_advance']
 # Actual retained borrower cash includes a gift; earned output does not.
 wallet_delta=net+subsidy
 sponsor_expected_num=-10000*subsidy-p*recovery if need else -10000*subsidy
 accounting={'buyer_delta_micros':-k['price'],'borrower_delta_micros':wallet_delta,'lender_delta_micros':fee-k['lender_cost'] if need else 0,'sponsor_delta_micros':-subsidy,'vendors_platform_provisions_delta_micros':costs,'lender_cost_recipient_delta_micros':k['lender_cost'] if need else 0}
 assert sum(accounting.values())==0
 # Default: a single stake recovery debits sponsor exactly once, never lender capital.
 default_accounting={'buyer_delta_micros':-k['spendable_prepayment'],'borrower_delta_micros':need+k['spendable_prepayment']+subsidy-upfront,'lender_delta_micros':-need+recovery-k['lender_cost'],'sponsor_delta_micros':-recovery-subsidy,'upfront_vendors_delta_micros':upfront,'lender_cost_recipient_delta_micros':k['lender_cost']} if need else None
 if default_accounting:assert sum(default_accounting.values())==0
 return dict(case=s['id'],evidence=s['evidence'],demand_origin=s.get('demand_origin','HYPOTHETICAL_NOT_OBSERVED'),price_status=s.get('price_status','HYPOTHETICAL_NOT_ACCEPTED'),payment_provenance=s.get('payment_provenance','UNVERIFIED'),funded_order=False,observed_revenue=False,partner_cost_quote='UNKNOWN',principal_micros=need,borrower_net_micros=net,lender_default_loss_micros=loss,lender_expected_margin_micros_floor=lender_expected_num//10000,lender_expected_margin_numerator=lender_expected_num,mode=mode,conditional_economic_admission=admit,market_qualified=False,human_spendable_micros=human,retained_earnings_jobs_to_no_loan=ceildiv(need,net) if need and net>0 else None,exit_assumption='All positive net retained; paying humans reduces retained capital. No double counting human payout and reinvestment.',human_fees=dict(ramp_micros=ramp,payout_micros=transfer),human_route_economically_viable=human>0,human_fee_basis='Quoted hypothetical fees; no real deductions. Negative predicted surplus means no viable route',total_operating_cost_micros=costs,borrower_actual_cash_delta_micros=wallet_delta,non_earned_subsidy_ringfenced_micros=subsidy,sponsor_expected_loss_micros_ceiling=ceildiv(-sponsor_expected_num,10000),recovery_source=s.get('recovery_source','none'),success_conservation=accounting,default_conservation=default_accounting,ecosystem_default_loss_micros=upfront+k['lender_cost'] if need else 0,conditional_human_spendability=False,human_eligibility='UNVERIFIED: no actual identity/legal/ramp/withdrawal access or quotes',human_payout_basis='Earned resource-adjusted net only; gift excluded and ringfenced, not human income')
def keeper(s):
 t=s['terms'];v={k:int(x)for k,x in t.items()};assert v['debtWei']==v['nativePrincipalWei']+v['loanFeeWei'];b=v['expectedExternalRewardWei']-v['borrowerGasReservedWei']-v['loanFeeWei']-v['workCostWei'];l=v['loanFeeWei']-v['lenderGasReservedWei'];assert b==v['borrowerMarginAtReservedGasWei'] and l==v['lenderMarginAtReservedGasWei'];assert v['totalGasReservedWei']==v['borrowerGasReservedWei']+v['lenderGasReservedWei'];return dict(case=s['id'],evidence=s['evidence'],asset='ETH',principal_wei=v['nativePrincipalWei'],borrower_margin_wei=b,lender_margin_wei=l,total_margin_wei=b+l,decision='NO_LOAN',earned=False,market_qualified=False,reason='Borrower negative even with zero work cost; snapshot expired, lens not actual revenue, full cycle unsupported')
def run(p):
 f=json.loads(Path(p).read_text());return dict(scope=f['scope'],results=[keeper(s) if s['kind']=='keeper' else service(s)for s in f['cases']])
if __name__=='__main__':print(json.dumps(run(sys.argv[1] if len(sys.argv)>1 else Path(__file__).with_name('fixtures.json')),indent=2))
