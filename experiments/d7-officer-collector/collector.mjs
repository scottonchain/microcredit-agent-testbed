// Read-only collector for the credit-desk officer (contract draft, source only, nothing deployed).
// It turns three untrusted inputs into the observer's input and a list of alerts: the officer's JSONL log text, the host's runtime
// file bytes, and an injected chain read of the pending desk queue. It performs no I/O itself (the caller reads the log, the file
// and the chain), holds no key, signs nothing and sends nothing. collectOnce never throws: any failure is an alert.
// Anything that leaves the host is built from a static table: codes plus fixed text, never a string taken from the log, the
// config or an exception (see toOutbound). Scope is the emitter schema of PR 458 head 9c181672 (fixtures/emitter-schema.json);
// nothing here accepts that head as the runtime.
import { createHash } from 'node:crypto';
import { evaluate } from '../d7-officer-observer/observer.mjs';

const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const inRange = (x, lo, hi, int) => isNum(x) && x >= lo && x <= hi && (!int || Number.isInteger(x));

// ---- privacy: the log holds applicant addresses, message text, transaction hashes and the RPC endpoint. Only typed fields leave:
// finite numbers (anything else becomes null, which the observer treats as unreadable) and strings from a closed list (anything
// else becomes 'other'). Unknown events are dropped whole. ----
const SPEC = {
  start: { enums: { mode: ['claude', 'rules', 'interview'] }, nums: [] },
  heartbeat: { enums: {}, nums: ['uptimeS', 'intervalS', 'pollOk', 'pollErr', 'handled', 'reverted', 'deferred', 'unavailable', 'held', 'handleErr', 'lastPollOkAgeS', 'lastPollErrAgeS', 'lastHandledAgeS', 'inflight'] },
  exit: { enums: { reason: ['signal', 'uncaught', 'unhandled-rejection', 'exit'] }, nums: ['uptimeS', 'lastPollOkAgeS'] },
  'state-unreadable': { enums: { why: ['read-failed', 'not-json', 'bad-schema'] }, nums: [] },
  'state-write-error': { enums: {}, nums: [] },
  'earlier-reply-stuck': { enums: {}, nums: ['ageS'] },
  'earlier-reply-settled': { enums: {}, nums: [] },
  'model-unavailable': { enums: {}, nums: [] },
  'send-ambiguous': { enums: {}, nums: [] },
  'poll-error': { enums: {}, nums: [] },
};
export const ALLOWED_FIELDS = Object.fromEntries(Object.entries(SPEC).map(([ev, s]) => [ev, [...Object.keys(s.enums), ...s.nums]]));

export function sanitize(e) {
  if (!e || typeof e !== 'object' || typeof e.ev !== 'string' || typeof e.t !== 'string') return null;
  const spec = Object.hasOwn(SPEC, e.ev) ? SPEC[e.ev] : null;
  if (!spec) return null; // replied, topup, llm-*, error, backing-unchanged and anything unknown: dropped whole
  const ms = Date.parse(e.t);
  if (!Number.isFinite(ms)) return null;
  const out = { t: new Date(ms).toISOString(), ev: e.ev };
  for (const k of spec.nums) if (e[k] !== undefined) out[k] = isNum(e[k]) ? e[k] : null;
  for (const [k, allowed] of Object.entries(spec.enums)) if (e[k] !== undefined) out[k] = typeof e[k] === 'string' && allowed.includes(e[k]) ? e[k] : 'other';
  return out;
}

