// Chain-only monitor adapter (source only; not run anywhere). It wires the block-bound reader to the collector's read validation
// and produces (a) an alert decision from CHAIN SYMPTOMS only (queue read health and oldest pending age) and (b) the one fixed-shape,
// static-text board message that may leave. It cannot see the officer log, heartbeat or runtime hash, so it complements the host
// collector and never replaces it. It posts nothing: sending is a separate, isolated step that re-validates the message first.
import { readPending, toOutbound, OUTBOUND_DETAIL } from '../d7-officer-collector/collector.mjs';
import { readWithFallback, makeJsonRpc, validEndpointUrl } from './reader.mjs';

const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const inRange = (x, lo, hi, int) => isNum(x) && x >= lo && x <= hi && (!int || Number.isInteger(x));
export const DEFAULT_ENDPOINTS = [{ label: 'primary', url: 'https://base-sepolia-rpc.publicnode.com' }, { label: 'fallback', url: 'https://sepolia.base.org' }];
const LABELS = ['primary', 'fallback'];
const RANGES = { pendingBudgetS: [60, 86400], staleBlockS: [30, 3600], clockSkewS: [1, 300], readTimeoutS: [5, 120] };
const DEFAULTS = { pendingBudgetS: 600, staleBlockS: 300, clockSkewS: 60, readTimeoutS: 60 };

export function parseMonitorConfig(raw) {
  const proto = raw && typeof raw === 'object' ? Object.getPrototypeOf(raw) : undefined;
  if (!raw || typeof raw !== 'object' || Array.isArray(raw) || (proto !== Object.prototype && proto !== null)) return { ok: false, detail: 'config is not a plain object' };
  const bad = []; const known = new Set(['desk', 'endpoints', ...Object.keys(RANGES)]);
  const unknown = Object.keys(raw).filter((k) => !known.has(k)); if (unknown.length) bad.push(`${unknown.length} unknown key(s)`);
  if (typeof raw.desk !== 'string' || !/^0x[0-9a-fA-F]{40}$/.test(raw.desk)) bad.push('desk');
  const cfg = { desk: raw.desk };
  for (const [k, [lo, hi, int]] of Object.entries(RANGES)) { const v = raw[k] === undefined ? DEFAULTS[k] : raw[k]; if (!inRange(v, lo, hi, int)) bad.push(k); else cfg[k] = v; }
  const eps = raw.endpoints === undefined ? DEFAULT_ENDPOINTS : raw.endpoints;
  if (!Array.isArray(eps) || eps.length < 1 || eps.length > 2 || !eps.every((e) => e && typeof e === 'object' && LABELS.includes(e.label) && validEndpointUrl(e.url)) || new Set(eps.map((e) => e.label)).size !== eps.length) bad.push('endpoints');
  else cfg.endpoints = eps.map((e) => ({ label: e.label, url: e.url }));
  return bad.length ? { ok: false, detail: `invalid: ${bad.join('; ')}` } : { ok: true, config: cfg };
}

// One chain-only check. Never throws; every failure is an alert; nothing is ever turned into an empty queue.
export async function chainOnlyCheck({ config, now, fetchImpl, sleep }) {
  const outcome = (alerts, health) => { const status = alerts.length ? 'ALERT' : 'OK'; return { status, alerts, health, outbound: toOutbound({ status, alerts }) }; };
  const empty = { endpoint: 'none', blockNumber: null, pendingCount: null, oldestPendingAgeS: null };
  try {
    const cfg = parseMonitorConfig(config); if (!cfg.ok) return outcome([{ code: 'CONFIG_INVALID', detail: cfg.detail }], empty);
    const c = cfg.config; let captured = null, label = 'none';
    const fetchPending = async () => {
      const r = await readWithFallback(c.endpoints, (url) => makeJsonRpc(url, fetchImpl), { desk: c.desk, now, sleep });
      if (!r.ok) throw new Error('read failed'); captured = r.snapshot; label = r.endpoint; return r.snapshot;
    };
    const nowMs = now(); if (!isNum(nowMs)) return outcome([{ code: 'COLLECTOR_FAILURE', detail: 'no clock' }], empty);
    const pend = await readPending(fetchPending, { nowMs, timeoutS: c.readTimeoutS, staleBlockS: c.staleBlockS, clockSkewS: c.clockSkewS });
    if (pend.alert) return outcome([pend.alert], { ...empty, endpoint: label });
    const alerts = [];
    const age = pend.read.oldestAgeS;
    if (age !== null && age > c.pendingBudgetS) alerts.push({ code: 'PENDING_AGE', detail: 'a desk request has waited longer than the budget' });
    return outcome(alerts, { endpoint: label, blockNumber: captured.blockNumber, pendingCount: captured.pending.length, oldestPendingAgeS: age === null ? null : Math.round(age) });
  } catch { return outcome([{ code: 'COLLECTOR_FAILURE', detail: 'chain-only check failed internally' }], empty); }
}

