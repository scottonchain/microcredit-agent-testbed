// Offline tests for the chain-only monitor (reader, adapter, validator, CLI, draft workflow). Run: node test-monitor.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { decodePending, decodeThreadTimes, decodeSmallUint, takeSnapshot, readWithFallback, makeJsonRpc, validEndpointUrl, SEL_PENDING, SEL_THREAD, SEL_UNANSWERED } from './reader.mjs';
import { parseMonitorConfig, chainOnlyCheck, boardMessage, boardComment, validateBoardComment, runOnce, DEFAULT_ENDPOINTS, FOOTER } from './adapter.mjs';
import { main as cliMain } from './run-chain-monitor.mjs';
import { main as validateMain } from './validate-comment.mjs';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) pass++; else { fail++; console.log('FAIL', n); } };
const here = dirname(fileURLToPath(import.meta.url));
const S = JSON.parse(readFileSync(join(here, 'fixtures', 'abi-samples.json'), 'utf8'));
const DESK = '0x28e1d776d9f9f60b90cfb8075ebb9d0f07c82462';
const A1 = '0x1111111111111111111111111111111111111111', A2 = '0x2222222222222222222222222222222222222222';
const NOWMS = 1794642162000; // 2026-11-13T... in the fixtures' world; block times are placed relative to this
const BLOCK_TS = 1794642155; // seconds
const HASH = '0x' + 'ab'.repeat(32), HASH2 = '0x' + 'cd'.repeat(32);

ok(S.selectors.pending === SEL_PENDING && S.selectors.thread === SEL_THREAD && S.selectors.unanswered === SEL_UNANSWERED, 'hard-coded selectors equal the ones viem computed from the ABI');

// ---- decoders ----
const dp = (h) => decodePending(h);
ok(dp(S.pending.empty).ok && dp(S.pending.empty).addresses.length === 0, 'empty pending decodes to an empty list');
ok(dp(S.pending.two).ok && dp(S.pending.two).addresses.join() === `${A1},${A2}`, 'two pending addresses decode');
ok(dp(S.pending.many201).why === 'TOO_MANY', 'more than 200 pending is refused, not truncated');
{ const h = S.pending.two;
  ok(dp(h.slice(0, -64)).why === 'BAD_LENGTH' && dp(h + '00'.repeat(32)).why === 'BAD_LENGTH', 'a missing or extra word is BAD_LENGTH');
  ok(dp(h.slice(0, -2)).ok === false && dp(h + '0').ok === false, 'odd or truncated hex is refused');
  ok(dp('0x' + '00'.repeat(31) + '40' + h.slice(66)).why === 'BAD_OFFSET', 'a wrong offset is BAD_OFFSET');
  ok(dp(h.slice(0, 2 + 64 * 2 + 2) + 'ff' + h.slice(2 + 64 * 2 + 4)).why === 'BAD_ADDRESS', 'dirty high bits in an address are refused');
  for (const bad of [undefined, null, 5, {}, 'x', '0x', '0xzz', '0x' + 'ff'.repeat(3 * 1024 * 1024)]) ok(dp(bad).ok === false, `pending decoder refuses ${typeof bad === 'string' ? bad.slice(0, 8) : String(bad)}`);
  for (let cut = 2; cut < h.length; cut += 2) { if (dp(h.slice(0, cut)).ok) { ok(false, `a truncated pending result (cut at ${cut}) must not decode`); break; } } pass++; }
