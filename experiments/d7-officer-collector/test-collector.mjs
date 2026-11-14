// Offline tests for the collector, alert state and watchdog. Run: node test-collector.mjs (exit 0 only if every check passes).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { collectOnce, parseLog, parseConfig, gitBlobSha, sanitize, toOutbound, OUTBOUND_DETAIL, ALLOWED_FIELDS, COLLECTOR_RANGES, COLLECTOR_DEFAULTS } from './collector.mjs';
import { newState, step, toSend, ack, inspectState } from './alertstate.mjs';
import { checkWatchdog } from './watchdog.mjs';
import { serializeDelivery, MAX_CODES, MAX_RAW } from './delivery.mjs';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) pass++; else { fail++; console.log('FAIL', n); } };
const here = dirname(fileURLToPath(import.meta.url));
const fx = (n) => readFileSync(join(here, 'fixtures', n), 'utf8');
const NOW = Date.parse('2026-12-01T12:00:00Z');
const FILE = Buffer.from('// stand-in for the pinned daemon file\n');
const SHA = gitBlobSha(FILE);
const cfg = { runtimeSha: SHA, heartbeatS: 300, pendingBudgetS: 600 };
const blk = (o = {}) => ({ readAtMs: NOW, blockNumber: 1000, blockTimeMs: NOW - 5000, pendingBlockNumber: 1000, ...o });
const emptyQ = async () => ({ pending: [], ...blk() });
const run = (o = {}) => collectOnce({ logText: fx('healthy.jsonl'), nowMs: NOW, config: cfg, fileBytes: FILE, fetchPending: emptyQ, ...o });
const codes = (r) => r.alerts.map((a) => a.code).sort();
const has = (r, c) => codes(r).includes(c);

