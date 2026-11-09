// Sanitized service status. Written only when a poll actually completed; read with stale/unknown states.
// No heartbeat is ever invented: the file carries the time of the last completed poll and the last reply, nothing else
// (no keys, addresses of signers, hostnames, raw errors or transaction bytes).
import { readFileSync, writeFileSync, renameSync } from 'node:fs';

export function recordPoll(path, { now = Date.now, lastReplyAt = null, openOps = 0, ok = true } = {}) {
  let prev = {}; try { prev = JSON.parse(readFileSync(path, 'utf8')); } catch {}
  const next = { v: 1, lastPollAt: now(), lastPollOk: !!ok, lastReplyAt: lastReplyAt ?? prev.lastReplyAt ?? null, openOps: Number(openOps) || 0 };
  const tmp = path + '.tmp'; writeFileSync(tmp, JSON.stringify(next)); renameSync(tmp, path); return next;
}
// state: 'unknown' (missing or unreadable file), 'stale' (last completed poll older than staleAfterMs), 'ok' (recent poll that worked), 'degraded' (recent poll that failed)
export function readStatus(path, { now = Date.now, staleAfterMs = 120_000 } = {}) {
  let s; try { s = JSON.parse(readFileSync(path, 'utf8')); } catch { return { state: 'unknown' }; }
  if (!s || s.v !== 1 || !Number.isFinite(s.lastPollAt)) return { state: 'unknown' };
  const age = now() - s.lastPollAt;
  const state = age > staleAfterMs ? 'stale' : s.lastPollOk ? 'ok' : 'degraded';
  return { state, lastPollAt: s.lastPollAt, ageMs: age, lastReplyAt: s.lastReplyAt, openOps: s.openOps };
}
