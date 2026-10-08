// READ ONLY Morpho Blue Base Liquidate log scan. <=40 RPC, no retries, no signing.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { writeFileSync } from 'node:fs';
const require = createRequire('/root/work/ptv5_probe_r6/package.json');
const { keccak256, toHex } = await import(pathToFileURL(require.resolve('viem')).href);
const URL_ = 'https://base-rpc.publicnode.com';
const BLUE = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb';
const SIG = 'Liquidate(bytes32,address,address,uint256,uint256,uint256,uint256,uint256)';
const topic0 = keccak256(toHex(SIG));
let n = 0; const t0 = Date.now(); const log = [];
async function rpc(method, params) {
  if (++n > 40) throw new Error('budget');
  if (Date.now() - t0 > 300000) throw new Error('time');
  let r;
  try {
    const res = await fetch(URL_, { method: 'POST', headers: { 'Content-Type': 'application/json', 'User-Agent': 'hermes-agent-909' }, body: JSON.stringify({ jsonrpc: '2.0', id: n, method, params }), signal: AbortSignal.timeout(20000) });
    r = await res.json();
  } catch (e) { r = { error: 'transport: ' + String(e).slice(0, 120) }; }
  log.push({ method, params, resp: r });
  return r;
}
const out = { started: new Date().toISOString(), rpc: 'base-rpc.publicnode.com', blue: BLUE, event: SIG, topic0 };
out.chainId = (await rpc('eth_chainId', [])).result;
const blk = (await rpc('eth_getBlockByNumber', ['latest', false])).result;
const head = parseInt(blk.number, 16);
out.head = { number: head, hash: blk.hash, timestamp: parseInt(blk.timestamp, 16) };
const hx = (x) => '0x' + x.toString(16);
const ws = [1000, 10000];
out.windows = [];
let logs = [];
for (const w of ws) {
  const r = await rpc('eth_getLogs', [{ address: BLUE, topics: [topic0], fromBlock: hx(head - w), toBlock: hx(head) }]);
  const k = Array.isArray(r.result) ? r.result.length : null;
  out.windows.push({ blocks: w, count: k, error: r.error || null });
  if (k && k > 0) { logs = r.result; break; }
}
out.logs = logs.slice(-10).map((l) => {
  const d = l.data.slice(2); const word = (i) => BigInt('0x' + d.slice(64 * i, 64 * (i + 1)));
  return { block: parseInt(l.blockNumber, 16), tx: l.transactionHash, marketId: l.topics[1], caller: '0x' + l.topics[2].slice(26), borrower: '0x' + l.topics[3].slice(26), repaidAssets: word(0).toString(), repaidShares: word(1).toString(), seizedAssets: word(2).toString(), badDebtAssets: word(3).toString(), badDebtShares: word(4).toString() };
});
out.totalLogsInWindow = logs.length;
out.rpcCount = n;
out.finished = new Date().toISOString();
writeFileSync('/root/work/run_r15/morpho_logs.json', JSON.stringify(out, null, 2));
writeFileSync('/root/work/run_r15/morpho_raw.json', JSON.stringify(log));
console.log(JSON.stringify(out, null, 1));