// ---- outbound alerts: static text per code. Unknown codes become UNKNOWN_CODE; nothing from runtime input is interpolated. ----
export const OUTBOUND_DETAIL = {
  CONFIG_INVALID: 'collector or observer configuration is missing, malformed or out of range',
  OBSERVER_FAILURE: 'the observer failed internally',
  COLLECTOR_FAILURE: 'the collector failed internally',
  LOG_UNREADABLE: 'the officer log could not be read',
  LOG_MALFORMED: 'unparseable lines were found in the officer log',
  RPC_UNAVAILABLE: 'the pending queue read failed or returned an unusable result',
  RPC_TIMEOUT: 'the pending queue read did not finish in time',
  RPC_STALE: 'the chain evidence is older than the allowed bound',
  RPC_BLOCK_INVALID: 'the chain read has no usable block evidence or it is dated in the future',
  RPC_BLOCK_MISMATCH: 'the pending queue is not bound to the same block as the block evidence',
  RUNTIME_HASH_MISMATCH: 'the running daemon file is not the pinned file or was not reported',
  EVENT_INVALID: 'malformed events or values were found in the officer log',
  FUTURE_EVIDENCE: 'evidence dated in the future was found',
  JOURNAL_UNREADABLE: 'the officer exited because its journal is unreadable',
  HEARTBEAT_MISSING: 'no recent officer heartbeat',
  POLL_STALLED: 'the officer has not polled the chain recently',
  HELD_REPLY: 'a reply is held awaiting chain evidence',
  HELD_REPLY_STUCK: 'a held reply is stuck and a person is needed',
  MODEL_UNAVAILABLE: 'the model was unavailable for one or more requests',
  AMBIGUOUS_TX: 'a send has an unknown broadcast outcome',
  PENDING_UNREADABLE: 'the pending desk queue was not read successfully',
  PENDING_STALE: 'the pending queue read is too old',
  PENDING_INVALID: 'the oldest pending age is unusable',
  PENDING_AGE: 'a desk request has waited longer than the budget',
  RESTART_LOOP: 'the officer restarted too many times in the window',
  PROCESS_EXITED: 'the officer exited and has not restarted',
  DUPLICATE_RUNNER: 'heartbeats are inconsistent with a single process',
  ALERT_STATE_INVALID: 'the alert outbox is damaged; undelivered items must be preserved and a person is needed',
  UNUSABLE_RESULT: 'the collector result was unusable',
  WATCHDOG_RECORD_MISSING: 'no usable collector run record',
  FUTURE_RECORD: 'the collector run record is dated in the future',
  COLLECTOR_MISSED_INVOCATION: 'the collector has not run within the limit',
  COLLECTOR_CRASHED: 'the last collector run crashed',
  WATCHDOG_FAILURE: 'the watchdog failed internally',
  UNKNOWN_CODE: 'an alert with an unrecognised code was raised',
};
export function toOutbound(result) {
  const list = result && Array.isArray(result.alerts) ? result.alerts : [];
  const codes = [...new Set(list.map((a) => (a && typeof a.code === 'string' && Object.hasOwn(OUTBOUND_DETAIL, a.code) ? a.code : 'UNKNOWN_CODE')))].sort();
  return { status: codes.length ? 'ALERT' : 'OK', alerts: codes.map((code) => ({ code, detail: OUTBOUND_DETAIL[code] })) };
}

// ---- log parsing: bounded tail (in UTF-16 characters, not bytes), no partial last line, malformed lines counted not trusted ----
export function parseLog(text, { maxChars = 1048576 } = {}) {
  if (typeof text !== 'string') return { ok: false, why: 'LOG_UNREADABLE' };
  let body = text, truncatedHead = false;
  if (body.length > maxChars) { body = body.slice(-maxChars); const nl = body.indexOf('\n'); body = nl === -1 ? '' : body.slice(nl + 1); truncatedHead = true; }
  const lines = body.split('\n');
  const partialTail = body.length > 0 && !body.endsWith('\n');
  if (partialTail) lines.pop(); // a line still being written is not evidence
  const events = []; let malformed = 0, dropped = 0;
  for (const line of lines) {
    if (line === '') continue;
    let o; try { o = JSON.parse(line); } catch { malformed++; continue; }
    if (!o || typeof o !== 'object' || typeof o.ev !== 'string' || typeof o.t !== 'string' || !Number.isFinite(Date.parse(o.t))) { malformed++; continue; }
    const s = sanitize(o); if (s) events.push(s); else dropped++;
  }
  return { ok: true, events, malformed, dropped, partialTail, truncatedHead };
}