const dt = (h) => decodeThreadTimes(h);
ok(dt(S.thread.ask).ok && JSON.stringify(dt(S.thread.ask).messages) === JSON.stringify([{ from: 0, at: 1794640000 }]), 'one-message thread decodes to its time only');
ok(dt(S.thread.askReplyAsk).ok && dt(S.thread.askReplyAsk).messages.map((m) => `${m.from}@${m.at}`).join() === '0@1794640000,1@1794640100,0@1794640500', 'ask, reply, ask decodes in order');
ok(dt(S.thread.empty).ok && dt(S.thread.empty).messages.length === 0, 'empty thread decodes');
ok(dt(S.thread.emptyText).ok && dt(S.thread.unicodeText).ok, 'empty and multi-byte text decode');
ok(dt(S.thread.badFrom).why === 'BAD_FROM', 'from above 1 is refused');
ok(dt(S.thread.eighty).ok && dt(S.thread.eighty).messages.length === 80 && dt(S.thread.eightyOne).why === 'TOO_MANY', 'the contract limit of 80 messages is the decoder cap: 80 decodes, 81 is refused');
for (const k of Object.keys(S.thread)) { const r = JSON.stringify(dt(S.thread[k])); ok(!/hello|first|second|reply|caf/.test(r), `thread sample ${k}: no message text in the decoded result`); }
{ const h = S.thread.askReplyAsk;
  let accepted = null; for (let cut = 2; cut < h.length; cut += 2) { const r = dt(h.slice(0, cut)); if (r.ok) { accepted = cut; break; } }
  ok(accepted === null, `regression: no truncation of a thread result decodes (first accepted cut: ${accepted})`);
  const setWord = (hex, wordIdx, val) => hex.slice(0, 2 + wordIdx * 64) + val.padStart(64, '0') + hex.slice(2 + (wordIdx + 1) * 64);
  ok(dt(setWord(h, 0, '40')).why === 'BAD_OFFSET', 'wrong outer offset');
  ok(dt(setWord(h, 1, '51')).why === 'TOO_MANY' && dt(setWord(h, 1, '10000')).why === 'TOO_MANY', 'a huge message count is refused before any allocation');
  ok(dt(setWord(h, 2, 'ffffffffffffffff')).why === 'BAD_OFFSET' && dt(setWord(h, 2, '0')).why === 'BAD_OFFSET', 'element offset out of range or inside the offsets table');
  ok(dt(setWord(h, 6, '10000000000')).why === 'BAD_TIME' && dt(setWord(h, 6, 'ffffffffffffffff')).why === 'BAD_TIME', 'a time of 2^40 or more is refused');
  ok(dt(setWord(h, 6, 'ffffffffff')).ok === true, 'control: the largest uint40 time is accepted');
  ok(dt(setWord(h, 2, '61')).why === 'BAD_OFFSET' && dt(setWord(h, 3, '21')).why === 'BAD_OFFSET', 'regression: an element offset that is not a whole word is refused');
  ok(dt(setWord(h, 7, '61')).why === 'BAD_STRING' && dt(setWord(h, 7, '21')).why === 'BAD_STRING', 'regression: a string offset that is not a whole word is refused');
  { // a string whose offset is one byte off a word boundary but whose shifted length word is perfectly in bounds: only an alignment check refuses it
    const a = S.thread.ask, at = (w) => 2 + w * 64;
    const shifted = a.slice(0, at(5)) + '61'.padStart(64, '0') + '00' + a.slice(at(6)) + '00'.repeat(31);
    ok(shifted.length === a.length + 64 && dt(shifted).why === 'BAD_STRING', 'regression: a misaligned string offset with an in-bounds shifted length word is refused (alignment is checked, not only bounds)'); }
  ok(dt(setWord(h, 7, 'ffffffffffffffffffffffff')).why === 'BAD_STRING' && dt(setWord(h, 7, '10000')).why === 'BAD_STRING', 'a string offset past the end is refused');
  ok(dt(setWord(h, 8, 'ffffffffffff')).why === 'BAD_STRING' && dt(setWord(h, 8, '1000')).why === 'BAD_STRING', 'an absurd string length is refused');
  for (const bad of [undefined, null, 7, 'x', '0x', '0x' + '00'.repeat(32), '0x' + 'ff'.repeat(3 * 1024 * 1024)]) ok(dt(bad).ok === false, `thread decoder refuses ${typeof bad === 'string' ? bad.slice(0, 8) : String(bad)}`); }

ok(decodeSmallUint(S.unanswered.n0, 3).value === 0 && decodeSmallUint(S.unanswered.n3, 3).value === 3 && decodeSmallUint(S.unanswered.n4, 3).why === 'TOO_LARGE', 'unanswered() decodes and is capped at the contract limit of 3');
for (const bad of [undefined, null, 5, '0x', '0x01', S.unanswered.n1 + '00', '0x' + 'zz'.repeat(32)]) ok(decodeSmallUint(bad, 3).ok === false, `unanswered() decoder refuses ${String(bad).slice(0, 10)}`);

// ---- a fake chain (JSON-RPC level) ----
function chain(o = {}) {
  const calls = [];
  const rpc = async (method, params) => {
    calls.push({ method, params });
    if (o.throwOn && o.throwOn(method, params, calls.length)) throw new Error('boom');
    if (method === 'eth_chainId') return o.chainId ?? '0x14a34';
    if (method === 'eth_getBlockByNumber') {
      const nth = calls.filter((c) => c.method === 'eth_getBlockByNumber').length;
      if (o.block === null) return null;
      const b = o.block ?? { number: '0xe1b0f7', timestamp: '0x' + BLOCK_TS.toString(16), hash: HASH };
      if (o.alternate) return { ...b, hash: '0x' + String(nth).padStart(64, '0') };
      return nth >= 2 && o.secondHash ? { ...b, hash: o.secondHash } : b;
    }
    if (method === 'eth_call') {
      const data = params[0].data;
      if (data === SEL_PENDING) return o.pending ?? S.pending.empty;
      if (data.startsWith(SEL_THREAD)) { const a = '0x' + data.slice(-40); return (o.threads ?? {})[a] ?? S.thread.ask; }
      if (data.startsWith(SEL_UNANSWERED)) { const a = '0x' + data.slice(-40); if (o.unanswered && o.unanswered[a] !== undefined) return o.unanswered[a]; const d = decodeThreadTimes((o.threads ?? {})[a] ?? S.thread.ask); let last = -1; (d.messages ?? []).forEach((m, i) => { if (m.from === 1) last = i; }); return S.unanswered['n' + ((d.messages ?? []).length - 1 - last)]; }
    }
    throw new Error('unexpected ' + method);
  };
  return { rpc, calls };
}
const now = () => NOWMS;
const T = async (o, args = {}) => takeSnapshot(chain(o).rpc, { desk: DESK, now, ...args });

