"""Proposed issuer-free graph reservation model; not deployed-contract/EVM code."""
from dataclasses import dataclass
from threading import RLock
from functools import wraps
def serialized(fn):
 @wraps(fn)
 def call(self,*a,**k):
  with self._lock:return fn(self,*a,**k)
 return call
def positive_int(x):return type(x) is int and x>0
class Refused(ValueError):pass
@dataclass
class Edge:
 limit:int
 locked:int=0
class Graph:
 def __init__(self):self._lock=RLock();self.stake={};self.locked={};self.consent={};self.edges={};self.loans={};self.sequence=0
 @serialized
 def root(self,r,amount,allowed):
  if r in self.stake or not positive_int(amount):raise Refused('unique actual stake root required')
  self.stake[r]=amount;self.locked[r]=0;self.consent[r]=set(allowed)
 @serialized
 def edge(self,a,b,limit):
  if a==b or not positive_int(limit) or (a,b) in self.edges:raise Refused('invalid unique directed edge')
  self.edges[a,b]=Edge(limit)
 @serialized
 def allocate(self,borrower,amount):
  """Deterministic bounded greedy path routing; feasibility, not max-flow optimality."""
  if not positive_int(amount):raise Refused('invalid requested principal')
  roots={r:self.stake[r]-self.locked[r] for r in self.stake}
  edges={e:self.edges[e].limit-self.edges[e].locked for e in self.edges}
  left=amount;paths=[];visits=0
  while left:
   found=None
   for root in sorted(roots):
    if roots[root]<=0 or (borrower not in self.consent[root] and '*' not in self.consent[root]):continue
    queue=[[root]]
    while queue:
     path=queue.pop(0);visits+=1
     if visits>1000:raise Refused('routing work bound exceeded')
     if len(path)>=5:continue
     for nxt in sorted(z for (a,z),cap in edges.items() if a==path[-1] and cap>0):
      if nxt in path:continue
      candidate=path+[nxt]
      if nxt==borrower:
       found=candidate;break
      queue.append(candidate)
      if len(queue)>1000:raise Refused('routing queue bound exceeded')
     if found:break
    if found:break
   if not found:raise Refused('no authorized uncommitted graph capacity')
   take=min([left,roots[found[0]]]+[edges[e] for e in zip(found,found[1:])])
   roots[found[0]]-=take
   for e in zip(found,found[1:]):edges[e]-=take
   paths.append((found,take));left-=take
   if len(paths)>16:raise Refused('allocation path count bound exceeded')
  return self.reserve(borrower,amount,paths)
 @serialized
 def reserve(self,borrower,amount,paths):
  if any(l['borrower']==borrower and l['state']=='Defaulted' for l in self.loans.values()):raise Refused('borrower has a recorded default')
  if not positive_int(amount) or sum(x for _,x in paths)!=amount:raise Refused('allocation principal mismatch')
  rd={};ed={}
  for path,x in paths:
   if not positive_int(x) or len(path)<2 or len(path)>5 or len(set(path))!=len(path) or path[-1]!=borrower:raise Refused('invalid bounded simple path')
   root=path[0]
   if root not in self.stake or (borrower not in self.consent[root] and '*' not in self.consent[root]):raise Refused('root downstream risk consent absent')
   rd[root]=rd.get(root,0)+x
   for edge in zip(path,path[1:]):
    if edge not in self.edges:raise Refused('unsigned/missing trust edge')
    ed[edge]=ed.get(edge,0)+x
  for r,x in rd.items():
   if self.locked[r]+x>self.stake[r]:raise Refused('shared root capacity exhausted')
  for e,x in ed.items():
   if self.edges[e].locked+x>self.edges[e].limit:raise Refused('shared edge capacity exhausted')
  for r,x in rd.items():self.locked[r]+=x
  for e,x in ed.items():self.edges[e].locked+=x
  self.sequence+=1;lid=self.sequence
  self.loans[lid]={'borrower':borrower,'principal':amount,'outstanding':amount,'paths':[[list(p),x] for p,x in paths],'state':'Active'}
  self.check();return lid
 @serialized
 def repay(self,lid,amount):
  loan=self.loans[lid]
  if loan['state']!='Active' or not positive_int(amount) or amount>loan['outstanding']:raise Refused('repayment amount/state')
  # Exact integer release, deterministic greedy assignment; no subcent forgiveness.
  remaining=amount
  for pathx in loan['paths']:
   path,x=pathx;cut=min(x,remaining)
   if cut:
    self.locked[path[0]]-=cut
    for e in zip(path,path[1:]):self.edges[e].locked-=cut
    pathx[1]-=cut;remaining-=cut
  assert remaining==0;loan['outstanding']-=amount
  if loan['outstanding']==0:loan['state']='Repaid'
  self.check()
 @serialized
 def default(self,lid):
  loan=self.loans[lid]
  if loan['state']!='Active':raise Refused('loan not active')
  recovered=0
  for path,x in loan['paths']:
   self.stake[path[0]]-=x;self.locked[path[0]]-=x;recovered+=x
   for e in zip(path,path[1:]):self.edges[e].locked-=x
  assert recovered==loan['outstanding'];loan['outstanding']=0;loan['paths']=[(p,0) for p,_ in loan['paths']];loan['state']='Defaulted';self.check();return recovered
 @serialized
 def unstake(self,r,x):
  if not positive_int(x) or self.stake[r]-x<self.locked[r]:raise Refused('stake remains committed')
  self.stake[r]-=x;self.check()
 @serialized
 def check(self):
  rr={r:0 for r in self.stake};ee={e:0 for e in self.edges}
  for l in self.loans.values():
   if l['state']=='Active':
    assert sum(x for _,x in l['paths'])==l['outstanding']
    for p,x in l['paths']:
     rr[p[0]]+=x
     for e in zip(p,p[1:]):ee[e]+=x
  assert rr==self.locked
  for r in rr:assert 0<=rr[r]<=self.stake[r]
  for e in ee:assert self.edges[e].locked==ee[e] and 0<=ee[e]<=self.edges[e].limit
  return True
