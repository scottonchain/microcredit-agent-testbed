#!/usr/bin/env node
// Simulates configured vault/pool callers with eth_call ONLY. No signer exists.
// Node >=20; npm install --save-exact viem@2.17.0
// BASE_READ_RPC=approvedHTTPS node read-only-claim-diagnostic.mjs > diagnostic.json
import { createPublicClient, http, parseAbi, decodeErrorResult } from 'viem';
import { base } from 'viem/chains';
const POOL='0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb';
const VAULT='0x7f5c2b379b88499ac2b997db583f8079503f25b9';
const WINNER='0xaf5911696ece7f384acff055ec435091487fc17a';
const RECIPIENT='0x62C4A163026feedB3eA1045d90bBa96d0C5d4F0B';
const errors=parseAbi([
  'error CallerNotClaimer(address caller,address claimer)',
  'error ClaimRecipientZeroAddress()', 'error ClaimPeriodExpired()',
  'error PrizePoolShutdown()', 'error PrizeIsZero()',
  'error RewardRecipientZeroAddress()',
  'error RewardTooLarge(uint256 reward,uint256 maxReward)',
  'error InsufficientLiquidity(uint104 requestedLiquidity)',
  'error DidNotWin(address vault,address winner,uint8 tier,uint32 prizeIndex)',
  'error AlreadyClaimed(address vault,address winner,uint8 tier,uint32 prizeIndex)',
  'error InvalidTier(uint8 tier,uint8 numberOfTiers)',
  'error InvalidPrizeIndex(uint32 invalidPrizeIndex,uint32 prizeCount,uint8 tier)',
  'error ReturnDataOverLimit(uint256 returnDataSize,uint256 hookDataLimit)',
  'error VrgdaClaimFeeBelowMin(uint256 minFee,uint256 fee)',
  'error FeeRecipientZeroAddress()',
  'error Error(string)', 'error Panic(uint256)'
]);
const vaultAbi=parseAbi([
  'function claimer() view returns(address)',
  'function prizePool() view returns(address)',
  'function getHooks(address) view returns((bool useBeforeClaimPrize,bool useAfterClaimPrize,address implementation))',
  'function claimPrize(address,uint8,uint32,uint96,address) returns(uint256)'
]);
const poolAbi=parseAbi([
  'function getLastAwardedDrawId() view returns(uint24)',
  'function isDrawFinalized(uint24) view returns(bool)',
  'function wasClaimed(address,address,uint24,uint8,uint32) view returns(bool)',
  'function isWinner(address,address,uint8,uint32) view returns(bool)',
  'function getTierPrizeSize(uint8) view returns(uint256)',
  'function getTierRemainingLiquidity(uint8) view returns(uint256)',
  'function reserve() view returns(uint256)',
  'function drawClosesAt(uint24) view returns(uint48)',
  'function claimPrize(address,uint8,uint32,address,uint96,address) returns(uint256)'
]);
const claimerAbi=parseAbi([
  'function computeFeePerClaim(uint8,uint256) view returns(uint256)',
  'function claimPrizes(address,uint8,address[],uint32[][],address,uint256) returns(uint256)'
]);
const report={schema:'codex.ptv5-read-only-revert-diagnostic/1',startedAt:new Date().toISOString(),
  readOnly:true,signing:false,spending:false,assumedEthCallSendersOnly:true,stage:'configuration',calls:0,
  vault:VAULT,pool:POOL,winner:WINNER,tier:6,prizeIndex:264,recipient:RECIPIENT,
  caveat:'The from field only selects eth_call simulation context. No configured caller is impersonated onchain; no private key is used. Direct pool simulation isolates the inner failure but does not replace normal permitted claim execution.',
  results:{}};
