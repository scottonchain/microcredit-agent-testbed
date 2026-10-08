// READ ONLY: eth_call + eth_estimateGas of Claimer.claimPrizes at a fixed block, from the public lender address as msg.sender. No signing.
import { createPublicClient, http, parseAbi, keccak256 } from 'viem';
import { base } from 'viem/chains';
import { readFileSync, writeFileSync } from 'node:fs';
const probe = JSON.parse(readFileSync('probe.json'));
const client = createPublicClient({ chain: base, transport: http(process.env.BASE_READ_RPC, { retryCount: 0, timeout: 12000 }) });
const claimer = probe.contracts.fingerprints.claimer.address;
const vault = probe.candidates[2].vault;
const cands = probe.candidates.filter(c => c.eligibleForFurtherSimulation && c.tier === 6);
const winner = cands[0].winner;
const idx = cands.filter(c => c.winner === winner).map(c => c.prizeIndex);
const abi = parseAbi(['function claimPrizes(address _vault,uint8 _tier,address[] _winners,uint32[][] _prizeIndices,address _feeRecipient,uint256 _minFeePerClaim) returns (uint256)']);
const from = '0x62C4A163026feedB3eA1045d90bBa96d0C5d4F0B'; // public borrower address from Codex r4; msg.sender/feeRecipient only, nothing sent
const out = { schema: 'hermes.ptv5-claim-sim/1', startedAt: new Date().toISOString(), calls: 0 };
const blk = await client.getBlock({ blockTag: 'latest' }); out.calls++;
out.block = { number: blk.number.toString(), hash: blk.hash, baseFeePerGas: blk.baseFeePerGas?.toString() };
out.gasPrice = (await client.getGasPrice()).toString(); out.calls++;
for (const n of [1, idx.length]) {
  const args = [vault, 6, [winner], [idx.slice(0, n)], from, 1n];
  const rec = { prizeCount: n, winner, tier: 6, prizeIndices: idx.slice(0, n), feeRecipient: from, minFeePerClaim: '1' };
  try { const r = await client.simulateContract({ address: claimer, abi, functionName: 'claimPrizes', args, account: from, blockNumber: blk.number }); out.calls++; rec.simulate = { ok: true, returnedTotalFeesWei: r.result.toString() }; }
  catch (e) { out.calls++; rec.simulate = { ok: false, error: (e.shortMessage || e.message || '').slice(0, 300) }; }
  try { const g = await client.estimateContractGas({ address: claimer, abi, functionName: 'claimPrizes', args, account: from, blockNumber: blk.number }); out.calls++; rec.estimateGas = g.toString(); rec.gasCostWeiAtGasPrice = (g * BigInt(out.gasPrice)).toString(); }
  catch (e) { out.calls++; rec.estimateGas = 'failed: ' + (e.shortMessage || e.message || '').slice(0, 200); }
  (out.sims ||= []).push(rec);
}
out.finishedAt = new Date().toISOString();
writeFileSync('sim-claim.json', JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
