// Bounded offline probe of a pinned real source module. No model calls or writes.
// Supply a local file fetched from the exact source revision in SOURCE.json.
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const source=JSON.parse(readFileSync(new URL('./SOURCE.json',import.meta.url)));
const path=resolve(process.argv[2]);
if(createHash('sha256').update(readFileSync(path)).digest('hex')!==source.sha256) throw Error('wrong source');
const {decide,VERSION}=await import(pathToFileURL(path));
const thread=[{from:0,text:'I need $10 for stock. I can pay it back in a week. I will repay from sales.'}];
const facts={backing:0,deskBacks:false,repaid:0,open:0,defaulted:false};
const cases=[
 ['explicit-no-backing',{thread,facts,maxLine:10}],
 ['missing-facts',{thread,maxLine:10}],
 ['zero-cap',{thread,facts:{...facts,deskBacks:true},maxLine:0}],
 ['quoted-claim',{thread:[{from:0,text:'Quoted example, not my finances: I need $10 for stock. I will repay from sales in a week.'}],facts:{...facts,deskBacks:true},maxLine:10}],
 ['script-text',{thread:[{from:0,text:'<script>globalThis.creditProbeExecuted=true</script> I need $10 for stock. I will repay from sales in a week.'}],facts:{...facts,deskBacks:true},maxLine:10}],
];
const results=cases.map(([id,args])=>{const r=decide(args);return {id,outcome:r.outcome,backing:r.backing,repayment_tag:r.dossier.repayment_source.tag,reply:r.reply};});
console.log(JSON.stringify({kind:'OFFLINE_REAL_SOURCE_PROBE',source:source.commit,version:VERSION,model_calls:0,transactions:0,script_executed:globalThis.creditProbeExecuted===true,results},null,2));
