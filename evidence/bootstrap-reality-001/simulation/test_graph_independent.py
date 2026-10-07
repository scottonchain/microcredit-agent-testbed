"""Independent adversarial tests of the proposed, serialized graph model."""
import copy
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from engine import Graph, Refused
class IndependentGraphTests(unittest.TestCase):
 def snapshot(self,g):return copy.deepcopy({k:v for k,v in g.__dict__.items() if k != "_lock"})
 def graph(self):
  g=Graph();g.root('root',1_000_000,['*']);g.edge('root','coordinator',1_000_000)
  for b in ('A','B','C','D'):g.edge('coordinator',b,1_000_000)
  return g
 def test_four_requests_serialized_reject_fourth_without_mutation(self):
  g=self.graph()
  for b in ('A','B','C'):g.reserve(b,300_000,[(['root','coordinator',b],300_000)])
  before=self.snapshot(g)
  with self.assertRaises(Refused):g.reserve('D',300_000,[(['root','coordinator','D'],300_000)])
  self.assertEqual(before,self.snapshot(g))
 def test_defaulted_identity_cannot_reborrow(self):
  g=self.graph();lid=g.reserve('A',300_000,[(['root','coordinator','A'],300_000)]);g.default(lid)
  before=self.snapshot(g)
  with self.assertRaises(Refused):g.reserve('A',1,[(['root','coordinator','A'],1)])
  self.assertEqual(before,self.snapshot(g))
 def test_supplied_allocation_mutation_cannot_change_reserved_loan(self):
  g=self.graph();path=['root','coordinator','A'];allocations=[(path,300_000)]
  lid=g.reserve('A',300_000,allocations);path[0]='fake';allocations[0]=(path,999_999)
  self.assertEqual(g.loans[lid]['paths'],[[['root','coordinator','A'],300_000]])
  self.assertTrue(g.check())
 def test_shared_edge_cap_rejects_even_when_origin_stake_available(self):
  g=self.graph();g.edges['root','coordinator'].limit=500_000
  g.reserve('A',300_000,[(['root','coordinator','A'],300_000)])
  before=self.snapshot(g)
  with self.assertRaises(Refused):g.reserve('B',300_000,[(['root','coordinator','B'],300_000)])
  self.assertEqual(before,self.snapshot(g))
 def test_duplicate_resource_initialization_refused(self):
  g=self.graph();before=self.snapshot(g)
  with self.assertRaises(Refused):g.root('root',1_000_000,['*'])
  with self.assertRaises(Refused):g.edge('root','coordinator',1_000_000)
  self.assertEqual(before,self.snapshot(g))
 def test_multiroot_partial_and_default_exact(self):
  g=self.graph();g.root('second',500_000,['A']);g.edge('second','A',500_000)
  lid=g.reserve('A',600_000,[(['root','coordinator','A'],300_000),(['second','A'],300_000)])
  g.repay(lid,400_000)
  self.assertEqual(g.locked,{'root':0,'second':200_000})
  self.assertEqual(g.default(lid),200_000)
  self.assertEqual(g.stake,{'root':1_000_000,'second':300_000});self.assertEqual(g.locked,{'root':0,'second':0})
 def test_failed_second_path_cannot_partially_commit_first(self):
  g=self.graph();before=self.snapshot(g)
  with self.assertRaises(Refused):g.reserve('A',600_000,[(['root','coordinator','A'],300_000),(['root','missing','A'],300_000)])
  self.assertEqual(before,self.snapshot(g))
 def test_duplicate_completion_cannot_burn_stake_twice(self):
  g=self.graph();lid=g.reserve('A',300_000,[(['root','coordinator','A'],300_000)]);g.default(lid)
  before=self.snapshot(g)
  with self.assertRaises(Refused):g.default(lid)
  with self.assertRaises(Refused):g.repay(lid,300_000)
  self.assertEqual(before,self.snapshot(g))
 def test_threaded_race_admits_exactly_three(self):
  g=self.graph();barrier=Barrier(4)
  def request(b):
   barrier.wait()
   try:return g.reserve(b,300_000,[(['root','coordinator',b],300_000)])
   except Refused:return None
  with ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(request,('A','B','C','D')))
  self.assertEqual(sum(x is not None for x in results),3);self.assertEqual(len(g.loans),3)
  self.assertEqual(g.locked['root'],900_000);self.assertTrue(g.check())
 def test_float_bool_quantities_refused_without_mutation(self):
  for value in (True,False,1.0,0.5,-1,0):
   with self.subTest(value=value):
    g=self.graph();before=self.snapshot(g)
    with self.assertRaises(Refused):g.root('other',value,['*'])
    with self.assertRaises(Refused):g.edge('other','A',value)
    with self.assertRaises(Refused):g.reserve('A',value,[(['root','coordinator','A'],value)])
    with self.assertRaises(Refused):g.unstake('root',value)
    self.assertEqual(before,self.snapshot(g))
 def test_float_bool_repayment_refused(self):
  g=self.graph();lid=g.reserve('A',300_000,[(['root','coordinator','A'],300_000)])
  for value in (True,False,1.0,0.5):
   before=self.snapshot(g)
   with self.assertRaises(Refused):g.repay(lid,value)
   self.assertEqual(before,self.snapshot(g))
if __name__=='__main__':unittest.main()