// ---- snapshot ----
{ const c = chain(); const r = await takeSnapshot(c.rpc, { desk: DESK, now });
  ok(r.ok && r.snapshot.pending.length === 0 && r.snapshot.blockNumber === 0xe1b0f7 && r.snapshot.pendingBlockNumber === r.snapshot.blockNumber && r.snapshot.blockTimeMs === BLOCK_TS * 1000 && r.snapshot.readAtMs === NOWMS, 'empty snapshot has the exact shape the collector requires, bound to one block');
  ok(c.calls.filter((x) => x.method === 'eth_call').every((x) => x.params[1] === '0xe1b0f7'), 'every eth_call is pinned to the same block number');
  ok(c.calls.filter((x) => x.method === 'eth_getBlockByNumber').length === 2 && c.calls[c.calls.length - 1].method === 'eth_getBlockByNumber' && c.calls[c.calls.length - 1].params[0] === '0xe1b0f7', 'the block hash is read again by number after all reads');
  ok(c.calls.every((x) => ['eth_chainId', 'eth_getBlockByNumber', 'eth_call'].includes(x.method)), 'only three read-only methods are ever called'); }
{ const th = { [A1]: S.thread.askReplyAsk, [A2]: S.thread.ask };
  const r = await T({ pending: S.pending.two, threads: th });
  ok(r.ok && r.snapshot.pending.map((p) => p.requestedAtMs).join() === '1794640500000,1794640000000', 'a pending applicant is dated by the latest APPLICANT message, not the officer reply');
  ok(!JSON.stringify(r).includes(A1.slice(2)) && !JSON.stringify(r).includes('hello') && !JSON.stringify(r).includes('first'), 'the snapshot carries no applicant address or message text');
  const c = chain({ pending: S.pending.two, threads: th }); await takeSnapshot(c.rpc, { desk: DESK, now });
  ok(c.calls.filter((x) => x.method === 'eth_call' && x.params[0].data.startsWith(SEL_THREAD)).map((x) => x.params[0].data.slice(-40)).join() === `${A1.slice(2)},${A2.slice(2)}`, 'thread() is called once per pending applicant with the address as the only argument');
  ok(c.calls.filter((x) => x.method === 'eth_call' && x.params[0].data.startsWith(SEL_UNANSWERED)).length === 2 && c.calls.filter((x) => x.method === 'eth_call').every((x) => x.params[1] === '0xe1b0f7'), 'unanswered() is cross-checked once per applicant at the same pinned block'); }
// ---- the request time is the OLDEST unanswered message, in thread order ----
{ const one = (hex, un) => T({ pending: S.pending.one, threads: { [A1]: hex }, ...(un ? { unanswered: { [A1]: un } } : {}) });
  const B = BLOCK_TS;
  let r = await one(S.thread.oldAnsweredThenTwoUnanswered); ok(r.ok && r.snapshot.pending[0].requestedAtMs === 1794641000000, 'old answered history followed by two unanswered: the wait starts at the first unanswered message, not at the history or the newest message');
  r = await one(S.thread.staleFirstFreshFollowup); ok(r.ok && r.snapshot.pending[0].requestedAtMs === (B - 1200) * 1000, 'regression: a fresh follow-up does not reset a stale first request (the age is about 1200 s, not about 5 s)');
  r = await one(S.thread.sameTimestampAskReplyAsk); ok(r.ok && r.snapshot.pending[0].requestedAtMs === (B - 60) * 1000 && r.snapshot.pending.length === 1, 'same-timestamp ask, reply, ask: order decides, the suffix after the officer message is the last ask');
  r = await one(S.thread.sameTimestampTwoAsks); ok(r.ok && r.snapshot.pending[0].requestedAtMs === (B - 60) * 1000, 'two unanswered asks sharing a timestamp are both in the suffix');
  ok((await one(S.thread.endsWithReply)).why === 'THREAD_NO_UNANSWERED', 'a thread ending with an officer message contradicts pending()');
  ok((await one(S.thread.futureAsk)).why === 'THREAD_FUTURE', 'a message dated after the block is refused');
  ok((await one(S.thread.decreasingTimes)).why === 'THREAD_TIME_ORDER', 'timestamps going backwards in thread order are refused');
  ok((await one(S.thread.fourUnanswered)).why === 'UNANSWERED_TOO_LARGE' || (await one(S.thread.fourUnanswered)).why === 'THREAD_INCONSISTENT', 'more unanswered messages than the contract allows is refused');
  ok((await one(S.thread.oldAnsweredThenTwoUnanswered, S.unanswered.n1)).why === 'THREAD_INCONSISTENT' && (await one(S.thread.oldAnsweredThenTwoUnanswered, S.unanswered.n3)).why === 'THREAD_INCONSISTENT' && (await one(S.thread.ask, S.unanswered.n0)).why === 'THREAD_INCONSISTENT', 'unanswered() at the same block must equal the length of the unanswered suffix');
  ok((await one(S.thread.ask, S.unanswered.n4)).why === 'UNANSWERED_TOO_LARGE' && (await one(S.thread.ask, '0x12')).why === 'UNANSWERED_BAD_HEX', 'an out-of-range or malformed unanswered() result is refused');
  ok((await one(S.thread.eightyOne)).why === 'THREAD_TOO_MANY', 'an 81-message thread is refused'); }
