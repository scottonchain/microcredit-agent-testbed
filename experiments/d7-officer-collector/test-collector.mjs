// Offline tests for the collector, alert state and watchdog. Run: node test-collector.mjs (exit 0 only if every check passes).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { collectOnce, parseLog, parseConfig, gitBlobSha, sanitize, ALLOWED_FIELDS, COLLECTOR_RANGES, COLLECTOR_DEFAULTS } from './collector.mjs';
import { newState, step, toSend, ack } from './alertstate.mjs';
import { checkWatchdog } from './watchdog.mjs';

let pass = 0, fail = 0;
const ok = (c, n) => { if (c) pass++; else { fail++; console.log('FAIL', n); } };
const here = dirname(fileURLToPath(import.meta.url));
const fx = (n) => readFileSync(join(here, 'fixtures', n), 'utf8');
const NOW = Date.parse('2026-12-01T12:00:00Z');
const FILE = Buffer.from('// stand-in for the pinned daemon file\n');
const SHA = gitBlobSha(FILE);
const cfg = { runtimeSha: SHA, heartbeatS: 300, pendingBudgetS: 600 };
const emptyQ = async () => ({ pending: [], readAtMs: NOW, blockTimeMs: NOW - 5000 });
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
ok(sanitize({ t: 'x', ev: 'replied', reply: 'secret' }) === null, 'unknown or private event dropped');
ok(sanitize({ t: 'x', ev: 'model-unavailable', applicant: '0x1', why: 'timeout' }).applicant === undefined, 'model-unavailable loses applicant');
ok(sanitize({ t: 'x', ev: 'heartbeat', lastPollOkAgeS: 5, secret: 'z' }).secret === undefined, 'unlisted heartbeat field dropped');
ok(JSON.stringify(Object.keys(ALLOWED_FIELDS).sort()) === JSON.stringify(['earlier-reply-settled', 'earlier-reply-stuck', 'exit', 'heartbeat', 'model-unavailable', 'poll-error', 'send-ambiguous', 'start', 'state-unreadable', 'state-write-error']), 'allowlisted event names pinned');
const schema = JSON.parse(fx('emitter-schema.json'));
for (const [ev, f] of Object.entries(ALLOWED_FIELDS)) ok(JSON.stringify([...f].sort()) === JSON.stringify([...schema.events[ev].forward].sort()), `schema file and code agree on forwarded fields of ${ev}`);

// ---- log shape: partial tail, truncated head, empty, unreadable, malformed ----
const pt = parseLog(fx('partial-tail.jsonl'));
ok(pt.ok && pt.partialTail === true && pt.malformed === 0 && pt.events.length === 3, 'partial last line is dropped, not counted as malformed, earlier lines kept');
ok(!parseLog(fx('healthy.jsonl')).partialTail, 'complete log has no partial tail');
const filler = (JSON.stringify({ t: '2026-12-01T10:00:00.000Z', ev: 'heartbeat', uptimeS: 1, lastPollOkAgeS: 1, held: 0 }) + '\n').repeat(60); // valid lines, so only a cut line could be malformed
const big = filler + fx('healthy.jsonl'); // far more than 4096 bytes
const tr = parseLog(big, { maxBytes: 4096 });
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
// chain read: unavailable, stale, malformed and slow reads never become an empty queue
const bad = (f, c, n) => run({ fetchPending: f }).then((r) => { ok(has(r, c) && has(r, 'PENDING_UNREADABLE') && r.status === 'ALERT', `${n}: ${c} and the observer sees an unread queue`); });
await bad(async () => { throw new Error('connect ECONNREFUSED'); }, 'RPC_UNAVAILABLE', 'rpc throws');
await bad(async () => undefined, 'RPC_UNAVAILABLE', 'rpc returns nothing');
await bad(async () => ({ readAtMs: NOW }), 'RPC_UNAVAILABLE', 'rpc returns no pending list');
await bad(async () => ({ pending: null, readAtMs: NOW }), 'RPC_UNAVAILABLE', 'pending is null, not empty');
await bad(async () => ({ pending: [], readAtMs: 'now' }), 'RPC_UNAVAILABLE', 'readAt is not a number');
await bad(async () => ({ pending: [{}], readAtMs: NOW }), 'RPC_UNAVAILABLE', 'entry without a request time');
await bad(async () => ({ pending: [{ requestedAtMs: NOW + 9e6 }], readAtMs: NOW }), 'RPC_UNAVAILABLE', 'entry dated after the read');
await bad(async () => ({ pending: [], readAtMs: NOW, blockTimeMs: NOW - 301000 }), 'RPC_STALE', 'latest block 301 s old');
await bad(async () => ({ pending: [], readAtMs: NOW, blockTimeMs: Number.NaN }), 'RPC_STALE', 'block time NaN');
{ const r = await run({ config: { ...cfg, rpcTimeoutS: 1 }, fetchPending: () => new Promise(() => {}) });
  ok(has(r, 'RPC_TIMEOUT') && has(r, 'PENDING_UNREADABLE') && r.status === 'ALERT', 'a read that never answers is RPC_TIMEOUT after the bound, never an empty queue'); }