// ---- runtime identity: the git blob sha of the exact daemon file the host runs, compared in full (no prefixes) ----
export const gitBlobSha = (bytes) => { const b = Buffer.from(bytes); return createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${b.length}\0`), b])).digest('hex'); };
const HEX40 = /^[0-9a-f]{40}$/;

// ---- config boundary: unknown keys, inherited properties and bad values are CONFIG_INVALID (key names are never echoed) ----
const OBSERVER_KEYS = ['runtimeSha', 'heartbeatS', 'pendingBudgetS', 'graceBeats', 'pollStaleS', 'eventWindowS', 'clockSkewS', 'pendingFreshS'];
export const COLLECTOR_RANGES = { logTailChars: [4096, 16777216, true], rpcTimeoutS: [1, 120], staleBlockS: [30, 3600], restartMax: [1, 20, true], restartWindowS: [60, 86400] };
export const COLLECTOR_DEFAULTS = { logTailChars: 1048576, rpcTimeoutS: 20, staleBlockS: 300, restartMax: 3, restartWindowS: 3600 };

export function parseConfig(raw) {
  const bad = [];
  const proto = raw && typeof raw === 'object' ? Object.getPrototypeOf(raw) : undefined;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || (proto !== Object.prototype && proto !== null)) return { ok: false, alerts: [{ code: 'CONFIG_INVALID', detail: 'config is not a plain object' }] };
  const known = new Set([...OBSERVER_KEYS, ...Object.keys(COLLECTOR_RANGES)]);
  const unknown = Object.keys(raw).filter((k) => !known.has(k));
  if (unknown.length) bad.push(`${unknown.length} unknown key(s)`);
  if (typeof raw.runtimeSha !== 'string' || !HEX40.test(raw.runtimeSha)) bad.push('runtimeSha (the full 40-hex blob sha is required)');
  const collector = {};
  for (const [k, [lo, hi, int]] of Object.entries(COLLECTOR_RANGES)) {
    const v = raw[k] === undefined ? COLLECTOR_DEFAULTS[k] : raw[k];
    if (!inRange(v, lo, hi, int)) bad.push(k); else collector[k] = v;
  }
  if (bad.length) return { ok: false, alerts: [{ code: 'CONFIG_INVALID', detail: `invalid: ${bad.join('; ')}` }] };
  const expect = {}; for (const k of OBSERVER_KEYS) if (raw[k] !== undefined) expect[k] = raw[k];
  return { ok: true, expect, collector };
}

// ---- chain read of the pending queue: injected, bounded in time, validated, bound to one block ----
// fetchPending() must resolve { pending: [{ requestedAtMs }...], readAtMs, blockNumber, blockTimeMs, pendingBlockNumber } where the
// queue was read AT blockNumber (pendingBlockNumber === blockNumber). An empty array is the only "empty queue"; a missing,
// future, stale or unbound block makes the read a non-read.
export async function readPending(fetchPending, { nowMs, timeoutS, staleBlockS, clockSkewS = 60 }) {
  const fail = (code, detail) => ({ read: { ok: false }, alert: { code, detail } });
  let r, timer;
  try {
    r = await Promise.race([Promise.resolve().then(fetchPending), new Promise((_, rej) => { timer = setTimeout(() => rej(new Error('timeout')), timeoutS * 1000); })]);
  } catch (e) { return fail(e && e.message === 'timeout' ? 'RPC_TIMEOUT' : 'RPC_UNAVAILABLE', 'pending queue read did not complete'); }
  finally { clearTimeout(timer); }
  if (!r || typeof r !== 'object' || !Array.isArray(r.pending) || !isNum(r.readAtMs)) return fail('RPC_UNAVAILABLE', 'pending queue read returned an unusable shape');
  const skewMs = clockSkewS * 1000;
  if (!isNum(r.blockTimeMs) || !Number.isInteger(r.blockNumber) || r.blockNumber < 0 || Math.abs(r.readAtMs - nowMs) > skewMs) return fail('RPC_BLOCK_INVALID', 'block evidence is missing or unusable');
  if (r.blockTimeMs > nowMs + skewMs) return fail('RPC_BLOCK_INVALID', 'block time is in the future');
  if (nowMs - r.blockTimeMs > staleBlockS * 1000) return fail('RPC_STALE', `latest block is older than ${staleBlockS} s`);
  if (r.pendingBlockNumber !== r.blockNumber) return fail('RPC_BLOCK_MISMATCH', 'the queue was not read at the evidenced block');
  if (r.pending.some((p) => !p || !isNum(p.requestedAtMs))) return fail('RPC_UNAVAILABLE', 'a pending entry has no usable request time');
  if (r.pending.some((p) => p.requestedAtMs > r.blockTimeMs + skewMs)) return fail('RPC_BLOCK_MISMATCH', 'a pending entry is dated after the evidenced block');
  const oldest = r.pending.length ? Math.max(0, (nowMs - r.pending.reduce((m, p) => Math.min(m, p.requestedAtMs), Infinity)) / 1000) : null;
  return { read: { ok: true, oldestAgeS: oldest, readAt: r.readAtMs } };
}

// ---- run identity: one process, one start; exits and restart loops are visible ----
export function runIdentity(events, nowMs, { restartMax, restartWindowS }) {
  const alerts = []; const evs = [...events].sort((a, b) => Date.parse(a.t) - Date.parse(b.t));
  const at = (e) => Date.parse(e.t);
  const starts = evs.filter((e) => e.ev === 'start'); const lastStart = starts[starts.length - 1];
  if (starts.filter((s) => nowMs - at(s) <= restartWindowS * 1000).length > restartMax) alerts.push({ code: 'RESTART_LOOP', detail: `more than ${restartMax} starts within ${restartWindowS} s` });
  const lastExit = [...evs].reverse().find((e) => e.ev === 'exit');
  if (lastExit && (!lastStart || at(lastExit) >= at(lastStart))) alerts.push({ code: 'PROCESS_EXITED', detail: `exit event after the last start (reason: ${lastExit.reason ?? 'unknown'})` });
  if (lastStart) {
    const beats = evs.filter((e) => e.ev === 'heartbeat' && at(e) >= at(lastStart));
    let prev = -1, dup = false;
    for (const b of beats) { if (isNum(b.uptimeS)) { if (b.uptimeS < prev) dup = true; prev = b.uptimeS; } }
    const lb = beats[beats.length - 1];
    if (lb && isNum(lb.uptimeS) && lb.uptimeS > (at(lb) - at(lastStart)) / 1000 + 120) dup = true; // a heartbeat from a process older than the latest start
    if (dup) alerts.push({ code: 'DUPLICATE_RUNNER', detail: 'heartbeat uptime is inconsistent with the latest start: a second or older process may be writing this log' });
  }
  return alerts;
}

// ---- one invocation: never throws, always yields a result, an outbound view and a run record for the external watchdog ----
export async function collectOnce(input) {
  const nowMs = input && typeof input === 'object' ? input.nowMs : undefined;
  const stamp = isNum(nowMs) && Number.isFinite(new Date(nowMs).getTime()) ? new Date(nowMs).toISOString() : null;
  const done = (alerts, extra = {}) => ({ status: alerts.length ? 'ALERT' : 'OK', alerts, outbound: toOutbound({ alerts }), ...extra, collectorRun: { at: stamp, status: alerts.length ? 'alert' : 'ok' } });
  try {
    if (!isNum(nowMs) || stamp === null) { const alerts = [{ code: 'CONFIG_INVALID', detail: 'nowMs is not a usable time' }]; return { status: 'ALERT', alerts, outbound: toOutbound({ alerts }), collectorRun: { at: null, status: 'crashed' } }; }
    const { logText, config, fileBytes, fetchPending } = input;
    const cfg = parseConfig(config);
    if (!cfg.ok) return done(cfg.alerts);
    const alerts = [];
    const parsed = parseLog(logText, { maxChars: cfg.collector.logTailChars });
    if (!parsed.ok) alerts.push({ code: 'LOG_UNREADABLE', detail: 'the officer log could not be read' });
    const events = parsed.ok ? parsed.events : [];
    if (parsed.ok && parsed.malformed > 0) alerts.push({ code: 'LOG_MALFORMED', detail: `${parsed.malformed} unparseable log line(s) ignored` });
    const runtimeSha = fileBytes === undefined || fileBytes === null ? null : gitBlobSha(fileBytes);
    const pend = await readPending(fetchPending, { nowMs, timeoutS: cfg.collector.rpcTimeoutS, staleBlockS: cfg.collector.staleBlockS, clockSkewS: cfg.expect.clockSkewS ?? 60 });
    if (pend.alert) alerts.push(pend.alert);
    alerts.push(...runIdentity(events, nowMs, cfg.collector));
    const ev = evaluate({ now: nowMs, events, pending: pend.read, runtimeSha, expect: cfg.expect });
    alerts.push(...ev.alerts);
    return done(alerts, { meta: { events: events.length, malformed: parsed.ok ? parsed.malformed : null, partialTail: parsed.ok ? parsed.partialTail : null, truncatedHead: parsed.ok ? parsed.truncatedHead : null } });
  } catch (e) {
    const alerts = [{ code: 'COLLECTOR_FAILURE', detail: 'collector threw an exception' }];
    return { status: 'ALERT', alerts, outbound: toOutbound({ alerts }), collectorRun: { at: stamp, status: 'crashed' } };
  }
}