ok((await T({ chainId: '0x1' })).why === 'WRONG_CHAIN' && (await T({ chainId: undefined, throwOn: (m) => m === 'eth_chainId' })).ok === false && (await T({ chainId: 'x' })).why === 'WRONG_CHAIN', 'a wrong or missing chain id is refused');
for (const [n, b] of [['null block', null], ['no number', { timestamp: '0x1', hash: HASH }], ['zero timestamp', { number: '0x1', timestamp: '0x0', hash: HASH }], ['bad hash', { number: '0x1', timestamp: '0x5', hash: '0x12' }], ['non-hex number', { number: '12', timestamp: '0x5', hash: HASH }], ['number beyond safe', { number: '0xffffffffffffffffff', timestamp: '0x5', hash: HASH }]]) ok((await T({ block: b })).why === 'BAD_BLOCK', `bad latest block (${n}) is refused`);
ok((await T({ alternate: true })).why === 'HASH_CHANGED', 'a block hash that changed during the reads (reorg or another node) invalidates the snapshot');
ok((await T({ secondHash: HASH2 })).why === 'HASH_CHANGED', 'a changed hash on the second read is HASH_CHANGED');
ok((await T({ pending: S.pending.many201 })).why === 'PENDING_TOO_MANY', 'too many pending applicants is a failure, not a truncation');
ok((await T({ pending: S.pending.one, threads: { [A1]: S.thread.replyOnly } })).why === 'THREAD_NO_UNANSWERED' && (await T({ pending: S.pending.one, threads: { [A1]: S.thread.empty } })).why === 'THREAD_NO_UNANSWERED' && (await T({ pending: S.pending.one, threads: { [A1]: S.thread.endsWithReply } })).why === 'THREAD_NO_UNANSWERED', 'regression: pending() listing an applicant whose thread has no unanswered suffix is a failure');
ok((await T({ pending: S.pending.one, threads: { [A1]: S.thread.badFrom } })).why === 'THREAD_BAD_FROM' && (await T({ pending: S.pending.one, threads: { [A1]: '0x00' } })).ok === false, 'an undecodable thread is a failure');
ok((await T({ pending: '0x1234' })).why === 'PENDING_BAD_LENGTH', 'an undecodable pending result is a failure');
for (const m of ['eth_chainId', 'eth_getBlockByNumber', 'eth_call']) ok((await T({ throwOn: (mm) => mm === m })).why === 'RPC_ERROR', `an RPC error from ${m} is RPC_ERROR`);
ok((await T({ pending: S.pending.one, throwOn: (m, p) => m === 'eth_call' && p[0].data.startsWith(SEL_THREAD) })).why === 'RPC_ERROR', 'an RPC error from thread() is RPC_ERROR');
ok((await takeSnapshot(chain().rpc, { desk: 'nope', now })).why === 'BAD_ARGS' && (await takeSnapshot(chain().rpc, { desk: DESK })).why === 'BAD_ARGS' && (await takeSnapshot(undefined, { desk: DESK, now })).why === 'BAD_ARGS' && (await takeSnapshot(chain().rpc)).why === 'BAD_ARGS', 'bad arguments are BAD_ARGS, not a throw');
ok((await takeSnapshot(chain().rpc, { desk: DESK, now: () => NaN })).why === 'BAD_CLOCK', 'a broken clock is refused');
ok((await T({}, { maxPending: 0 })).ok === true && (await T({ pending: S.pending.one }, { maxPending: 0 })).why === 'TOO_MANY_PENDING', 'maxPending is enforced');

// ---- fallback: whole snapshots only, never mixed ----
const EPS = [{ label: 'primary', url: 'https://p.example.invalid' }, { label: 'fallback', url: 'https://f.example.invalid' }];
{ const sleeps = []; const sleep = async (ms) => { sleeps.push(ms); };
  const prim = chain({ block: { number: '0x64', timestamp: '0x' + BLOCK_TS.toString(16), hash: HASH } }), fb = chain({ block: { number: '0xc8', timestamp: '0x' + BLOCK_TS.toString(16), hash: HASH2 } });
  const mk = (map) => (url) => map[url].rpc;
  let r = await readWithFallback(EPS, mk({ 'https://p.example.invalid': prim, 'https://f.example.invalid': fb }), { desk: DESK, now, sleep });
  ok(r.ok && r.endpoint === 'primary' && r.snapshot.blockNumber === 0x64 && fb.calls.length === 0 && sleeps.length === 0, 'a healthy primary is used alone and the fallback is never called');
  const prim2 = chain({ throwOn: (m, p) => m === 'eth_call' && p[0].data === SEL_PENDING, block: { number: '0x64', timestamp: '0x' + BLOCK_TS.toString(16), hash: HASH } });
  r = await readWithFallback(EPS, mk({ 'https://p.example.invalid': prim2, 'https://f.example.invalid': fb }), { desk: DESK, now, sleep });
  ok(r.ok && r.endpoint === 'fallback' && r.snapshot.blockNumber === 0xc8 && r.snapshot.pendingBlockNumber === 0xc8, 'regression: after the primary fails at pending(), the WHOLE snapshot is restarted on the fallback; no field comes from the primary block');
  ok(sleeps.join() === '500', `bounded backoff between attempts on one provider (slept ${sleeps.join()})`);
  const dead = chain({ throwOn: () => true });
  r = await readWithFallback(EPS, mk({ 'https://p.example.invalid': dead, 'https://f.example.invalid': dead }), { desk: DESK, now, sleep });
  ok(r.ok === false && r.why === 'ALL_ENDPOINTS_FAILED' && r.tried.length === 4 && r.tried.every((t) => ['primary', 'fallback'].includes(t.endpoint)) && !JSON.stringify(r).includes('example.invalid'), 'all providers failing is a failure that names labels and reasons, never a URL, never an empty queue');
  for (const bad of [[], undefined, [1, 2, 3, 4, 5]]) ok((await readWithFallback(bad, mk({}), { desk: DESK, now, sleep })).why === 'BAD_ARGS', 'bad endpoint list is BAD_ARGS');
  ok((await readWithFallback(EPS, () => { throw new Error('x'); }, { desk: DESK, now, sleep })).why === 'ALL_ENDPOINTS_FAILED', 'a throwing transport factory is a failure, not a throw'); }

