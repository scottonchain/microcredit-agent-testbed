#!/usr/bin/env node
// READ ONLY. No keys, signatures, approvals, transfers or deployments.
// All HTTP JSON-RPC methods are checked against the explicit read-only allowlist.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const argv = process.argv.slice(2);
if (argv.includes('--help')) {
  console.log(`READ-ONLY TVL-ranked Beefy Base harvest probe. Node >=20.
Install in a dedicated directory: npm install --save-exact viem@2.17.0
Run: BASE_READ_RPC='approved HTTPS endpoint' node read-only-beefy-ranked-probe.mjs --registry beefy-base-vaults.json --tvl beefy-tvl.json --tvl-observed-at ISO_TIMESTAMP --deps /path/to/install-directory > beefy-ranked-probe.json
Optional: --rpc-env NAME (default BASE_READ_RPC); --select-only validates and emits the ranking without RPC.
GET https://api.beefy.finance/tvl separately using approved access; retain its original bytes, acquisition timestamp and SHA256.
TVL schema from official beefy-api source: {"8453":{"vault-id": numericUSDTVL}}. The API caches values; acquisition time is not valuation time.
Limits: sixteen source-listed TVL-ranked vaults, 128 JSON-RPC requests, 180 seconds; no retries.
The eight earlier sampled vaults are excluded. Ranked negatives do not establish market-wide absence.
Lens harvest() is ETH_CALL ONLY. Actual lens transactions are expressly excluded.
This probe does not qualify spending: fresh direct-call validation, deployed source verification,
whole-cycle fees and a concrete transaction approval remain required.
No endpoint URLs or secrets are printed. Retain source files, script/output hashes and package-lock.json.`);
  process.exit(0);
}

