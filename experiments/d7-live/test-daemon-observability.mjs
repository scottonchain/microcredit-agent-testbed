// Offline test of the desk daemon's observability events (heartbeat and exit). No chain, no key, no model: a stub JSON-RPC
// server answers the daemon's pending() read, and the daemon runs in MODE=rules with a throwaway key.
//   node test-daemon-observability.mjs
import http from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const EMPTY_ARRAY = '0x' + '00'.repeat(31) + '20' + '00'.repeat(32); // abi-encoded address[] of length 0

function stub(mode) {
  const answer = (r) => ({ jsonrpc: '2.0', id: r.id, result: r.method === 'eth_chainId' ? '0x14a34' : r.method === 'eth_call' ? EMPTY_ARRAY : null });
  const srv = http.createServer((req, res) => {
    let b = ''; req.on('data', (d) => (b += d)); req.on('end', () => {
      if (mode.fail) { res.writeHead(500); res.end('boom SECRET-RPC-TEXT'); return; }
      const j = JSON.parse(b); res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify(Array.isArray(j) ? j.map(answer) : answer(j)));
    });
  });
  return new Promise((r) => srv.listen(0, '127.0.0.1', () => r(srv)));
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function run({ fail: failRpc = false, how, preload, ms = 1300 }) {
  const dir = mkdtempSync(join(tmpdir(), 'obs-')); const LOG = join(dir, 'd.log');
  const srv = await stub({ fail: failRpc });
  const env = { ...process.env, RPC_URL: `http://127.0.0.1:${srv.address().port}`, DESK: '0x' + '22'.repeat(20), OFFICER_KEY: '0x' + '11'.repeat(32), MODE: 'rules', POLL: '40', LOG, HEARTBEAT_FLOOR_MS: '100', HEARTBEAT_MS: '250' };
  if (preload) { const f = join(dir, 'pre.mjs'); writeFileSync(f, preload); env.NODE_OPTIONS = `--import file://${f}`; }
  const ch = spawn('node', [join(here, 'desk-daemon.mjs')], { env, stdio: ['ignore', 'ignore', 'ignore'] });
  const exited = new Promise((r) => ch.on('close', (code, sig) => r({ code, sig })));
  await wait(ms);
  let res = null; if (how === 'term') ch.kill('SIGTERM'); else if (how === 'kill') ch.kill('SIGKILL');
  res = await Promise.race([exited, wait(3000).then(() => 'timeout')]);
  srv.close();
  const lines = existsSync(LOG) ? readFileSync(LOG, 'utf8').trim().split('\n').map((l) => JSON.parse(l)) : [];
  return { lines, res, raw: existsSync(LOG) ? readFileSync(LOG, 'utf8') : '' };
}
const HB_KEYS = ['t', 'ev', 'uptimeS', 'intervalS', 'pollOk', 'pollErr', 'handled', 'handleErr', 'lastPollOkAgeS', 'lastPollErrAgeS', 'lastHandledAgeS', 'inflight'];
const EX_KEYS = ['t', 'ev', 'reason', 'uptimeS', 'lastPollOkAgeS', 'signal', 'kind', 'code'];

// 1. healthy poll, SIGTERM
{ const r = await run({ how: 'term' }); const hb = r.lines.filter((l) => l.ev === 'heartbeat'); const ex = r.lines.filter((l) => l.ev === 'exit');
  ok(r.lines[0].ev === 'start', 'start event first');
  ok(hb.length >= 2 && hb.length <= 8, 'heartbeat is rate bounded and present: ' + hb.length);
  ok(hb.every((h) => Object.keys(h).every((k) => HB_KEYS.includes(k))), 'heartbeat has only whitelisted keys');
  ok(hb.some((h) => h.pollOk > 0) && hb.every((h) => h.pollErr === 0), 'poll success counted, no poll errors');
  ok(hb.every((h) => h.lastPollOkAgeS !== null && h.lastPollOkAgeS < 2), 'last poll age small and present');
  ok(hb.every((h) => h.handled === 0 && h.lastHandledAgeS === null), 'no request handled is reported as such, apart from poll success');
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

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
