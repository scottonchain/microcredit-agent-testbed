// Offline test of the desk daemon's observability events (heartbeat and exit). No chain, no key, no model: a stub JSON-RPC
// server answers the daemon's pending() read, and the daemon runs in MODE=rules with a throwaway key.
//   node test-daemon-observability.mjs
import http from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeFunctionData, encodeAbiParameters } from 'viem';
import { ADDR, ABI } from './lib/chain.mjs';

const here = dirname(fileURLToPath(import.meta.url));
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const EMPTY_ARRAY = '0x' + '00'.repeat(31) + '20' + '00'.repeat(32); // abi-encoded address[] of length 0

const DESK = '0x' + '22'.repeat(20), APPLICANT = '0x' + '33'.repeat(20), TXHASH = '0x' + 'ab'.repeat(32), BLK = '0x64';
const deskAbi = JSON.parse(readFileSync(join(here, 'build', 'CreditDesk.json'))).abi;
const abis = [deskAbi, ABI.pool, ABI.erc20];
// Answers the daemon's reads by function name. With mode.applicant the desk has one pending applicant (once) whose last
// message is a feedback note, which the daemon answers with a fixed reply: one real send and one receipt, mined with
// mode.status (success or reverted).
function callResult(data, mode, state) {
  for (const abi of abis) {
    let d; try { d = decodeFunctionData({ abi, data }); } catch { continue; }
    // encode the return values straight from the ABI's output list; this is the same call in every viem version
    // (encodeFunctionResult reads a single array result differently across versions)
    const outputs = abi.find((f) => f.type === 'function' && f.name === d.functionName).outputs;
    const out = (...vals) => encodeAbiParameters(outputs, vals);
    switch (d.functionName) {
      case 'pending': if (mode.applicant && !state.served) { state.served = true; return out([APPLICANT]); } return out([]);
      case 'maxLine': return out(5_000_000n);
      case 'freeStake': return out(7_000_000n);
      case 'backingOf': return out(0n);
      case 'thread': return out([{ from: 0, at: 1_800_000_000, text: 'feedback: hello' }]);
      case 'reply': return '0x';
      case 'getBorrowLimit': return out(0n, 0n);
      case 'getBorrowerLoanIds': return out([]);
      case 'defaultedLoans': return out(0n);
      case 'balanceOf': return out(0n);
      default: return '0x';
    }
  }
  return '0x';
}
function stub(mode) {
  const state = {};
  const answer = (r) => {
    const res = (result) => ({ jsonrpc: '2.0', id: r.id, result });
    switch (r.method) {
      case 'eth_chainId': return res('0x14a34');
      case 'eth_call': return res(callResult(r.params[0].data || r.params[0].input, mode, state));
      case 'eth_blockNumber': return res(BLK);
      case 'eth_getTransactionCount': return res('0x1');
      case 'eth_estimateGas': return res('0x30000');
      case 'eth_gasPrice': case 'eth_maxPriorityFeePerGas': return res('0x3b9aca00');
      case 'eth_getBlockByNumber': return res({ number: BLK, hash: '0x' + 'cd'.repeat(32), parentHash: '0x' + '00'.repeat(32), timestamp: '0x6000', baseFeePerGas: '0x3b9aca00', gasLimit: '0x1c9c380', gasUsed: '0x0', miner: '0x' + '00'.repeat(20), transactions: [], uncles: [], nonce: '0x0000000000000000', difficulty: '0x0', totalDifficulty: '0x0', extraData: '0x', logsBloom: '0x' + '00'.repeat(256), sha3Uncles: '0x' + '00'.repeat(32), stateRoot: '0x' + '00'.repeat(32), transactionsRoot: '0x' + '00'.repeat(32), receiptsRoot: '0x' + '00'.repeat(32), size: '0x100', mixHash: '0x' + '00'.repeat(32) });
      case 'eth_feeHistory': return res({ oldestBlock: BLK, baseFeePerGas: ['0x3b9aca00', '0x3b9aca00'], gasUsedRatio: [0], reward: [['0x3b9aca00']] });
      case 'eth_sendRawTransaction': state.sent = (state.sent || 0) + 1; return res(TXHASH);
      // older viem versions look the transaction up before they wait for its receipt
      case 'eth_getTransactionByHash': return res(state.sent ? { hash: TXHASH, blockHash: '0x' + 'cd'.repeat(32), blockNumber: BLK, transactionIndex: '0x0', from: '0x' + '44'.repeat(20), to: DESK, input: '0x', nonce: '0x1', value: '0x0', gas: '0x30000', gasPrice: '0x3b9aca00', maxFeePerGas: '0x3b9aca00', maxPriorityFeePerGas: '0x3b9aca00', type: '0x2', chainId: '0x14a34', accessList: [], v: '0x0', yParity: '0x0', r: '0x' + '11'.repeat(32), s: '0x' + '22'.repeat(32) } : null);
      case 'eth_getTransactionReceipt': return res(state.sent ? { transactionHash: TXHASH, blockHash: '0x' + 'cd'.repeat(32), blockNumber: BLK, transactionIndex: '0x0', from: '0x' + '44'.repeat(20), to: DESK, status: mode.status || '0x1', gasUsed: '0x5208', cumulativeGasUsed: '0x5208', effectiveGasPrice: '0x3b9aca00', logs: [], logsBloom: '0x' + '00'.repeat(256), type: '0x2', contractAddress: null } : null);
      default: return res(null);
    }
  };
  const srv = http.createServer((req, res) => {
    let b = ''; req.on('data', (d) => (b += d)); req.on('end', () => {
      if (mode.fail) { res.writeHead(500); res.end('boom SECRET-RPC-TEXT'); return; }
      const j = JSON.parse(b); res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify(Array.isArray(j) ? j.map(answer) : answer(j)));
    });
  });
  srv.state = state;
  return new Promise((r) => srv.listen(0, '127.0.0.1', () => r(srv)));
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const until = async (cond, limitMs) => { const t0 = Date.now(); while (!cond() && Date.now() - t0 < limitMs) await wait(25); };
async function run({ fail: failRpc = false, how, preload, ms = 1300, applicant = false, status, env: extraEnv = {}, floor = '100' }) {
  const dir = mkdtempSync(join(tmpdir(), 'obs-')); const LOG = join(dir, 'd.log');
  const srv = await stub({ fail: failRpc, applicant, status });
  const env = { ...process.env, RPC_URL: `http://127.0.0.1:${srv.address().port}`, DESK, OFFICER_KEY: '0x' + '11'.repeat(32), MODE: 'rules', POLL: '40', LOG, HEARTBEAT_FLOOR_MS: floor, HEARTBEAT_MS: '250', ...extraEnv };
  if (floor === null) delete env.HEARTBEAT_FLOOR_MS;
  if (preload) { const f = join(dir, 'pre.mjs'); writeFileSync(f, preload); env.NODE_OPTIONS = `--import file://${f}`; }
  const ch = spawn('node', [join(here, 'desk-daemon.mjs')], { env, stdio: ['ignore', 'ignore', 'ignore'] });
  const exited = new Promise((r) => ch.on('close', (code, sig) => r({ code, sig })));
  await until(() => existsSync(LOG) && readFileSync(LOG, 'utf8').includes('"ev":"start"'), 20000); // a slow module load must not shorten the observed window
  await wait(ms);
  let res = null; if (how === 'term') ch.kill('SIGTERM'); else if (how === 'kill') ch.kill('SIGKILL');
  res = await Promise.race([exited, wait(3000).then(() => 'timeout')]);
  srv.close();
  const lines = existsSync(LOG) ? readFileSync(LOG, 'utf8').trim().split('\n').map((l) => JSON.parse(l)) : [];
  return { lines, res, sent: srv.state.sent || 0, raw: existsSync(LOG) ? readFileSync(LOG, 'utf8') : '' };
}
const HB_KEYS = ['t', 'ev', 'uptimeS', 'intervalS', 'pollOk', 'pollErr', 'handled', 'reverted', 'handleErr', 'lastPollOkAgeS', 'lastPollErrAgeS', 'lastHandledAgeS', 'inflight'];
const EX_KEYS = ['t', 'ev', 'reason', 'uptimeS', 'lastPollOkAgeS', 'signal', 'kind', 'code'];