const BASE_DIR = dirname(fileURLToPath(import.meta.url));
const MAX_MS = 180_000, MAX_RPC = 128;
const BORROWER = '0x62c4a163026feedb3ea1045d90bba96d0c5d4f0b';
const WETH = '0x4200000000000000000000000000000000000006';
const LENS = '0x71e4df2bdc7ce0b2dc7cdb9eac983b251f8a0b58';
const MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11';
const REGISTRY_SHA256 = '9444a807f47f72844e221854cd8b058b2f0e7995b9978fa2345df0755cdc5a62';
const EXCLUDED_PREVIOUS_VAULTS = new Set([
  '0xfca983ea00d87de9bb7eaf5561cc1ec4050ad1ba',
  '0x15f91999e54452139258079355f057aa66c9f196',
  '0x81336f242caa6cf779d56a775ac1f642e3ac3b84',
  '0x65d3107cf955ca222321c6d016667e037b3d6fe2',
  '0x9f66dc0e9e164f6c1605d43a0cdff8153d77b46f',
  '0x4fcbcec8f9da4026cf9431d43c632632540b0ff7',
  '0xa8c718cdfd58b3a33e7d29cff8aa459a4abd8472',
  '0xee9de934e0273556a3b4585abf6fcc29fe365dd6'
]);
const started = Date.now(), controller = new AbortController();
let emitted = false, stage = 'arguments', blockHex;
const report = {
  schema: 'codex.eth-gas-read-only-beefy-ranked-probe/1', mode: 'READ_ONLY_TVL_RANKED_DISCOVERY',
  startedAt: new Date().toISOString(), chainId: 8453, borrower: BORROWER,
  weth: WETH, lens: LENS, multicall: MULTICALL,
  status: 'RUNNING', rpcRequests: 0,
  limits: { maxCandidates: 16, maxRpcRequests: MAX_RPC, maxRuntimeMs: MAX_MS },
  sources: {
    vaultRegistryRepository: 'beefyfinance/beefy-v2',
    vaultRegistryCommit: 'c30017071065df81a32890eb2a36c3c05c2dc604',
    vaultRegistryPath: 'src/config/vault/base.json',
    vaultRegistryGitBlob: '2554ccd2949e5a138f0950d66e5aca49c18d402a',
    vaultRegistrySha256: '9444a807f47f72844e221854cd8b058b2f0e7995b9978fa2345df0755cdc5a62',
    lensRepository: 'beefyfinance/beefy-cowllector-v2',
    lensCommit: '00955cd894ba2605b0936688e3908e51ccb185ae',
    lensAbiPath: 'apps/cowllector/src/abi/BeefyHarvestLensV2ABI.ts',
    baseLensConfigPath: 'apps/cowllector/src/lib/config.ts',
    tvlApi: 'https://api.beefy.finance/tvl',
    tvlSchemaRepository: 'beefyfinance/beefy-api',
    tvlSchemaCommit: '73aada396ffcb4e7fec1061ac8579c0f8495c5a1',
    tvlSchemaPath: 'src/api/stats/getChainTvl.ts',
    tvlCacheRefreshMs: 900000,
    strategyRepository: 'beefyfinance/beefy-contracts',
    strategyCommit: 'e33f868e2d995c2db9219029c26d31cd8e7d5cb2',
    strategySourceCandidates: [
      'contracts/BIFI/strategies/Velodrome/StrategyVelodromeGaugeV2.sol',
      'contracts/BIFI/strategies/Common/BaseAllToNativeFactoryStrat.sol'
    ]
  },
  candidates: [],
  claims: { loanDisbursed: false, liveTransactionSubmitted: false, earnedRevenue: false, globalOpportunityAbsence: false },
  caveats: [
    'Registry active status is source metadata, not verified live economic activity.',
    'Vault strategy() can change; recorded code hashes are not verified-source matches.',
    'callReward() is an estimate. Lens callReward records actual simulated canonical WETH balance delta.',
    'Lens caller is a contract and fee recipient is the lens; direct mainnet harvest must use the controlled borrower as fee recipient.',
    'Direct EOA eth_call validates success only; its empty returndata is not independent proof of WETH receipt.',
    'No simulated lens or multicall call may be submitted as a mainnet transaction.',
    'Pinned block state can change before execution; competitors can consume rewards.',
    'Gas-price-zero eth_estimateGas is diagnostic and excludes L1 data fee, funding, unwrap and repayment costs.',
    'TVL ranking is a heuristic, not a reward estimate; cached USD valuations can be stale or incomplete.',
    'Sixteen newly ranked vaults do not establish global opportunity presence or absence.'
  ]
};
function finish(status, errorKind) {
  if (emitted) return;
  emitted = true;
  report.status = status;
  report.stage = stage;
  report.finishedAt = new Date().toISOString();
  report.elapsedMs = Date.now() - started;
  if (errorKind) report.errorKind = errorKind;
  console.log(JSON.stringify(report, (_, value) => typeof value === 'bigint' ? value.toString() : value, 2));
}
const deadline = setTimeout(() => {
  controller.abort();
  finish('STOPPED_RUNTIME_CAP', 'RuntimeCap');
  process.exit(2);
}, MAX_MS);
function arg(name, fallback) {
  const index = argv.indexOf(name);
  if (index < 0) return fallback;
  if (!argv[index + 1] || argv[index + 1].startsWith('--')) throw new Error('ArgumentValue');
  return argv[index + 1];
}
const addressPattern = /^0x[0-9a-f]{40}$/;
const allowed = new Set(['eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_getBalance', 'eth_getTransactionCount', 'eth_gasPrice', 'eth_call', 'eth_estimateGas']);
let endpoint, encodeFunctionData, decodeFunctionResult, parseAbi, keccak256;
async function rpc(method, params = []) {
  if (!allowed.has(method)) throw new Error('DeniedRpcMethod');
  if (controller.signal.aborted || Date.now() - started >= MAX_MS) throw new Error('RuntimeCap');
  if (++report.rpcRequests > MAX_RPC) throw new Error('RpcRequestCap');
  const response = await fetch(endpoint, {
    method: 'POST', redirect: 'error',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: report.rpcRequests, method, params }),
    signal: AbortSignal.any([controller.signal, AbortSignal.timeout(8_000)])
  });
  if (!response.ok) throw new Error(`RpcHttp${response.status}`);
  const bytes = await response.text();
  if (bytes.length > 2_000_000) throw new Error('RpcResponseLimit');
  const value = JSON.parse(bytes);
  if (value.error) { const error = new Error('RpcError'); error.rpcCode = value.error.code; throw error; }
  if (!('result' in value)) throw new Error('MissingRpcResult');
  return value.result;
}
async function call(to, abi, functionName, args = [], extra = {}) {
  const data = encodeFunctionData({ abi, functionName, args });
  const raw = await rpc('eth_call', [{ from: BORROWER, to, data, gas: '0x4c4b40', gasPrice: '0x0', value: '0x0', ...extra }, blockHex]);
  return { data, raw, decoded: decodeFunctionResult({ abi, functionName, data: raw }) };
}
function errorRecord(error) { return { kind: error.name || 'Error', message: error.message?.match(/^[A-Za-z0-9]+$/)?.[0] || 'ReadFailed', rpcCode: error.rpcCode }; }

