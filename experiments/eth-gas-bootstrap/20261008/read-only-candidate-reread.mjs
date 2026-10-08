#!/usr/bin/env node
// READ ONLY. Reuse calculated winners; fresh period/claim checks, no calculator rerun.
// Node >=20, exact dependency viem@2.17.0. Never signs, sends, deploys or loads keys.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
const argv = process.argv.slice(2);
if (argv.includes('--help')) { console.log(`Install: npm install --save-exact viem@2.17.0
Run: BASE_READ_RPC='approved HTTPS endpoint' node read-only-candidate-reread.mjs --probe probe.json > reread.json
Reuses calculated winners ONLY when current draw equals input draw. Reads claim-period expiry first.
Checks at most128 prize entries, highest fee tiers first; simulates at most12 current unclaimed entries.
One eth_call aggregate3 contains read-only isWinner/wasClaimed calls. At most2 zero-fee vault calls expose caught errors.
Limits: 45 HTTP/RPC requests,90seconds. No endpoint or RPC error message is printed.
Output candidate format works as input to read-only-cycle-quote.mjs. This does not authorize spending.`); process.exit(0); }
function arg(k,f){const i=argv.indexOf(k);if(i<0)return f;if(!argv[i+1])throw new Error('ArgumentValue');return argv[i+1];}
const POOL='0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb';
const BORROWER='0x62c4a163026feedb3ea1045d90bba96d0c5d4f0b';
const MULTICALL='0xca11bde05977b3631167028862be2a173976ca11';
const started=Date.now(),abort=new AbortController();let done=false,stage='arguments';
const report={schema:'codex.eth-gas-read-only-candidate-reread/1',mode:'READ_ONLY_BOUNDED_SNAPSHOT',chainId:8453,startedAt:new Date().toISOString(),counters:{httpRequests:0,rpcOperations:0},candidates:[],diagnostics:[],spendAuthorized:false,loanDisbursed:false,earnedRevenue:false,globalOpportunityAbsence:false,
 caveats:['Previously calculated winners are a historical-address sample, not complete current inventory.','Claim periods expire independently of isWinner and wasClaimed.','Exact positive claim does not establish complete-cycle profitability or prevent race loss.','Candidate selection prioritizes quoted fee tiers and can omit lower-ranked jobs.','Direct vault diagnostic uses eth_call with from=actual configured claimer. It is not sent.']};