// 1. healthy poll, SIGTERM
{ const r = await run({ how: 'term' }); const hb = r.lines.filter((l) => l.ev === 'heartbeat'); const ex = r.lines.filter((l) => l.ev === 'exit');
  ok(r.lines[0].ev === 'start', 'start event first');
  ok(hb.length >= 1 && hb.length <= 8, 'heartbeat is rate bounded and present: ' + hb.length);
  ok(hb.every((h) => Object.keys(h).every((k) => HB_KEYS.includes(k))), 'heartbeat has only whitelisted keys');
  ok(hb.some((h) => h.pollOk > 0) && hb.every((h) => h.pollErr === 0), 'poll success counted, no poll errors');
  // the first heartbeat can fire before the first poll has returned (pollOk 0, age null: no successful poll yet); every heartbeat that counts a successful poll must carry a small age
  ok(hb.filter((h) => h.pollOk > 0).length > 0 && hb.filter((h) => h.pollOk > 0).every((h) => h.lastPollOkAgeS !== null && h.lastPollOkAgeS < 2), 'last poll age small and present once a poll has succeeded');
  ok(hb.filter((h) => h.lastPollOkAgeS !== null).every((h) => h.lastPollOkAgeS < 2) && hb.slice(1).some((h) => h.lastPollOkAgeS !== null), 'a poll age is never stale and is present after the first heartbeat');
  ok(hb.every((h) => h.handled === 0 && h.reverted === 0 && h.lastHandledAgeS === null), 'no request handled is reported as such, apart from poll success');
  ok(ex.length === 1 && ex[0].reason === 'signal' && ex[0].signal === 'SIGTERM', 'one controlled exit event for SIGTERM');
  ok(Object.keys(ex[0] || {}).every((k) => EX_KEYS.includes(k)), 'exit event has only whitelisted keys');
  ok(r.res && r.res.code === 143, 'exit code 128+15 kept: ' + JSON.stringify(r.res)); }

