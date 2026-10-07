#!/usr/bin/env python3
"""Executable SOURCE-GROUNDED SIMULATION; no deployed contract or merchant payments."""
import argparse,json,hashlib,sys,importlib.util
from pathlib import Path
from engine import Graph,Refused
U=1000000;P=Path(__file__).resolve().parent
PRICE_SOURCE='https://github.com/scottonchain/microcredit-contract/issues/7#issuecomment-6049070792'
# Hermes captured unpaid merchant402 Exa search0.01, Base mainnet; no paid fulfilment.
BID=500000;LOAN=200000;INPUT=100000;INFERENCE=50000
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
class Cash:
 def __init__(self,b):self.b=dict(b);self.total=sum(b.values());self.records=[];self.tip='0'*64
 def event(self,kind,data):
  e=dict(seq=len(self.records)+1,previous=self.tip,kind=kind,data=data);self.tip=hashlib.sha256(canonical(e)).hexdigest();e['sha256']=self.tip;self.records.append(e)
 def move(self,a,b,x,reason):
  assert type(x)is int and x>=0 and self.b.get(a,0)>=x
  self.b[a]-=x;self.b[b]=self.b.get(b,0)+x;assert sum(self.b.values())==self.total
  self.event('modeled_usdc_transfer',dict(sender=a,recipient=b,units=x,reason=reason,balances=dict(self.b)))
def make():
 c=Cash(dict(lender=5*U,sponsor=U,buyer1=BID,buyer2=BID,buyer3=BID,worker1=0,worker2=0));g=Graph();g.root('sponsor',U,['*']);g.edge('sponsor','coordinator',U)
 for w in ['worker1','worker2']:g.edge('coordinator',w,500000)
 c.move('lender','pool',5*U,'modelled seed lender liquidity');c.move('sponsor','stake',U,'separate stake with explicit bounded onward delegation consent')
 return c,g

