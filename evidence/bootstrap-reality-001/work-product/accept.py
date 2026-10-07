#!/usr/bin/env python3
"""Independent acceptance: re-read source bytes and validate every evidence claim.
Does not import producer or compare to a precomputed expected report.
Does not independently certify semantic interpretations, demand or live deployment.
"""
import hashlib,json,pathlib,re,time
P=pathlib.Path(__file__).resolve().parent
def accept(data,base=P):
 spec=json.loads((base/'source-spec.json').read_text());trusted={s['input']:s for s in spec['sources']}
 assert data['schema_version']==1 and data['known_incremental_usdc_input_cost']==0 and data['external_customer_payment_observed'] is False
 assert len(data['rows'])==10 and len(trusted)==10
 assert len({r['input'] for r in data['rows']})==10
 n=0
 for r in data['rows']:
  s=trusted[r['input']];file=(base/r['input']).resolve();assert file.is_relative_to(base.resolve())
  raw=file.read_bytes();n+=len(raw);digest=hashlib.sha256(raw).hexdigest();assert digest==s['sha256']==r['source_sha256']
  assert re.fullmatch('[0-9a-f]{40}',r['commit'])
  assert (r['repo'],r['commit'],r['source_path'],r['company_or_protocol'])==(s['repo'],s['commit'],s['path'],s['name'])
  lines=raw.decode().splitlines();lo=r['line_start'];hi=r['line_end'];assert 1<=lo<=hi<=len(lines) and hi-lo<=4
  excerpt='\n'.join(lines[lo-1:hi]);assert r['excerpt']==excerpt
  assert any(r['literal_fact']==l.strip() for l in lines[lo-1:hi]) and s['needle'] in r['literal_fact']
  m=re.fullmatch(r'https://github.com/([^/]+/[^/]+)/blob/([0-9a-f]{40})/(.+)#L([0-9]+)',r['url']);assert m
  repo,sha,path,lineno=m.groups();assert (repo,sha,path)==(s['repo'],s['commit'],s['path']);assert lo<=int(lineno)<=hi
  assert lines[int(lineno)-1].strip()==r['literal_fact']
  assert r['evidence_class']=='pinned_primary_source_not_usage_proof' and isinstance(r['interpretation_limit'],str) and len(r['interpretation_limit'])>20
 return {'accepted_rows':10,'source_bytes_independently_reread':n,'checks':['source-byte hashes','immutable commit identities','exact line excerpts','literal factual grounding','unique source coverage','zero-cost/no-payment scope'], 'semantic_interpretations':'human research judgment; validator certifies literal grounds not paraphrase truth','independent_customer_verified':False,'onchain_execution_verified':False}
if __name__=='__main__':
 start=time.perf_counter();raw=(P/'report.json').read_bytes();out=accept(json.loads(raw));out.update(accepted=True,report_sha256=hashlib.sha256(raw).hexdigest(),measured_runtime_seconds=time.perf_counter()-start,network_requests=0);(P/'acceptance-receipt.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
