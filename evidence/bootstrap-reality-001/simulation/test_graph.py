import unittest
from engine import Graph,Refused
class SharedStake(unittest.TestCase):
 def graph(self):
  g=Graph();g.root('s',1000000,['b','c']);g.edge('s','a',1000000);g.edge('a','b',1000000);g.edge('a','c',1000000);return g
 def test_no_officer_multi_hop(self):
  g=self.graph();a=g.reserve('b',300000,[(['s','a','b'],300000)]);g.repay(a,300000);self.assertEqual(g.locked['s'],0)
 def test_competing_borrowers_global_not_per_sink(self):
  g=self.graph();g.reserve('b',600000,[(['s','a','b'],600000)])
  with self.assertRaises(Refused):g.reserve('c',500000,[(['s','a','c'],500000)])
  self.assertEqual(g.locked['s'],600000)
 def test_diamond_repeated_root_no_duplication(self):
  g=self.graph();g.edge('s','x',1000000);g.edge('x','b',1000000)
  with self.assertRaises(Refused):g.reserve('b',1200000,[(['s','a','b'],600000),(['s','x','b'],600000)])
  self.assertEqual(g.locked['s'],0)
 def test_cycles_no_new_funding(self):
  g=self.graph();g.edge('b','a',1000000)
  with self.assertRaises(Refused):g.reserve('b',1,[(['s','a','b','a','b'],1)])
 def test_no_root_risk_consent(self):
  g=self.graph();g.edge('a','stranger',1000000)
  with self.assertRaises(Refused):g.reserve('stranger',1,[(['s','a','stranger'],1)])
 def test_locked_exit(self):
  g=self.graph();g.reserve('b',600000,[(['s','a','b'],600000)])
  with self.assertRaises(Refused):g.unstake('s',400001)
 def test_partial_repay_default_cannot_consume_reused_stake(self):
  g=self.graph();l=g.reserve('b',600000,[(['s','a','b'],600000)]);g.repay(l,100000);g.reserve('c',500000,[(['s','a','c'],500000)]);self.assertEqual(g.default(l),500000);self.assertEqual(g.stake['s'],500000);self.assertEqual(g.locked['s'],500000)
 def test_no_forgiveness_recycles(self):
  g=self.graph()
  for _ in range(10):
   l=g.reserve('b',9999,[(['s','a','b'],9999)]);g.repay(l,1);self.assertEqual(g.loans[l]['state'],'Active');self.assertEqual(g.loans[l]['outstanding'],9998)
  self.assertEqual(g.locked['s'],99980)
class AlgorithmicRouting(unittest.TestCase):
 def test_algorithm_finds_and_splits_paths_no_officer_input(self):
  g=Graph();g.root('r',1000000,['*']);g.edge('r','a',300000);g.edge('a','b',300000);g.edge('r','c',300000);g.edge('c','b',300000);l=g.allocate('b',500000)
  self.assertEqual(g.locked['r'],500000);self.assertEqual(len(g.loans[l]['paths']),2);g.repay(l,500000);self.assertEqual(g.locked['r'],0)
 def test_allocator_no_partial_commit_when_insufficient(self):
  g=Graph();g.root('r',1000000,['*']);g.edge('r','a',300000);g.edge('a','b',300000)
  with self.assertRaises(Refused):g.allocate('b',400000)
  self.assertEqual(g.locked['r'],0);self.assertEqual(g.edges['r','a'].locked,0)
class RoutingWorkBound(unittest.TestCase):
 def test_adversarial_breadth_exhaustion_leaves_capacity_free(self):
  g=Graph();g.root('r',1000000,['*'])
  for i in range(1001):g.edge('r','x'+str(i),1000000)
  with self.assertRaisesRegex(Refused,'queue bound'):g.allocate('b',1)
  self.assertEqual(g.locked['r'],0);self.assertTrue(all(e.locked==0 for e in g.edges.values()))
if __name__=='__main__':unittest.main()
