// READ ONLY follow-up on Morpho Liquidate logs already fetched: caller code, tx receipts, market params. Budget: <=30 RPC (total with morpho_logs.mjs <=40 reached at 34), no retries.
import { readFileSync, writeFileSync } from 'node:fs';
const URL_ = 'https://base-rpc.publicnode.com';
const BLUE = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb';
const raw = JSON.parse(readFileSync('/root/work/run_r15/morpho_raw.json'));
const logs = raw.filter((x) => x.method === 'eth_getLogs').at(-1).resp.result;
let n = 4; const log = [];
async function rpc(method, params) {
  if (++n > 40) throw new Error('budget');
  let r;
  try { r = await (await fetch(URL_, { method: 'POST', headers: { 'Content-Type': 'application/json', 'User-Agent': 'hermes-agent-909' }, body: JSON.stringify({ jsonrpc: '2.0', id: n, method, params }), signal: AbortSignal.timeout(20000) })).json(); }
  catch (e) { r = { error: 'transport: ' + String(e).slice(0, 100) }; }
  log.push({ method, params, resp: r }); return r;
}
const callers = [...new Set(logs.map((l) => '0x' + l.topics[2].slice(26)))];
const txs = [...new Set(logs.map((l) => l.transactionHash))];
const markets = [...new Set(logs.map((l) => l.topics[1]))];
const out = { started: new Date().toISOString(), callers: [], txs: [], markets: [] };
for (const c of callers) { const r = await rpc('eth_getCode', [c, 'latest']); out.callers.push({ caller: c, isContract: r.result && r.result !== '0x', codeBytes: r.result ? (r.result.length - 2) / 2 : null, err: r.error || null }); }
for (const t of txs) {
  const r = (await rpc('eth_getTransactionReceipt', [t])).result;
  out.txs.push(r ? { tx: t, block: parseInt(r.blockNumber, 16), status: r.status, from: r.from, to: r.to, gasUsed: parseInt(r.gasUsed, 16), effGasPrice: parseInt(r.effectiveGasPrice, 16), l1Fee: r.l1Fee ? parseInt(r.l1Fee, 16) : null, nLogs: r.logs.length } : { tx: t, err: 'no receipt' });
}
for (const m of markets) {
  const data = '0x2c3c9157' + m.slice(2); // idToMarketParams(bytes32)
  const r = await rpc('eth_call', [{ to: BLUE, data }, 'latest']);
  const d = r.result ? r.result.slice(2) : '';
  const w = (i) => '0x' + d.slice(64 * i + 24, 64 * (i + 1));
  out.markets.push({ id: m, loanToken: w(0), collateralToken: w(1), oracle: w(2), irm: w(3), lltv: d ? BigInt('0x' + d.slice(256, 320)).toString() : null, err: r.error || null, logsInWindow: logs.filter((l) => l.topics[1] === m).length });
}
out.rpcTotalIncludingLogScan = n;
out.finished = new Date().toISOString();
writeFileSync('/root/work/run_r15/morpho_callers.json', JSON.stringify(out, null, 2));
writeFileSync('/root/work/run_r15/morpho_callers_raw.json', JSON.stringify(log));
console.log(JSON.stringify(out, null, 1));
