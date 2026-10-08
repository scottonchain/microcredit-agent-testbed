#!/usr/bin/env node
// Synthetic/offline only. Public dummy key; no real wallet file is opened.
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {readFileSync} from 'node:fs';
import {validateHarvest,validateHarvestPreparation,BORROWER,LENDER,WETH,LENS,QUOTE_HELPER_SHA256,AUDITOR_SHA256,CLONE_STRATEGY,CLONE_VAULT,CLONE_IMPLEMENTATION,CLONE_RUNTIME,CLONE_RUNTIME_HASH,CLONE_IMPLEMENTATION_RUNTIME_HASH,CLONE_VERIFIED_SOURCE_SHA256} from './sign-exact-harvest-phase.mjs';
const require=createRequire('/tmp/codex-eth-audit-deps/package.json');
const {parseAbi,encodeFunctionData,encodeFunctionResult,serializeTransaction,parseTransaction,keccak256,recoverTransactionAddress}=require('viem');
const {privateKeyToAccount}=require('viem/accounts');
const now=Date.parse('2026-10-08T03:00:00Z'),stamp=String(Math.floor(now/1000)),iso=new Date(now).toISOString();
const strategy='0x1111111111111111111111111111111111111111',vault='0x2222222222222222222222222222222222222222',oracle='0x420000000000000000000000000000000000000f',priceFeed='0x71041dddad3595f9ced3dccfbe3d1f4b0a16bb70';
const h=n=>'0x'+String(n).padStart(64,'0'),s=n=>String(n),clone=x=>JSON.parse(JSON.stringify(x));
const a=parseAbi(['function harvest(address callFeeRecipient)']),w=parseAbi(['function withdraw(uint256)']);
const la=parseAbi(['function harvest(address _strategy,address _rewardToken) returns((uint256 callReward,uint256 lastHarvest,uint256 gasUsed,uint256 blockNumber,int8 isCalmBeforeHarvest,bool paused,bool success,bytes harvestResult) res)']);
const gas=[21000n,200000n,100000n,21000n],mf=8000000n,tip=2000000n,rs=gas.map(g=>g*mf+210000000n),bg=rs.slice(1).reduce((a,b)=>a+b,0n),lg=rs[0],fee=lg+1000000000n,principal=bg+bg/10n+1n,req=bg+fee+1000000000n,reward=req*2n;
const data=['0x',encodeFunctionData({abi:a,functionName:'harvest',args:[BORROWER]}),encodeFunctionData({abi:w,functionName:'withdraw',args:[reward]}),'0x'],to=[BORROWER,strategy,WETH,LENDER],values=[principal,0n,0n,principal+fee],names=['fund','harvest','unwrap','repay'];
const transactions=gas.map((g,i)=>{const f={type:'eip1559',chainId:8453,nonce:i===0?2:i-1,gas:g,maxFeePerGas:mf,maxPriorityFeePerGas:tip,to:to[i],data:data[i],value:values[i]},enc=serializeTransaction(f);return {name:names[i],from:i===0?LENDER:BORROWER,...f,nonce:s(f.nonce),gas:s(g),maxFeePerGas:s(mf),maxPriorityFeePerGas:s(tip),value:s(values[i]),unsignedSerializedForOracleOnly:enc,unsignedByteLength:s((enc.length-2)/2),l2FeeHardCapWei:s(g*mf),l1SnapshotUpperQuoteWei:'100000000',operatorSnapshotUpperQuoteWei:'5000000',l1ReservedWei:'200000000',operatorReservedWei:'10000000',totalGasReservedWei:s(rs[i])};});
const contracts={vault,strategy,freshVaultStrategy:strategy,nativeRewardToken:WETH,paused:false,lastHarvest:'1700000000',weth:WETH,lens:LENS,gasOracle:oracle};
const fingerprints=Object.fromEntries(Object.entries({vault,strategy,weth:WETH,oracle,lens:LENS,priceFeed}).map(([k,address],i)=>[k,{address,runtimeCodeKeccak256:h(i+1)}]));
const qualification=Object.fromEntries(['vaultStillUsesSelectedStrategy','unpaused','canonicalWethNative','positiveActualSimulatedLensWethDelta','directBorrowerHarvestNonreverting','borrowerStartsAtZero','principalNativeCap','principalUsdCap','grossExposureUsdCap','worstLossUsdCap','principalCoversUpdatedBorrowerGas','lensRewardCoversUpdatedReserves','lenderHasFundingAndGas','lenderPositiveMargin','noPendingTransactions','includesCurrentL1AndOperatorQuotes','noActualLensTransaction'].map(k=>[k,true]));
const usd=wei=>(wei*360000000000n+100000000000000000000n-1n)/100000000000000000000n;
const lensRaw=encodeFunctionResult({abi:la,functionName:'harvest',result:{callReward:reward,lastHarvest:1700000000n,gasUsed:150000n,blockNumber:100n,isCalmBeforeHarvest:1,paused:false,success:true,harvestResult:'0x'}});
const q={schema:'codex.eth-gas-read-only-harvest-cycle-quote/1',venue:'beefy-harvest',mode:'READ_ONLY_DIRECT_HARVEST_CONSERVATIVE_CYCLE',status:'QUALIFIED_READ_ONLY_PACKET_REQUIRES_SOURCE_AND_SIGNER_REVIEW',chainId:8453,borrower:BORROWER,lender:LENDER,weth:WETH,lens:LENS,finishedAt:iso,qualifiedForExactTransactionReview:true,requiresIndependentSignerReviewAndFreshSimulation:true,signerMustNeverSignLensIntent:true,qualification,spendAuthorized:false,loanDisbursed:false,liveExecution:false,earnedRevenue:false,input:{vault,strategy},block:{number:'100',hash:h(100),timestamp:stamp,baseFeePerGas:'3000000'},contracts,fingerprints,before:{borrower:{nativeWei:'0',wethWei:'0',nonce:'0'},lender:{nativeWei:'10000000000000000',wethWei:'0',nonce:'2'}},pendingNonces:{borrower:'0',lender:'2'},transactions,caps:{nativePrincipalWei:'50000000000000',principalUsdMicros:'500000',grossExposureUsdMicros:'1000000',worstLossUsdMicros:'250000'},ethUsd:{feed:priceFeed,decimals:8,description:'ETH / USD',answer:'300000000000',updatedAt:stamp,capPriceAnswerWith20PercentBuffer:'360000000000'},lensSimulation:{to:LENS,mode:'ETH_CALL_ONLY_NEVER_SUBMIT',data:encodeFunctionData({abi:la,functionName:'harvest',args:[strategy,WETH]}),rawReturnData:lensRaw,actualSimulatedLensWethDeltaWei:s(reward)},directHarvestSimulation:{from:BORROWER,to:strategy,feeRecipient:BORROWER,data:data[1],valueWei:'0',rawReturnData:'0x',nonreverting:true,estimatedGas:'170000',gasLimitReserved:'200000'},terms:{nativePrincipalWei:s(principal),loanFeeWei:s(fee),debtWei:s(principal+fee),workCostWei:'0',expectedExternalRewardWei:s(reward),borrowerGasReservedWei:s(bg),lenderGasReservedWei:s(lg),totalGasReservedWei:s(bg+lg),requiredExternalRewardWei:s(req),borrowerMarginAtReservedGasWei:s(reward-bg-fee),lenderMarginAtReservedGasWei:s(fee-lg),targetBorrowerMarginWei:'1000000000',targetLenderMarginWei:'1000000000',worstLossExposureWei:s(principal+lg),grossExposureWei:s(principal+bg+lg),principalUsdMicrosAtBufferedPrice:s(usd(principal)),grossExposureUsdMicrosAtBufferedPrice:s(usd(principal+bg+lg)),worstLossUsdMicrosAtBufferedPrice:s(usd(principal+lg))}};
// Match the updated quote's empty-code, pricing/freshness and preview-only metadata.
q.actorCode={borrower:'0x',lender:'0x',borrowerHasEmptyCode:true,lenderHasEmptyCode:true,nativeTransfer21000GasAssumptionsVerified:true};
Object.assign(q.qualification,{actorsHaveEmptyCode:true,principalIncludesUpdatedTenPercentGasReserve:true,lenderMeetsDeclaredTarget:true,pricingStable:true,blockStillWithinWallClockFreshnessBounds:true});
q.pricing={maxPasses:3,stable:true,passes:[{pass:2,pricedPrincipalWei:s(principal),pricedLoanFeeWei:s(fee),borrowerGasReservedWei:s(bg),lenderGasReservedWei:s(lg),recommendedPrincipalWei:s(principal),recommendedLoanFeeWei:s(fee),unsignedByteLengths:transactions.map(t=>t.unsignedByteLength),stable:true}]};
const freshness={wallClockUnixSeconds:stamp,blockTimestamp:stamp,ageSeconds:'0',maxAgeSeconds:120,maxFutureSeconds:5,withinBounds:true};
q.freshness={initial:clone(freshness),completed:clone(freshness)};
q.transactions[2].amountBasis='PREVIEW_ONLY_REBUILD_FROM_ACTUAL_CANONICAL_WETH_HARVEST_RECEIPT';q.transactions[2].previewLensRewardWei=s(reward);
q.signerMustNeverPresignPreviewBundle=true;q.requiresActualHarvestReceiptBeforeUnwrapRebuild=true;
const fg=21000n*6000000n+105000000n,hashes={quote:'a'.repeat(64),evidence:'b'.repeat(64)};
const topicAddress=address=>'0x'+'0'.repeat(24)+address.slice(2);
const transfer={address:WETH,topics:['0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef',topicAddress(strategy),topicAddress(BORROWER)],data:'0x'+reward.toString(16).padStart(64,'0'),logIndex:'0x0',removed:false};
const simCall={from:BORROWER,to:strategy,nonce:'0x0',gas:'0x'+gas[1].toString(16),maxFeePerGas:'0x'+mf.toString(16),maxPriorityFeePerGas:'0x'+tip.toString(16),value:'0x0',data:data[1]};
const e={schema:'codex.eth-gas-funded-harvest-evidence/1',chainId:8453,quoteSha256:hashes.quote,observedAt:iso,funding:{transaction:{hash:h(999),chainId:8453,type:2,from:LENDER,to:BORROWER,nonce:'2',valueWei:s(principal),data:'0x'},receipt:{transactionHash:h(999),status:'0x1',blockNumber:'101',blockHash:h(101),gasUsed:'21000',effectiveGasPrice:'6000000',l1FeeWei:'100000000',operatorFeeWei:'5000000'}},fresh:{block:{number:'101',hash:h(101),timestamp:stamp},contracts:clone(contracts),fingerprints:clone(fingerprints),borrower:{address:BORROWER,nativeWei:s(principal),wethWei:'0',nonce:'0',pendingNonce:'0'},lender:{address:LENDER,nativeWei:s(10000000000000000n-principal-fg),nonce:'3',pendingNonce:'3'},directHarvestSimulation:{nonreverting:true,from:BORROWER,to:strategy,data:data[1],valueWei:'0',blockHash:h(101),estimatedGas:'170000',requiredMaxFeePerGas:s(mf),l1FeeUpperBoundWei:'100000000',operatorFeeUpperBoundWei:'5000000'},directRewardEvidence:{method:'eth_simulateV1',rpcBlockTag:'0x65',simulationInput:{blockStateCalls:[{calls:[simCall]}],validation:true,traceTransfers:true},rawResult:[{calls:[{status:'0x1',returnData:'0x',logs:[transfer]}]}],actualSimulatedDirectEoaWethRewardWei:s(reward)}}};
const r={schema:'codex.eth-gas-exact-harvest-review/1',phase:'harvest',executionAllowed:true,authorizationReference:'SYNTHETIC OFFLINE TEST ONLY',reviewedAt:iso,quoteSha256:hashes.quote,evidenceSha256:hashes.evidence,quoteHelperSha256:QUOTE_HELPER_SHA256,auditorSha256:AUDITOR_SHA256,vault,strategy,runtimeCodeKeccak256:Object.fromEntries(Object.entries(fingerprints).map(([k,v])=>[k,v.runtimeCodeKeccak256])),unsignedHarvestKeccak256:keccak256(transactions[1].unsignedSerializedForOracleOnly),strategyReview:{deployedSourceIndependentlyVerified:true,publicHarvestPaysExplicitRecipient:true,noTeamSeedVerified:true,proxyDetected:false,runtimeCodeKeccak256:fingerprints.strategy.runtimeCodeKeccak256,sourceEvidence:'synthetic source evidence only',feeMechanismEvidence:'synthetic fee mechanism only',noTeamSeedEvidence:'synthetic independence only'}};
const valid=validateHarvest(q,e,r,hashes,now);assert.equal(valid.public.selector,'0x0e5c011e');
const checks=[
 ['wrong chain',q=>{q.chainId=1;}],['unapproved',(_q,_e,r)=>{r.executionAllowed=false;}],['unwrap phase',(_q,_e,r)=>{r.phase='unwrap';}],
 ['stale evidence',(_q,e)=>{e.observedAt=new Date(now-61000).toISOString();}],['bad evidence hash',(_q,_e,r)=>{r.evidenceSha256='c'.repeat(64);}],
 ['unverified source',(_q,_e,r)=>{r.strategyReview.deployedSourceIndependentlyVerified=false;}],['proxy route',(_q,_e,r)=>{r.strategyReview.proxyDetected=true;}],['team seed unknown',(_q,_e,r)=>{r.strategyReview.noTeamSeedVerified=false;}],
 ['strategy changed',(_q,e)=>{e.fresh.contracts.freshVaultStrategy=LENS;}],['paused strategy',(_q,e)=>{e.fresh.contracts.paused=true;}],['wrong native token',(_q,e)=>{e.fresh.contracts.nativeRewardToken=LENDER;}],['runtime changed',(_q,e)=>{e.fresh.fingerprints.strategy.runtimeCodeKeccak256=h(99);}],
 ['lens transaction',q=>{q.transactions[1].to=LENS;}],['nonzero harvest value',q=>{q.transactions[1].value='1';}],['wrong recipient calldata',q=>{q.transactions[1].data=encodeFunctionData({abi:a,functionName:'harvest',args:[LENDER]});}],['wrong nonce',q=>{q.transactions[1].nonce='1';}],
 ['excess principal',q=>{q.terms.nativePrincipalWei='50000000000001';}],['false qualification',q=>{q.qualification.unpaused=false;}],
 ['failed funding',(_q,e)=>{e.funding.receipt.status='0x0';}],['wrong funding amount',(_q,e)=>{e.funding.transaction.valueWei='1';}],['funding fee overrun',(_q,e)=>{e.funding.receipt.l1FeeWei='99999999999999';}],['borrower pending tx',(_q,e)=>{e.fresh.borrower.pendingNonce='1';}],
 ['empty direct return alone',(_q,e)=>{delete e.fresh.directRewardEvidence;}],['zero successful fee',(_q,e)=>{e.fresh.directRewardEvidence.rawResult[0].calls[0].logs=[];}],['failed direct call',(_q,e)=>{e.fresh.directRewardEvidence.rawResult[0].calls[0].status='0x0';}],['lens simulation callee',(_q,e)=>{e.fresh.directRewardEvidence.simulationInput.blockStateCalls[0].calls[0].to=LENS;}],['simulation state override',(_q,e)=>{e.fresh.directRewardEvidence.simulationInput.blockStateCalls[0].stateOverrides={};}],
 ['duplicate fee logs',(_q,e)=>{e.fresh.directRewardEvidence.rawResult[0].calls[0].logs.push(clone(transfer));}],['removed fee log',(_q,e)=>{e.fresh.directRewardEvidence.rawResult[0].calls[0].logs[0].removed=true;}],['fee from lender gift',(_q,e)=>{e.fresh.directRewardEvidence.rawResult[0].calls[0].logs[0].topics[1]=topicAddress(LENDER);}],
 ['fresh fee quote overrun',(_q,e)=>{e.fresh.directHarvestSimulation.l1FeeUpperBoundWei='100000001';}],['quote source changed',(_q,_e,r)=>{r.quoteHelperSha256='c'.repeat(64);}],['auditor changed',(_q,_e,r)=>{r.auditorSha256='c'.repeat(64);}],
];
for(const [label,mutate]of checks){const x=clone(q),y=clone(e),z=clone(r);mutate(x,y,z);assert.throws(()=>validateHarvest(x,y,z,hashes,now),undefined,label);}
const dummy=privateKeyToAccount('0x'+'0'.repeat(63)+'1'),raw=await dummy.signTransaction(valid.transaction),parsed=parseTransaction(raw);assert.equal((await recoverTransactionAddress({serializedTransaction:raw})).toLowerCase(),dummy.address.toLowerCase());assert.equal(serializeTransaction(valid.transaction),serializeTransaction({...parsed,r:undefined,s:undefined,v:undefined,yParity:undefined}));
// Public runtime fixture from the read-only r14 record, not a source certificate.
// Every source/fee/independence assertion below is SYNTHETIC and must never enable execution.
const runtime=JSON.parse(readFileSync(new URL('./sign-exact-harvest-clone-runtime.fixture.json',import.meta.url)));
assert.equal(keccak256(runtime.strategy_runtime),CLONE_RUNTIME_HASH);assert.equal(keccak256(runtime.implementation_runtime),CLONE_IMPLEMENTATION_RUNTIME_HASH);assert.equal(runtime.source.source_verification_status,'NOT_VERIFIED');
const cq=clone(q),ce=clone(e),cr=clone(r),testSourceSha='f'.repeat(64);
cq.input.vault=CLONE_VAULT;cq.input.strategy=CLONE_STRATEGY;cr.vault=CLONE_VAULT;cr.strategy=CLONE_STRATEGY;
for(const c of [cq.contracts,ce.fresh.contracts]){c.vault=CLONE_VAULT;c.strategy=CLONE_STRATEGY;c.freshVaultStrategy=CLONE_STRATEGY;}
for(const f of [cq.fingerprints,ce.fresh.fingerprints]){f.vault.address=CLONE_VAULT;f.strategy.address=CLONE_STRATEGY;f.strategy.runtimeCodeKeccak256=CLONE_RUNTIME_HASH;}
cr.runtimeCodeKeccak256.strategy=CLONE_RUNTIME_HASH;
const ct=cq.transactions[1];ct.to=CLONE_STRATEGY;ct.unsignedSerializedForOracleOnly=serializeTransaction({...valid.transaction,to:CLONE_STRATEGY});ct.unsignedByteLength=s((ct.unsignedSerializedForOracleOnly.length-2)/2);
cq.directHarvestSimulation.to=CLONE_STRATEGY;ce.fresh.directHarvestSimulation.to=CLONE_STRATEGY;
cq.lensSimulation.data=encodeFunctionData({abi:la,functionName:'harvest',args:[CLONE_STRATEGY,WETH]});
ce.fresh.directRewardEvidence.simulationInput.blockStateCalls[0].calls[0].to=CLONE_STRATEGY;
ce.fresh.directRewardEvidence.rawResult[0].calls[0].logs[0].topics[1]=topicAddress(CLONE_STRATEGY);
cr.unsignedHarvestKeccak256=keccak256(ct.unsignedSerializedForOracleOnly);
Object.assign(cr.strategyReview,{proxyDetected:true,proxyKind:'EIP1167_IMMUTABLE_CLONE',runtimeCodeKeccak256:CLONE_RUNTIME_HASH,immutableCloneRuntimeIndependentlyVerified:true,implementationSourceIndependentlyVerified:true,implementationFeeRoutingIndependentlyVerified:true,implementationUpgradeRoutesExcluded:true,cloneStorageInitializationReviewed:true,implementationAddress:CLONE_IMPLEMENTATION,cloneRuntimeCode:CLONE_RUNTIME,implementationRuntimeCodeKeccak256:CLONE_IMPLEMENTATION_RUNTIME_HASH,implementationSourceEvidence:'SYNTHETIC SOURCE EVIDENCE ONLY',implementationSourceSha256:testSourceSha});
cr.verifiedImplementationSourceSha256=testSourceSha;
ce.fresh.immutableCloneEvidence={strategyAddress:CLONE_STRATEGY,strategyRuntimeCode:runtime.strategy_runtime,implementationAddress:CLONE_IMPLEMENTATION,implementationRuntimeCode:runtime.implementation_runtime,implementationRuntimeCodeKeccak256:CLONE_IMPLEMENTATION_RUNTIME_HASH,implementationSourceSha256:testSourceSha};
const prepared=validateHarvestPreparation(cq,ce,cr,hashes,now);
assert.equal(prepared.public.immutableCloneBranch,true);assert.equal(prepared.public.cloneExecutionEnabled,false);assert.equal(CLONE_VERIFIED_SOURCE_SHA256,null);
assert.throws(()=>validateHarvest(cq,ce,cr,hashes,now),/CloneBranchPreparationOnly/);
const cloneChecks=[
 ['wrong clone byte suffix',(_q,e)=>{e.fresh.immutableCloneEvidence.strategyRuntimeCode=CLONE_RUNTIME.slice(0,-2)+'00';}],
 ['clone runtime extra bytes',(_q,e)=>{e.fresh.immutableCloneEvidence.strategyRuntimeCode=CLONE_RUNTIME+'00';}],
 ['wrong hardcoded implementation',(_q,_e,r)=>{r.strategyReview.implementationAddress=LENDER;}],
 ['fresh wrong implementation',(_q,e)=>{e.fresh.immutableCloneEvidence.implementationAddress=LENS;}],
 ['implementation runtime changed',(_q,e)=>{const c=e.fresh.immutableCloneEvidence.implementationRuntimeCode;e.fresh.immutableCloneEvidence.implementationRuntimeCode=c.slice(0,-2)+(c.slice(-2)==='00'?'01':'00');}],
 ['fresh implementation hash changed',(_q,e)=>{e.fresh.immutableCloneEvidence.implementationRuntimeCodeKeccak256=h(999);} ],
 ['source hash differs from review',(_q,_e,r)=>{r.verifiedImplementationSourceSha256='e'.repeat(64);}],
 ['fresh source hash differs',(_q,e)=>{e.fresh.immutableCloneEvidence.implementationSourceSha256='e'.repeat(64);}],
 ['missing source verification',(_q,_e,r)=>{r.strategyReview.implementationSourceIndependentlyVerified=false;}],
 ['upgrade route not excluded',(_q,_e,r)=>{r.strategyReview.implementationUpgradeRoutesExcluded=false;}],
 ['missing fee-routing verification',(_q,_e,r)=>{r.strategyReview.implementationFeeRoutingIndependentlyVerified=false;}],
 ['unreviewed clone storage',(_q,_e,r)=>{r.strategyReview.cloneStorageInitializationReviewed=false;}],
 ['other proxy type',(_q,_e,r)=>{r.strategyReview.proxyKind='ERC1967';}],
 ['clone disguised as nonproxy',(_q,_e,r)=>{r.strategyReview.proxyDetected=false;r.strategyReview.proxyKind='NONE';}],
 ['other clone strategy',q=>{q.input.strategy=strategy;}],
 ['other clone vault',q=>{q.input.vault=vault;}],
];
for(const [label,mutate]of cloneChecks){const x=clone(cq),y=clone(ce),z=clone(cr);mutate(x,y,z);assert.throws(()=>validateHarvestPreparation(x,y,z,hashes,now),undefined,label);}
console.log(JSON.stringify({synthetic:true,offline:true,realWalletKeyRead:false,realTransactionsSigned:false,negativeChecksPassed:checks.length,cloneNegativeChecksPassed:cloneChecks.length,positiveValidationPassed:true,clonePreparationPassed:true,realCloneExecutionStaticallyDisabled:true,dummyEip1559RoundTripPassed:true}));