// ---- the one message that may leave: fixed shape, fixed text, whitelisted values only ----
const SCOPE = 'chain symptoms only: no officer log, heartbeat or runtime hash is seen';
export function boardMessage({ outcome, nowMs, idSuffix }) {
  const o = outcome && typeof outcome === 'object' ? outcome : {}; const h = o.health && typeof o.health === 'object' ? o.health : {};
  const codes = (o.outbound && Array.isArray(o.outbound.alerts) ? o.outbound.alerts : []).map((a) => (typeof a.code === 'string' && Object.hasOwn(OUTBOUND_DETAIL, a.code) ? a.code : 'UNKNOWN_CODE'));
  const status = o.status === 'OK' && codes.length === 0 ? 'OK' : 'ALERT';
  const unusable = o.status !== 'OK' && o.status !== 'ALERT'; if (unusable) codes.push('UNUSABLE_RESULT');
  const n = (v) => (Number.isSafeInteger(v) && v >= 0 ? String(v) : 'unknown');
  const ep = LABELS.includes(h.endpoint) ? h.endpoint : 'none';
  const when = isNum(nowMs) && Math.abs(nowMs) <= 8.64e15 ? new Date(nowMs).toISOString() : 'unknown';
  const suffix = typeof idSuffix === 'string' && /^[0-9]{14}$/.test(idSuffix) ? idSuffix : '00000000000000';
  const text = `Officer chain monitor ${status}${codes.length ? ` (${[...new Set(codes)].sort().join(', ')})` : ''}: block ${n(h.blockNumber)}, pending ${n(h.pendingCount)}, oldest pending ${n(h.oldestPendingAgeS)} s, reader ${ep}, at ${when}. ${SCOPE}.`;
  return { v: 2, id: `m-officer-chain-monitor-${suffix}`, k: 'health', f: 'monitor', t: ['x', 'h'], tr: 'gh:board-default', i: [{ w: 'officer-chain-monitor', op: status === 'OK' ? 'ok' : 'alert', x: text }] };
}
export const FOOTER = '_Automated read-only monitor (source: experiments/d7-officer-monitor); not an AI-authored analysis._';
export const boardComment = (msg) => '```json\n' + JSON.stringify(msg) + '\n```\n\n---\n' + FOOTER + '\n';

// The sender re-validates before posting: exact keys, exact shape, text built only from the template's alphabet. Returns { ok } or { ok: false, why }.
const CODE_LIST = Object.keys(OUTBOUND_DETAIL).join('|');
const TEXT_RE = new RegExp(`^Officer chain monitor (OK|ALERT)(?: \\(((?:${CODE_LIST})(?:, (?:${CODE_LIST}))*)\\))?: block (\\d{1,16}|unknown), pending (\\d{1,6}|unknown), oldest pending (\\d{1,10}|unknown) s, reader (primary|fallback|none), at (\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z|unknown)\\. ${SCOPE.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\.$`);
export function validateBoardComment(body) {
  try {
    if (typeof body !== 'string' || body.length > 2000) return { ok: false, why: 'SIZE' };
    const m = /^```json\n(\{.*\})\n```\n\n---\n(.*)\n$/s.exec(body); if (!m || m[2] !== FOOTER) return { ok: false, why: 'FORM' };
    const j = JSON.parse(m[1]);
    if (JSON.stringify(j) !== m[1]) return { ok: false, why: 'NOT_CANONICAL' }; // the bytes that are posted must be exactly the bytes that were validated: no duplicate keys, escapes or spacing tricks
    const keys = Object.keys(j).sort().join(); if (keys !== 'f,i,id,k,t,tr,v') return { ok: false, why: 'KEYS' };
    if (j.v !== 2 || j.k !== 'health' || j.f !== 'monitor' || j.tr !== 'gh:board-default' || JSON.stringify(j.t) !== '["x","h"]' || !/^m-officer-chain-monitor-[0-9]{14}$/.test(j.id)) return { ok: false, why: 'FIELDS' };
    if (!Array.isArray(j.i) || j.i.length !== 1) return { ok: false, why: 'ITEMS' };
    const it = j.i[0]; if (Object.keys(it).sort().join() !== 'op,w,x' || it.w !== 'officer-chain-monitor' || !['ok', 'alert'].includes(it.op) || typeof it.x !== 'string') return { ok: false, why: 'ITEM' };
    const t = TEXT_RE.exec(it.x); if (!t) return { ok: false, why: 'TEXT' };
    if ((t[1] === 'OK') !== (it.op === 'ok') || (t[1] === 'OK' && t[2] !== undefined)) return { ok: false, why: 'STATUS' };
    return { ok: true };
  } catch { return { ok: false, why: 'ERROR' }; }
}

// Entry point used by the CLI and by tests: pure given its injected effects. Returns the comment text and an exit code (0 OK, 2 ALERT, 3 config).
export async function runOnce({ config, now, fetchImpl, sleep }) {
  const outcome = await chainOnlyCheck({ config, now, fetchImpl, sleep });
  const nowMs = (() => { try { return now(); } catch { return NaN; } })();
  const stamp = isNum(nowMs) ? new Date(nowMs).toISOString().replace(/[-:T]/g, '').slice(0, 14) : '00000000000000';
  const msg = boardMessage({ outcome, nowMs, idSuffix: stamp });
  const body = boardComment(msg); const v = validateBoardComment(body);
  const hasConfig = outcome.alerts.some((a) => a.code === 'CONFIG_INVALID');
  return { outcome, body: v.ok ? body : null, validation: v, exitCode: !v.ok || hasConfig ? 3 : outcome.status === 'OK' ? 0 : 2 };
}
