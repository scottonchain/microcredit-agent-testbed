#!/usr/bin/env python3
"""Deterministic economic/source arithmetic; NOT EVM or customer execution."""
import json,argparse
from pathlib import Path
U=1000000; DAY=86400
def interest(p,t):return 0 if t<DAY else (p*933//10000)*t//31536000
def job(days,accepted=True,fee=3000000):
 b=dict(lender=500*U,sponsor=100*U,worker=10*U,customer=150*U,input_vendor=0,execution_vendor=0,pool=0,stake=0,reserve=0)
 initial=sum(b.values());trace=[]
 def move(a,z,x,label):
  assert 0<=x<=b[a];b[a]-=x;b[z]+=x;assert sum(b.values())==initial
  trace.append(dict(event=label,sender=a,recipient=z,units=x,balances=dict(b)))
 move('lender','pool',500*U,'distinct liquidity');move('sponsor','stake',100*U,'secured backing, zero free grant');move('pool','worker',100*U,'borrow');move('worker','input_vendor',100*U,'modeled input');move('worker','execution_vendor',10*U,'modeled execution')
 i=interest(100*U,days*DAY);r=0
 if accepted:
  move('customer','worker',150*U,'modeled customer settlement');move('worker','pool',100*U+i,'full repayment');r=i*4500//10000;move('pool','reserve',r,'protected dues');move('stake','sponsor',100*U,'released stake');move('worker','sponsor',fee,'off-contract success fee');move('pool','lender',500*U+i-r,'full withdrawal')
 else:
  assert days>60,'30day term+30day late, strict >';move('stake','pool',100*U,'eligible default slash, no forced cure');move('pool','lender',500*U,'principal recovered after delay')
 return dict(branch='paid' if accepted else 'failed',days=days,interest_units=i,repay_units=100*U+i if accepted else 0,reserve_dues_units=r,net_surplus_usd=(b['worker']-10*U)/U-.5,sponsor_principal_loss_units=0 if accepted else 100*U,lender_principal_loss_units=0,initial_total_units=initial,final_total_units=sum(b.values()),final_balances=b,trace=trace,gas='Separate ETH expense priced at USD0.50; not a USDC transfer. Customer/input/controller facts are assumptions.')
def suite():
 i=interest(100*U,7*DAY)
 return dict(schema='coldstart-economic-suite/1',scope='Three agent communities plus deterministic source-arithmetic branches; no EVM, new wallets, actual customers or independent-controller proof.',success=job(7),delayed_success=job(45,fee=0),failure=job(61,False),commercial=dict(lender_gain_units=i-i*4500//10000,lender_outside_option_units=500*U*300*7//(10000*365),required_utilization_before_costs=.03/(.0933*.55),decision='500 liquidity funding100: commercial lender refuses3pct outside option; mission subsidy or improved utilization required',parameters='APR933bps,reserve4500bps,fee0 are historical; gas, default probability and opportunity rates uncalibrated'),attacks=dict(secured_coalition=dict(borrowed_units=100*U,stake_lost_units=100*U,principal_net_gain_units=0,ten_grace_rounds_dues_units=0,limits='Free temporary liquidity/interest avoidance possible; not complete incentive proof'),grant_first=dict(granted_units=100*U,stake_units=100*U,secured_edge_units=0,unsecured_edge_units=100*U,lender_default_loss_units=100*U),issuer_reset=dict(active_budget_units=100*U,loss_control='Active budget can be reissued after default; cumulative losses can exceed100, subject to remaining liquidity/origination gates. Require nonrenewing lifetime pilot risk cap.'),ci30=dict(cycles=10,borrow_units=9999,pay_units=1,coalition_gain_units=99980,stake_slashed_units=0),multi_backer_rounding=dict(principal_units=U,secured_edges_units=[U,U,U],recovered_units=3*(U//3),lender_loss_units=1)),mainnet_readiness='NO-GO: deployed CI30 defect; independent demand, settlement and deployment/operator controls unverified')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();s=json.dumps(suite(),indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
