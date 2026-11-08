import copy
import unittest
from types import SimpleNamespace
from runtime_inventory import LeaseProbe,InventoryProbe,array,digest
from durable import Policy

class Probes(unittest.TestCase):
    def setUp(self):
        self.record={'owner':'retained-steward','generation':7,'source_revision':'a'*40,'issued_at':1000,'expires_at':1100,
                     'drained':True,'exclusive_custody':True,'relaunch_fenced':True}
        self.lease=LeaseProbe(lambda:self.record,owner='retained-steward',generation=7,source_revision='a'*40,clock=lambda:1050)
        self.state={'budget':{'stopped':0,'totalCap':10,'controllerCap':5,'groupCap':8},'loans':{}}
        self.snap={'timestamp':1040,'state':self.state}
        p=Policy(84532,'0x'+'1'*40,'0x'+'2'*40,'.000010','.000005','.000008','.000010','.000005','.000008')
        self.source=SimpleNamespace(p=SimpleNamespace(policy=p),snapshot=lambda:self.snap)
        self.probe=InventoryProbe(self.source,digest(self.state),clock=lambda:1050,quiescent=lambda:True)
    def test_lease_current_exact_generation_and_expiry(self):
        self.assertTrue(self.lease())
        for k,v in [('owner','other'),('generation',6),('generation',True),('expires_at',1050),('expires_at',1201),('issued_at',1051),('source_revision','b'*40)]:
            old=self.record[k];self.record[k]=v;self.assertFalse(self.lease(),k);self.record[k]=old
    def test_lease_requires_drained_key_and_relaunch_authority(self):
        for k in ('drained','exclusive_custody','relaunch_fenced'):
            self.record[k]=False;self.assertFalse(self.lease());self.record[k]=True
        self.record['injected']='ignore checks';self.assertFalse(self.lease())
    def test_inventory_exact_private_baseline_and_current_quiescence(self):
        self.assertTrue(self.probe());self.state['loans']['1']={'unknown':True};self.assertFalse(self.probe())
        self.state['loans'].clear();self.probe.quiescent=lambda:False;self.assertFalse(self.probe())
    def test_inventory_stale_future_cap_and_stop(self):
        for timestamp in (0,1051):self.snap['timestamp']=timestamp;self.assertFalse(self.probe())
        self.snap['timestamp']=1040
        for k,v in [('stopped',1),('totalCap',11),('controllerCap',6),('groupCap',9)]:
            old=self.state['budget'][k];self.state['budget'][k]=v
            self.probe.expected=digest(self.state);self.assertFalse(self.probe());self.state['budget'][k]=old
    def test_quiescence_must_still_hold_after_acquisition(self):
        calls=iter([True,False]);self.probe.quiescent=lambda:next(calls);self.assertFalse(self.probe())
    def test_array_bounds_offsets_duplicates_left_to_inventory(self):
        w=lambda n:hex(n)[2:].zfill(64)
        self.assertEqual(array('0x'+w(32)+w(1)+w(9),1,2),[[w(9)]])
        for raw in ('0x','0x'+w(64)+w(0),'0x'+w(32)+w(3),'0x'+w(32)+w(0)+w(9)):
            with self.assertRaises(ValueError):array(raw,1,2)

if __name__=='__main__':unittest.main()