// ---- JSON-RPC transport over a fake fetch ----
const resp = (o) => ({ ok: true, text: async () => JSON.stringify(o), ...o.__meta });
const fetchOf = (f) => async (url, init) => f(url, init, JSON.parse(init.body));
{ const good = makeJsonRpc('https://x.example.invalid', fetchOf((u, i, b) => resp({ jsonrpc: '2.0', id: b.id, result: '0x14a34' })));
  ok(await good('eth_chainId', []) === '0x14a34', 'a good response returns its result');
  ok(await good('eth_chainId', []) === '0x14a34', 'ids advance per request');
  const rejects = async (f, n) => { let threw = false; try { await makeJsonRpc('https://x.example.invalid', fetchOf(f), { timeoutMs: 50, maxBytes: 1000 })('m', []); } catch { threw = true; } ok(threw, `transport refuses: ${n}`); };
  await rejects(() => ({ ok: false, text: async () => '' }), 'HTTP error');
  await rejects((u, i, b) => resp({ jsonrpc: '2.0', id: b.id + 1, result: '0x1' }), 'wrong id');
  await rejects((u, i, b) => resp({ jsonrpc: '2.0', id: b.id, error: { code: -1, message: 'x' } }), 'error field');
  await rejects((u, i, b) => resp({ jsonrpc: '2.0', id: b.id }), 'no result');
  await rejects((u, i, b) => resp({ jsonrpc: '1.0', id: b.id, result: '0x1' }), 'wrong version');
  await rejects((u, i, b) => ({ ok: false, text: async () => JSON.stringify({ jsonrpc: '2.0', id: b.id, result: '0x1' }) }), 'a non-2xx HTTP status even with a well-formed body');
  await rejects((u, i, b) => resp({ jsonrpc: '2.0', id: b.id, result: '0x1', error: { code: -1, message: 'x' } }), 'both a result and an error');
  await rejects(() => ({ ok: true, text: async () => 'not json' }), 'invalid JSON');
  await rejects((u, i, b) => resp({ jsonrpc: '2.0', id: b.id, result: 'x'.repeat(2000) }), 'oversize body');
  await rejects(() => ({ ok: true, text: async () => 5 }), 'non-text body');
  await rejects((u, init) => new Promise((_, rej) => init.signal.addEventListener('abort', () => rej(new Error('aborted')))), 'a request that never answers (aborted at the timeout)');
  for (const bad of ['http://x.example.invalid', 'https://user:pw@x.example.invalid', 'https://x.example.invalid/?key=SECRET', 'https://x.example.invalid/#f', 'x.example.invalid', '', undefined, 5]) ok(!validEndpointUrl(bad) && (() => { try { makeJsonRpc(bad, async () => {}); return false; } catch { return true; } })(), `endpoint ${String(bad)} is refused (no http, no credentials, no query)`);
  ok(validEndpointUrl('https://base-sepolia-rpc.publicnode.com') && validEndpointUrl('https://sepolia.base.org'), 'the two selected public endpoints are valid'); }

// ---- config ----
const cfgBase = { desk: DESK };
ok(parseMonitorConfig(cfgBase).ok && parseMonitorConfig(cfgBase).config.endpoints.length === 2 && JSON.stringify(parseMonitorConfig(cfgBase).config.endpoints) === JSON.stringify(DEFAULT_ENDPOINTS), 'minimal config takes the two default public endpoints and default ranges');
{ const u = parseMonitorConfig({ ...cfgBase, 'SECRETKEY-1': 1, other: 2 }); ok(!u.ok && !JSON.stringify(u).includes('SECRETKEY') && u.detail.includes('2 unknown'), 'unknown keys are counted, never echoed'); }
ok(!parseMonitorConfig(Object.create(cfgBase)).ok && !parseMonitorConfig(null).ok && !parseMonitorConfig([cfgBase]).ok && !parseMonitorConfig('x').ok, 'inherited, null, array and string configs are refused');
for (const d of [undefined, '0x12', 'x', DESK.slice(0, 41), DESK + '0']) ok(!parseMonitorConfig({ desk: d }).ok, `desk ${String(d)} refused`);
for (const [k, [lo, hi]] of Object.entries({ pendingBudgetS: [60, 86400], staleBlockS: [30, 3600], clockSkewS: [1, 300], readTimeoutS: [5, 120] })) { ok(parseMonitorConfig({ ...cfgBase, [k]: lo }).ok && parseMonitorConfig({ ...cfgBase, [k]: hi }).ok, `${k} min and max accepted`); ok(!parseMonitorConfig({ ...cfgBase, [k]: lo - 1 }).ok && !parseMonitorConfig({ ...cfgBase, [k]: hi + 1 }).ok, `${k} just outside refused`); for (const v of [null, 'x', NaN, Infinity]) ok(!parseMonitorConfig({ ...cfgBase, [k]: v }).ok, `${k} = ${String(v)} refused`); }
for (const [n, e] of [['empty', []], ['three', [...EPS, EPS[0]]], ['http', [{ label: 'primary', url: 'http://p.example.invalid' }]], ['key in query', [{ label: 'primary', url: 'https://p.example.invalid/?apikey=SECRET' }]], ['credentials', [{ label: 'primary', url: 'https://u:p@p.example.invalid' }]], ['unknown label', [{ label: 'third', url: 'https://p.example.invalid' }]], ['duplicate label', [EPS[0], { ...EPS[1], label: 'primary' }]], ['not an array', 'x'], ['null entry', [null]]]) ok(!parseMonitorConfig({ ...cfgBase, endpoints: e }).ok, `endpoints (${n}) refused`);
ok(!JSON.stringify(parseMonitorConfig({ ...cfgBase, endpoints: [{ label: 'primary', url: 'https://p.example.invalid/?apikey=SECRET' }] })).includes('SECRET'), 'a refused endpoint URL is never echoed');