ok((await run({ fetchPending: async () => ({ pending: [], readAtMs: NOW }) })).status === 'OK', 'control: an explicit empty list with no block time is a successful empty read');
ok(has(await run({ fetchPending: async () => ({ pending: [{ requestedAtMs: NOW - 700000 }], readAtMs: NOW, blockTimeMs: NOW - 2000 }) }), 'PENDING_AGE'), 'a 700 s old pending request alerts PENDING_AGE');
ok((await run({ fetchPending: async () => ({ pending: [{ requestedAtMs: NOW - 100000 }], readAtMs: NOW, blockTimeMs: NOW - 2000 }) })).status === 'OK', 'a 100 s old pending request is inside the budget');
ok(has(await run({ fetchPending: undefined }), 'RPC_UNAVAILABLE'), 'no chain reader supplied is RPC_UNAVAILABLE');

// ---- config boundary ----
const cc = async (c) => codes(await run({ config: c }));
ok((await cc({ ...cfg, graceBeat: 1 })).join() === 'CONFIG_INVALID', 'regression: unknown key graceBeat is CONFIG_INVALID, not a silent default');
ok((await run({ config: { ...cfg, graceBeat: 1 } })).alerts[0].detail.includes('graceBeat'), 'the alert names the unknown key');
ok((await cc(Object.create(cfg))).join() === 'CONFIG_INVALID', 'inherited properties are rejected');
ok((await cc([cfg])).join() === 'CONFIG_INVALID' && (await cc(null)).join() === 'CONFIG_INVALID' && (await cc(undefined)).join() === 'CONFIG_INVALID' && (await cc('x')).join() === 'CONFIG_INVALID', 'non-object config rejected');
ok((await cc({ ...cfg, runtimeSha: SHA.slice(0, 8) })).join() === 'CONFIG_INVALID', 'a short sha prefix is rejected');
ok((await cc({ ...cfg, runtimeSha: SHA.toUpperCase() })).join() === 'CONFIG_INVALID', 'an uppercase sha is rejected');
ok((await cc({ heartbeatS: 300, pendingBudgetS: 600 })).join() === 'CONFIG_INVALID', 'runtimeSha missing is CONFIG_INVALID');
ok(Object.keys(parseConfig(Object.assign(Object.create(null), cfg))).includes('ok') && parseConfig(Object.assign(Object.create(null), cfg)).ok, 'a null-prototype plain object is accepted');
ok((await cc({ ...cfg, heartbeatS: 5 })).join() === 'CONFIG_INVALID', 'observer ranges still apply through the collector');
const EXPECTED = { logTailBytes: [4096, 16777216, true], rpcTimeoutS: [1, 120], staleBlockS: [30, 3600], restartMax: [1, 20, true], restartWindowS: [60, 86400] };
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