// ---- identity function ----
ok(gitBlobSha('hello\n') === 'ce013625030ba8dba906f756967f9e9ca394464a', 'gitBlobSha matches git hash-object for hello');
ok(gitBlobSha('') === 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391', 'gitBlobSha of the empty file');
ok(/^[0-9a-f]{40}$/.test(SHA), 'sha is 40 lowercase hex');

// ---- privacy: only allowlisted fields leave; private data never appears ----
const h = parseLog(fx('healthy.jsonl'));
ok(h.ok && h.events.length === 8 && h.dropped === 1 && h.malformed === 0, 'healthy log: 8 events kept, the replied event dropped');
const dump = JSON.stringify(h.events);
for (const bad of ['PRIVATE APPLICANT TEXT', 'KEY_SHOULD_NOT_LEAVE', 'rpc.example', '0xaaaa', '0xbbbb', 'applicant', '"desk"', '"officer"', '"rpc"', '"tx"']) ok(!dump.includes(bad), `private value not forwarded: ${bad}`);
ok(h.events.find((e) => e.ev === 'start').mode === 'claude' && Object.keys(h.events.find((e) => e.ev === 'start')).sort().join() === 'ev,mode,t', 'start keeps only mode');
ok(sanitize({ t: '2026-12-01T00:00:00Z', ev: 'replied', reply: 'secret' }) === null, 'unknown or private event dropped');
ok(sanitize({ t: '2026-12-01T00:00:00Z', ev: 'model-unavailable', applicant: '0x1', why: 'timeout' }).applicant === undefined, 'model-unavailable loses applicant');
ok(sanitize({ t: '2026-12-01T00:00:00Z', ev: 'heartbeat', lastPollOkAgeS: 5, secret: 'z' }).secret === undefined, 'unlisted heartbeat field dropped');
{ const T0 = '2026-12-01T00:00:00Z';
  const e1 = sanitize({ t: T0, ev: 'exit', reason: 'fetch failed https://rpc.example.org/v2/SECRETKEY123', uptimeS: 5 });
  ok(e1.reason === 'other' && !JSON.stringify(e1).includes('SECRETKEY123'), 'regression: a URL-bearing exit reason becomes other');
  ok(sanitize({ t: T0, ev: 'exit', reason: 'signal' }).reason === 'signal' && sanitize({ t: T0, ev: 'exit', reason: 'uncaught' }).reason === 'uncaught', 'known exit reasons pass');
  ok(sanitize({ t: T0, ev: 'exit', reason: { a: 1 } }).reason === 'other' && sanitize({ t: T0, ev: 'exit', reason: ['x'] }).reason === 'other', 'object or array reasons become other');
  ok(sanitize({ t: T0, ev: 'state-unreadable', why: 'bad-schema' }).why === 'bad-schema' && sanitize({ t: T0, ev: 'state-unreadable', why: 'my secret detail' }).why === 'other', 'state-unreadable why is a closed list');
  ok(sanitize({ t: T0, ev: 'start', mode: 'claude' }).mode === 'claude' && sanitize({ t: T0, ev: 'start', mode: 'KEY=abc' }).mode === 'other', 'start mode is a closed list');
  const hb = sanitize({ t: T0, ev: 'heartbeat', held: { applicant: '0x1', reply: 'secret' }, uptimeS: [1, 2], lastPollOkAgeS: 'x', pollOk: Infinity, handled: 3 });
  ok(hb.held === null && hb.uptimeS === null && hb.lastPollOkAgeS === null && hb.pollOk === null && hb.handled === 3, 'regression: non-number values of numeric fields become null, finite numbers pass');
  ok(!JSON.stringify(hb).includes('secret') && !JSON.stringify(hb).includes('0x1'), 'no object content survives in a numeric field');
  ok(sanitize({ t: 'Dec 1 2026 SECRET-TEXT', ev: 'heartbeat' }) === null && sanitize({ t: 'x', ev: 'heartbeat' }) === null && sanitize(null) === null && sanitize({ ev: 'heartbeat' }) === null, 'an unparseable or missing time is dropped, never forwarded, and sanitize does not throw');
  ok(sanitize({ t: '2026-12-01T00:00:00+02:00', ev: 'heartbeat' }).t === '2026-11-30T22:00:00.000Z', 'the time is re-serialised in UTC, never forwarded as given');
  ok(sanitize({ t: T0, ev: '__proto__' }) === null && sanitize({ t: T0, ev: 'constructor' }) === null && sanitize({ t: T0, ev: 'toString' }) === null, 'inherited names are not events'); }
ok(JSON.stringify(Object.keys(ALLOWED_FIELDS).sort()) === JSON.stringify(['earlier-reply-settled', 'earlier-reply-stuck', 'exit', 'heartbeat', 'model-unavailable', 'poll-error', 'send-ambiguous', 'start', 'state-unreadable', 'state-write-error']), 'allowlisted event names pinned');
const schema = JSON.parse(fx('emitter-schema.json'));
for (const [ev, f] of Object.entries(ALLOWED_FIELDS)) ok(JSON.stringify([...f].sort()) === JSON.stringify([...schema.events[ev].forward].sort()), `schema file and code agree on forwarded fields of ${ev}`);

// ---- log shape: partial tail, truncated head, empty, unreadable, malformed ----
const pt = parseLog(fx('partial-tail.jsonl'));
ok(pt.ok && pt.partialTail === true && pt.malformed === 0 && pt.events.length === 3, 'partial last line is dropped, not counted as malformed, earlier lines kept');
ok(!parseLog(fx('healthy.jsonl')).partialTail, 'complete log has no partial tail');
const filler = (JSON.stringify({ t: '2026-12-01T10:00:00.000Z', ev: 'heartbeat', uptimeS: 1, lastPollOkAgeS: 1, held: 0 }) + '\n').repeat(60); // valid lines, so only a cut line could be malformed
const big = filler + fx('healthy.jsonl'); // far more than 4096 bytes
const tr = parseLog(big, { maxChars: 4096 });
ok(tr.truncatedHead === true && tr.ok, 'a log larger than the tail bound is read from its tail');
ok(tr.malformed === 0, 'the cut line at the head of the tail is dropped, not counted as malformed or trusted');
ok(tr.events.every((e) => typeof e.ev === 'string'), 'tail read yields only valid events');
ok(parseLog('').ok && parseLog('').events.length === 0, 'empty log is readable and has no events');
ok(parseLog(undefined).ok === false && parseLog(null).ok === false && parseLog(42).ok === false, 'non-string log is LOG_UNREADABLE');
ok(parseLog(fx('malformed.jsonl')).malformed === 2, 'two malformed lines counted');
ok(parseLog('{"t":"not a time","ev":"heartbeat"}\n').malformed === 1, 'bad time is malformed');
ok(parseLog('[1,2]\nnull\n"x"\n').malformed === 3, 'non-object lines are malformed');

// ---- the healthy path and each distinct failure ----
const good = await run();
ok(good.status === 'OK' && good.alerts.length === 0, `healthy run is OK (${JSON.stringify(codes(good))})`);
ok(good.collectorRun.status === 'ok' && good.collectorRun.at === '2026-12-01T12:00:00.000Z', 'run record written with time and ok');
ok(has(await run({ logText: fx('malformed.jsonl') }), 'LOG_MALFORMED'), 'malformed lines raise LOG_MALFORMED');
ok(has(await run({ logText: undefined }), 'LOG_UNREADABLE') && has(await run({ logText: undefined }), 'HEARTBEAT_MISSING'), 'missing log is LOG_UNREADABLE and no heartbeat');
ok(has(await run({ logText: '' }), 'HEARTBEAT_MISSING'), 'an empty log (just rotated) alerts until the next heartbeat');
ok((await run({ logText: fx('rotated-new-file.jsonl') })).status === 'OK', 'a fresh rotated file with a recent start and heartbeat is healthy');
ok((await run({ logText: fx('partial-tail.jsonl') })).status === 'OK', 'a partial last line does not by itself alert');
// restart identity and duplicate runner
ok(has(await run({ logText: fx('duplicate-runner.jsonl') }), 'DUPLICATE_RUNNER'), 'old process still heartbeating after a fresh start: DUPLICATE_RUNNER');
ok(has(await run({ logText: fx('restart-loop.jsonl') }), 'RESTART_LOOP'), 'five starts in an hour: RESTART_LOOP');
ok(has(await run({ logText: fx('exited.jsonl') }), 'PROCESS_EXITED'), 'exit event after the last start: PROCESS_EXITED');
const exitThenStart = fx('exited.jsonl') + JSON.stringify({ t: '2026-12-01T11:56:00.000Z', ev: 'start', mode: 'claude' }) + '\n' + JSON.stringify({ t: '2026-12-01T11:59:00.000Z', ev: 'heartbeat', uptimeS: 180, lastPollOkAgeS: 10, held: 0 }) + '\n';
ok(!has(await run({ logText: exitThenStart }), 'PROCESS_EXITED'), 'a later start clears an earlier exit');
ok(!has(await run({ logText: fx('rotated-new-file.jsonl') }), 'DUPLICATE_RUNNER'), 'no duplicate alert for a normal fresh start');
{ const T = (ago) => new Date(NOW - ago * 1000).toISOString();
  const L = (...x) => x.map((o) => JSON.stringify(o)).join('\n') + '\n';
  const dec = L({ t: T(600), ev: 'start', mode: 'claude' }, { t: T(500), ev: 'heartbeat', uptimeS: 100, lastPollOkAgeS: 5, held: 0 }, { t: T(400), ev: 'heartbeat', uptimeS: 40, lastPollOkAgeS: 5, held: 0 }, { t: T(60), ev: 'heartbeat', uptimeS: 540, lastPollOkAgeS: 5, held: 0 });
  ok(has(await run({ logText: dec }), 'DUPLICATE_RUNNER'), 'uptime going backwards between heartbeats of one run: DUPLICATE_RUNNER even when the last beat looks consistent');
  const inc = L({ t: T(600), ev: 'start', mode: 'claude' }, { t: T(500), ev: 'heartbeat', uptimeS: 100, lastPollOkAgeS: 5, held: 0 }, { t: T(60), ev: 'heartbeat', uptimeS: 540, lastPollOkAgeS: 5, held: 0 });
  ok(!has(await run({ logText: inc }), 'DUPLICATE_RUNNER'), 'control: increasing uptime is not a duplicate'); }
// exact runtime identity
ok(has(await run({ fileBytes: Buffer.from('another file') }), 'RUNTIME_HASH_MISMATCH'), 'a different daemon file alerts');
ok(has(await run({ fileBytes: undefined }), 'RUNTIME_HASH_MISMATCH'), 'unreported runtime file alerts');
ok(!has(await run(), 'RUNTIME_HASH_MISMATCH'), 'the exact file matches');
// chain read: unavailable, stale, unbound, malformed and slow reads never become an empty queue
const bad = (f, c, n) => run({ fetchPending: f }).then((r) => { ok(has(r, c) && has(r, 'PENDING_UNREADABLE') && r.status === 'ALERT', `${n}: ${c} and the observer sees an unread queue`); });
await bad(async () => { throw new Error('connect ECONNREFUSED'); }, 'RPC_UNAVAILABLE', 'rpc throws');
await bad(async () => undefined, 'RPC_UNAVAILABLE', 'rpc returns nothing');
await bad(async () => ({ ...blk() }), 'RPC_UNAVAILABLE', 'rpc returns no pending list');
await bad(async () => ({ pending: null, ...blk() }), 'RPC_UNAVAILABLE', 'pending is null, not empty');
await bad(async () => ({ pending: [], ...blk({ readAtMs: 'now' }) }), 'RPC_UNAVAILABLE', 'readAt is not a number');
await bad(async () => ({ pending: [{}], ...blk() }), 'RPC_UNAVAILABLE', 'entry without a request time');
await bad(async () => ({ pending: [{ requestedAtMs: NOW + 9e6 }], ...blk({ blockTimeMs: NOW - 1000 }) }), 'RPC_BLOCK_MISMATCH', 'entry dated after the evidenced block');
await bad(async () => ({ pending: [], ...blk({ blockTimeMs: NOW - 301000 }) }), 'RPC_STALE', 'latest block 301 s old');
await bad(async () => ({ pending: [], ...blk({ blockTimeMs: Number.NaN }) }), 'RPC_BLOCK_INVALID', 'block time NaN');
// block evidence is required and bounded (missing, future, stale regressions) with a healthy control
await bad(async () => ({ pending: [], readAtMs: NOW - 1000, blockNumber: 1000, pendingBlockNumber: 1000 }), 'RPC_BLOCK_INVALID', 'regression: blockTimeMs omitted');
await bad(async () => ({ pending: [], ...blk({ blockTimeMs: undefined }) }), 'RPC_BLOCK_INVALID', 'blockTimeMs undefined');
await bad(async () => ({ pending: [], ...blk({ blockTimeMs: NOW + 10 * 86400000 }) }), 'RPC_BLOCK_INVALID', 'regression: block time 10 days in the future');
await bad(async () => ({ pending: [], ...blk({ blockTimeMs: NOW + 61000 }) }), 'RPC_BLOCK_INVALID', 'block time 61 s ahead exceeds the skew bound');
await bad(async () => ({ pending: [], ...blk({ blockNumber: undefined }) }), 'RPC_BLOCK_INVALID', 'block number omitted');
await bad(async () => ({ pending: [], ...blk({ blockNumber: -1, pendingBlockNumber: -1 }) }), 'RPC_BLOCK_INVALID', 'negative block number');
await bad(async () => ({ pending: [], ...blk({ blockNumber: 1000.5, pendingBlockNumber: 1000.5 }) }), 'RPC_BLOCK_INVALID', 'fractional block number');
await bad(async () => ({ pending: [], ...blk({ pendingBlockNumber: 999 }) }), 'RPC_BLOCK_MISMATCH', 'queue read at a different block');
await bad(async () => ({ pending: [], ...blk({ pendingBlockNumber: undefined }) }), 'RPC_BLOCK_MISMATCH', 'queue block number omitted');
await bad(async () => ({ pending: [], ...blk({ readAtMs: NOW - 120000 }) }), 'RPC_BLOCK_INVALID', 'read time far from now');
ok((await run({ fetchPending: async () => ({ pending: [], ...blk({ blockTimeMs: NOW + 30000 }) }) })).status === 'OK', 'control: 30 s of block-time skew is tolerated');
ok((await run({ fetchPending: async () => ({ pending: [], ...blk({ blockTimeMs: NOW - 300000 }) }) })).status === 'OK', 'control: a block exactly at the stale bound is accepted');
ok((await run({ fetchPending: async () => ({ pending: [], ...blk({ blockTimeMs: NOW - 4000, readAtMs: NOW - 59000 }) }) })).status === 'OK', 'control: a read 59 s from now is inside the skew bound');
{ const r = await run({ config: { ...cfg, rpcTimeoutS: 1 }, fetchPending: () => new Promise(() => {}) });
  ok(has(r, 'RPC_TIMEOUT') && has(r, 'PENDING_UNREADABLE') && r.status === 'ALERT', 'a read that never answers is RPC_TIMEOUT after the bound, never an empty queue'); }
ok((await run({ fetchPending: async () => ({ pending: [], readAtMs: NOW }) })).status === 'ALERT', 'an empty list with no block evidence is no longer a successful read');
ok((await run()).status === 'OK', 'healthy control: explicit empty list with bound, fresh block evidence is OK');
ok(has(await run({ fetchPending: async () => ({ pending: [{ requestedAtMs: NOW - 700000 }], ...blk() }) }), 'PENDING_AGE'), 'a 700 s old pending request alerts PENDING_AGE');
ok((await run({ fetchPending: async () => ({ pending: [{ requestedAtMs: NOW - 100000 }], ...blk() }) })).status === 'OK', 'a 100 s old pending request is inside the budget');
ok(has(await run({ fetchPending: undefined }), 'RPC_UNAVAILABLE'), 'no chain reader supplied is RPC_UNAVAILABLE');
{ const many = Array.from({ length: 200000 }, (_, i) => ({ requestedAtMs: NOW - 1000 - i * 10 })); const r = await run({ fetchPending: async () => ({ pending: many, ...blk() }) });
  ok(!has(r, 'COLLECTOR_FAILURE') && has(r, 'PENDING_AGE'), 'regression: a 200,000-entry pending list does not overflow the stack and still alerts on its real age'); }

// ---- config boundary ----
const cc = async (c) => codes(await run({ config: c }));
ok((await cc({ ...cfg, graceBeat: 1 })).join() === 'CONFIG_INVALID', 'regression: unknown key graceBeat is CONFIG_INVALID, not a silent default');
ok(!JSON.stringify(await run({ config: { ...cfg, graceBeat: 1, 'SECRETKEY-abc': 1 } })).includes('SECRETKEY') && !JSON.stringify(await run({ config: { ...cfg, graceBeat: 1 } })).includes('graceBeat'), 'regression: unknown key names are counted, never echoed');
ok((await cc(Object.create(cfg))).join() === 'CONFIG_INVALID', 'inherited properties are rejected');
ok((await cc([cfg])).join() === 'CONFIG_INVALID' && (await cc(null)).join() === 'CONFIG_INVALID' && (await cc(undefined)).join() === 'CONFIG_INVALID' && (await cc('x')).join() === 'CONFIG_INVALID', 'non-object config rejected');
ok((await cc({ ...cfg, runtimeSha: SHA.slice(0, 8) })).join() === 'CONFIG_INVALID', 'a short sha prefix is rejected');
ok((await cc({ ...cfg, runtimeSha: SHA.toUpperCase() })).join() === 'CONFIG_INVALID', 'an uppercase sha is rejected');
ok((await cc({ heartbeatS: 300, pendingBudgetS: 600 })).join() === 'CONFIG_INVALID', 'runtimeSha missing is CONFIG_INVALID');
ok(Object.keys(parseConfig(Object.assign(Object.create(null), cfg))).includes('ok') && parseConfig(Object.assign(Object.create(null), cfg)).ok, 'a null-prototype plain object is accepted');
ok((await cc({ ...cfg, heartbeatS: 5 })).join() === 'CONFIG_INVALID', 'observer ranges still apply through the collector');
const EXPECTED = { logTailChars: [4096, 16777216, true], rpcTimeoutS: [1, 120], staleBlockS: [30, 3600], restartMax: [1, 20, true], restartWindowS: [60, 86400] };
ok(JSON.stringify(COLLECTOR_RANGES) === JSON.stringify(EXPECTED) && COLLECTOR_DEFAULTS.rpcTimeoutS === 20, 'collector range table pinned');
for (const [k, [lo, hi, int]] of Object.entries(EXPECTED)) {
  ok(parseConfig({ ...cfg, [k]: lo }).ok, `${k} min accepted`); ok(parseConfig({ ...cfg, [k]: hi }).ok, `${k} max accepted`);
  ok(!parseConfig({ ...cfg, [k]: lo - (int ? 1 : 0.5) }).ok, `${k} below min rejected`); ok(!parseConfig({ ...cfg, [k]: hi + (int ? 1 : 1) }).ok, `${k} above max rejected`);
  for (const v of [null, 'x', Number.NaN, Infinity]) ok(!parseConfig({ ...cfg, [k]: v }).ok, `${k} = ${String(v)} rejected`);
}
ok(!parseConfig({ ...cfg, restartMax: 2.5 }).ok, 'fractional restartMax rejected');

// ---- the collector itself failing ----
ok(await collectOnce({ get logText() { throw new TypeError('boom'); }, nowMs: NOW, config: cfg, fileBytes: FILE, fetchPending: emptyQ }).then((r) => codes(r).join() === 'COLLECTOR_FAILURE' && r.collectorRun.status === 'crashed'), 'an internal throw is COLLECTOR_FAILURE with a crashed run record');
ok(await collectOnce(undefined).then((r) => r.status === 'ALERT' && r.collectorRun.status === 'crashed'), 'no input at all is an alert, not a throw');
ok(await collectOnce({ nowMs: Number.NaN }).then((r) => r.status === 'ALERT' && r.collectorRun.at === null), 'nowMs NaN is an alert with no timestamp');
ok(await collectOnce({ nowMs: 1e20, config: cfg }).then((r) => r.status === 'ALERT'), 'an unusable timestamp is an alert');

// ---- alert state: typed results, unique persisted occurrence keys, dedup, retry, recovery ----
const A = { status: 'ALERT', alerts: [{ code: 'HEARTBEAT_MISSING' }] }, B = { status: 'ALERT', alerts: [{ code: 'RPC_STALE' }, { code: 'PENDING_UNREADABLE' }] }, OK = { status: 'OK', alerts: [] };
const T = 1e12;
const st = (r) => { if (!r.ok) throw new Error(`step failed: ${r.error}`); return r.state; };
const items = (s) => { const r = toSend(s); if (!r.ok) throw new Error('toSend failed'); return r.items; };
const kinds = (s) => items(s).map((x) => x.kind).join();
let s = newState();
s = st(step(s, OK, T)); ok(items(s).length === 0 && s.status === 'OK', 'healthy start sends nothing');
const s0 = JSON.stringify(s); step(s, A, T + 1000); ok(JSON.stringify(s) === s0, 'step does not mutate its input');
s = st(step(s, A, T + 60000)); ok(items(s).length === 1 && items(s)[0].kind === 'alert' && items(s)[0].codes.join() === 'HEARTBEAT_MISSING', 'first failure queues exactly one alert');
const k1 = items(s)[0].key;
s = st(step(s, A, T + 120000)); s = st(step(s, A, T + 180000)); ok(items(s).length === 1 && items(s)[0].key === k1, 'an undelivered alert stays queued once and keeps ONE key across all retries');
s = st(ack(s, k1)); ok(items(s).length === 0, 'an acknowledged alert is removed');
s = st(step(s, A, T + 240000)); ok(items(s).length === 0, 'the same failure after delivery is deduplicated');
s = st(step(s, B, T + 300000)); ok(items(s).length === 1 && items(s)[0].kind === 'alert' && items(s)[0].codes.join() === 'PENDING_UNREADABLE,RPC_STALE', 'a changed code set queues a new alert');
const k2 = items(s)[0].key; s = st(ack(s, k2));
s = st(step(s, A, T + 360000)); const k3 = items(s)[0].key; s = st(ack(s, k3));
ok(new Set([k1, k2, k3]).size === 3, `regression: A to B to A (each delivered) gives three distinct occurrence keys (${k1}, ${k2}, ${k3})`);
s = st(step(s, A, T + 360000 + 3500 * 1000)); ok(items(s).length === 0, 'no repeat before the repeat interval');
const rkeys = [];
for (let i = 1; i <= 3; i++) { s = st(step(s, A, T + 360000 + i * 3600 * 1000)); const it = items(s); ok(it.length === 1 && it[0].kind === 'repeat', `repeat ${i} queued once`); rkeys.push(it[0].key); s = st(ack(s, it[0].key)); }
ok(new Set(rkeys).size === 3 && !rkeys.includes(k1), `regression: three scheduled repeats have distinct keys (${rkeys.join(', ')})`);
{ const u1 = st(step(s, A, T + 360000 + 4 * 3600 * 1000)), u2 = st(step(u1, A, T + 360000 + 5 * 3600 * 1000)), u3 = st(step(u2, A, T + 360000 + 9 * 3600 * 1000));
  ok(items(u3).filter((x) => x.kind === 'repeat').length === 1, 'an undelivered repeat is not queued again at later intervals (no pile-up while delivery is failing)'); }
// persisted counters: the state survives a JSON round trip and a restart without reusing a key
{ const allKeys = [k1, k2, k3, ...rkeys]; let r = JSON.parse(JSON.stringify(s)); r = st(step(r, B, T + 5e7)); const nk = items(r)[0].key; ok(!allKeys.includes(nk), 'after a restart (state reloaded from JSON) the next key is new'); }
// several events at the same clock tick still get distinct keys
{ let q = newState(); const seen = []; for (const res of [A, OK, OK, A, OK, OK, B, OK, OK]) { q = st(step(q, res, T)); for (const it of items(q)) { seen.push(it.key); q = st(ack(q, it.key)); } } ok(seen.length >= 3 && new Set(seen).size === seen.length, `many events at the same tick: all keys distinct (${seen.join(', ')})`); }
// recovery
s = newState(); s = st(step(s, B, T)); s = st(ack(s, items(s)[0].key));
s = st(step(s, OK, T + 60000)); ok(s.status === 'ALERT' && items(s).length === 0, 'one healthy run is not yet a recovery');
s = st(step(s, B, T + 120000)); s = st(step(s, OK, T + 180000)); ok(s.status === 'ALERT' && items(s).length === 0, 'a flap (alert, ok) resets the recovery count');
s = st(step(s, OK, T + 240000)); ok(s.status === 'OK' && kinds(s) === 'recovery', 'two consecutive healthy runs queue one recovery');
s = st(step(s, OK, T + 300000)); ok(items(s).length === 1, 'recovery stays queued until delivered, not duplicated');
s = st(ack(s, items(s)[0].key)); ok(items(s).length === 0 && s.status === 'OK', 'delivered recovery clears the queue');
for (const unusable of [null, undefined, { status: 'ALERT', alerts: [] }, { status: 'OK' }, { alerts: [] }, 'x', { status: 'OK', alerts: 'no' }]) { const u = st(step(newState(), unusable, T)); ok(u.status === 'ALERT' && items(u).length === 1, `an unusable result (${JSON.stringify(unusable)}) is a failure, not a quiet OK`); }
{ let u = st(step(newState(), null, T)); u = st(step(u, OK, T + 1000)); u = st(step(u, OK, T + 2000)); ok(items(u).some((x) => x.kind === 'recovery'), 'recovery after an unusable-result alert needs two OKs'); }
// invalid parameters: a typed failure, never a throw
for (const [name, args] of [['nowMs NaN', [NaN]], ['repeatEveryS 0', [T, { repeatEveryS: 0 }]], ['recoveryOks 0', [T, { recoveryOks: 0 }]], ['recoveryOks 1.5', [T, { recoveryOks: 1.5 }]]]) { let r, threw = false; try { r = step(newState(), OK, ...args); } catch { threw = true; } ok(!threw && r.ok === false && r.error === 'PARAMS_INVALID' && r.code === 'ALERT_STATE_INVALID', `invalid parameters (${name}) are a typed failure`); }
// damaged state: never reset, never thrown; valid undelivered items are salvaged and returned
{ let good = st(step(newState(), A, T)); const itm = items(good)[0];
  const damaged = [undefined, null, {}, 'x', [], { ...good, pending: 'x' }, { ...good, status: 'WEIRD' }, { ...good, seq: -1 }, { ...good, okStreak: 1.5 }, { ...good, pending: [itm, { key: 5 }] }, { ...good, pending: [itm, itm] }, { ...good, seq: 0 }, { ...good, firstAlertAt: 'x' }];
  for (const d of damaged) {
    const snap = JSON.stringify(d); let r1, r2, r3, threw = false; try { r1 = step(d, OK, T + 1); r2 = toSend(d); r3 = ack(d, 'x'); } catch { threw = true; }
    ok(!threw && r1.ok === false && r1.error === 'STATE_INVALID' && r2.ok === false && r3.ok === false && r1.code === 'ALERT_STATE_INVALID', `damaged state ${snap && snap.slice(0, 40)} is a typed failure from step, toSend and ack`);
    ok(JSON.stringify(d) === snap, 'the damaged input is left untouched (not reset)');
  }
  const mixed = { ...good, pending: [itm, { key: 5 }, { ...itm, key: 'alert:o9', seq: 9 }] };
  const rr = step(mixed, OK, T + 1);
  ok(rr.ok === false && rr.salvaged.length === 2 && rr.salvaged.some((x) => x.key === itm.key) && rr.salvaged.some((x) => x.key === 'alert:o9'), 'regression: every structurally valid undelivered item in a damaged outbox is salvaged, none lost');
  ok(inspectState(good).valid && !inspectState({ ...good, pending: [itm, itm] }).valid, 'inspectState tells valid from damaged'); }

// ---- watchdog ----
const REC = { at: '2026-12-01T11:59:00.000Z', status: 'ok' };
const w = (o) => checkWatchdog({ nowMs: NOW, record: REC, maxSilenceS: 900, ...o });
const wc = (r) => r.alerts.map((a) => a.code).sort().join();
ok(w().status === 'OK', 'fresh ok record is OK');
ok(w({ record: { at: '2026-12-01T11:45:00.000Z', status: 'ok' } }).status === 'OK', 'exactly at the limit is OK');
ok(wc(w({ record: { at: '2026-12-01T11:44:59.000Z', status: 'ok' } })) === 'COLLECTOR_MISSED_INVOCATION', 'one second over the limit is a missed invocation');
ok(wc(w({ record: { at: '2026-12-01T11:59:30.000Z', status: 'crashed' } })) === 'COLLECTOR_CRASHED', 'a crashed run record alerts');
ok(w({ record: { at: '2026-12-01T11:59:30.000Z', status: 'alert' } }).status === 'OK', 'an alert-status record still proves the collector ran');
for (const rec of [undefined, null, 'x', {}, { at: 'bad', status: 'ok' }, { at: REC.at, status: 'weird' }, { at: 5, status: 'ok' }]) ok(wc(w({ record: rec })) === 'WATCHDOG_RECORD_MISSING', `damaged record ${JSON.stringify(rec)} alerts`);
ok(wc(w({ record: { at: '2026-12-01T12:05:00.000Z', status: 'ok' } })) === 'FUTURE_RECORD', 'a future record alerts');
ok(w({ record: { at: '2026-12-01T12:00:30.000Z', status: 'ok' } }).status === 'OK', 'skew inside the bound is tolerated');
for (const o of [{ maxSilenceS: 59 }, { maxSilenceS: 86401 }, { maxSilenceS: Number.NaN }, { maxSilenceS: undefined }, { nowMs: Number.NaN }, { skewS: 0 }, { skewS: 301 }]) ok(wc(w(o)) === 'CONFIG_INVALID', `watchdog config ${JSON.stringify(o)} is CONFIG_INVALID`);
for (const bad3 of [undefined, null, 5, 'x']) { let t4 = false, r; try { r = checkWatchdog(bad3); } catch { t4 = true; } ok(!t4 && r.status === 'ALERT', `watchdog(${JSON.stringify(bad3)}) alerts without throwing`); }
ok(wc(checkWatchdog({ nowMs: NOW, get record() { throw new Error('x'); }, maxSilenceS: 900 })) === 'WATCHDOG_FAILURE', 'a throwing input becomes WATCHDOG_FAILURE');
ok(!/^\s*import\s/m.test(readFileSync(join(here, 'watchdog.mjs'), 'utf8')), 'the watchdog imports nothing, so it shares no code with the collector');
// end to end: a collector that stops running is caught by the watchdog although it can no longer alert for itself
{ const r1 = await run(); let st = step(newState(), r1, NOW); const later = NOW + 40 * 60000; // 40 minutes with no collector run
  ok(checkWatchdog({ nowMs: later, record: r1.collectorRun, maxSilenceS: 900 }).alerts[0].code === 'COLLECTOR_MISSED_INVOCATION', 'end to end: silence after the last good run is caught outside the collector'); }
// end to end: a failure then recovery produces one alert and one recovery for the owner, and a failed delivery is retried
{ let q = newState(); const sent = []; let failNext = 1;
  const deliver = (state) => { for (const m of items(state)) { if (failNext > 0) { failNext--; continue; } sent.push(m.kind); state = st(ack(state, m.key)); } return state; };
  const rBad = await run({ fetchPending: async () => { throw new Error('down'); } }), rGood = await run();
  for (const [r, at] of [[rBad, 0], [rBad, 60], [rBad, 120], [rGood, 180], [rGood, 240], [rGood, 300]]) q = deliver(st(step(q, r, NOW + at * 1000)));
  ok(sent.join() === 'alert,recovery', `end to end: one alert (after one failed delivery was retried) and one recovery (got ${sent.join()})`); }

// ---- privacy of what actually leaves: serialize the outbound payloads ----
const SECRETS = ['SECRETKEY123', 'rpc.example.org', 'SECRETNAME', 'KEY=abc', '0xdeadbeef', 'PRIVATE'];
{ const evil = (o) => JSON.stringify({ t: '2026-12-01T11:59:00.000Z', ...o }) + '\n';
  const log = fx('healthy.jsonl') + evil({ ev: 'exit', reason: 'fetch failed https://rpc.example.org/v2/SECRETKEY123', code: 'SECRETKEY123' }) + evil({ ev: 'heartbeat', uptimeS: 2100, held: { applicant: '0xdeadbeef' }, lastPollOkAgeS: 'PRIVATE' }) + evil({ ev: 'state-unreadable', why: 'KEY=abc' }) + evil({ ev: 'start', mode: 'KEY=abc' });
  class SECRETNAME extends Error { constructor(m) { super(m); this.name = 'SECRETNAME'; } }
  const rs = [await run({ logText: log }), await run({ config: { ...cfg, 'KEY=abc': 1, SECRETKEY123: 2 } }), await run({ fetchPending: async () => { throw new SECRETNAME('0xdeadbeef PRIVATE'); } }),
    await collectOnce({ get logText() { throw new SECRETNAME('boom 0xdeadbeef'); }, nowMs: NOW, config: cfg, fileBytes: FILE, fetchPending: emptyQ })];
  for (const [i, r] of rs.entries()) { const out = JSON.stringify(r.outbound); for (const x of SECRETS) ok(!out.includes(x), `outbound payload ${i} never contains ${x}`); ok(r.outbound.alerts.every((a) => a.detail === OUTBOUND_DETAIL[a.code]), `outbound payload ${i} uses only the static text for each code`); const inner = JSON.stringify(r.alerts); for (const x of SECRETS) ok(!inner.includes(x), `the internal alert list ${i} never contains ${x} either`); }
  ok(rs[3].outbound.alerts.map((a) => a.code).join() === 'COLLECTOR_FAILURE', 'a thrown exception becomes the static COLLECTOR_FAILURE with no exception name');
  const o = toOutbound({ status: 'ALERT', alerts: [{ code: 'EVIL SECRETNAME', detail: 'SECRETKEY123' }, { code: 'HEARTBEAT_MISSING', detail: 'x SECRETKEY123' }, null, { code: 5 }, { code: '__proto__' }] });
  ok(JSON.stringify(o).includes('UNKNOWN_CODE') && !JSON.stringify(o).includes('SECRET') && o.alerts.length === 2, 'unknown or malformed alert codes become UNKNOWN_CODE with static text');
  for (const unusable of [undefined, null, {}, { alerts: 'x' }, { status: 'OK' }, { alerts: [] }, { status: 'ALERT', alerts: [] }, { status: 'WEIRD', alerts: [] }, 'x', 5]) { const r = toOutbound(unusable); ok(r.status === 'ALERT' && r.alerts.map((a) => a.code).join() === 'UNUSABLE_RESULT', `regression: an unusable result (${JSON.stringify(unusable)}) is UNUSABLE_RESULT, never a reassuring OK`); }
  ok(toOutbound({ status: 'OK', alerts: [] }).status === 'OK' && toOutbound({ status: 'OK', alerts: [] }).alerts.length === 0, 'control: a genuine OK result stays OK');
  ok(toOutbound({ status: 'OK', alerts: [{ code: 'RPC_STALE' }] }).status === 'ALERT', 'an OK status with alerts inside is still an alert');
  // every code the code base can raise has static text
  const raised = new Set(); for (const r of [...rs, await run({ logText: fx('duplicate-runner.jsonl') }), await run({ logText: fx('restart-loop.jsonl') }), await run({ logText: fx('exited.jsonl') }), await run({ logText: undefined })]) for (const a of r.alerts) raised.add(a.code);
  ok([...raised].every((c) => Object.hasOwn(OUTBOUND_DETAIL, c)), `every raised code has static outbound text (${[...raised].filter((c) => !Object.hasOwn(OUTBOUND_DETAIL, c)).join(',') || 'none missing'})`); }


// ---- safe integers and numeric bounds ----
{ const good = st(step(newState(), A, T)); const itm = items(good)[0];
  const SAFE = Number.MAX_SAFE_INTEGER;
  for (const [name, d] of [['seq 2^53', { ...good, seq: 2 ** 53 }], ['seq MAX_SAFE_INTEGER (cannot increment)', { ...good, seq: SAFE }], ['seq 1e300', { ...good, seq: 1e300 }], ['okStreak 1e300', { ...good, okStreak: 1e300 }], ['okStreak 2^53', { ...good, okStreak: 2 ** 53 }],
    ['item seq 1e300', { ...good, seq: 1e300, pending: [{ ...itm, seq: 1e300 }] }], ['item seq MAX_SAFE_INTEGER', { ...good, seq: SAFE, pending: [{ ...itm, seq: SAFE }] }], ['codes of 33 entries', { ...good, pending: [{ ...itm, codes: Array(33).fill('A') }] }], ['a 65-character code', { ...good, pending: [{ ...itm, codes: ['A'.repeat(65)] }] }]]) {
    ok(inspectState(d).valid === false, `regression: ${name} is a damaged state, not valid`); }
  let big = { ...good, seq: SAFE - 2, pending: [] }; ok(inspectState(big).valid === true, 'control: a seq below the safe limit is valid');
  ok(step(big, B, T + 5).ok === true && step(big, B, T + 5).state.seq === SAFE - 1, 'the last usable seq still increments exactly');
  ok(step({ ...big, seq: SAFE - 1 }, B, T + 5).ok === false, 'one step later the state is refused rather than reusing keys');
  ok(inspectState({ ...good, pending: [{ ...itm, codes: Array(32).fill('A') }] }).valid === true && inspectState({ ...good, pending: [{ ...itm, codes: ['A'.repeat(64)] }] }).valid === true, 'control: 32 codes and a 64-character code are inside the bounds'); }
for (const bn of [1e300, 2 ** 53, Number.MAX_SAFE_INTEGER + 1]) ok(has(await run({ fetchPending: async () => ({ pending: [], ...blk({ blockNumber: bn, pendingBlockNumber: bn }) }) }), 'RPC_BLOCK_INVALID'), `regression: blockNumber ${bn} is not a safe integer`);
ok((await run({ fetchPending: async () => ({ pending: [], ...blk({ blockNumber: Number.MAX_SAFE_INTEGER, pendingBlockNumber: Number.MAX_SAFE_INTEGER }) }) })).status === 'OK', 'control: the largest safe block number is accepted');
{ const T0 = '2026-12-01T00:00:00Z';
  for (const v of [1e308, -1, 1e12 + 1, -0.0001]) ok(sanitize({ t: T0, ev: 'heartbeat', inflight: v }).inflight === null, `regression: heartbeat value ${v} is outside the plausible range and becomes null`);
  for (const v of [0, 1, 1e12, 31536000]) ok(sanitize({ t: T0, ev: 'heartbeat', inflight: v }).inflight === v, `control: heartbeat value ${v} passes`);
  ok(sanitize({ t: T0, ev: 'exit', uptimeS: 1e300 }).uptimeS === null, 'exit uptime out of range becomes null'); }

// ---- delivery serializer: the only path from outbox items to a sender ----
{ const mk = (o = {}) => ({ key: 'alert:o3', kind: 'alert', codes: ['HEARTBEAT_MISSING', 'RPC_STALE'], at: NOW, seq: 3, ...o });
  const g = serializeDelivery(mk());
  ok(g.ok && g.message.id === 'alert:o3' && g.message.kind === 'alert' && g.message.alerts.map((a) => a.code).join() === 'HEARTBEAT_MISSING,RPC_STALE' && g.message.alerts.every((a) => a.detail === OUTBOUND_DETAIL[a.code]) && g.quarantine === undefined && g.message.at === '2026-12-01T12:00:00.000Z', 'a normal item becomes a message with static text and an ISO time, no quarantine');
  ok(serializeDelivery(mk({ kind: 'recovery', key: 'recovery:o3', codes: [] })).ok, 'a recovery item with no codes is deliverable');
  const SEC = 'SECRETKEY123';
  const cases = [['secret in a code', mk({ codes: [`HEARTBEAT_MISSING ${SEC}`, 'RPC_STALE'] })], ['secret as a code that is a known name prefix', mk({ codes: [`RPC_STALE${SEC}`] })], ['__proto__ code', mk({ codes: ['__proto__'] })], ['non-string codes', mk({ codes: [5, null, { a: SEC }] })],
    ['oversized code', mk({ codes: ['A'.repeat(100000)] })]];
  for (const [n, it] of cases) { const r = serializeDelivery(it); ok(r.ok && !JSON.stringify(r.message).includes(SEC) && JSON.stringify(r.message).length < 2000 && r.quarantine && r.quarantine.reason === 'CODES_ALTERED' && r.quarantine.raw.length <= MAX_RAW, `${n}: message is safe, raw evidence is quarantined locally and bounded`); }
  ok(serializeDelivery(mk({ codes: Array(MAX_CODES + 1).fill('RPC_STALE') })).ok === false, 'more than the allowed number of codes is not sent');
  ok(serializeDelivery(mk({ codes: [] })).ok === false, 'an alert with no codes is not sent');
  for (const [n, it] of [['secret in the key', mk({ key: `alert:o3 ${SEC}` })], ['key without the o-prefix', mk({ key: 'alert:3' })], ['key with leading zero', mk({ key: 'alert:o03', seq: 3 })], ['key too long', mk({ key: 'alert:o' + '9'.repeat(40) })], ['unknown kind', mk({ kind: 'page', key: 'page:o3' })],
    ['kind and key disagree', mk({ kind: 'repeat' })], ['seq and key disagree', mk({ seq: 4 })], ['seq not a safe integer', mk({ seq: 1e300, key: 'alert:o1e+300' })], ['null item', null], ['array item', []], ['string item', 'x'], ['codes not an array', mk({ codes: SEC })]]) {
    const r = serializeDelivery(it); ok(r.ok === false && r.quarantine && r.quarantine.raw.length <= MAX_RAW && typeof r.reason === 'string' && !('message' in r), `${n}: refused, nothing to send, raw evidence kept for local storage only`); }
  { const sparse = serializeDelivery(mk({ codes: [, 'RPC_STALE'] })); // eslint-disable-line no-sparse-arrays
    ok(sparse.ok === true && sparse.message.alerts.every((a) => typeof a.code === 'string' && typeof a.detail === 'string') && sparse.message.alerts.map((a) => a.code).join() === 'RPC_STALE,UNKNOWN_CODE' && sparse.quarantine && sparse.quarantine.reason === 'CODES_ALTERED', 'regression: a hole in a sparse codes array becomes UNKNOWN_CODE, never an empty alert object');
    const g2 = st(step(newState(), A, T)); const i2 = items(g2)[0];
    ok(inspectState({ ...g2, pending: [{ ...i2, codes: [, 'RPC_STALE'] }] }).valid === false && step({ ...g2, pending: [i2, { ...i2, key: 'alert:o9', seq: 9, codes: [, 'A'] }] }, OK, T + 1).salvaged.length === 1, 'regression: a sparse codes array makes an item invalid in state and it is not salvaged'); }
  const huge = mk({ junk: 'x'.repeat(1e6) }); ok(serializeDelivery({ ...huge, key: 'bad' }).quarantine.raw.length === MAX_RAW, 'quarantined evidence is bounded at the cap');
  const cyc = mk({ key: 'bad' }); cyc.self = cyc; ok(serializeDelivery(cyc).ok === false && serializeDelivery(cyc).quarantine.raw === '[unserializable]', 'an unserialisable item is refused and does not throw');
  ok(serializeDelivery(mk({ at: Number.NaN })).message.at === null && serializeDelivery(mk({ at: 1e300 })).message.at === null, 'an unusable time is omitted, not forwarded');
  ok(serializeDelivery({ get key() { throw new Error('x'); } }).ok === false, 'a throwing item is refused without throwing');
  // salvaged items from a damaged outbox go through the same serializer
  const good = st(step(newState(), A, T)); const it0 = items(good)[0];
  const damaged = { ...good, pending: [it0, { key: 'alert:o9', kind: 'alert', codes: [`EVIL ${SEC}`], at: NOW, seq: 9 }, { key: 'x', nope: SEC }] };
  const rr = step(damaged, OK, T + 1); ok(rr.ok === false && rr.salvaged.length === 2, 'two of three items in a damaged outbox are salvageable');
  const unsafeSeq = step({ ...good, pending: [it0, { ...it0, key: 'alert:o9', seq: 1e300 }, { ...it0, key: 'alert:o8', seq: 2 ** 53 }] }, OK, T + 1);
  ok(unsafeSeq.ok === false && unsafeSeq.salvaged.length === 1 && unsafeSeq.salvaged[0].key === it0.key, 'regression: an item whose seq is not a safe integer is not salvaged');
  const sent = rr.salvaged.map(serializeDelivery); ok(sent.every((x) => x.ok) && !JSON.stringify(sent.map((x) => x.message)).includes(SEC) && sent.filter((x) => x.quarantine).length === 1, 'salvaged items are serialised safely: no secret in any message, the altered one quarantined locally'); }
console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