// ---- a JSON-RPC server emulation for end-to-end checks ----
function server(map) {
  const log = [];
  const f = async (url, init) => { const b = JSON.parse(init.body); log.push({ url, method: b.method }); const h = map[url]; if (!h) throw new Error('no route'); const r = await h(b); return { ok: true, text: async () => JSON.stringify({ jsonrpc: '2.0', id: b.id, result: r }) }; };
  return { f, log };
}
const handlerOf = (o) => { const c = chain(o); return (b) => c.rpc(b.method, b.params); };
const U = { p: 'https://base-sepolia-rpc.publicnode.com', f: 'https://sepolia.base.org' };
const sleepNone = async () => {};
const check = (map, cfg = {}, nowFn = now) => chainOnlyCheck({ config: { desk: DESK, readTimeoutS: 5, ...cfg }, now: nowFn, fetchImpl: server(map).f, sleep: sleepNone });
{ const r = await check({ [U.p]: handlerOf({}) });
  ok(r.status === 'OK' && r.alerts.length === 0 && r.health.endpoint === 'primary' && r.health.pendingCount === 0 && r.health.oldestPendingAgeS === null && r.health.blockNumber === 0xe1b0f7, 'healthy empty queue is OK with block and count');
  const old = await check({ [U.p]: handlerOf({ pending: S.pending.one, threads: { [A1]: S.thread.ask } }) });
  ok(old.status === 'ALERT' && old.alerts.some((a) => a.code === 'PENDING_AGE') && old.health.pendingCount === 1 && old.health.oldestPendingAgeS === 2162, 'a request older than the budget alerts PENDING_AGE with its age');
  const young = await check({ [U.p]: handlerOf({ pending: S.pending.one, threads: { [A1]: S.thread.askAt57sBeforeNow } }) });
  ok(young.status === 'OK' && young.health.oldestPendingAgeS === 57 && young.health.pendingCount === 1, 'a request inside the budget is OK and its age is reported');
  const youngExact = await check({ [U.p]: handlerOf({ pending: S.pending.one, threads: { [A1]: S.thread.askAt120sBeforeNow } }) }, { pendingBudgetS: 120 });
  ok(youngExact.status === 'OK' && youngExact.health.oldestPendingAgeS === 120, 'an age exactly at the budget is OK');
  const justOver = await check({ [U.p]: handlerOf({ pending: S.pending.one, threads: { [A1]: S.thread.askAt120sBeforeNow } }) }, { pendingBudgetS: 60 });
  ok(justOver.status === 'ALERT' && justOver.alerts.some((a) => a.code === 'PENDING_AGE'), 'an age above a 60 s budget alerts');
  const both = await check({}); ok(both.status === 'ALERT' && both.alerts.map((a) => a.code).join() === 'RPC_UNAVAILABLE' && both.health.pendingCount === null, 'no reachable provider is RPC_UNAVAILABLE, never OK, never an empty queue');
  const fb = await check({ [U.p]: handlerOf({ throwOn: () => true }), [U.f]: handlerOf({}) }); ok(fb.status === 'OK' && fb.health.endpoint === 'fallback', 'the fallback is used when the primary fails, and reported as such');
  const stale = await check({ [U.p]: handlerOf({ block: { number: '0x10', timestamp: '0x' + (BLOCK_TS - 10000).toString(16), hash: HASH } }) }); ok(stale.status === 'ALERT' && stale.alerts.some((a) => a.code === 'RPC_STALE'), 'a stale latest block is RPC_STALE');
  const fut = await check({ [U.p]: handlerOf({ block: { number: '0x10', timestamp: '0x' + (BLOCK_TS + 100000).toString(16), hash: HASH } }) }); ok(fut.status === 'ALERT' && fut.alerts.some((a) => a.code === 'RPC_BLOCK_INVALID'), 'a future block is RPC_BLOCK_INVALID');
  const reorg = await check({ [U.p]: handlerOf({ alternate: true }), [U.f]: handlerOf({ alternate: true }) }); ok(reorg.status === 'ALERT' && reorg.alerts.some((a) => a.code === 'RPC_UNAVAILABLE'), 'a hash that keeps changing is an alert, never a snapshot');
  const slow = await check({ [U.p]: () => new Promise(() => {}), [U.f]: () => new Promise(() => {}) }, { readTimeoutS: 5 }); ok(slow.status === 'ALERT' && slow.alerts.some((a) => a.code === 'RPC_TIMEOUT'), 'a read that never answers is RPC_TIMEOUT after the bound');
  const badcfg = await chainOnlyCheck({ config: { desk: 'x' }, now, fetchImpl: server({}).f, sleep: sleepNone }); ok(badcfg.status === 'ALERT' && badcfg.alerts[0].code === 'CONFIG_INVALID', 'a bad config is CONFIG_INVALID');
  const noclock = await chainOnlyCheck({ config: { desk: DESK }, now: () => NaN, fetchImpl: server({}).f, sleep: sleepNone }); ok(noclock.status === 'ALERT', 'a broken clock is an alert');
  const thrower = await chainOnlyCheck({ config: { desk: DESK }, now: () => { throw new Error('x'); }, fetchImpl: server({}).f, sleep: sleepNone }); ok(thrower.status === 'ALERT' && thrower.alerts[0].code === 'COLLECTOR_FAILURE', 'a throwing clock is COLLECTOR_FAILURE, not a throw');
  for (const o of [r, old, both, fb, stale, fut, slow, reorg, young]) { const s = JSON.stringify(o); ok(!s.includes(U.p) && !s.includes(U.f) && !s.includes(DESK) && !s.includes(A1.slice(2)), 'no endpoint URL, desk address or applicant address in the outcome'); } }

