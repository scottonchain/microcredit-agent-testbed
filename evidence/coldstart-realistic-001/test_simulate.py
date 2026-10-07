import unittest
from simulate import interest,suite,U,DAY
class Economics(unittest.TestCase):
 def test_grace_trigger(self):
  self.assertEqual(interest(100*U,DAY-1),0);self.assertEqual(interest(100*U,7*DAY),178931)
 def test_external_job_cash_conservation(self):
  r=suite()['success'];self.assertEqual(r['reserve_dues_units'],80518);self.assertAlmostEqual(r['net_surplus_usd'],36.321069)
  for e in r['trace']:self.assertEqual(sum(e['balances'].values()),r['initial_total_units'])
 def test_failure_real_loss(self):
  r=suite()['failure'];self.assertEqual(r['sponsor_principal_loss_units'],100*U);self.assertEqual(r['final_balances']['worker'],0);self.assertEqual(r['reserve_dues_units'],0);self.assertGreater(r['days'],60)
 def test_counterexamples_block_launch(self):
  r=suite();self.assertEqual(r['attacks']['ci30']['coalition_gain_units'],99980);self.assertEqual(r['attacks']['multi_backer_rounding']['lender_loss_units'],1);self.assertEqual(r['attacks']['grant_first']['secured_edge_units'],0);self.assertTrue(r['mainnet_readiness'].startswith('NO-GO'))
if __name__=='__main__':unittest.main()
