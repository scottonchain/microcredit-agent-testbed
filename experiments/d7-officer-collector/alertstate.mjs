// Alert delivery state: dedup, undelivered retry and recovery. Pure functions over a plain JSON state; no I/O and no sending.
// Every function returns a typed result and none throws: { ok: true, ... } or { ok: false, error, code: 'ALERT_STATE_INVALID',
// salvaged }. A damaged or unknown state is NEVER reset: the damaged input is left untouched, every structurally valid undelivered
// item found in it is returned as `salvaged` so the host can still deliver those obligations, and the host must raise an alert on
// its independent path and keep the damaged state file for repair.
// The caller sends what toSend() returns and calls ack(state, key) only after the delivery succeeded. An unacknowledged item is
// returned again at every step (retried, never lost). Each item has a persisted occurrence key `${kind}:o${seq}`; seq lives in the
// state, so keys stay unique across A to B to A flips, every repeat, steps at the same clock tick, and process restarts (the state is
// plain JSON). One item keeps the same key across all retries of its delivery.
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const KINDS = ['alert', 'repeat', 'recovery'];
export const newState = () => ({ status: 'OK', codesKey: '', firstAlertAt: null, lastQueuedAt: null, okStreak: 0, seq: 0, pending: [] });
const clone = (s) => JSON.parse(JSON.stringify(s));
const validItem = (p) => !!p && typeof p === 'object' && typeof p.key === 'string' && p.key.length > 0 && p.key.length <= 120 && KINDS.includes(p.kind)
  && Array.isArray(p.codes) && p.codes.every((c) => typeof c === 'string') && isNum(p.at) && Number.isInteger(p.seq) && p.seq >= 1;
export function inspectState(state) {
  const pendingIn = state && typeof state === 'object' && Array.isArray(state.pending) ? state.pending : [];
  let salvaged = []; try { salvaged = pendingIn.filter(validItem).map((p) => ({ key: p.key, kind: p.kind, codes: [...p.codes], at: p.at, seq: p.seq })); } catch { salvaged = []; }
  const s = state;
  const valid = !!s && typeof s === 'object' && !Array.isArray(s) && (s.status === 'OK' || s.status === 'ALERT') && typeof s.codesKey === 'string'
    && (s.firstAlertAt === null || isNum(s.firstAlertAt)) && (s.lastQueuedAt === null || isNum(s.lastQueuedAt))
    && Number.isInteger(s.okStreak) && s.okStreak >= 0 && Number.isInteger(s.seq) && s.seq >= 0
    && Array.isArray(s.pending) && s.pending.every(validItem) && s.pending.every((p) => p.seq <= s.seq)
    && new Set(s.pending.map((p) => p.key)).size === s.pending.length;
  return { valid, salvaged };
}
const invalid = (state, error) => ({ ok: false, error, code: 'ALERT_STATE_INVALID', salvaged: inspectState(state).salvaged });

export function toSend(state) { const i = inspectState(state); return i.valid ? { ok: true, items: state.pending.map((p) => ({ ...p, codes: [...p.codes] })) } : invalid(state, 'STATE_INVALID'); }
export function ack(state, key) { const i = inspectState(state); if (!i.valid) return invalid(state, 'STATE_INVALID'); const s = clone(state); s.pending = s.pending.filter((p) => p.key !== key); return { ok: true, state: s }; }

export function step(state, result, nowMs, { repeatEveryS = 3600, recoveryOks = 2 } = {}) {
  if (!isNum(nowMs) || !(isNum(repeatEveryS) && repeatEveryS > 0) || !(Number.isInteger(recoveryOks) && recoveryOks >= 1)) return invalid(state, 'PARAMS_INVALID');
  if (!inspectState(state).valid) return invalid(state, 'STATE_INVALID');
  const s = clone(state);
  const codes = [...new Set((result && Array.isArray(result.alerts) ? result.alerts : []).map((a) => String(a && a.code)))].sort();
  const usable = !!result && typeof result === 'object' && Array.isArray(result.alerts) && (result.status === 'OK' || result.status === 'ALERT');
  const failing = codes.length > 0 || !usable || result.status !== 'OK'; // an unusable or inconsistent result is never a recovery
  const key = codes.length ? codes.join(',') : 'UNUSABLE_RESULT';
  const queue = (kind, kk) => {
    if (s.pending.some((p) => p.kind === kind && p.codes.join(',') === (kk ? kk : ''))) { return; } // identical undelivered item: no pile-up
    s.seq += 1; s.pending.push({ key: `${kind}:o${s.seq}`, kind, codes: kk ? kk.split(',') : [], at: nowMs, seq: s.seq }); s.lastQueuedAt = nowMs;
  };
  if (failing) {
    s.okStreak = 0;
    if (s.status === 'OK') { s.status = 'ALERT'; s.firstAlertAt = nowMs; s.codesKey = key; queue('alert', key); }
    else if (key !== s.codesKey) { s.codesKey = key; queue('alert', key); }
    else if (nowMs - s.lastQueuedAt >= repeatEveryS * 1000) queue('repeat', key);
  } else if (s.status === 'ALERT') {
    s.okStreak += 1;
    if (s.okStreak >= recoveryOks) { queue('recovery', s.codesKey); s.status = 'OK'; s.codesKey = ''; s.okStreak = 0; s.firstAlertAt = nowMs; }
  }
  return { ok: true, state: s };
}