// 2. RPC down: process alive, polls failing, no raw error text in heartbeat
{ const r = await run({ fail: true, how: 'term', ms: 4500 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat'); // the RPC client retries a failing read for about a second before it throws
  ok(hb.length >= 2, 'heartbeat continues while RPC fails');
  ok(hb.some((h) => h.pollErr > 0 && h.lastPollErrAgeS !== null) && hb.every((h) => h.pollOk === 0 && h.lastPollOkAgeS === null), 'poll failure distinguished from process alive');
  ok(!JSON.stringify(hb).includes('SECRET-RPC-TEXT'), 'heartbeat carries no raw error text'); }

// 3. unhandled rejection: class only, never the message
{ const r = await run({ how: 'none', preload: "setTimeout(() => Promise.reject(new TypeError('LEAK-ME-12345')), 500);" }); const ex = r.lines.filter((l) => l.ev === 'exit');
  ok(ex.length === 1 && ex[0].reason === 'unhandled-rejection' && ex[0].kind === 'TypeError', 'unhandled rejection exit event with error class');
  ok(!r.raw.includes('LEAK-ME-12345'), 'exit event carries no error message');
  ok(r.res && r.res.code === 1, 'exit code 1 kept'); }

// 4. SIGKILL: nothing can be written; the evidence is a heartbeat that stops
{ const r = await run({ how: 'kill' }); ok(!r.lines.some((l) => l.ev === 'exit'), 'SIGKILL writes no exit event (documented limit)'); ok(r.lines.some((l) => l.ev === 'heartbeat'), 'heartbeats exist before the kill'); }

// 5. a confirmed reply counts as handled; a reply whose receipt is reverted does not
{ const r = await run({ how: 'term', applicant: true, status: '0x1', ms: 2500 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat');
  ok(r.sent === 1 && r.lines.some((l) => l.ev === 'feedback' && l.ok === true), 'control: the daemon sent one reply and it mined successfully');
  ok(hb.reduce((n, h) => n + h.handled, 0) === 1 && hb.every((h) => h.reverted === 0), 'confirmed reply counted as handled');
  ok(hb.some((h) => h.lastHandledAgeS !== null), 'last handled age set after a confirmed reply'); }
{ const r = await run({ how: 'term', applicant: true, status: '0x0', ms: 2500 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat');
  ok(r.sent === 1 && r.lines.some((l) => l.ev === 'feedback' && l.ok === false), 'the daemon sent one reply and its receipt was reverted');
  ok(hb.reduce((n, h) => n + h.reverted, 0) === 1 && hb.every((h) => h.handled === 0 && h.lastHandledAgeS === null), 'reverted reply is counted as reverted, never as handled, and sets no last handled age');
  ok(!r.lines.some((l) => l.ev === 'error'), 'a reverted receipt does not change the daemon behavior (no new error path)'); }

// 6. invalid heartbeat configuration is bounded, not a flood
for (const [name, extraEnv, floor, expectMax] of [['non-numeric', { HEARTBEAT_MS: 'abc' }, null, 0], ['empty', { HEARTBEAT_MS: '' }, null, 0], ['NaN', { HEARTBEAT_MS: 'NaN' }, null, 0], ['below the floor', { HEARTBEAT_MS: '5' }, null, 0], ['huge', { HEARTBEAT_MS: '99999999999999' }, null, 0], ['non-numeric floor', { HEARTBEAT_MS: '5' }, 'xyz', 0], ['floor above 60 s', { HEARTBEAT_MS: '5' }, '999999', 0]]) {
  const r = await run({ how: 'term', env: extraEnv, floor, ms: 900 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat');
  ok(hb.length <= expectMax, `${name} heartbeat setting does not flood (${hb.length} heartbeats in 0.9 s)`);
  ok(r.lines.some((l) => l.ev === 'exit' && l.reason === 'signal'), `${name}: daemon still runs and exits cleanly`); }

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
