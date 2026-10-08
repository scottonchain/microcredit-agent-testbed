// READ ONLY. eth_call / estimateGas only; no signer, no spend. Hermes r12 ranked Beefy harvest-lens scan.
import { createPublicClient, http, parseAbi } from 'viem';
import { base } from 'viem/chains';
import { readFileSync, writeFileSync } from 'node:fs';
const BORROWER = '0x62C4A163026feedB3eA1045d90bBa96d0C5d4F0B';
const WETH = '0x4200000000000000000000000000000000000006';
const LENS = '0x71e4DF2Bdc7ce0b2dc7CDB9EaC983B251F8A0B58';
const sel = JSON.parse(readFileSync('/root/work/r12/selected.json', 'utf8')).candidates;
if (sel.length > 16) throw new Error('too many');
const abi = parseAbi([
  'function strategy() view returns (address)',
  'function native() view returns (address)',
  'function vault() view returns (address)',
  'function paused() view returns (bool)',
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
const client = createPublicClient({ chain: base, transport: http(rpc, { retryCount: 0, timeout: 10000 }) });
const out = { schema: 'hermes.beefy-ranked-r12/1', startedAt: new Date().toISOString(), readOnly: true, ops: 0, vaults: [] };
const bump = () => { if (++out.ops > 128) throw new Error('OpBudget'); };
const J = v => JSON.stringify(v, (_, x) => typeof x === 'bigint' ? x.toString() : x, 2);
async function t(fn) { bump(); try { return { ok: true, v: await fn() }; } catch (e) { return { ok: false, err: (e.shortMessage || e.name || 'err').slice(0, 160) }; } }
bump(); out.chainId = await client.getChainId();
bump(); const blk = await client.getBlock({ blockTag: 'latest' });
const blockNumber = blk.number;
out.block = { number: blk.number.toString(), hash: blk.hash, timestamp: blk.timestamp.toString() };
bump(); out.gasPriceWei = (await client.getGasPrice()).toString();
for (const c of sel) {
  const r = { id: c.id, vault: c.vault, tvlUsd: c.tvl };
  const s = await t(() => client.readContract({ address: c.vault, abi, functionName: 'strategy', blockNumber }));
  r.strategy = s;
  if (s.ok) {
    const st = s.v;
    const rd = fn => t(() => client.readContract({ address: st, abi, functionName: fn, blockNumber }));
    r.native = await rd('native'); r.stratVault = await rd('vault'); r.paused = await rd('paused');
    const lens = await t(() => client.simulateContract({ address: LENS, abi: lensAbi, functionName: 'harvest', args: [st, WETH], account: BORROWER, blockNumber }));
    r.lens = lens.ok ? { ok: true, res: lens.v.result } : lens;
    const d = await t(() => client.simulateContract({ address: st, abi, functionName: 'harvest', args: [BORROWER], account: BORROWER, blockNumber }));
    r.directHarvestSim = d.ok ? { ok: true } : d;
    if (r.lens.ok && r.lens.res.success && BigInt(r.lens.res.callReward) > 0n && d.ok) {
      // estimateGas with proper calldata
      const { encodeFunctionData } = await import('viem');
      const data = encodeFunctionData({ abi, functionName: 'harvest', args: [BORROWER] });
      const g2 = await t(() => client.estimateGas({ account: BORROWER, to: st, data, blockNumber }));
      r.estimateGas = g2.ok ? g2.v.toString() : g2;
      if (g2.ok) {
        r.l2CostWei = (BigInt(g2.v) * BigInt(out.gasPriceWei)).toString();
        r.rewardOverL2Cost = Number(BigInt(r.lens.res.callReward)) / Number(r.l2CostWei);
      }
    }
  }
  out.vaults.push(r);
}
out.finishedAt = new Date().toISOString();
writeFileSync('/root/work/r12/beefy-ranked-r12.json', J(out));
console.log(J(out.vaults.map(v => ({ id: v.id, tvl: Math.round(v.tvlUsd), strat: v.strategy.ok, lens: v.lens && v.lens.ok ? { ok: v.lens.res.success, reward: v.lens.res.callReward, lh: v.lens.res.lastHarvest } : (v.lens || null), direct: v.directHarvestSim && v.directHarvestSim.ok, gas: v.estimateGas, ratio: v.rewardOverL2Cost }))));
console.log('ops', out.ops, 'block', out.block.number, 'gasPrice', out.gasPriceWei);
