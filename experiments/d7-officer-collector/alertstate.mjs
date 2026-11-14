// Alert delivery state: dedup, undelivered retry and recovery. Pure functions over a plain-object state; no I/O and no sending.
// The caller sends what toSend() returns and calls ack(state, key) only after the delivery succeeded. An unacknowledged item
// is returned again at every step, so a failed delivery is retried, never lost. Items carry a stable idempotency key.
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
export const newState = () => ({ status: 'OK', codesKey: '', firstAlertAt: null, lastQueuedAt: null, okStreak: 0, pending: [] });
const clone = (s) => JSON.parse(JSON.stringify(s));
export const toSend = (state) => state.pending.map((p) => ({ ...p }));
export function ack(state, key) { const s = clone(state); s.pending = s.pending.filter((p) => p.key !== key); return s; }

export function step(state, result, nowMs, { repeatEveryS = 3600, recoveryOks = 2 } = {}) {
  if (!isNum(nowMs) || !(isNum(repeatEveryS) && repeatEveryS > 0) || !(Number.isInteger(recoveryOks) && recoveryOks >= 1)) throw new RangeError('invalid alert-state parameters');
  const s = clone(state);
  const codes = [...new Set((result && Array.isArray(result.alerts) ? result.alerts : []).map((a) => String(a.code)))].sort();
  const usable = !!result && typeof result === 'object' && Array.isArray(result.alerts) && (result.status === 'OK' || result.status === 'ALERT');
  const failing = codes.length > 0 || !usable || result.status !== 'OK'; // an unusable or inconsistent result is never a recovery
  const key = codes.length ? codes.join(',') : (failing ? 'UNUSABLE_RESULT' : '');
  const queue = (kind, kk, extra = {}) => { const id = `${kind}:${kk}:${s.firstAlertAt}`; if (!s.pending.some((p) => p.key === id)) s.pending.push({ key: id, kind, codes: kk ? kk.split(',') : [], at: nowMs, ...extra }); s.lastQueuedAt = nowMs; };
  if (failing) {
    s.okStreak = 0;
    if (s.status === 'OK') { s.status = 'ALERT'; s.firstAlertAt = nowMs; s.codesKey = key; queue('alert', key); }
    else if (key !== s.codesKey) { s.codesKey = key; queue('alert', key); }
    else if (nowMs - s.lastQueuedAt >= repeatEveryS * 1000) queue('repeat', key);
  } else if (s.status === 'ALERT') {
    s.okStreak += 1;
    if (s.okStreak >= recoveryOks) { queue('recovery', s.codesKey); s.status = 'OK'; s.codesKey = ''; s.okStreak = 0; s.firstAlertAt = nowMs; }
  }
  return s;
}
