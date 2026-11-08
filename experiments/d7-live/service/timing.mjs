// Bounded timeouts and restart backoff.
export class Timeout extends Error { constructor(label, ms) { super(`${label} timed out after ${ms} ms`); this.name = 'Timeout'; } }
export function withTimeout(promise, ms, label = 'call', { setTimer = setTimeout, clearTimer = clearTimeout } = {}) {
  let t;
  const timer = new Promise((_, rej) => { t = setTimer(() => rej(new Timeout(label, ms)), ms); });
  return Promise.race([promise, timer]).finally(() => clearTimer(t));
}
// Exponential backoff with a cap and bounded jitter; attempt starts at 0. rng injected for tests.
export function backoffMs(attempt, { baseMs = 1000, capMs = 60_000, jitter = 0.2, rng = Math.random } = {}) {
  const raw = Math.min(capMs, baseMs * 2 ** Math.max(0, attempt));
  return Math.min(capMs, Math.round(raw * (1 - jitter + 2 * jitter * rng())));
}
