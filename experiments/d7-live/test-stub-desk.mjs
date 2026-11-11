// Shared offline harness for the desk daemon tests: a stub JSON-RPC server that plays the credit desk, and a runner that spawns
// the daemon against it with a throwaway key. No chain, no real key, no model (a fake `claude` command can stand in for it).
import http from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync, chmodSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeFunctionData, encodeAbiParameters } from 'viem';
import { ABI } from './lib/chain.mjs';

const here = dirname(fileURLToPath(import.meta.url));

export const DESK = '0x' + '22'.repeat(20), APPLICANT = '0x' + '33'.repeat(20), TXHASH = '0x' + 'ab'.repeat(32), BLK = '0x64';
const deskAbi = JSON.parse(readFileSync(join(here, 'build', 'CreditDesk.json'))).abi;
const abis = [deskAbi, ABI.pool, ABI.erc20];
// Answers the daemon's reads by function name. With mode.applicant the desk has one pending applicant (once) whose last
// message is a feedback note, which the daemon answers with a fixed reply: one real send and one receipt, mined with
// mode.status (success or reverted).
// With mode.receiptDelayMs the reply's receipt is not available until that long after it was sent (an ambiguous send), and the
// desk keeps listing the applicant as pending until then.
const minedNow = (mode, state) => state.sentAt !== undefined && Date.now() - state.sentAt >= mode.receiptDelayMs;
const listedNow = (mode, state) => state.sentAt === undefined || Date.now() - state.sentAt < mode.receiptDelayMs + (mode.pendingLagMs || 0); // still listed pending a little after the receipt appears
function callResult(data, mode, state) {
  for (const abi of abis) {
    let d; try { d = decodeFunctionData({ abi, data }); } catch { continue; }
    // encode the return values straight from the ABI's output list; this is the same call in every viem version
    // (encodeFunctionResult reads a single array result differently across versions)
    const outputs = abi.find((f) => f.type === 'function' && f.name === d.functionName).outputs;
    const out = (...vals) => encodeAbiParameters(outputs, vals);
    switch (d.functionName) {
      case 'pending': if (mode.applicant) { if (mode.receiptDelayMs) { if (listedNow(mode, state)) return out([APPLICANT]); } else if (!state.served) { state.served = true; return out([APPLICANT]); } } return out([]);
      case 'maxLine': return out(5_000_000n);
      case 'freeStake': return out(7_000_000n);
      case 'backingOf': return out(0n);
      case 'thread': return out([{ from: 0, at: 1_800_000_000, text: mode.threadText || 'feedback: hello' }, ...(mode.threadGrows && state.sentAt !== undefined && Date.now() - state.sentAt >= mode.receiptDelayMs ? [{ from: 1, at: 1_800_000_060, text: 'officer reply' }] : [])]); // with threadGrows the officer's own reply appears once it has mined
      case 'reply': (state.replies ||= []).push({ text: d.args[1], amount: d.args[2] }); return '0x';
      case 'getBorrowLimit': return out(0n, 0n);
      case 'getBorrowerLoanIds': return out([]);
      case 'defaultedLoans': return out(0n);
      case 'balanceOf': return out(0n);
      default: return '0x';
    }
  }
  return '0x';
}
export function stub(mode) {
  const state = {};
  const answer = (r) => {
    const res = (result) => ({ jsonrpc: '2.0', id: r.id, result });
    switch (r.method) {
      case 'eth_chainId': return res('0x14a34');
      case 'eth_call': return res(callResult(r.params[0].data || r.params[0].input, mode, state));
      case 'eth_blockNumber': return res(BLK);
      case 'eth_getTransactionCount': { // the account's nonce: pending counts every send, latest counts mined ones and, with dropAfterMs, a nonce another transaction took
        const mined = state.sent && (!mode.receiptDelayMs || minedNow(mode, state)) ? 1 : 0;
        const taken = mode.dropAfterMs && state.sentAt !== undefined && Date.now() - state.sentAt >= mode.dropAfterMs ? 1 : 0;
        return res('0x' + (r.params[1] === 'pending' ? 1 + (state.sent || 0) : 1 + mined + taken).toString(16)); }
      case 'eth_estimateGas': return res('0x30000');
      case 'eth_gasPrice': case 'eth_maxPriorityFeePerGas': return res('0x3b9aca00');
      case 'eth_getBlockByNumber': return res({ number: BLK, hash: '0x' + 'cd'.repeat(32), parentHash: '0x' + '00'.repeat(32), timestamp: '0x6000', baseFeePerGas: '0x3b9aca00', gasLimit: '0x1c9c380', gasUsed: '0x0', miner: '0x' + '00'.repeat(20), transactions: [], uncles: [], nonce: '0x0000000000000000', difficulty: '0x0', totalDifficulty: '0x0', extraData: '0x', logsBloom: '0x' + '00'.repeat(256), sha3Uncles: '0x' + '00'.repeat(32), stateRoot: '0x' + '00'.repeat(32), transactionsRoot: '0x' + '00'.repeat(32), receiptsRoot: '0x' + '00'.repeat(32), size: '0x100', mixHash: '0x' + '00'.repeat(32) });
      case 'eth_feeHistory': return res({ oldestBlock: BLK, baseFeePerGas: ['0x3b9aca00', '0x3b9aca00'], gasUsedRatio: [0], reward: [['0x3b9aca00']] });
      case 'eth_sendRawTransaction': state.sent = (state.sent || 0) + 1; if (state.sentAt === undefined) state.sentAt = Date.now(); state.sendCalls = (state.sendCalls || 0) + 1; if (mode.throwAfterBroadcast && state.sendCalls === 1) return { jsonrpc: '2.0', id: r.id, error: { code: -32000, message: 'request timed out after the transaction was accepted' } }; return res(TXHASH);
      // older viem versions look the transaction up before they wait for its receipt
      case 'eth_getTransactionByHash': return res(state.sent && (!mode.receiptDelayMs || minedNow(mode, state)) ? { hash: TXHASH, blockHash: '0x' + 'cd'.repeat(32), blockNumber: BLK, transactionIndex: '0x0', from: '0x' + '44'.repeat(20), to: DESK, input: '0x', nonce: '0x1', value: '0x0', gas: '0x30000', gasPrice: '0x3b9aca00', maxFeePerGas: '0x3b9aca00', maxPriorityFeePerGas: '0x3b9aca00', type: '0x2', chainId: '0x14a34', accessList: [], v: '0x0', yParity: '0x0', r: '0x' + '11'.repeat(32), s: '0x' + '22'.repeat(32) } : null);
      case 'eth_getTransactionReceipt': return res(state.sent && (!mode.receiptDelayMs || minedNow(mode, state)) ? { transactionHash: TXHASH, blockHash: '0x' + 'cd'.repeat(32), blockNumber: BLK, transactionIndex: '0x0', from: '0x' + '44'.repeat(20), to: DESK, status: mode.status || '0x1', gasUsed: '0x5208', cumulativeGasUsed: '0x5208', effectiveGasPrice: '0x3b9aca00', logs: [], logsBloom: '0x' + '00'.repeat(256), type: '0x2', contractAddress: null } : null);
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
export const wait = (ms) => new Promise((r) => setTimeout(r, ms));
export const until = async (cond, limitMs) => { const t0 = Date.now(); while (!cond() && Date.now() - t0 < limitMs) await wait(25); };
export async function run({ fail: failRpc = false, how, preload, ms = 1300, applicant = false, status, env: extraEnv = {}, floor = '100', threadText, receiptDelayMs, pendingLagMs, threadGrows, dropAfterMs, throwAfterBroadcast, reuse, keep, fakeClaude, mode: daemonMode = 'rules' }) {
  const dir = reuse ? reuse.dir : mkdtempSync(join(tmpdir(), 'obs-')); const LOG = join(dir, 'd.log');
  const srv = reuse ? reuse.srv : await stub({ fail: failRpc, applicant, status, threadText, receiptDelayMs, pendingLagMs, threadGrows, dropAfterMs, throwAfterBroadcast });
  const env = { ...process.env, RPC_URL: `http://127.0.0.1:${srv.address().port}`, DESK, OFFICER_KEY: '0x' + '11'.repeat(32), MODE: daemonMode, POLL: '40', LOG, HEARTBEAT_FLOOR_MS: floor, HEARTBEAT_MS: '250', ...extraEnv };
  if (floor === null) delete env.HEARTBEAT_FLOOR_MS;
  if (fakeClaude) { // a stand-in for the claude command the daemon spawns for each model call
    const bin = join(dir, 'bin'); mkdirSync(bin); const f = join(bin, 'claude');
    const out = { ok: 'echo \'{"structured_output":{"reply":"Thanks, the desk backs you with $3 of test credit.","backing":3},"total_cost_usd":0.01,"usage":{},"modelUsage":{"m":{}}}\'', exit1: 'echo model-failed-SECRET >&2; exit 1', sleep: 'sleep 30', empty: 'echo \'{"structured_output":{"reply":"","backing":3},"total_cost_usd":0.01,"usage":{},"modelUsage":{"m":{}}}\'' }[fakeClaude];
    writeFileSync(f, '#!/bin/sh\n' + out + '\n'); chmodSync(f, 0o755); env.PATH = bin + ':' + process.env.PATH;
  }
  if (preload) { const f = join(dir, 'pre.mjs'); writeFileSync(f, preload); env.NODE_OPTIONS = `--import file://${f}`; }
  const ch = spawn('node', [join(here, 'desk-daemon.mjs')], { env, stdio: ['ignore', 'ignore', 'ignore'] });
  const exited = new Promise((r) => ch.on('close', (code, sig) => r({ code, sig })));
  await until(() => existsSync(LOG) && readFileSync(LOG, 'utf8').includes('"ev":"start"'), 20000); // a slow module load must not shorten the observed window
  await wait(ms);
  let res = null; if (how === 'term') ch.kill('SIGTERM'); else if (how === 'kill') ch.kill('SIGKILL');
  res = await Promise.race([exited, wait(3000).then(() => 'timeout')]);
  if (!keep) srv.close();
  const lines = existsSync(LOG) ? readFileSync(LOG, 'utf8').trim().split('\n').map((l) => JSON.parse(l)) : [];
  return { lines, res, srv, dir, sent: srv.state.sent || 0, replies: srv.state.replies || [], raw: existsSync(LOG) ? readFileSync(LOG, 'utf8') : '' };
}