function finish(status,error){if(done)return;done=true;Object.assign(report,{status,stage,finishedAt:new Date().toISOString(),elapsedMs:Date.now()-started});if(error)report.error={kind:error.safeKind||(/^[A-Za-z][A-Za-z0-9_]{0,80}$/.test(error.message||'')?error.message:error.name)||'Error'};console.log(JSON.stringify(report,(_,v)=>typeof v==='bigint'?v.toString():v,2));}
const timer=setTimeout(()=>{abort.abort();finish('STOPPED_RUNTIME_CAP');process.exit(2);},90_000);
try{
 const name=arg('--rpc-env','BASE_READ_RPC');if(!/^[A-Z][A-Z0-9_]*$/.test(name))throw new Error('RpcEnvName');
 const endpoint=process.env[name];if(!endpoint||new URL(endpoint).protocol!=='https:')throw new Error('ApprovedHttpsRpcRequired');
 const bytes=readFileSync(resolve(arg('--probe','probe.json')));if(bytes.length>2_000_000)throw new Error('InputTooLarge');const source=JSON.parse(bytes);
 if(!Array.isArray(source.calculatedWinners)||!source.seed?.vault||!source.contracts?.drawId)throw new Error('SourceProbeSchema');
 const vault=source.seed.vault.toLowerCase();report.input={sha256:createHash('sha256').update(bytes).digest('hex'),sourceDrawId:source.contracts.drawId,sourceBlock:source.block,vault};
 const require=createRequire(import.meta.url);let root=dirname(require.resolve('viem')),manifest;
 for(let i=0;i<4;i++){try{const m=JSON.parse(readFileSync(resolve(root,'package.json')));if(m.name==='viem'){manifest=m;break;}}catch{}root=dirname(root);}if(manifest?.version!=='2.17.0')throw new Error('ExactViemVersionRequired');
 const {parseAbi,encodeFunctionData,decodeFunctionResult,decodeErrorResult,keccak256}=await import('viem');
 const allowed=new Set(['eth_chainId','eth_getBlockByNumber','eth_call','eth_getCode']);let id=0;
 function extractHex(data){if(typeof data==='string'&&/^0x[0-9a-fA-F]*$/.test(data)&&data.length<=20_000)return data;if(data&&typeof data==='object'){for(const key of ['data','result','return','originalError']){const h=extractHex(data[key]);if(h)return h;}}return undefined;}
 async function rpc(method,params){if(!allowed.has(method))throw new Error('DeniedRpcMethod');if(++report.counters.httpRequests>45||++report.counters.rpcOperations>45)throw new Error('RpcCap');
 const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:++id,method,params}),redirect:'error',signal:AbortSignal.any([abort.signal,AbortSignal.timeout(12_000)])});const text=await response.text();if(!response.ok||text.length>2_000_000)throw new Error('RpcHttpFailure');const packet=JSON.parse(text);if(packet.error){const e=new Error('RpcError');e.safeKind='RpcError_'+String(packet.error.code);e.revertData=extractHex(packet.error.data);throw e;}return packet.result;}
 stage='fresh_claim_period';if(BigInt(await rpc('eth_chainId',[]))!==8453n)throw new Error('WrongChain');const block=await rpc('eth_getBlockByNumber',['latest',false]);if(!block?.hash||!block?.number||!block?.timestamp)throw new Error('BlockSchema');const tag=block.number;
 report.block={number:BigInt(tag),hash:block.hash,timestamp:BigInt(block.timestamp),fixedRpcCallTag:tag};
 const poolAbi=parseAbi(['function getLastAwardedDrawId() view returns(uint24)','function isDrawFinalized(uint24) view returns(bool)','function drawClosesAt(uint24) view returns(uint48)','function isShutdown() view returns(bool)','function drawTimeoutAt() view returns(uint256)','function isWinner(address,address,uint8,uint32) view returns(bool)','function wasClaimed(address,address,uint24,uint8,uint32) view returns(bool)']);
 const vaultAbi=parseAbi(['function claimer() view returns(address)','function prizePool() view returns(address)','function getHooks(address) view returns((bool useBeforeClaimPrize,bool useAfterClaimPrize,address implementation))','function claimPrize(address,uint8,uint32,uint96,address) returns(uint256)']);
 const claimerAbi=parseAbi(['function prizePool() view returns(address)','function computeFeePerClaim(uint8,uint256) view returns(uint256)','function claimPrizes(address,uint8,address[],uint32[][],address,uint256) returns(uint256)']);
 const errorAbi=parseAbi(['error ClaimPeriodExpired()','error PrizeIsZero()','error RewardTooLarge(uint256 reward,uint256 maxReward)','error AlreadyClaimed(address vault,address winner,uint8 tier,uint32 prizeIndex)','error DidNotWin(address vault,address winner,uint8 tier,uint32 prizeIndex)','error InsufficientReserve(uint104 amount,uint104 reserve)','error CallerNotClaimer(address caller,address claimer)']);
 const read=async(to,abi,fn,args=[])=>decodeFunctionResult({abi,functionName:fn,data:await rpc('eth_call',[{to,data:encodeFunctionData({abi,functionName:fn,args})},tag])});
 const draw=await read(POOL,poolAbi,'getLastAwardedDrawId');
 const [expired,periodEnd,shutdown,timeout,claimer,vaultPool]=await Promise.all([read(POOL,poolAbi,'isDrawFinalized',[draw]),read(POOL,poolAbi,'drawClosesAt',[draw+1]),read(POOL,poolAbi,'isShutdown'),read(POOL,poolAbi,'drawTimeoutAt'),read(vault,vaultAbi,'claimer'),read(vault,vaultAbi,'prizePool')]);
 report.contracts={drawId:draw,claimer,prizePool:POOL,vault,vaultPool};report.claimPeriod={expired,lastAwardedDrawId:draw,claimPeriodEndsAt:periodEnd,snapshotTimestamp:BigInt(block.timestamp),isShutdown:shutdown,drawTimeoutAt:timeout};
 if(vaultPool.toLowerCase()!==POOL||(await read(claimer,claimerAbi,'prizePool')).toLowerCase()!==POOL)throw new Error('PoolMismatch');
 if(draw!==Number(source.contracts.drawId)){finish('NEW_DRAW_RECOMPUTE_WINNERS_REQUIRED');}
 else if(expired){finish('NO_LOAN_LAST_AWARDED_DRAW_CLAIM_PERIOD_EXPIRED');}
 else{
  stage='fee_prioritized_inventory';const inventory=[];const unique=new Set();
  for(const w of source.calculatedWinners)for(const [tier,indices]of Object.entries(w.prizes||{}))for(const index of indices){const key=[w.user,tier,index].join(':');if(!unique.has(key)){unique.add(key);inventory.push({vault,winner:w.user.toLowerCase(),tier:Number(tier),prizeIndex:Number(index),drawId:draw});}}
  const tiers=[...new Set(inventory.map(c=>c.tier))].sort((a,b)=>a-b).slice(0,3),fees=new Map();for(const tier of tiers)fees.set(tier,await read(claimer,claimerAbi,'computeFeePerClaim',[tier,1n]));
  const ranked=inventory.filter(c=>fees.has(c.tier)).sort((a,b)=>fees.get(a.tier)>fees.get(b.tier)?-1:fees.get(a.tier)<fees.get(b.tier)?1:a.tier-b.tier||a.winner.localeCompare(b.winner)||a.prizeIndex-b.prizeIndex).slice(0,128);
  report.inventory={availableCalculatedPrizeEntries:inventory.length,entriesFreshlyChecked:ranked.length,tiersQuoted:Object.fromEntries(fees),ordering:'quoted single-claim fee descending, then winner/index; first128 only'};
  const mcAbi=parseAbi(['function aggregate3((address target,bool allowFailure,bytes callData)[] calls) payable returns((bool success,bytes returnData)[] returnData)']);
  const code=await rpc('eth_getCode',[MULTICALL,tag]);if(!code||code==='0x')throw new Error('MulticallCodeMissing');report.multicall={address:MULTICALL,runtimeCodeKeccak256:keccak256(code),onlyReadFunctions:true};
  const calls=ranked.flatMap(c=>[{target:POOL,allowFailure:true,callData:encodeFunctionData({abi:poolAbi,functionName:'isWinner',args:[vault,c.winner,c.tier,c.prizeIndex]})},{target:POOL,allowFailure:true,callData:encodeFunctionData({abi:poolAbi,functionName:'wasClaimed',args:[vault,c.winner,draw,c.tier,c.prizeIndex]})}]);
  const result=await read(MULTICALL,mcAbi,'aggregate3',[calls]);const checked=ranked.map((c,i)=>{const win=result[2*i],claimed=result[2*i+1];return {...c,readSucceeded:win.success&&claimed.success,isWinner:win.success?decodeFunctionResult({abi:poolAbi,functionName:'isWinner',data:win.returnData}):null,wasClaimed:claimed.success?decodeFunctionResult({abi:poolAbi,functionName:'wasClaimed',data:claimed.returnData}):null,singleClaimQuotedFeeWethWei:fees.get(c.tier)};});report.checkedInventory=checked;
  const selection=checked.filter(c=>c.isWinner===true&&c.wasClaimed===false&&c.singleClaimQuotedFeeWethWei>0n).slice(0,12);const hookCache=new Map();let diagnosed=0;
  stage='bounded_exact_claims';for(const c of selection){if(!hookCache.has(c.winner))hookCache.set(c.winner,await read(vault,vaultAbi,'getHooks',[c.winner]));const hooks=hookCache.get(c.winner);const rec={...c,hooks,noEnabledHooks:!hooks.useBeforeClaimPrize&&!hooks.useAfterClaimPrize,unclaimedAtSnapshot:true,exactClaimSimulated:false,completeCyclePriced:false,spendAuthorizedByProbe:false};rec.eligibleForFurtherSimulation=rec.noEnabledHooks;
   if(rec.noEnabledHooks){try{const returnData=await rpc('eth_call',[{from:BORROWER,to:claimer,data:encodeFunctionData({abi:claimerAbi,functionName:'claimPrizes',args:[vault,c.tier,[c.winner],[[c.prizeIndex]],BORROWER,1n]})},tag]);rec.exactClaimRewardWei=decodeFunctionResult({abi:claimerAbi,functionName:'claimPrizes',data:returnData});rec.exactClaimSimulated=true;rec.exactClaimReturnData=returnData;}catch(e){rec.exactClaimErrorKind=e.safeKind||e.name;rec.exactClaimRevertData=e.revertData;}}
   if(rec.exactClaimRewardWei===0n&&diagnosed<2){diagnosed++;const diagnostic={winner:c.winner,tier:c.tier,prizeIndex:c.prizeIndex,caller:claimer,rewardWei:c.singleClaimQuotedFeeWethWei,mode:'ETH_CALL_ONLY_FROM_CONFIGURED_CLAIMER'};try{const r=await rpc('eth_call',[{from:claimer,to:vault,data:encodeFunctionData({abi:vaultAbi,functionName:'claimPrize',args:[c.winner,c.tier,c.prizeIndex,c.singleClaimQuotedFeeWethWei,BORROWER]})},tag]);diagnostic.returnedPrizeWei=decodeFunctionResult({abi:vaultAbi,functionName:'claimPrize',data:r});}catch(e){diagnostic.errorKind=e.safeKind||e.name;diagnostic.revertData=e.revertData;if(e.revertData){try{const d=decodeErrorResult({abi:errorAbi,data:e.revertData});diagnostic.decodedError={name:d.errorName,args:d.args};}catch{diagnostic.unknownErrorSelector=e.revertData.slice(0,10);}}}report.diagnostics.push(diagnostic);}
   report.candidates.push(rec);
  }
  report.positiveExactClaimCount=report.candidates.filter(c=>c.exactClaimRewardWei>0n).length;finish(report.positiveExactClaimCount?'POSITIVE_EXACT_CLAIMS_NEED_FULL_CYCLE_QUOTE':'NO_POSITIVE_EXACT_CLAIM_IN_BOUNDED_SAMPLE');
 }
}catch(error){finish('STOPPED_WITHOUT_EXECUTION',error);process.exitCode=2;}finally{clearTimeout(timer);abort.abort();}
