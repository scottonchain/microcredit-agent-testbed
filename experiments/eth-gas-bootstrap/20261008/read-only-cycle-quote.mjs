#!/usr/bin/env node
// READ ONLY: restricted JSON-RPC, no key handling, signing, deployment or sending.
// Node >=20; exact dependency viem@2.17.0. A quote is never spend authorization.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';

const argv = process.argv.slice(2);
if (argv.includes('--help')) {
  console.log(`Install in a dedicated folder: npm install --save-exact viem@2.17.0
Run: BASE_READ_RPC='approved HTTPS RPC' node read-only-cycle-quote.mjs --probe probe.json --index 0 > cycle-quote.json
The index selects ONE candidate from probe.candidates. An arbitrary supplied candidate is not trusted.
Optional --work-cost-wei N (default 0, on-chain margin only), --rpc-env NAME.
Finite limits: 60 HTTP / 75 RPC operations / 90 seconds. No endpoint is printed.
Stages after claim use conservative gas limits, not falsely described as gas estimates.
Attempts ONE optional eth_simulateV1 full-cycle check; an unsupported provider is recorded.
Re-read and re-simulate immediately before any separately authorized transaction.
No transaction is signed or sent. Unsigned serialization is only oracle fee input.`);
  process.exit(0);
}
function arg(name, fallback) {
  const i = argv.indexOf(name);
  if (i < 0) return fallback;
  if (!argv[i + 1] || argv[i + 1].startsWith('--')) throw new Error('ArgumentValue');
  return argv[i + 1];
}
const BORROWER = '0x62c4a163026feedb3ea1045d90bba96d0c5d4f0b';
const LENDER = '0xdb3de88e9dba1b07a06d186dfbd86fae309043ad';
// Public root-controlled wallet inventory, never private material. Include the team lender.
const CONTROLLED_WINNERS = new Set([
  '0x5225c44c41566d2c8785cfadfc712a21c0b51575','0xab7a7ee666b83607cb9d11b5d54f49c1085f980c',BORROWER,
  '0xe2a2fd6c6b1e2ddf70b3edc84b10e7d6e1039f2f','0x421ada122cf9823ee129179354a461013e0156e4',
  '0x711e15425326fe01b958ea97ff37aa6336a7cec3','0x56214ae2cfcd5ed76cb79126a595010cb831c407',
  '0x43bd2b18caaf9ef7cefadbcedb392d378469f118','0xb96c4e7c0cc25af24795097b6d8eac17b8519866',
  '0x4d05b8b4fe3d90c15f54dc041ef29a1bc7c59633','0xb07f3b50d91e584f05817d367a12fab1e7bfad6f',
  '0x9e6bb5e66138666a69e366f7bb0bd6489c347e9f','0x59b2c48fdeda316d4a442627e4b4a2e1ad81d2b1',LENDER
]);
const POOL = '0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb';
const WETH = '0x4200000000000000000000000000000000000006';
const ORACLE = '0x420000000000000000000000000000000000000f';
const PRICE_FEED = '0x71041dddad3595f9ced3dccfbe3d1f4b0a16bb70';
const MAX_MS = 90_000, MAX_HTTP = 60, MAX_RPC = 75;
const started = Date.now(), abort = new AbortController();
const report = {
  schema: 'codex.eth-gas-read-only-cycle-quote/1', mode: 'READ_ONLY_EXACT_CLAIM_CONSERVATIVE_CYCLE',
  chainId: 8453, startedAt: new Date().toISOString(), status: 'RUNNING',
  borrower: BORROWER, lender: LENDER, counters: { httpRequests: 0, rpcOperations: 0 },
  caps: { nativePrincipalWei: '50000000000000', principalUsdMicros: '500000', grossExposureUsdMicros: '1000000', worstLossUsdMicros: '250000' },
  spendAuthorized: false, loanDisbursed: false, liveExecution: false, earnedRevenue: false,
  caveats: [
    'A positive eth_call result can race; receipt status 1 can contain zero successful claims.',
    'Plain-EOA claim has no atomic aggregate profit guard. One bounded failed claim is possible.',
    'Downstream limits are conservative reservations unless fullCycleSimulation is successful.',
    'L1 upper-bound API covers 99.99% of transactions, not a mathematical worst-case guarantee.',
    'L1 and operator quotes are snapshot values. The packet doubles them but cannot cap their future protocol prices.',
    'ETH/USD is an on-chain Chainlink snapshot; an additional 20% price buffer is used for dollar caps.',
    'Zero work cost means on-chain contribution margin only; it is not a claim of total business profitability.',
    'This helper never signs or sends. Later signer must independently validate every field and refresh state.'
  ],
  sources: {
    gasOracle: 'https://github.com/ethereum-optimism/optimism/blob/develop/packages/contracts-bedrock/src/L2/GasPriceOracle.sol',
    gasOracleFileBlobSha: 'ab6cdcf80c4fe4336aa0711d91982bc282c96f77',
    ethUsdFeed: 'https://data.chain.link/feeds/base/mainnet/eth-usd'
  }
};
let printed = false, stage = 'arguments';
function finish(status, error) {
  if (printed) return;
  printed = true;
  Object.assign(report, { status, stage, finishedAt: new Date().toISOString(), elapsedMs: Date.now() - started });
  if (error) report.error = { kind: error.safeKind || (/^[A-Za-z][A-Za-z0-9_]{0,80}$/.test(error.message||'') ? error.message : error.name) || 'Error', message: 'Read-only quote stopped. No signing or spending occurred.' };
  console.log(JSON.stringify(report, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2));
}
const deadline = setTimeout(() => { abort.abort(); finish('STOPPED_RUNTIME_CAP'); process.exit(2); }, MAX_MS);
try {
  const envName = arg('--rpc-env', 'BASE_READ_RPC');
  if (!/^[A-Z][A-Z0-9_]*$/.test(envName)) throw new Error('RpcEnvName');
  const endpoint = process.env[envName];
  if (!endpoint || new URL(endpoint).protocol !== 'https:') throw new Error('ApprovedHttpsRpcRequired');
  const inputPath = resolve(arg('--probe', 'probe.json'));
  const inputBytes = readFileSync(inputPath);
  if (inputBytes.length > 2_000_000) throw new Error('InputTooLarge');
  const probe = JSON.parse(inputBytes), index = Number(arg('--index', '0'));
  if (!Array.isArray(probe.candidates) || !Number.isInteger(index) || index < 0 || index >= probe.candidates.length) throw new Error('CandidateIndex');
  const candidate = probe.candidates[index];
  if (!/^0x[0-9a-fA-F]{40}$/.test(candidate.vault) || !/^0x[0-9a-fA-F]{40}$/.test(candidate.winner) || !Number.isInteger(candidate.tier) || candidate.tier < 0 || candidate.tier > 255 || !Number.isInteger(candidate.prizeIndex) || candidate.prizeIndex < 0 || candidate.prizeIndex > 0xffffffff) throw new Error('CandidateSchema');
  const vault = candidate.vault.toLowerCase(), winner = candidate.winner.toLowerCase();
  if (CONTROLLED_WINNERS.has(winner)) throw new Error('WinnerIsKnownControlledCounterparty');
  const workCost = BigInt(arg('--work-cost-wei', '0'));
  if (workCost < 0n || workCost > 50_000_000_000_000n) throw new Error('WorkCostLimit');
  report.input = { sha256: createHash('sha256').update(inputBytes).digest('hex'), candidateIndex: index, candidate: { vault, winner, tier: candidate.tier, prizeIndex: candidate.prizeIndex }, priorBlock: probe.block || null };
  const require = createRequire(import.meta.url);
  const viemEntry = require.resolve('viem');
  let packageRoot = dirname(viemEntry), manifest;
  for (let i = 0; i < 4; i++) { try { const p = JSON.parse(readFileSync(resolve(packageRoot, 'package.json'))); if (p.name === 'viem') { manifest = p; break; } } catch {} packageRoot = dirname(packageRoot); }
  if (!manifest || manifest.version !== '2.17.0') throw new Error('ExactViemVersionRequired');
  const { parseAbi, encodeFunctionData, decodeFunctionResult, serializeTransaction, keccak256 } = await import('viem');
  const hex = n => '0x' + BigInt(n).toString(16);
  const allowed = new Set(['eth_chainId','eth_getBlockByNumber','eth_call','eth_getCode','eth_getBalance','eth_getTransactionCount','eth_maxPriorityFeePerGas','eth_gasPrice','eth_estimateGas','eth_simulateV1']);
  let rpcId = 0;
  async function rpc(method, params) {
    if (!allowed.has(method)) throw new Error('DeniedRpcMethod');
    if (++report.counters.httpRequests > MAX_HTTP || ++report.counters.rpcOperations > MAX_RPC) throw new Error('RpcCap');
    if (Date.now() - started >= MAX_MS) throw new Error('RuntimeCap');
    const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type':'application/json' }, body: JSON.stringify({ jsonrpc:'2.0', id:++rpcId, method, params }), redirect:'error', signal:AbortSignal.any([abort.signal,AbortSignal.timeout(10_000)]) });
    const text = await response.text();
    if (!response.ok || text.length > 2_000_000) throw new Error('RpcHttpFailure');
    const result = JSON.parse(text);
    if (result.error) { const error = new Error('RpcError'); error.safeKind = 'RpcError_' + String(result.error.code); throw error; }
    if (!Object.hasOwn(result, 'result')) throw new Error('RpcResultMissing');
    return result.result;
  }
  stage = 'fresh_snapshot';
  if (BigInt(await rpc('eth_chainId', [])) !== 8453n) throw new Error('WrongChain');
  const block = await rpc('eth_getBlockByNumber', ['latest',false]);
  if (!block?.hash || !block?.number || !block?.timestamp || !block?.baseFeePerGas) throw new Error('BlockSchema');
  const tag = block.number;
  report.block = { number: BigInt(tag), hash: block.hash, timestamp: BigInt(block.timestamp), baseFeePerGas: BigInt(block.baseFeePerGas), fixedRpcCallTag: tag };
  const poolAbi = parseAbi(['function prizeToken() view returns(address)','function getLastAwardedDrawId() view returns(uint24)','function isWinner(address,address,uint8,uint32) view returns(bool)','function wasClaimed(address,address,uint24,uint8,uint32) view returns(bool)','function rewardBalance(address) view returns(uint256)','function withdrawRewards(address,uint256)']);
  const vaultAbi = parseAbi(['function claimer() view returns(address)','function prizePool() view returns(address)','function getHooks(address) view returns((bool useBeforeClaimPrize,bool useAfterClaimPrize,address implementation))']);
  const claimerAbi = parseAbi(['function prizePool() view returns(address)','function claimPrizes(address,uint8,address[],uint32[][],address,uint256) returns(uint256)']);
  const wethAbi = parseAbi(['function balanceOf(address) view returns(uint256)','function withdraw(uint256)']);
  const oracleAbi = parseAbi(['function getL1FeeUpperBound(uint256) view returns(uint256)','function getOperatorFee(uint256) view returns(uint256)','function isFjord() view returns(bool)']);
  const priceAbi = parseAbi(['function decimals() view returns(uint8)','function description() view returns(string)','function latestRoundData() view returns(uint80,int256,uint256,uint256,uint80)']);
  const read = async (to,abi,name,args=[]) => decodeFunctionResult({ abi,functionName:name,data:await rpc('eth_call',[{ to,data:encodeFunctionData({abi,functionName:name,args}) },tag]) });
  const [claimer, vaultPool, prizeToken, drawId, hooks, borrowerEth, lenderEth, borrowerNonce, lenderNonce, borrowerWeth, lenderWeth, borrowerRewards, lenderRewards, priceDecimals, priceDescription, priceRound, fjord] = await Promise.all([
    read(vault,vaultAbi,'claimer'),read(vault,vaultAbi,'prizePool'),read(POOL,poolAbi,'prizeToken'),read(POOL,poolAbi,'getLastAwardedDrawId'),read(vault,vaultAbi,'getHooks',[winner]),
    rpc('eth_getBalance',[BORROWER,tag]),rpc('eth_getBalance',[LENDER,tag]),rpc('eth_getTransactionCount',[BORROWER,tag]),rpc('eth_getTransactionCount',[LENDER,tag]),
    read(WETH,wethAbi,'balanceOf',[BORROWER]),read(WETH,wethAbi,'balanceOf',[LENDER]),read(POOL,poolAbi,'rewardBalance',[BORROWER]),read(POOL,poolAbi,'rewardBalance',[LENDER]),
    read(PRICE_FEED,priceAbi,'decimals'),read(PRICE_FEED,priceAbi,'description'),read(PRICE_FEED,priceAbi,'latestRoundData'),read(ORACLE,oracleAbi,'isFjord')
  ]);
  const [claimerPool, isWinner, wasClaimed] = await Promise.all([read(claimer,claimerAbi,'prizePool'),read(POOL,poolAbi,'isWinner',[vault,winner,candidate.tier,candidate.prizeIndex]),read(POOL,poolAbi,'wasClaimed',[vault,winner,drawId,candidate.tier,candidate.prizeIndex])]);
  report.contracts = { vault, claimer, prizePool:POOL, weth:WETH, oracle:ORACLE, prizeToken, vaultPool, claimerPool, drawId, hooks, isWinner, wasClaimed };
  if (vaultPool.toLowerCase() !== POOL || claimerPool.toLowerCase() !== POOL || prizeToken.toLowerCase() !== WETH || !fjord || !isWinner || wasClaimed || hooks.useBeforeClaimPrize || hooks.useAfterClaimPrize) throw new Error('CandidateNotEligibleAtFreshSnapshot');
  report.before = { borrower:{nativeWei:BigInt(borrowerEth),wethWei:borrowerWeth,rewardWei:borrowerRewards,nonce:BigInt(borrowerNonce)}, lender:{nativeWei:BigInt(lenderEth),wethWei:lenderWeth,rewardWei:lenderRewards,nonce:BigInt(lenderNonce)} };
  const [borrowerPendingNonce,lenderPendingNonce] = await Promise.all([rpc('eth_getTransactionCount',[BORROWER,'pending']),rpc('eth_getTransactionCount',[LENDER,'pending'])]);
  report.pendingNonces = { borrower:BigInt(borrowerPendingNonce),lender:BigInt(lenderPendingNonce) };
  report.fingerprints = {};
  for (const [name,address] of [['pool',POOL],['vault',vault],['claimer',claimer],['weth',WETH],['oracle',ORACLE],['priceFeed',PRICE_FEED]]) {
    const code = await rpc('eth_getCode',[address,tag]);
    if (!code || code === '0x') throw new Error('ContractCodeMissing');
    report.fingerprints[name] = { address,runtimeCodeKeccak256:keccak256(code) };
  }
  if (priceDecimals !== 8 || !/ETH\s*\/\s*USD/i.test(priceDescription) || priceRound[1] <= 0n || priceRound[3] <= 0n || BigInt(block.timestamp) - priceRound[3] < 0n || BigInt(block.timestamp) - priceRound[3] > 3600n || priceRound[4] < priceRound[0]) throw new Error('PriceFeedNotFresh');
  const price8 = priceRound[1], bufferedPrice8 = (price8*120n+99n)/100n;
  report.ethUsd = { feed:PRICE_FEED,description:priceDescription,decimals:priceDecimals,roundId:priceRound[0],answer:price8,updatedAt:priceRound[3],ageSeconds:BigInt(block.timestamp)-priceRound[3],capPriceAnswerWith20PercentBuffer:bufferedPrice8 };
  const usdMicros = wei => (wei*bufferedPrice8 + 100_000_000_000_000_000_000n-1n)/100_000_000_000_000_000_000n;
  stage = 'exact_claim_simulation';
  let tip;
  try { tip = BigInt(await rpc('eth_maxPriorityFeePerGas',[])); } catch { tip = 1_000_000n; report.priorityFeeFallbackWei = tip; }
  if (tip < 1_000_000n) tip = 1_000_000n;
  const maxFee = 2n*BigInt(block.baseFeePerGas)+tip;
  const claimArgs = floor => [vault,candidate.tier,[winner],[[candidate.prizeIndex]],BORROWER,floor];
  const claimData = floor => encodeFunctionData({abi:claimerAbi,functionName:'claimPrizes',args:claimArgs(floor)});
  const firstData = claimData(0n);
  const callResult = await rpc('eth_call',[{from:BORROWER,to:claimer,data:firstData},tag]);
  const firstFee = decodeFunctionResult({abi:claimerAbi,functionName:'claimPrizes',data:callResult});
  report.initialExactClaim = { minFeePerClaimWei:0n,decodedNewRewardWei:firstFee,rawReturnData:callResult };
  if (firstFee <= 0n) throw new Error('ExactCallEarnsZero');
  // A READ-ONLY native balance override enables gas estimation for the as-yet unfunded EOA.
  const estimateTx = { from:BORROWER,to:claimer,data:firstData,maxFeePerGas:hex(maxFee),maxPriorityFeePerGas:hex(tip),value:'0x0' };
  const estimatedClaim = BigInt(await rpc('eth_estimateGas',[estimateTx,tag,{[BORROWER]:{balance:hex(1_000_000_000_000_000_000n)}}]));
  const claimGas = (estimatedClaim*130n+99n)/100n;
  if (claimGas > 4_000_000n) throw new Error('ClaimGasLimitExceeded');
  const Bnonce = BigInt(borrowerNonce), Lnonce = BigInt(lenderNonce);
  if (Bnonce+3n>BigInt(Number.MAX_SAFE_INTEGER)||Lnonce>BigInt(Number.MAX_SAFE_INTEGER)) throw new Error('NonceUnsafeInteger');
  const txBase = (name,from,to,nonce,gas,data='0x',value=0n) => ({name,from,to,chainId:8453,nonce,gas,maxFeePerGas:maxFee,maxPriorityFeePerGas:tip,data,value,type:'eip1559'});
  const txs = [
    txBase('fund',LENDER,BORROWER,Lnonce,21_000n),
    txBase('claim',BORROWER,claimer,Bnonce,claimGas,firstData),
    txBase('withdrawReward',BORROWER,POOL,Bnonce+1n,160_000n,encodeFunctionData({abi:poolAbi,functionName:'withdrawRewards',args:[BORROWER,firstFee]})),
    txBase('unwrap',BORROWER,WETH,Bnonce+2n,100_000n,encodeFunctionData({abi:wethAbi,functionName:'withdraw',args:[firstFee]})),
    txBase('repay',BORROWER,LENDER,Bnonce+3n,21_000n)
  ];
  async function priceTx(tx) {
    const serialized = serializeTransaction({type:tx.type,chainId:8453,nonce:Number(tx.nonce),gas:tx.gas,maxFeePerGas:tx.maxFeePerGas,maxPriorityFeePerGas:tx.maxPriorityFeePerGas,to:tx.to,data:tx.data,value:tx.value});
    const unsignedBytes = BigInt((serialized.length-2)/2);
    const [l1,operator] = await Promise.all([read(ORACLE,oracleAbi,'getL1FeeUpperBound',[unsignedBytes]),read(ORACLE,oracleAbi,'getOperatorFee',[tx.gas])]);
    return { ...tx,unsignedSerializedForOracleOnly:serialized,unsignedByteLength:unsignedBytes,l2FeeHardCapWei:tx.gas*maxFee,l1SnapshotUpperQuoteWei:l1,operatorSnapshotUpperQuoteWei:operator,l1ReservedWei:l1*2n,operatorReservedWei:operator*2n,totalGasReservedWei:tx.gas*maxFee+2n*l1+2n*operator };
  }
  stage = 'cycle_pricing';
  let priced = [];
  for (const tx of txs) priced.push(await priceTx(tx));
  let borrowerGas = priced.slice(1).reduce((s,t)=>s+t.totalGasReservedWei,0n);
  let lenderGas = priced[0].totalGasReservedWei;
  const borrowerTarget = 1_000_000_000n, lenderTarget = 1_000_000_000n;
  let loanFee = lenderGas+lenderTarget;
  let requiredReward = borrowerGas+loanFee+workCost+borrowerTarget;
  // Single claim: floor == required reward protects one successful claim, but not ZERO success.
  // Allow final encoded value/floor size changes while keeping the actual floor independently recorded.
  const actualFeeFloor = requiredReward+requiredReward/10n+1n;
  txs[1].data = claimData(actualFeeFloor);
  const floorResult = await rpc('eth_call',[{from:BORROWER,to:claimer,data:txs[1].data},tag]);
  const exactReward = decodeFunctionResult({abi:claimerAbi,functionName:'claimPrizes',data:floorResult});
  if (exactReward <= 0n || exactReward < requiredReward) throw new Error('FullCycleRewardBelowRequiredFloor');
  const estimatedFinal = BigInt(await rpc('eth_estimateGas',[{...estimateTx,data:txs[1].data},tag,{[BORROWER]:{balance:hex(1_000_000_000_000_000_000n)}}]));
  if (estimatedFinal > claimGas) throw new Error('FinalClaimExceedsReservedGas');
  const principal = borrowerGas+borrowerGas/10n+1n;
  txs[0].value = principal;
  txs[2].data = encodeFunctionData({abi:poolAbi,functionName:'withdrawRewards',args:[BORROWER,exactReward]});
  txs[3].data = encodeFunctionData({abi:wethAbi,functionName:'withdraw',args:[exactReward]});
  txs[4].value = principal+loanFee;
  // Nonzero values and floors may increase encoded size: reprice exact final calldata/value.
  priced = [];
  for (const tx of txs) priced.push(await priceTx(tx));
  borrowerGas = priced.slice(1).reduce((s,t)=>s+t.totalGasReservedWei,0n);
  lenderGas = priced[0].totalGasReservedWei;
  requiredReward = borrowerGas+loanFee+workCost+borrowerTarget;
  const allGas = borrowerGas+lenderGas, worstLoss = principal+lenderGas;
  report.transactions = priced;
  report.claimSimulation = { sender:BORROWER,feeRecipient:BORROWER,minFeePerClaimWei:actualFeeFloor,rawReturnData:floorResult,decodedNewRewardWei:exactReward,estimatedClaimGas:estimatedFinal,gasLimitReserved:claimGas,simulationUsesNoBalanceOverride:true,gasEstimationUsesNativeBalanceOverride:true };
  report.terms = { nativePrincipalWei:principal,loanFeeWei:loanFee,debtWei:principal+loanFee,workCostWei:workCost,borrowerGasReservedWei:borrowerGas,lenderGasReservedWei:lenderGas,totalGasReservedWei:allGas,requiredExternalRewardWei:requiredReward,expectedExternalRewardWei:exactReward,borrowerMarginAtReservedGasWei:exactReward-borrowerGas-loanFee-workCost,lenderMarginAtReservedGasWei:loanFee-lenderGas,targetBorrowerMarginWei:borrowerTarget,targetLenderMarginWei:lenderTarget,worstLossExposureWei:worstLoss,grossExposureWei:principal+allGas,principalUsdMicrosAtBufferedPrice:usdMicros(principal),grossExposureUsdMicrosAtBufferedPrice:usdMicros(principal+allGas),worstLossUsdMicrosAtBufferedPrice:usdMicros(worstLoss) };
  report.qualification = {
    exactPositiveClaim:true,oneEligibleClaim:true,noEnabledWinnerHooks:true,canonicalWeth:true,winnerOutsideKnownControlledAddresses:true,
    borrowerStartsAtZero:BigInt(borrowerEth)===0n && borrowerWeth===0n && borrowerRewards===0n,
    principalNativeCap:principal<=50_000_000_000_000n,principalUsdCap:usdMicros(principal)<=500_000n,
    grossExposureUsdCap:usdMicros(principal+allGas)<=1_000_000n,worstLossUsdCap:usdMicros(worstLoss)<=250_000n,
    principalCoversUpdatedBorrowerGas:principal>=borrowerGas,
    externalRewardCoversUpdatedReserves:exactReward>=requiredReward,
    actualSubmittedFloorCoversUpdatedReserves:actualFeeFloor>=requiredReward,
    lenderHasFundingAndGas:BigInt(lenderEth)>=principal+lenderGas,
    lenderPositiveMargin:loanFee>lenderGas,nonceSafeIntegers:true,
    noPendingTransactions:Bnonce===BigInt(borrowerPendingNonce)&&Lnonce===BigInt(lenderPendingNonce),
    includesCurrentL1AndOperatorQuotes:true,downstreamConservativeGasLimitsUsed:true
  };
  stage = 'optional_stateful_cycle_simulation';
  try {
    const calls = txs.map(t=>({from:t.from,to:t.to,nonce:hex(t.nonce),gas:hex(t.gas),maxFeePerGas:hex(t.maxFeePerGas),maxPriorityFeePerGas:hex(t.maxPriorityFeePerGas),value:hex(t.value),data:t.data}));
    const simulated = await rpc('eth_simulateV1',[{blockStateCalls:[{calls}],validation:true,traceTransfers:true},tag]);
    const results = simulated?.[0]?.calls;
    const allSuccessful = Array.isArray(results)&&results.length===5&&results.every(c=>BigInt(c.status)===1n);
    const cycleClaimReward = allSuccessful ? decodeFunctionResult({abi:claimerAbi,functionName:'claimPrizes',data:results[1].returnData}) : 0n;
    report.fullCycleSimulation = { attempted:true,supported:true,rawResult:simulated,allFiveCallsSuccessful:allSuccessful,
      simulatedClaimRewardWei:cycleClaimReward,claimRewardCoversRequiredFloor:cycleClaimReward>=requiredReward,
      downstreamRewardAmountSpecifiedWei:exactReward,
      includesL1AndOperatorFeeDebitsInState:false,
      caveat:'eth_simulateV1 is stateful call execution. Separate oracle reserves account for L1/operator fees; provider state simulation may omit their native debits.' };
  } catch (error) {
    report.fullCycleSimulation = {attempted:true,supported:false,errorKind:error.safeKind||error.name,allFiveCallsSuccessful:false};
  }
  report.qualifiedForExactTransactionReview = Object.values(report.qualification).every(v=>v===true);
  report.exactCycleStatefullyDemonstrated = report.fullCycleSimulation.allFiveCallsSuccessful && report.fullCycleSimulation.claimRewardCoversRequiredFloor===true;
  report.requiresIndependentSignerReviewAndFreshSimulation = true;
  stage = 'complete';
  finish(report.qualifiedForExactTransactionReview?'QUALIFIED_READ_ONLY_PACKET_REQUIRES_SIGNER_REVIEW':'NO_LOAN_CAP_OR_MARGIN_CHECK_FAILED');
} catch (error) { finish('STOPPED_WITHOUT_EXECUTION',error); process.exitCode = 2; }
finally { clearTimeout(deadline); abort.abort(); }
