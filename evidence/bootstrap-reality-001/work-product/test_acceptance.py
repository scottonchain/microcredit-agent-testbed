#!/usr/bin/env python3
import copy,json,pathlib,tempfile,shutil
from accept import accept,P
original=json.loads((P/'report.json').read_text());tests=[]
def reject(name,data,base=P):
 try:accept(data,base)
 except (AssertionError,KeyError,ValueError):tests.append({'case':name,'rejected':True});return
 raise RuntimeError('corruption accepted: '+name)
d=copy.deepcopy(original);d['rows'][0]['excerpt']+=' invented';reject('altered excerpt',d)
d=copy.deepcopy(original);d['rows'][0]['literal_fact']='Protocol guarantees profitable loans';reject('unsupported claim',d)
d=copy.deepcopy(original);d['rows'][0]['url']=d['rows'][0]['url'].replace(d['rows'][0]['commit'],'main');reject('mutable source link',d)
d=copy.deepcopy(original);d['rows'][1]=copy.deepcopy(d['rows'][0]);reject('duplicate coverage',d)
d=copy.deepcopy(original);d['external_customer_payment_observed']=True;reject('false customer payment',d)
with tempfile.TemporaryDirectory() as t:
 base=pathlib.Path(t)/'copy';shutil.copytree(P,base);f=base/original['rows'][0]['input'];f.write_bytes(f.read_bytes()+b'corrupted');reject('source-byte mutation',original,base)
(P/'corruption-tests.json').write_text(json.dumps({'passed':True,'tests':tests},indent=2)+'\n');print(json.dumps({'passed':True,'tests':tests}))
