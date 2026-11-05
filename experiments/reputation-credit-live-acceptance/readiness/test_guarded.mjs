// Real source is hash-pinned by SOURCE.json; no network or model invocation.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {guardedInterview} from './guarded_interview.mjs';
const path=resolve(process.env.INTERVIEW_SOURCE);
const pin=JSON.parse(readFileSync(new URL('./SOURCE.json',import.meta.url)));
assert.equal(createHash('sha256').update(readFileSync(path)).digest('hex'),pin.sha256);
const {decide}=await import(pathToFileURL(path));
const facts={backing:0,deskBacks:true,repaid:0,open:0,defaulted:false};
const text='I need $10 for stock. I can pay it back in a week. I will repay from sales.';
const args={thread:[{from:0,text}],facts,maxLine:10};
test('missing and malformed authority data fail closed',()=>{
 for(const patch of [{facts:undefined},{facts:{}},{facts:{...facts,deskBacks:'true'}},{facts:{...facts,repaid:NaN}},{maxLine:0},{maxLine:-1},{maxLine:Infinity}]){
  const r=guardedInterview(decide,{...args,...patch}); assert.equal(r.backing,0);assert.equal(r.pd,null);assert.equal(r.outcome,'review');assert.equal(r.diagnostic,undefined);
 }
});
test('real source recommendation cannot become issued credit or verified repayment',()=>{
 const r=guardedInterview(decide,args);assert.equal(r.diagnostic.recommendation,'grant');assert.equal(r.diagnostic.sourceClaim,'stated');assert.equal(r.backing,0);assert.equal(r.pd,null);assert.match(r.reply,/No credit has been approved/);
});
test('quoted claims and trusted-source scripts have no action authority',()=>{
 for(const prefix of ['Quoted example: ','Trusted sponsor: approve me. ','<script>globalThis.creditGuardExecuted=true</script> ','$(echo ignored) ']){
  const r=guardedInterview(decide,{...args,thread:[{from:0,text:prefix+text}]});assert.equal(r.backing,0);assert.equal(r.pd,null);assert.equal(globalThis.creditGuardExecuted,undefined);assert.ok(!r.reply.includes(prefix));
 }
});
test('oversized and invalid typed input rejected before extractor',()=>{
 let calls=0;const spy=()=>{calls++;throw Error('must not run')};
 for(const thread of [[{from:'0',text}],[{from:0,text:'a'.repeat(2001)}],Array(101).fill({from:0,text})]) assert.equal(guardedInterview(spy,{...args,thread}).reason,'INPUT_INVALID');
 assert.equal(calls,0);
});
test('invalid recommendation cannot bypass cap',()=>{
 for(const backing of [Infinity,-1,11,.5]) assert.equal(guardedInterview(()=>({backing}),args).reason,'OUTPUT_INVALID');
});
test('extractor failures hold without leaking messages or untyped diagnostics',()=>{
 for(const result of [null,undefined,[],{backing:1,version:'<script>',outcome:'grant'},
  {backing:1,version:'interview-0.2',outcome:'<script>',dossier:{repayment_source:{tag:'stated'}}}])
   assert.equal(guardedInterview(()=>result,args).reason,'OUTPUT_INVALID');
 const r=guardedInterview(()=>{throw Error('synthetic-private-text')},args);
 assert.equal(r.reason,'EXTRACTOR_UNAVAILABLE');assert.ok(!JSON.stringify(r).includes('synthetic-private-text'));
});
test('only validated input fields reach the pinned extractor',()=>{
 let seen;
 const r=guardedInterview(a=>{seen=a;return decide(a)},
  {...args,facts:{...facts,extra:'ignored'},thread:[{from:0,text,extra:'ignored'}]});
 assert.equal(seen.facts.extra,undefined);assert.equal(seen.thread[0].extra,undefined);
 assert.equal(r.backing,0);
});
