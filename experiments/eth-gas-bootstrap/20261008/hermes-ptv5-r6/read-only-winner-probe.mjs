#!/usr/bin/env node
// READ ONLY. No accounts, keys, signing, approvals, transfers or deployments.
// Exact official API: js-winner-calc 1.3.1, source commit
// 442688d182bc7dba100c729530d3f3db5fd336d1, src/index.ts.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const argv = process.argv.slice(2);
if (argv.includes('--help')) {
  console.log(`Read-only finite Base winner probe. Node >=20.
Install in a dedicated directory: npm install --save-exact @generationsoftware/js-winner-calc@1.3.1 viem@2.17.0
Run: BASE_READ_RPC='approved HTTPS endpoint' node read-only-winner-probe.mjs --seed historical-draw735-vault-seed.json --limit 128 > probe.json
Optional: --rpc-env NAME (default BASE_READ_RPC), --tiers 4,5,6 (default last 3 active tiers).
The endpoint is supplied by the operator; this script does not grant network access.
Limits: 128 sampled addresses, 12 checked candidates, 80 HTTP requests / 160 RPC operations / 90 seconds.
Historical seed supplies addresses only. Zero candidates is not global absence or a profitability result.
No secrets or endpoint URLs are printed. Keep package-lock.json and hash this script, seed and output.`);
  process.exit(0);
}
function arg(name, fallback) {
  const i = argv.indexOf(name);
  if (i === -1) return fallback;
  if (!argv[i + 1] || argv[i + 1].startsWith('--')) throw new Error('ArgumentValue');
  return argv[i + 1];
}

const POOL = '0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb';
const WETH = '0x4200000000000000000000000000000000000006';
const MAX_HTTP = 80, MAX_RPC = 160, MAX_CANDIDATES = 12, MAX_MS = 90_000;
const started = Date.now();
const controller = new AbortController();
const report = {
  schema: 'codex.eth-gas-read-only-winner-probe/1', startedAt: new Date().toISOString(),
  mode: 'READ_ONLY_SAMPLED_DISCOVERY', chainId: 8453, prizePool: POOL,
  status: 'RUNNING', stage: 'arguments',
  limits: { maxAddresses: 128, maxCandidatesChecked: MAX_CANDIDATES, maxHttpRequests: MAX_HTTP, maxRpcOperations: MAX_RPC, maxRuntimeMs: MAX_MS },
  counters: { httpRequests: 0, rpcOperations: 0 }, candidates: [],
  claims: { liveExecution: false, earnedRevenue: false, loanDisbursed: false, globalOpportunityAbsence: false },
  caveats: [
    'Historical addresses are an incomplete sample, not current winner evidence.',
    'Calculator results are checked at the recorded block; all conditions can change afterward.',
    'A candidate is not a profitable operation; exact fresh call simulation and whole-cycle gas pricing remain required.',
    'minFeePerClaim does not protect against zero successful claims or race gas loss.',
    'This script forces all eth_call and eth_getCode reads to one block, including official helper calls missing explicit blockNumber.'
  ]
};
let printed = false, fixedBlockHex, stage = 'arguments';
function finish(status, error) {
  if (printed) return;
  printed = true;
  report.status = status;
  report.stage = stage;
  report.finishedAt = new Date().toISOString();
  report.elapsedMs = Date.now() - started;
  if (error) report.error = { kind: error.name || 'Error', message: 'Read-only probe did not complete. No signing or spending occurred.' };
  console.log(JSON.stringify(report, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2));
}
const deadline = setTimeout(() => {
  controller.abort();
  finish('STOPPED_RUNTIME_CAP', { name: 'RuntimeCap' });
  process.exit(2);
}, MAX_MS);

