// READ ONLY. eth_call only; no signer, no spend. Hermes r10 Beefy harvest-lens probe.
import { createPublicClient, http, parseAbi, decodeErrorResult } from 'viem';
import { base } from 'viem/chains';
import { writeFileSync } from 'node:fs';
const BORROWER = '0x62C4A163026feedB3eA1045d90bBa96d0C5d4F0B';
const WETH = '0x4200000000000000000000000000000000000006';
const LENS = '0x71e4DF2Bdc7ce0b2dc7CDB9EaC983B251F8A0B58';
const VAULTS = [
  ['aerodrome-usdc-alusdb', '0xfCa983Ea00D87DE9BB7eAF5561cC1ec4050Ad1ba'],
  ['aerodrome-bd-usdc', '0x15f91999e54452139258079355f057aa66c9f196'],
  ['aerodrome-virtual-aero', '0x81336F242caa6Cf779D56a775AC1f642e3AC3b84'],
  ['aerodrome-msusd-frxusd', '0x65D3107cf955cA222321C6d016667E037b3d6FE2'],
  ['aerodrome-weth-edel', '0x9f66dc0E9E164F6c1605d43a0cDff8153D77B46F'],
  ['aerodrome-lcap-eusd', '0x4fcBCEC8f9da4026CF9431d43C632632540B0FF7'],
  ['aerodrome-usdc-send', '0xA8c718CdFD58B3A33e7d29Cff8aa459A4aBd8472'],
  ['aerodrome-synd-weth', '0xeE9DE934e0273556A3b4585abf6fCc29fE365dd6'],
];
const abi = parseAbi([
  'function strategy() view returns (address)',
  'function native() view returns (address)',
  'function vault() view returns (address)',
  'function paused() view returns (bool)',
  'function lastHarvest() view returns (uint256)',
  'function callFee() view returns (uint256)',
  'function harvest(address callFeeRecipient)',
]);
const lensAbi = [{ type: 'function', name: 'harvest', stateMutability: 'nonpayable',
  inputs: [{ name: '_strategy', type: 'address' }, { name: '_rewardToken', type: 'address' }],
  outputs: [{ name: 'res', type: 'tuple', components: [
    { name: 'callReward', type: 'uint256' }, { name: 'lastHarvest', type: 'uint256' }, { name: 'gasUsed', type: 'uint256' },
    { name: 'blockNumber', type: 'uint256' }, { name: 'isCalmBeforeHarvest', type: 'int8' }, { name: 'paused', type: 'bool' },
    { name: 'success', type: 'bool' }, { name: 'harvestResult', type: 'bytes' }] }] }];
const rpc = process.env.BASE_READ_RPC;
if (!rpc || new URL(rpc).protocol !== 'https:') throw new Error('rpc');
const client = createPublicClient({ chain: base, transport: http(rpc, { retryCount: 0, timeout: 8000 }) });
const out = { schema: 'hermes.beefy-lens-probe/1', startedAt: new Date().toISOString(), readOnly: true, ops: 0, vaults: [] };
const bump = () => { if (++out.ops > 80) throw new Error('OpBudget'); };
const J = v => JSON.stringify(v, (_, x) => typeof x === 'bigint' ? x.toString() : x, 2);
async function t(fn) { bump(); try { return { ok: true, v: await fn() }; } catch (e) { return { ok: false, err: (e.shortMessage || e.name || 'err').slice(0, 160), data: (e.data && e.data.errorName) || undefined }; } }
bump(); out.chainId = await client.getChainId();
bump(); const blk = await client.getBlock({ blockTag: 'latest' });
const blockNumber = blk.number;
out.block = { number: blk.number.toString(), hash: blk.hash, timestamp: blk.timestamp.toString() };
bump(); out.lensCodeBytes = ((await client.getCode({ address: LENS, blockNumber })) || '0x').length / 2 - 1;
for (const [id, vault] of VAULTS) {
  const r = { id, vault };
  const s = await t(() => client.readContract({ address: vault, abi, functionName: 'strategy', blockNumber }));
  r.strategy = s;
  if (s.ok) {
    const st = s.v;
    const rd = fn => t(() => client.readContract({ address: st, abi, functionName: fn, blockNumber }));
    r.native = await rd('native'); r.stratVault = await rd('vault'); r.paused = await rd('paused'); r.lastHarvest = await rd('lastHarvest'); r.callFee = await rd('callFee');
    const lens = await t(() => client.simulateContract({ address: LENS, abi: lensAbi, functionName: 'harvest', args: [st, WETH], account: BORROWER, blockNumber }));
    r.lens = lens.ok ? { ok: true, res: lens.v.result } : lens;
    // direct strategy.harvest(borrower) simulation as borrower
    const d = await t(() => client.simulateContract({ address: st, abi, functionName: 'harvest', args: [BORROWER], account: BORROWER, blockNumber }));
    r.directHarvestSim = d.ok ? { ok: true } : d;
  }
  out.vaults.push(r);
}
out.finishedAt = new Date().toISOString();
writeFileSync('beefy-lens-probe.json', J(out));
console.log(J(out));