// ---- the message that may leave ----
const okOutcome = await check({ [U.p]: handlerOf({}) });
{
  const chk = await check({ [U.p]: handlerOf({ pending: S.pending.one, threads: { [A1]: S.thread.staleFirstFreshFollowup } }) });
  ok(chk.status === 'ALERT' && chk.alerts.some((a) => a.code === 'PENDING_AGE') && chk.health.oldestPendingAgeS === 1207, 'end to end: the stalled demo with a follow-up message alerts PENDING_AGE with its true wait');
}
const m1 = boardMessage({ outcome: okOutcome, nowMs: NOWMS, idSuffix: '202611141200' });
ok(m1.i[0].op === 'ok' && /^Officer chain monitor OK: block 14790903, pending 0, oldest pending unknown s, reader primary, at 2026-11-14T07:42:42\.000Z\. chain symptoms only/.test(m1.i[0].x) && m1.id === 'm-officer-chain-monitor-202611141200', 'the OK message has the fixed text, with unknown for the age of an empty queue');
ok(validateBoardComment(boardComment(m1)).ok, 'the OK message validates');
{ const al = await check({ [U.p]: handlerOf({ pending: S.pending.one, threads: { [A1]: S.thread.ask } }) }); const m = boardMessage({ outcome: al, nowMs: NOWMS, idSuffix: '202611141200' });
  ok(m.i[0].op === 'alert' && /\(PENDING_AGE\)/.test(m.i[0].x) && validateBoardComment(boardComment(m)).ok, 'an alert message names its code and validates');
  const none = boardMessage({ outcome: await check({}), nowMs: NOWMS, idSuffix: '202611141200' }); ok(/\(RPC_UNAVAILABLE\)/.test(none.i[0].x) && /reader none/.test(none.i[0].x) && /block unknown, pending unknown/.test(none.i[0].x) && validateBoardComment(boardComment(none)).ok, 'an unreachable-chain message uses unknown and none, and validates'); }
{ const hostile = boardMessage({ outcome: { status: 'OK', alerts: [], outbound: { alerts: [{ code: 'EVIL SECRET' }] }, health: { endpoint: 'https://secret.example', blockNumber: -5, pendingCount: '9; DROP', oldestPendingAgeS: 1e300 } }, nowMs: 1e300, idSuffix: 'SECRET' });
  ok(!JSON.stringify(hostile).includes('SECRET') && !JSON.stringify(hostile).includes('secret.example') && !JSON.stringify(hostile).includes('DROP') && validateBoardComment(boardComment(hostile)).ok && hostile.i[0].op === 'alert', 'hostile values in the outcome never reach the message; an inconsistent OK with alert codes becomes an ALERT');
  for (const un of [undefined, null, 5, 'x', {}, { status: 'WEIRD' }]) { const m = boardMessage({ outcome: un, nowMs: NOWMS }); ok(m.i[0].op === 'alert' && /\(UNUSABLE_RESULT\)/.test(m.i[0].x) && validateBoardComment(boardComment(m)).ok, `an unusable outcome (${JSON.stringify(un)}) is an ALERT message naming UNUSABLE_RESULT, never OK`); } }
{ const good = boardComment(m1); const v = (b) => validateBoardComment(b);
  const tampered = [['text changed', good.replace('chain symptoms only', 'all is fine')], ['extra key', good.replace('"v":2', '"v":2,"z":1')], ['URL in text', good.replace('reader primary', 'reader https://x.example')], ['address in text', good.replace('pending 0', 'pending 0x1111111111111111111111111111111111111111')], ['status and op disagree', good.replace('"op":"ok"', '"op":"alert"')], ['unknown code', good.replace('monitor OK:', 'monitor ALERT (EVIL):').replace('"op":"ok"', '"op":"alert"')], ['OK with a code', good.replace('monitor OK:', 'monitor OK (PENDING_AGE):')], ['newline injected', good.replace('block ', 'block\\n')], ['footer changed', good.replace(FOOTER, '_something else_')], ['no footer', good.replace(/---\n.*\n$/s, '')], ['wrong kind', good.replace('"k":"health"', '"k":"ans"')], ['wrong id', good.replace(/m-officer-chain-monitor-\d+/, 'x-1')], ['two items', good.replace('"i":[', '"i":[{"w":"a","op":"ok","x":"y"},')], ['padding', good + 'x'.repeat(3000)], ['trailing text', good + 'hello'], ['not a string', null], ['wrong tr', good.replace('gh:board-default', 'other')]];
  for (const [n, b] of tampered) ok(v(b).ok === false, `validator refuses: ${n}`);
  const dupX = good.replace('"x":"', '"x":"FREE TEXT LEAK","x":"'); const dupW = good.replace('"w":"officer-chain-monitor"', '"w":"FREE TEXT","w":"officer-chain-monitor"'); const esc = good.replace('"op":', '"o\\u0070":'); const spaced = good.replace('"v":2,', '"v": 2,');
  ok(v(dupX).ok === false && v(dupX).why === 'NOT_CANONICAL' && v(dupW).ok === false && v(esc).ok === false && v(spaced).ok === false, 'regression: duplicate x, duplicate w, an escaped key and non-canonical spacing are refused (the posted bytes must equal the validated bytes)');
  ok(v(good.replace(/\n$/, '')).ok === false, 'a missing final newline is refused, as posted bytes must match');
  ok(v(good).ok, 'control: the untouched message validates'); }