try {
  const rpcEnv = arg('--rpc-env', 'BASE_READ_RPC');
  if (!/^[A-Z][A-Z0-9_]*$/.test(rpcEnv)) throw new Error('RpcEnvName');
  const rpcUrl = process.env[rpcEnv];
  if (!rpcUrl || new URL(rpcUrl).protocol !== 'https:') throw new Error('ApprovedHttpsRpcRequired');
  const endpoint = new URL(rpcUrl).href;
  const limit = Number(arg('--limit', '128'));
  if (!Number.isInteger(limit) || limit < 1 || limit > 128) throw new Error('SampleLimit');
  const defaultSeed = resolve(dirname(fileURLToPath(import.meta.url)), 'historical-draw735-vault-seed.json');
  const seedPath = resolve(arg('--seed', defaultSeed));
  const seedBytes = readFileSync(seedPath);
  if (seedBytes.length > 2_000_000) throw new Error('SeedTooLarge');
  const seed = JSON.parse(seedBytes);
  if (Number(seed.chainId) !== 8453 || seed.prizePoolAddress.toLowerCase() !== POOL || !/^0x[0-9a-fA-F]{40}$/.test(seed.vaultAddress) || !Array.isArray(seed.userAddresses)) throw new Error('SeedSchema');
  const userAddresses = [...new Set(seed.userAddresses.filter(a => typeof a === 'string' && /^0x[0-9a-fA-F]{40}$/.test(a)).map(a => a.toLowerCase()))].slice(0, limit);
  if (!userAddresses.length) throw new Error('EmptySample');
  const vault = seed.vaultAddress.toLowerCase();
  report.seed = { sha256: createHash('sha256').update(seedBytes).digest('hex'), historical: true, vault, availableAddressCount: seed.userAddresses.length, sampledAddressCount: userAddresses.length, sample: 'first unique <=128 supplied addresses; not representative' };

  // Refuse all non-RPC destinations and all mutation/signing methods, even if a
  // dependency requests them. Counters include retry attempts and batched RPCs.
  const nativeFetch = globalThis.fetch.bind(globalThis);
  const allowed = new Set(['eth_chainId', 'eth_blockNumber', 'eth_getBlockByNumber', 'eth_call', 'eth_getCode']);
  globalThis.fetch = async (input, init = {}) => {
    if (controller.signal.aborted || Date.now() - started >= MAX_MS) throw new Error('RuntimeCap');
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (new URL(url).href !== endpoint || (init.method || 'GET').toUpperCase() !== 'POST') throw new Error('DeniedNetworkDestination');
    if (++report.counters.httpRequests > MAX_HTTP) throw new Error('HttpRequestCap');
    if (typeof init.body !== 'string' || init.body.length > 250_000) throw new Error('RpcBodyLimit');
    const body = JSON.parse(init.body);
    const calls = Array.isArray(body) ? body : [body];
    if (!calls.length) throw new Error('EmptyRpcBatch');
    for (const call of calls) {
      if (!allowed.has(call.method)) throw new Error('DeniedRpcMethod');
      if (++report.counters.rpcOperations > MAX_RPC) throw new Error('RpcOperationCap');
      if (fixedBlockHex && ['eth_call', 'eth_getCode'].includes(call.method)) {
        if (!Array.isArray(call.params) || !call.params.length) throw new Error('RpcParams');
        call.params[1] = fixedBlockHex;
      }
    }
    const response = await nativeFetch(input, { ...init, body: JSON.stringify(body), signal: AbortSignal.any([controller.signal, AbortSignal.timeout(12_000)]), redirect: 'error' });
    const content = await response.text();
    if (content.length > 2_000_000) throw new Error('RpcResponseLimit');
    return new Response(content, { status: response.status, statusText: response.statusText, headers: response.headers });
  };

  stage = 'dependencies';
  const require = createRequire(import.meta.url);
  const calcEntry = require.resolve('@generationsoftware/js-winner-calc');
  const manifest = JSON.parse(readFileSync(resolve(dirname(calcEntry), '..', 'package.json')));
  if (manifest.version !== '1.3.1') throw new Error('CalculatorVersion');
  const { computeWinners } = await import(pathToFileURL(calcEntry).href);
  const { createPublicClient, http, parseAbi, keccak256 } = await import('viem');
  const { base } = await import('viem/chains');
  report.library = { name: manifest.name, version: manifest.version, officialApiSourceCommit: '442688d182bc7dba100c729530d3f3db5fd336d1', executedEntrySha256: createHash('sha256').update(readFileSync(calcEntry)).digest('hex') };
  const client = createPublicClient({ chain: base, transport: http(rpcUrl, { retryCount: 0, timeout: 12_000 }) });
  stage = 'chain_snapshot';
  if (await client.getChainId() !== 8453) throw new Error('WrongChain');
  const block = await client.getBlock({ blockTag: 'latest' });
  if (!block.hash || block.number === null) throw new Error('UnnumberedBlock');
  fixedBlockHex = '0x' + block.number.toString(16);
  report.block = { number: block.number, hash: block.hash, timestamp: block.timestamp, fixedRpcCallTag: fixedBlockHex };
  const poolAbi = parseAbi([
    'function getLastAwardedDrawId() view returns (uint24)',
    'function numberOfTiers() view returns (uint8)',
    'function prizeToken() view returns (address)',
    'function isWinner(address,address,uint8,uint32) view returns (bool)',
    'function wasClaimed(address,address,uint24,uint8,uint32) view returns (bool)'
  ]);
  const vaultAbi = parseAbi([
    'function claimer() view returns (address)', 'function prizePool() view returns (address)',
    'function getHooks(address) view returns ((bool useBeforeClaimPrize,bool useAfterClaimPrize,address implementation))'
  ]);
  const claimerAbi = parseAbi([
    'function prizePool() view returns (address)',
    'function computeFeePerClaim(uint8,uint256) view returns (uint256)'
  ]);
  const read = (address, abi, functionName, args = []) => client.readContract({ address, abi, functionName, args, blockNumber: block.number });
  stage = 'contract_consistency';
  const [drawId, numTiers, prizeToken, claimer, vaultPool] = await Promise.all([
    read(POOL, poolAbi, 'getLastAwardedDrawId'), read(POOL, poolAbi, 'numberOfTiers'),
    read(POOL, poolAbi, 'prizeToken'), read(vault, vaultAbi, 'claimer'), read(vault, vaultAbi, 'prizePool')
  ]);
  if (vaultPool.toLowerCase() !== POOL || (await read(claimer, claimerAbi, 'prizePool')).toLowerCase() !== POOL) throw new Error('PoolMismatch');
  const fingerprints = {};
  for (const [name, address] of [['pool',POOL],['vault',vault],['claimer',claimer],['prizeToken',prizeToken]]) {
    const code = await client.getBytecode({ address, blockNumber: block.number });
    if (!code || code === '0x') throw new Error('ContractCodeMissing');
    fingerprints[name] = { address, runtimeCodeKeccak256: keccak256(code) };
  }
  report.contracts = { drawId, numTiers, prizeToken, claimer, canonicalBaseWethAddressMatch: prizeToken.toLowerCase() === WETH, fingerprints };
  if (prizeToken.toLowerCase() !== WETH) throw new Error('NonWethMinimalPilot');
  const tierArg = arg('--tiers', null);
  const tiers = tierArg === null ? [numTiers - 3, numTiers - 2, numTiers - 1].filter(t => t >= 0) : tierArg.split(',').map(Number);
  if (!tiers.length || tiers.length > 3 || new Set(tiers).size !== tiers.length || tiers.some(t => !Number.isInteger(t) || t < 0 || t >= numTiers)) throw new Error('TierSelection');
  report.tiers = tiers;
  stage = 'sampled_winner_calculation';
  const winners = await computeWinners({ chainId: 8453, rpcUrl, prizePoolAddress: POOL, vaultAddress: vault, userAddresses, prizeTiers: tiers, blockNumber: block.number, multicallBatchSize: 2048, accountTwabBatchSize: 128, debug: false });
  // Preserve raw positive calculator output. It is not a payable/live claim.
  report.calculatedWinners = winners;
  const selected = [];
  for (const winner of winners) for (const [tier, indices] of Object.entries(winner.prizes)) for (const index of indices) {
    if (selected.length < MAX_CANDIDATES) selected.push({ winner: winner.user, tier: Number(tier), prizeIndex: index });
  }
  stage = 'bounded_candidate_checks';
  const hooks = new Map(), fees = new Map();
  for (const candidate of selected) {
    if (!hooks.has(candidate.winner)) hooks.set(candidate.winner, await read(vault, vaultAbi, 'getHooks', [candidate.winner]));
    if (!fees.has(candidate.tier)) fees.set(candidate.tier, await read(claimer, claimerAbi, 'computeFeePerClaim', [candidate.tier, 1n]));
    const [isWinner, wasClaimed] = await Promise.all([
      read(POOL, poolAbi, 'isWinner', [vault, candidate.winner, candidate.tier, candidate.prizeIndex]),
      read(POOL, poolAbi, 'wasClaimed', [vault, candidate.winner, drawId, candidate.tier, candidate.prizeIndex])
    ]);
    const hook = hooks.get(candidate.winner);
    const noEnabledHooks = !hook.useBeforeClaimPrize && !hook.useAfterClaimPrize;
    report.candidates.push({ ...candidate, vault, drawId, isWinner, wasClaimed,
      hooks: hook, noEnabledHooks, singleClaimQuotedFeeWethWei: fees.get(candidate.tier),
      unclaimedAtSnapshot: isWinner && !wasClaimed,
      eligibleForFurtherSimulation: isWinner && !wasClaimed && noEnabledHooks && fees.get(candidate.tier) > 0n,
      exactClaimSimulated: false, completeCyclePriced: false, spendAuthorizedByProbe: false });
  }
  report.eligibleForFurtherSimulationCount = report.candidates.filter(c => c.eligibleForFurtherSimulation).length;
  stage = 'complete';
  finish('COMPLETE_READ_ONLY_SAMPLE');
} catch (error) {
  finish('STOPPED_WITHOUT_EXECUTION', error);
  process.exitCode = 2;
} finally {
  clearTimeout(deadline);
  controller.abort();
}