def useful_acceptance():
 base=P.parent/'work-product';spec=importlib.util.spec_from_file_location('independent_accept',base/'accept.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 raw=(base/'report.json').read_bytes();result=m.accept(json.loads(raw),base=base)
 return dict(result,report_sha256=hashlib.sha256(raw).hexdigest(),actual_paid_input_usdc_units=0,acceptance='Executed independent SOURCE/OUTPUT verifier, not a real commercial buyer')

def admit(c,g,worker,escrow,bid,input_cost=INPUT,inference=INFERENCE):
 # A serialized reference admission policy, not an EVM atomic escrow/loan adapter.
 if any(type(x)is not int or x<0 for x in [bid,input_cost,inference]):raise Refused('invalid invoice quantities')
 if c.b.get(escrow,0)<bid:raise Refused('customer escrow not funded')
 if input_cost+inference>LOAN:raise Refused('quote exceeds bounded loan budget')
 if bid<=LOAN+10000+5000:raise Refused('bid below worst-case cost/fee/gas budget')
 if c.b.get(worker,0)>=input_cost+inference:return None
 if c.b.get('pool',0)<LOAN:raise Refused('pool liquidity unavailable')
 lid=g.allocate(worker,LOAN)
 c.move('pool',worker,LOAN,'issuer-free2hop reference allocator disburses working capital')
 c.event('capacity_reserved',{'loan':lid,'path':['sponsor','coordinator',worker],'locked':dict(g.locked),'stake':dict(g.stake),'officer_grants':0})
 return lid

def success():
 c,g=make();accept=useful_acceptance();jobs=[]
 for i,(w,buyer) in enumerate([('worker1','buyer1'),('worker2','buyer2'),('worker1','buyer3')],1):
  job={'job':i,'worker':w,'buyer':buyer,'opening_worker_cash':c.b[w],'price_source':PRICE_SOURCE,'buyer_bid_units':BID,'buyer_bid_evidence':'MODELED funded bid, not observed outside customer','catalog_search_input_units':INPUT,'modeled_inference_units':50000,'native_eth_gas_usd_cap_assumption':.005,'interest_units':0,'officer_grants':0}
  c.move(buyer,'escrow'+str(i),BID,'modeled buyer funds escrow before delivery; worker cannot spend it yet')
  # Upper total cost budget .20; root1 -> coordinator -> new worker, no issuer/scoring key.
  lid=admit(c,g,w,'escrow'+str(i),BID);need=LOAN if lid else 0
  c.move(w,'modeled_API_merchant',INPUT,'SIMULATED10search calls at Hermes-observed catalog price0.01; no paid provider call');c.move(w,'modeled_inference',INFERENCE,'ASSUMED inference budget, not actual service invoice')
  c.event('output_acceptance',{'job':i,'report_sha256':accept['report_sha256'],'accepted':True,'actual_input_source':'free cached pinned public files; paid API is analog fixture, not incurred bill'})
  if lid:
   c.move('escrow'+str(i),'pool',need,'modeled contractual escrow repayment priority after acceptance');g.repay(lid,need)
  c.move('escrow'+str(i),w,BID-need,'modeled net customer settlement')
  c.move(w,'sponsor',10000 if lid else 0,'disclosed modeled success fee only if guaranteed loan')
  job.update(loan_units=need,loan_id=lid,closing_worker_cash=c.b[w],root_stake_locked=g.locked['sponsor'],unspent_principal_units=need-INPUT-INFERENCE if need else 0,work_source_real_cost_units=0)
  jobs.append(job)
 c.move('pool','lender',c.b['pool'],'modeled full lender withdrawal');g.unstake('sponsor',U);c.move('stake','sponsor',U,'all sponsor stake released')
 assert jobs[0]['opening_worker_cash']==jobs[1]['opening_worker_cash']==0
 assert jobs[0]['loan_units']==jobs[1]['loan_units']==LOAN and jobs[2]['loan_units']==0
 assert c.b['lender']==5*U and g.locked['sponsor']==0 and c.b['stake']==0
 return {'status':'passed_reference_bootstrap','jobs':jobs,'acceptance':accept,'seed_and_customers_total_units':c.total,'final_balances':c.b,'officer_grants':0,'current_deployment_used':False,'transitive_hops':2,'self_financing_repeat':True,'lender_yield_units':0,'lender_consent':'explicit mission/mechanics seed, not a commercially priced lender; grace loans earn0interest','ledger':c.records,'journal_tip':c.tip}

def failure():
 c,g=make();c.move('buyer1','rejected_job_escrow',BID,'modeled buyer funds conditional job');lid=g.reserve('worker1',LOAN,[(['sponsor','coordinator','worker1'],LOAN)]);c.move('pool','worker1',LOAN,'modeled loan');c.move('worker1','modeled_API_merchant',INPUT,'consumed modeled inputs');c.move('worker1','modeled_inference',INFERENCE,'consumed assumed inference');c.move('rejected_job_escrow','buyer1',BID,'rejected delivery refunds buyer, no revenue claimed');c.event('job_rejected',{'forced_cure':False,'synthetic_elapsed_seconds':61*86400,'default_rule':'reference driver enforces term30days+late30days strict greater; graph alone does not'})
 recovered=g.default(lid);c.move('stake','pool',recovered,'model default consumes backing, not officer grant');c.move('pool','lender',c.b['pool'],'model lender principal recovered after defaultdelay')
 return dict(status='failed_job_loss_contained_in_model',sponsor_loss_units=recovered,worker_cash_reclaimable_units=c.b['worker1'],lender_final_units=c.b['lender'],remaining_root_stake_units=g.stake['sponsor'],ledger=c.records,journal_tip=c.tip)

def output():
 return dict(schema='grounded-bootstrap-reference/1',scope='Actual accepted public-source work plus source-price-grounded economic/capacity simulation. No real customer/merchant payment, new EVM/fork execution, independent controllers, implemented onchain multi-hop or mainnet readiness.',basis={'paid_API_prices_source':PRICE_SOURCE,'actual_useful_work_known_usdc_cost':0,'modeled_API_cost':INPUT,'assumed_inference':INFERENCE,'assumed_retry_budget':LOAN-INPUT-INFERENCE,'assumed_ETH_gas_usd_cap':.005,'native_gas_precondition':'Seed operator/relayer supplies native gas; zero worker USDC is not zero infrastructure or free gas','assumed_success_fee':10000,'modeled_buyer_prices_not_quotes':[100000,150000,200000,500000,U]},bid_screen=[{'modeled_bid_units':x,'worst_case_minimum_price_usd':.20+.01+.005,'decision':'ACCEPT_SIMULATION_BID' if x/U>.215 else 'NO_LOAN','not_market_evidence':True} for x in [100000,150000,200000,500000,U]],success=success(),failure=failure(),comparators={'actual_cached_work':'NO_LOAN: real paid resource cost0; do not manufacture financing need','customer_prepay':'If available to worker before input, no need to borrow .20','direct_sponsor':'Can fund .20 directly with less committed capital; pool must justify standardized/cross-customer services, not assume superiority','trading':'Agent tool delegation/margin/flashloan not proof of profitable workingcapital; CoinbaseAgentKit specifically prohibits loan-funded digitalasset purchases'},mainnet='NO-GO until CI30/security/actual provider quote+customer terms and verified multi-hop enforcement/migration')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);a=parser.parse_args();s=json.dumps(output(),indent=2,sort_keys=True)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