// ---- runOnce and the CLIs ----
{ const r = await runOnce({ config: { desk: DESK }, now, fetchImpl: server({ [U.p]: handlerOf({}) }).f, sleep: sleepNone }); ok(r.exitCode === 0 && r.body && validateBoardComment(r.body).ok, 'runOnce healthy: exit 0 with a valid body');
  const a = await runOnce({ config: { desk: DESK, readTimeoutS: 5 }, now, fetchImpl: server({}).f, sleep: sleepNone }); ok(a.exitCode === 2 && a.body && /RPC_UNAVAILABLE/.test(a.body), 'runOnce unreachable chain: exit 2 with an alert body');
  const c = await runOnce({ config: { desk: 'bad' }, now, fetchImpl: server({}).f, sleep: sleepNone }); ok(c.exitCode === 3, 'runOnce bad config: exit 3');
  { const far = await runOnce({ config: { desk: DESK, readTimeoutS: 5 }, now: () => 8.64e15, fetchImpl: server({ [U.p]: handlerOf({}) }).f, sleep: sleepNone });
    ok(far.validation.ok === false && far.exitCode === 3 && far.body === null, 'regression: when the message fails its own validation (a year outside four digits) the exit code is 3 and nothing is printed');
    let printed = 'unset'; const codeFar = await cliMain(['node', 'x', 'cfg.json'], { readFile: () => JSON.stringify({ desk: DESK, readTimeoutS: 5 }), fetchImpl: server({ [U.p]: handlerOf({}) }).f, now: () => 8.64e15, sleep: sleepNone, write: (s) => { printed = s; } });
    ok(codeFar === 3 && printed === '', 'the CLI prints nothing and exits 3 when the message does not validate'); }
  let out = ''; const code = await cliMain(['node', 'x', 'cfg.json'], { readFile: () => JSON.stringify({ desk: DESK }), fetchImpl: server({ [U.p]: handlerOf({}) }).f, now, sleep: sleepNone, write: (s) => { out += s; } }); ok(code === 0 && validateBoardComment(out).ok, 'the CLI prints only the validated comment');
  let out2 = 'unset'; const code2 = await cliMain(['node', 'x', 'missing.json'], { readFile: () => { throw new Error('ENOENT'); }, fetchImpl: server({}).f, now, sleep: sleepNone, write: (s) => { out2 = s; } }); ok(code2 === 3, 'a missing or unreadable config file is exit 3');
  ok(validateMain(['n', 'x', 'f'], () => boardComment(m1)) === 0 && validateMain(['n', 'x', 'f'], () => 'hello') === 1 && validateMain(['n', 'x', 'f'], () => { throw new Error('x'); }) === 1, 'the sender-side gate exits 0 only for the exact comment'); }

// ---- the draft workflow stays inactive and least-privilege ----
{ const wf = readFileSync(join(here, 'draft-workflow', 'officer-chain-monitor.yml'), 'utf8');
  ok(here.split('/').includes('experiments') && !here.includes('.github'), 'the draft lives under experiments, not in .github/workflows');
  const jobs = [...wf.matchAll(/^  (snapshot|send):\n((?:    .*\n)+)/gm)];
  ok(jobs.length === 2 && jobs.every((j) => /^    if: \$\{\{ false \}\}$/m.test(j[2])), 'every job is disabled with if: false');
  ok(/^permissions: \{\}$/m.test(wf) && /contents: read/.test(jobs[0][2]) && !/issues: write|contents: write|id-token|actions: write/.test(jobs[0][2]), 'the snapshot job has contents: read only');
  ok(/issues: write/.test(jobs[1][2]) && !/contents: write/.test(jobs[1][2]), 'only the isolated sender has issues: write');
  ok(!/secrets\.(?!GITHUB_TOKEN)/.test(wf) && !/pull_request|issue_comment|workflow_run|push:/.test(wf.replace(/#.*$/gm, '')), 'no secret other than the repository token and no untrusted-event trigger');
  ok(/concurrency:/.test(wf) && (wf.match(/timeout-minutes: 5/g) || []).length === 2 && /persist-credentials: false/.test(wf), 'concurrency, timeouts and no persisted credentials');
  ok(/validate-comment\.mjs/.test(wf) && wf.indexOf('validate-comment.mjs') < wf.indexOf('gh api'), 'the sender validates before it posts');
  ok(!/\|\| true/.test(wf) && /exit "\$code"/.test(wf) && /-ne 2/.test(wf), 'regression: no || true; only exit 0 and the ALERT exit 2 continue, any other exit fails the job visibly');
  ok(/jq -Rs '\{body: \.\}' status-comment\.md \| gh api/.test(wf) && !/-f body=/.test(wf), 'regression: the exact validated bytes are posted (no command substitution that strips the final newline)'); }

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