// ---- alert state: dedup, retry, recovery ----
const A = { status: 'ALERT', alerts: [{ code: 'HEARTBEAT_MISSING' }] }, B = { status: 'ALERT', alerts: [{ code: 'RPC_STALE' }, { code: 'PENDING_UNREADABLE' }] }, OK = { status: 'OK', alerts: [] };
let s = newState(); const T = 1e12;
s = step(s, OK, T); ok(toSend(s).length === 0 && s.status === 'OK', 'healthy start sends nothing');
const s0 = JSON.parse(JSON.stringify(s)); step(s, A, T + 1000); ok(JSON.stringify(s) === JSON.stringify(s0), 'step does not mutate its input');
s = step(s, A, T + 60000); ok(toSend(s).length === 1 && toSend(s)[0].kind === 'alert' && toSend(s)[0].codes.join() === 'HEARTBEAT_MISSING', 'first failure queues exactly one alert');
const k1 = toSend(s)[0].key;
s = step(s, A, T + 120000); s = step(s, A, T + 180000); ok(toSend(s).length === 1 && toSend(s)[0].key === k1, 'regression: an undelivered alert stays queued once (retried, not duplicated)');
s = ack(s, k1); ok(toSend(s).length === 0, 'an acknowledged alert is removed');
s = step(s, A, T + 240000); ok(toSend(s).length === 0, 'the same failure after delivery is deduplicated');
s = step(s, B, T + 300000); ok(toSend(s).length === 1 && toSend(s)[0].kind === 'alert' && toSend(s)[0].codes.join() === 'PENDING_UNREADABLE,RPC_STALE', 'a changed code set queues a new alert');
s = ack(s, toSend(s)[0].key);
s = step(s, B, T + 60000 + 3500 * 1000); ok(toSend(s).length === 0, 'no repeat before the repeat interval');
s = step(s, B, T + 300000 + 3600 * 1000); ok(toSend(s).length === 1 && toSend(s)[0].kind === 'repeat', 'one repeat after the interval');
{ const unacked = step(s, B, T + 300000 + 3600 * 1000 * 2 + 10), still = step(unacked, B, T + 300000 + 3600 * 1000 * 3 + 20);
  ok(toSend(unacked).filter((x) => x.kind === 'repeat').length === 1 && toSend(still).filter((x) => x.kind === 'repeat').length === 1, 'an undelivered repeat is not queued again at the next interval (no pile-up while delivery is failing)'); }
s = ack(s, toSend(s)[0].key);
s = step(s, OK, T + 4000000); ok(s.status === 'ALERT' && toSend(s).length === 0, 'one healthy run is not yet a recovery');
s = step(s, B, T + 4060000); s = step(s, OK, T + 4120000); ok(s.status === 'ALERT' && toSend(s).length === 0, 'a flap (alert, ok) resets the recovery count');
s = step(s, OK, T + 4180000); ok(s.status === 'OK' && toSend(s).length === 1 && toSend(s)[0].kind === 'recovery', 'two consecutive healthy runs queue one recovery');
s = step(s, OK, T + 4240000); ok(toSend(s).length === 1, 'recovery stays queued until delivered, not duplicated');
s = ack(s, toSend(s)[0].key); ok(toSend(s).length === 0 && s.status === 'OK', 'delivered recovery clears the queue');
{ let t2 = step(newState(), A, T); const t3 = step(newState(), A, T); ok(toSend(t2)[0].key === toSend(t3)[0].key, 'idempotency keys are stable for the same event'); }
for (const unusable of [null, undefined, { status: 'ALERT', alerts: [] }, { status: 'OK' }, { alerts: [] }, 'x']) { const u = step(newState(), unusable, T); ok(u.status === 'OK' ? !!(unusable && unusable.status === 'OK' && Array.isArray(unusable.alerts)) : toSend(u).length === 1, `an unusable result (${JSON.stringify(unusable)}) is a failure, not a quiet OK`); }
{ let u = step(newState(), null, T); u = step(u, OK, T + 1000); u = step(u, OK, T + 2000); ok(toSend(u).some((x) => x.kind === 'recovery'), 'recovery after an unusable-result alert needs two OKs'); }
let threw = 0; for (const bad2 of [[NaN], [T, { repeatEveryS: 0 }], [T, { recoveryOks: 0 }], [T, { recoveryOks: 1.5 }]]) { try { step(newState(), OK, ...bad2); } catch (e) { if (e instanceof RangeError) threw++; } } ok(threw === 4, 'invalid parameters throw RangeError at the boundary (the caller must turn that into an alert)');

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
// end to end: a failure then recovery produces one alert and one recovery for the owner
{ let st = newState(); const sent = []; const deliver = (state) => { for (const m of toSend(state)) { sent.push(m.kind); state = ack(state, m.key); } return state; };
  const rBad = await run({ fetchPending: async () => { throw new Error('down'); } }), rGood = await run();
  for (const [r, at] of [[rBad, 0], [rBad, 60], [rBad, 120], [rGood, 180], [rGood, 240], [rGood, 300]]) st = deliver(step(st, r, NOW + at * 1000));
  ok(sent.join() === 'alert,recovery', `end to end: one alert and one recovery (got ${sent.join()})`); }

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
