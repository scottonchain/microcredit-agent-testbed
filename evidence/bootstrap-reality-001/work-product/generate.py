#!/usr/bin/env python3
"""Deterministic producer: find grounded literal facts; no network or spend."""
import hashlib,json,pathlib,time
P=pathlib.Path(__file__).resolve().parent
def produce():
 start=time.perf_counter();spec=json.loads((P/'source-spec.json').read_text());rows=[];total=0
 for s in spec['sources']:
  raw=(P/s['input']).read_bytes();total+=len(raw)
  if hashlib.sha256(raw).hexdigest()!=s['sha256']:raise ValueError('source integrity failed')
  lines=raw.decode().splitlines();hits=[i for i,l in enumerate(lines) if s['needle'] in l]
  if not hits:raise ValueError('fact not found')
  i=hits[0];lo=max(0,i-1);hi=min(len(lines),i+2)
  rows.append({'company_or_protocol':s['name'],'repo':s['repo'],'commit':s['commit'],'source_path':s['path'],'input':s['input'],'source_sha256':s['sha256'],'url':f"https://github.com/{s['repo']}/blob/{s['commit']}/{s['path']}#L{i+1}",'literal_fact':lines[i].strip(),'line_start':lo+1,'line_end':hi,'excerpt':'\n'.join(lines[lo:hi]),'interpretation_limit':s['limitation'],'evidence_class':'pinned_primary_source_not_usage_proof'})
 report={'schema_version':1,'scope':spec['scope'],'known_incremental_usdc_input_cost':0,'external_customer_payment_observed':False,'rows':rows}
 encoded=(json.dumps(report,sort_keys=True,indent=2)+'\n').encode();(P/'report.json').write_bytes(encoded)
 receipt={'task':'produce10row-primary-source-report','source_count':len(rows),'input_bytes':total,'output_bytes':len(encoded),'output_sha256':hashlib.sha256(encoded).hexdigest(),'measured_runtime_seconds':time.perf_counter()-start,'network_requests':0,'usdc_spent':0,'runtime_scope':'local Python parsing/hashing only; not source discovery, LLM or hosting cost'}
 (P/'producer-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt
if __name__=='__main__':print(json.dumps(produce()))