try {
  stage = 'source_files_and_ranking';
  const registryBytes = readFileSync(resolve(arg('--registry', resolve(BASE_DIR, 'beefy-base-vaults.json'))));
  if (registryBytes.length > 10_000_000) throw new Error('RegistryFileLimit');
  if (createHash('sha256').update(registryBytes).digest('hex') !== REGISTRY_SHA256) throw new Error('RegistrySourceHashMismatch');
  const registry = JSON.parse(registryBytes);
  if (!Array.isArray(registry) || registry.length !== 1192) throw new Error('RegistrySchema');
  const tvlFile = arg('--tvl');
  if (!tvlFile) throw new Error('TvlFileRequired');
  const tvlBytes = readFileSync(resolve(tvlFile));
  if (tvlBytes.length > 10_000_000) throw new Error('TvlFileLimit');
  const tvl = JSON.parse(tvlBytes);
  if (!tvl || typeof tvl !== 'object' || Array.isArray(tvl) || !tvl['8453'] || typeof tvl['8453'] !== 'object' || Array.isArray(tvl['8453'])) throw new Error('TvlSchema');
  const observedAt = arg('--tvl-observed-at');
  if (!observedAt || !Number.isFinite(Date.parse(observedAt))) throw new Error('TvlAcquisitionTimeRequired');
  const clmAddresses = new Set(registry.filter(x => x.type === 'cowcentrated' || x.id?.toLowerCase().includes('cow')).map(x => x.earnContractAddress?.toLowerCase()).filter(Boolean));
  const eligible = registry.map((vault, registryIndex) => ({ vault, registryIndex })).filter(({ vault }) => (
    vault.status === 'active' && (vault.type || 'standard') === 'standard' &&
    typeof vault.id === 'string' && !vault.id.toLowerCase().includes('cow') &&
    !clmAddresses.has(vault.tokenAddress?.toLowerCase()) &&
    addressPattern.test(vault.earnContractAddress?.toLowerCase()) &&
    !EXCLUDED_PREVIOUS_VAULTS.has(vault.earnContractAddress.toLowerCase())
  ));
  const ranked = eligible.map(({ vault, registryIndex }) => ({
    id: vault.id, vault: vault.earnContractAddress.toLowerCase(),
    type: 'standard', platform: vault.platformId, registryIndex,
    tvlUsd: tvl['8453'][vault.id]
  })).filter(x => typeof x.tvlUsd === 'number' && Number.isFinite(x.tvlUsd) && x.tvlUsd > 0)
    .sort((a, b) => b.tvlUsd - a.tvlUsd || a.id.localeCompare(b.id));
  const candidates = ranked.slice(0, 16).map((x, index) => ({ ...x, selectedRank: index + 1 }));
  report.ranking = {
    rule: 'Largest positive cached USD TVL among active standard non-cow/non-CLM Base registry entries, excluding the eight previously checked vault addresses; ties by vault id.',
    registrySha256: REGISTRY_SHA256,
    tvlSha256: createHash('sha256').update(tvlBytes).digest('hex'),
    tvlSourceUrl: 'https://api.beefy.finance/tvl',
    tvlAcquiredAtOperatorReported: new Date(observedAt).toISOString(),
    tvlValuationTimestamp: null,
    eligibleRegistryCount: eligible.length, eligibleWithPositiveTvlCount: ranked.length,
    excludedPreviousVaultAddresses: [...EXCLUDED_PREVIOUS_VAULTS],
    excludedClmTokenAddressCount: clmAddresses.size,
    selectedCount: candidates.length, selected: candidates
  };
  if (argv.includes('--select-only')) { finish('COMPLETE_READ_ONLY_RANKING_NO_RPC'); process.exit(0); }
  if (!candidates.length) throw new Error('NoRankedCandidates');
  const envName = arg('--rpc-env', 'BASE_READ_RPC');
  if (!/^[A-Z][A-Z0-9_]*$/.test(envName)) throw new Error('RpcEnvName');
  const rpcUrl = process.env[envName];
  if (!rpcUrl || new URL(rpcUrl).protocol !== 'https:') throw new Error('ApprovedHttpsRpcRequired');
  endpoint = new URL(rpcUrl).href;

  stage = 'dependencies';
  const depDir = resolve(arg('--deps', BASE_DIR));
  const require = createRequire(resolve(depDir, 'package.json'));
  const manifestPath = require.resolve('viem/package.json');
  const manifest = JSON.parse(readFileSync(manifestPath));
  if (manifest.version !== '2.17.0') throw new Error('ViemVersion');
  ({ encodeFunctionData, decodeFunctionResult, parseAbi, keccak256 } = await import(pathToFileURL(require.resolve('viem')).href));
  report.library = { name: 'viem', version: manifest.version };
  const vaultAbi = parseAbi(['function strategy() view returns(address)']);
  const strategyAbi = parseAbi([
    'function paused() view returns(bool)', 'function native() view returns(address)',
    'function callReward() view returns(uint256)', 'function lastHarvest() view returns(uint256)',
    'function harvest(address callFeeRecipient)'
  ]);
  // Exact tuple copied from the immutable official V2 ABI referenced above.
  const lensAbi = parseAbi(['function harvest(address _strategy,address _rewardToken) returns((uint256 callReward,uint256 lastHarvest,uint256 gasUsed,uint256 blockNumber,int8 isCalmBeforeHarvest,bool paused,bool success,bytes harvestResult) res)']);
  const multiAbi = parseAbi(['function tryAggregate(bool requireSuccess,(address target,bytes callData)[] calls) payable returns((bool success,bytes returnData)[] returnData)']);
  const tokenAbi = parseAbi(['function balanceOf(address) view returns(uint256)']);
  stage = 'chain_snapshot';
  if (BigInt(await rpc('eth_chainId')) !== 8453n) throw new Error('WrongChain');
  const block = await rpc('eth_getBlockByNumber', ['latest', false]);
  if (!block?.number || !block.hash) throw new Error('UnnumberedBlock');
  blockHex = block.number;
  report.block = { number: BigInt(block.number), hash: block.hash, timestamp: BigInt(block.timestamp), fixedRpcCallTag: blockHex };
  const lensCode = await rpc('eth_getCode', [LENS, blockHex]);
  const multiCode = await rpc('eth_getCode', [MULTICALL, blockHex]);
  if (lensCode === '0x' || multiCode === '0x') throw new Error('MissingReadHelperCode');
  report.helperCodeHashes = { lens: keccak256(lensCode), multicall: keccak256(multiCode) };
  report.gasPriceWei = BigInt(await rpc('eth_gasPrice'));
  report.borrowerBefore = {
    nativeWei: BigInt(await rpc('eth_getBalance', [BORROWER, blockHex])),
    nonce: BigInt(await rpc('eth_getTransactionCount', [BORROWER, blockHex])),
    wethWei: (await call(WETH, tokenAbi, 'balanceOf', [BORROWER])).decoded
  };

  for (const candidate of candidates) {
    stage = `vault_${candidate.id}`;
    const row = { ...candidate, vault: candidate.vault.toLowerCase(), status: 'CHECKING' };
    report.candidates.push(row);
    try {
      row.strategyRead = await call(row.vault, vaultAbi, 'strategy');
      row.strategy = row.strategyRead.decoded.toLowerCase();
      if (!addressPattern.test(row.strategy) || /^0x0{40}$/.test(row.strategy)) throw new Error('InvalidStrategy');
      const code = await rpc('eth_getCode', [row.strategy, blockHex]);
      row.strategyCodeBytes = (code.length - 2) / 2;
      row.strategyCodeKeccak256 = keccak256(code);
      if (code === '0x') throw new Error('MissingStrategyCode');
      const names = ['paused', 'native', 'callReward', 'lastHarvest'];
      const meta = await call(MULTICALL, multiAbi, 'tryAggregate', [false, names.map(functionName => ({ target: row.strategy, callData: encodeFunctionData({ abi: strategyAbi, functionName }) }))]);
      row.metadataRaw = meta.raw;
      row.metadata = {};
      for (let i = 0; i < names.length; i++) {
        const value = meta.decoded[i];
        row.metadata[names[i]] = value.success ? { success: true, raw: value.returnData, decoded: decodeFunctionResult({ abi: strategyAbi, functionName: names[i], data: value.returnData }) } : { success: false, raw: value.returnData };
      }
      if (row.metadata.paused.decoded !== false || row.metadata.native.decoded?.toLowerCase() !== WETH) { row.status = 'SKIP_PAUSED_OR_WRONG_REWARD_TOKEN'; continue; }
      row.lensSimulation = await call(LENS, lensAbi, 'harvest', [row.strategy, WETH]);
      if (row.lensSimulation.decoded.blockNumber !== BigInt(blockHex)) throw new Error('LensBlockMismatch');
      row.actualSimulatedWethDeltaWei = row.lensSimulation.decoded.callReward;
      if (!row.lensSimulation.decoded.success || row.actualSimulatedWethDeltaWei <= 0n) { row.status = 'NO_POSITIVE_SIMULATED_REWARD'; continue; }
      const directData = encodeFunctionData({ abi: strategyAbi, functionName: 'harvest', args: [BORROWER] });
      row.directEOACall = { to: row.strategy, from: BORROWER, value: '0', data: directData };
      row.directEOACall.rawReturn = await rpc('eth_call', [{ from: BORROWER, to: row.strategy, data: directData, gas: '0x4c4b40', gasPrice: '0x0', value: '0x0' }, blockHex]);
      try {
        row.directEOAGasEstimate = BigInt(await rpc('eth_estimateGas', [{ from: BORROWER, to: row.strategy, data: directData, gas: '0x4c4b40', gasPrice: '0x0', value: '0x0' }, blockHex]));
      } catch (error) { row.gasEstimateError = errorRecord(error); }
      row.status = 'POSITIVE_SIMULATION_REQUIRES_FULL_CYCLE_QUALIFICATION';
    } catch (error) { row.status = 'READ_CHECK_FAILED'; row.error = errorRecord(error); }
    if (report.rpcRequests >= MAX_RPC) break;
  }
  finish('COMPLETE_BOUNDED_READ_ONLY_SAMPLE');
} catch (error) {
  finish('STOPPED_READ_ONLY_CHECK_FAILED', errorRecord(error).message);
  process.exitCode = 2;
} finally { clearTimeout(deadline); controller.abort(); }
