import unittest,hashlib
from run_bootstrap import output,canonical,make,admit
from engine import Refused
class Bootstrap(unittest.TestCase):
 def test_actual_acceptance_and_zeroofficer_bootstrap(self):
  r=output()['success'];self.assertEqual(r['officer_grants'],0);self.assertEqual(r['transitive_hops'],2);self.assertEqual(r['acceptance']['accepted_rows'],10);self.assertEqual(r['acceptance']['actual_paid_input_usdc_units'],0);self.assertEqual([x['loan_units'] for x in r['jobs']],[200000,200000,0]);self.assertEqual(r['jobs'][0]['opening_worker_cash'],0);self.assertEqual(r['jobs'][1]['opening_worker_cash'],0)
 def test_modeled_revenue_origin_and_cashconservation(self):
  r=output()['success'];self.assertEqual(r['final_balances']['lender'],5000000);self.assertEqual(r['final_balances']['sponsor'],1020000);self.assertEqual(r['final_balances']['worker1'],690000);self.assertEqual(r['final_balances']['worker2'],340000)
  for e in r['ledger']:
   if e['kind']=='modeled_usdc_transfer':self.assertEqual(sum(e['data']['balances'].values()),r['seed_and_customers_total_units'])
 def test_hashchain_recomputes(self):
  r=output()['success'];prev='0'*64
  for e in r['ledger']:
   self.assertEqual(e['previous'],prev);prev=hashlib.sha256(canonical({k:v for k,v in e.items() if k!='sha256'})).hexdigest();self.assertEqual(e['sha256'],prev)
  self.assertEqual(prev,r['journal_tip'])
 def test_failurerisknotforcedcure(self):
  r=output()['failure'];self.assertEqual(r['sponsor_loss_units'],200000);self.assertEqual(r['worker_cash_reclaimable_units'],50000);self.assertEqual(r['lender_final_units'],5000000);self.assertEqual(r['remaining_root_stake_units'],800000)
  transfers=[e['data'] for e in r['ledger'] if e['kind']=='modeled_usdc_transfer'];self.assertTrue(any(x['sender']=='rejected_job_escrow' and x['recipient']=='buyer1' and x['units']==500000 for x in transfers))
 def test_lowbid_funded_but_no_origination(self):
  c,g=make();c.move('buyer1','low',200000,'testfund');before=dict(c.b)
  with self.assertRaises(Refused):admit(c,g,'worker1','low',200000)
  self.assertEqual(c.b,before);self.assertEqual(g.locked['sponsor'],0)
 def test_no_customer_funding_no_origination(self):
  c,g=make();before=dict(c.b)
  with self.assertRaises(Refused):admit(c,g,'worker1','empty',500000)
  self.assertEqual(c.b,before);self.assertEqual(g.locked['sponsor'],0)
 def test_changed_quote_refuses_without_mutation(self):
  c,g=make();c.move('buyer1','esc',500000,'testfund');before=dict(c.b)
  with self.assertRaises(Refused):admit(c,g,'worker1','esc',500000,input_cost=200000,inference=50000)
  self.assertEqual(c.b,before);self.assertEqual(g.locked['sponsor'],0)
if __name__=='__main__':unittest.main()
