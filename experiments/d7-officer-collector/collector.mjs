// Read-only collector for the credit-desk officer (contract draft, source only, nothing deployed).
// It turns three untrusted inputs into the observer's input and a list of alerts: the officer's JSONL log text, the host's runtime
// file bytes, and an injected chain read of the pending desk queue. It performs no I/O itself (the caller reads the log, the file
// and the chain), holds no key, signs nothing and sends nothing. It never throws: any failure is an alert.
// Scope is the emitter schema of PR 458 head 9c181672 (see fixtures/emitter-schema.json); nothing here accepts that head as the runtime.
import { createHash } from 'node:crypto';
import { evaluate } from '../d7-officer-observer/observer.mjs';

const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const inRange = (x, lo, hi, int) => isNum(x) && x >= lo && x <= hi && (!int || Number.isInteger(x));

// ---- privacy: the log holds applicant addresses, message text, transaction hashes and the RPC endpoint. Only these fields leave. ----
export const ALLOWED_FIELDS = {
  start: ['mode'],
  heartbeat: ['uptimeS', 'intervalS', 'pollOk', 'pollErr', 'handled', 'reverted', 'deferred', 'unavailable', 'held', 'handleErr', 'lastPollOkAgeS', 'lastPollErrAgeS', 'lastHandledAgeS', 'inflight'],
  exit: ['reason', 'uptimeS', 'lastPollOkAgeS'],
  'state-unreadable': ['why'],
  'state-write-error': [],
  'earlier-reply-stuck': ['ageS'],
  'earlier-reply-settled': [],
  'model-unavailable': [],
  'send-ambiguous': [],
  'poll-error': [],
};

export function sanitize(e) {
  const keep = ALLOWED_FIELDS[e.ev];
  if (!keep) return null; // replied, topup, llm-*, error, backing-unchanged and anything unknown: dropped
  const out = { t: e.t, ev: e.ev };
  for (const k of keep) if (e[k] !== undefined) out[k] = typeof e[k] === 'string' ? e[k].slice(0, 80) : e[k];
  return out;
}

// ---- log parsing: bounded tail, no partial last line, malformed lines counted not trusted ----
export function parseLog(text, { maxBytes = 1048576 } = {}) {
  if (typeof text !== 'string') return { ok: false, why: 'LOG_UNREADABLE' };
  let body = text, truncatedHead = false;
  if (body.length > maxBytes) { body = body.slice(-maxBytes); const nl = body.indexOf('\n'); body = nl === -1 ? '' : body.slice(nl + 1); truncatedHead = true; }
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

// ---- config boundary: unknown keys, inherited properties and bad values are CONFIG_INVALID ----
const OBSERVER_KEYS = ['runtimeSha', 'heartbeatS', 'pendingBudgetS', 'graceBeats', 'pollStaleS', 'eventWindowS', 'clockSkewS', 'pendingFreshS'];
export const COLLECTOR_RANGES = { logTailBytes: [4096, 16777216, true], rpcTimeoutS: [1, 120], staleBlockS: [30, 3600], restartMax: [1, 20, true], restartWindowS: [60, 86400] };
export const COLLECTOR_DEFAULTS = { logTailBytes: 1048576, rpcTimeoutS: 20, staleBlockS: 300, restartMax: 3, restartWindowS: 3600 };

export function parseConfig(raw) {
  const bad = [];
  const proto = raw && typeof raw === 'object' ? Object.getPrototypeOf(raw) : undefined;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || (proto !== Object.prototype && proto !== null)) return { ok: false, alerts: [{ code: 'CONFIG_INVALID', detail: 'config is not a plain object' }] };
  const known = new Set([...OBSERVER_KEYS, ...Object.keys(COLLECTOR_RANGES)]);
  const unknown = Object.keys(raw).filter((k) => !known.has(k));
  if (unknown.length) bad.push(`unknown key(s): ${unknown.join(', ')}`);
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

// ---- chain read of the pending queue: injected, bounded in time, validated; every failure is a distinct, explicit non-read ----
// fetchPending() must resolve { pending: [{ requestedAtMs }...], readAtMs, blockTimeMs? }. An empty array is the only "empty queue".
export async function readPending(fetchPending, { nowMs, timeoutS, staleBlockS, clockSkewS = 60 }) {
  let r, timer;
  try {
    r = await Promise.race([Promise.resolve().then(fetchPending), new Promise((_, rej) => { timer = setTimeout(() => rej(new Error('timeout')), timeoutS * 1000); })]);
  } catch (e) { return { read: { ok: false }, alert: { code: e && e.message === 'timeout' ? 'RPC_TIMEOUT' : 'RPC_UNAVAILABLE', detail: 'pending queue read did not complete' } }; }
  finally { clearTimeout(timer); }
  if (!r || typeof r !== 'object' || !Array.isArray(r.pending) || !isNum(r.readAtMs)) return { read: { ok: false }, alert: { code: 'RPC_UNAVAILABLE', detail: 'pending queue read returned an unusable shape' } };
  if (r.blockTimeMs !== undefined && (!isNum(r.blockTimeMs) || nowMs - r.blockTimeMs > staleBlockS * 1000)) return { read: { ok: false }, alert: { code: 'RPC_STALE', detail: `latest block seen is older than ${staleBlockS} s or has no usable time` } };
  if (r.pending.some((p) => !p || !isNum(p.requestedAtMs) || p.requestedAtMs > r.readAtMs + clockSkewS * 1000)) return { read: { ok: false }, alert: { code: 'RPC_UNAVAILABLE', detail: 'a pending entry has no usable request time' } };
  const oldest = r.pending.length ? Math.max(0, (r.readAtMs - Math.min(...r.pending.map((p) => p.requestedAtMs))) / 1000) : null;
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

// ---- one invocation: never throws, always yields a result and a run record for the external watchdog ----
export async function collectOnce(input) {
  const nowMs = input && typeof input === 'object' ? input.nowMs : undefined;
  const stamp = isNum(nowMs) && Number.isFinite(new Date(nowMs).getTime()) ? new Date(nowMs).toISOString() : null;
  const done = (alerts, extra = {}) => ({ status: alerts.length ? 'ALERT' : 'OK', alerts, ...extra, collectorRun: { at: stamp, status: alerts.length ? 'alert' : 'ok' } });
  try {
    if (!isNum(nowMs) || stamp === null) return { status: 'ALERT', alerts: [{ code: 'CONFIG_INVALID', detail: 'nowMs is not a usable time' }], collectorRun: { at: null, status: 'crashed' } };
    const { logText, config, fileBytes, fetchPending } = input;
    const cfg = parseConfig(config);
    if (!cfg.ok) return done(cfg.alerts);
    const alerts = [];
    const parsed = parseLog(logText, { maxBytes: cfg.collector.logTailBytes });
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
    return { status: 'ALERT', alerts: [{ code: 'COLLECTOR_FAILURE', detail: `collector threw ${e && e.name ? e.name : 'an error'}` }], collectorRun: { at: stamp, status: 'crashed' } };
  }
}