const deadline=Date.now()+90_000;
let client,blockNumber;
function json(v){return JSON.stringify(v,(_,x)=>typeof x==='bigint'?x.toString():x,2)}
function failure(error){
  const out={kind:error.name||'Error'};
  let e=error,visited=new Set();
  for(let i=0;e&&i<12&&!visited.has(e);i++,e=e.cause){
    visited.add(e);
    if(e.data&&typeof e.data==='object'&&e.data.errorName){out.errorName=e.data.errorName;out.args=e.data.args;}
    for(const value of [e.raw,e.rawData,e.data]){
      if(typeof value==='string'&&/^0x[0-9a-fA-F]+$/.test(value)&&value.length<=4096){
        out.revertData=value;
        try{const d=decodeErrorResult({abi:errors,data:value});out.errorName=d.errorName;out.args=d.args}catch{}
      }
    }
  }
  return out; // Never emit error.message/stack: provider URL may contain a key.
}
async function op(name,fn){
  if(++report.calls>25||Date.now()>deadline)throw new Error('ReadBudget');
  try{const value=await fn();report.results[name]={ok:true,value};return value}
  catch(e){report.results[name]={ok:false,...failure(e)};return undefined}
}
try{
  const rpc=process.env.BASE_READ_RPC;
  if(!rpc||new URL(rpc).protocol!=='https:')throw new Error('ApprovedHttpsRpcRequired');
  client=createPublicClient({chain:base,transport:http(rpc,{retryCount:0,timeout:5000})});
  if(await op('chainId',()=>client.getChainId())!==8453)throw new Error('WrongChain');
  const blockArg=process.argv[2];
  if(blockArg!==undefined&&!/^\d+$/.test(blockArg))throw new Error('InvalidBlockArgument');
  const block=await op('block',()=>client.getBlock(blockArg?{blockNumber:BigInt(blockArg)}:{blockTag:'latest'}));
  if(!block||block.number===null)throw new Error('BlockUnavailable');
  // Avoid publishing the entire block transaction list in result artifact.
  report.results.block={ok:true,value:{number:block.number,hash:block.hash,timestamp:block.timestamp}};
  blockNumber=block.number;
  report.stage='fresh_state';
  const read=(address,abi,functionName,args=[])=>client.readContract({address,abi,functionName,args,blockNumber});
  const claimer=await op('actualVaultClaimer',()=>read(VAULT,vaultAbi,'claimer'));
  const vaultPool=await op('vaultPool',()=>read(VAULT,vaultAbi,'prizePool'));
  const draw=await op('drawId',()=>read(POOL,poolAbi,'getLastAwardedDrawId'));
  if(!claimer||vaultPool?.toLowerCase()!==POOL||draw===undefined)throw new Error('ContractMismatch');
  const fee=await op('currentSingleFee',()=>read(claimer,claimerAbi,'computeFeePerClaim',[6,1n]));
  if(fee===undefined||fee>(1n<<96n)-1n)throw new Error('FeeUnavailable');
  await op('drawFinalized',()=>read(POOL,poolAbi,'isDrawFinalized',[draw]));
  await op('drawClosesAt',()=>read(POOL,poolAbi,'drawClosesAt',[draw]));
  await op('isWinner',()=>read(POOL,poolAbi,'isWinner',[VAULT,WINNER,6,264]));
  await op('wasClaimed',()=>read(POOL,poolAbi,'wasClaimed',[VAULT,WINNER,draw,6,264]));
  await op('hooks',()=>read(VAULT,vaultAbi,'getHooks',[WINNER]));
  await op('tierPrizeSize',()=>read(POOL,poolAbi,'getTierPrizeSize',[6]));
  await op('tierRemainingLiquidity',()=>read(POOL,poolAbi,'getTierRemainingLiquidity',[6]));
  await op('reserve',()=>read(POOL,poolAbi,'reserve'));
  report.stage='exact_eth_call_diagnostic';
  // Claimer catches the per-prize revert; directly simulate its configured
  // vault call to surface the same cause. eth_call discards all state writes.
  await op('vaultClaimFromConfiguredClaimer',async()=>{
    const r=await client.simulateContract({address:VAULT,abi:[...vaultAbi,...errors],functionName:'claimPrize',args:[WINNER,6,264,fee,RECIPIENT],account:claimer,blockNumber});return r.result;
  });
  // Isolate the PrizePool call with its proper vault caller and no custom hooks.
  await op('poolClaimFromVault',async()=>{
    const r=await client.simulateContract({address:POOL,abi:[...poolAbi,...errors],functionName:'claimPrize',args:[WINNER,6,264,WINNER,fee,RECIPIENT],account:VAULT,blockNumber});return r.result;
  });
  await op('normalClaimerCall',async()=>{
    const r=await client.simulateContract({address:claimer,abi:[...claimerAbi,...errors],functionName:'claimPrizes',args:[VAULT,6,[WINNER],[[264]],RECIPIENT,fee],account:RECIPIENT,blockNumber});return r.result;
  });
  report.stage='complete';report.status='COMPLETE_READ_ONLY_DIAGNOSTIC';
}catch(e){report.status='STOPPED_WITHOUT_EXECUTION';report.error=failure(e);process.exitCode=2}
report.finishedAt=new Date().toISOString();console.log(json(report));
