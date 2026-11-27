// Read-only external observer for the credit-desk officer daemon (design draft, source only, nothing deployed).
// It decides OK or ALERT from signals the daemon already emits at the reviewed head (heartbeat, start, state-unreadable,
// earlier-reply-stuck, model-unavailable, send-ambiguous) plus two facts only an outside party can read from the chain:
// the age of the oldest pending desk request and the runtime hash the host reports. It holds no key, signs nothing and
// sends nothing; delivery of an alert to a named owner is the host's job and is checked by the drills in CUTOVER.md.
//
// Fail-closed rule: anything missing, malformed, stale, from the future or not provably fine is an ALERT. The function never
// throws; if the observer itself breaks the result is ALERT with OBSERVER_FAILURE, and the caller must also alert when
// evaluate() is not called or does not return at all (see the observer-execution-failure drill in CUTOVER.md).
//
// evaluate({ now, events, pending, runtimeSha, expect }) -> { status: 'OK'|'ALERT', alerts: [{ code, detail }] }
//   now:         ms epoch of the check (finite number)
//   events:      array of parsed log lines ({ t, ev, ... }) in any order; the newest TIMESTAMP wins, not the last array entry
//   pending:     the chain-read outcome, always explicit: { ok: true, oldestAgeS: number|null, readAt: ms }
//                oldestAgeS null means a successful read found NO pending request; a failed read is { ok: false } or
//                anything else. Undefined or missing is unknown, never "empty".
//   runtimeSha:  the sha the host says it is running, or null if unreported
//   expect:      required { runtimeSha, heartbeatS, pendingBudgetS }; optional { graceBeats (3), pollStaleS (600),
//                eventWindowS (3600), clockSkewS (60), pendingFreshS (120) }. Every value, defaults included, must lie in
//                RANGES below or the result is CONFIG_INVALID. Out-of-range values are rejected, never clamped, because a
//                typo that silences a check is the failure this monitor exists to prevent.
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const inRange = (x, lo, hi, int) => isNum(x) && x >= lo && x <= hi && (!int || Number.isInteger(x));
// Operational ranges (seconds unless stated). graceBeats is a whole number of missed beats. MAX_SILENCE_S bounds heartbeatS * graceBeats.
export const RANGES = {
  heartbeatS: [10, 3600], pendingBudgetS: [60, 86400], graceBeats: [1, 10, true], pollStaleS: [60, 86400],
  eventWindowS: [10, 86400], clockSkewS: [1, 300], pendingFreshS: [10, 3600],
};
export const DEFAULTS = { graceBeats: 3, pollStaleS: 600, eventWindowS: 3600, clockSkewS: 60, pendingFreshS: 120 };
const MAX_SILENCE_S = 3600;

export function evaluate(input) {
  try { return run(input); } catch (e) { return { status: 'ALERT', alerts: [{ code: 'OBSERVER_FAILURE', detail: `observer threw ${e && e.name ? e.name : 'an error'}` }] }; }
}

function run(input) {
  const alerts = [];
  const add = (code, detail) => alerts.push({ code, detail });
  const { now, events, pending, runtimeSha, expect } = input && typeof input === 'object' ? input : {};

  // 1. configuration: a typo must make the monitor loud, never permanently green
  const bad = [];
  if (!isNum(now)) bad.push('now');
  let heartbeatS, grace, skewS, staleS, windowS, freshS;
  if (!expect || typeof expect !== 'object') bad.push('expect');
  else {
    if (typeof expect.runtimeSha !== 'string' || expect.runtimeSha.length === 0) bad.push('expect.runtimeSha');
    const dv = (v, d) => (v === undefined ? d : v); // only a missing value takes the default; null or anything else supplied is validated
    heartbeatS = expect.heartbeatS; grace = dv(expect.graceBeats, DEFAULTS.graceBeats); skewS = dv(expect.clockSkewS, DEFAULTS.clockSkewS);
    staleS = dv(expect.pollStaleS, DEFAULTS.pollStaleS); windowS = dv(expect.eventWindowS, DEFAULTS.eventWindowS); freshS = dv(expect.pendingFreshS, DEFAULTS.pendingFreshS);
    const eff = { heartbeatS, pendingBudgetS: expect.pendingBudgetS, graceBeats: grace, pollStaleS: staleS, eventWindowS: windowS, clockSkewS: skewS, pendingFreshS: freshS };
    for (const [k, [lo, hi, int]] of Object.entries(RANGES)) if (!inRange(eff[k], lo, hi, int)) bad.push(`expect.${k}`);
    if (!bad.length) {
      // relations between knobs, checked on the effective values so defaults cannot hide a bad combination
      if (heartbeatS * grace > MAX_SILENCE_S) bad.push('heartbeatS*graceBeats');
      if (staleS < heartbeatS) bad.push('pollStaleS<heartbeatS');
      if (windowS < heartbeatS) bad.push('eventWindowS<heartbeatS');
    }
  }
  if (bad.length) return { status: 'ALERT', alerts: [{ code: 'CONFIG_INVALID', detail: `invalid, missing or out of range: ${bad.join(', ')}` }] };

  if (runtimeSha !== expect.runtimeSha) add('RUNTIME_HASH_MISMATCH', runtimeSha ? 'host reports a different runtime sha' : 'host did not report a runtime sha');

  // 2. events: validate shape and time; malformed and future events are alerts and are never used as evidence
  if (!Array.isArray(events)) add('EVENT_INVALID', 'events is not an array');
  const evs = [];
  let malformed = 0, future = 0;
  for (const e of Array.isArray(events) ? events : []) {
    const t = e && typeof e === 'object' && typeof e.ev === 'string' && typeof e.t === 'string' ? Date.parse(e.t) : NaN;
    if (!Number.isFinite(t)) { malformed++; continue; }
    if (t > now + skewS * 1000) { future++; continue; }
    evs.push({ ...e, at: t });
  }
  if (malformed) add('EVENT_INVALID', `${malformed} event(s) with a missing name or unparseable time were ignored`);
  if (future) add('FUTURE_EVIDENCE', `${future} event(s) dated more than ${skewS} s ahead of now were ignored (clock skew or bad data)`);
  evs.sort((a, b) => a.at - b.at); // order of arrival does not matter: 'newest' means newest timestamp
  const last = (name) => { for (let i = evs.length - 1; i >= 0; i--) if (evs[i].ev === name) return evs[i]; return null; };
  const ageOf = (t) => Math.max(0, (now - t) / 1000);

  const unreadable = last('state-unreadable'), start = last('start');
  if (unreadable && (!start || unreadable.at >= start.at)) add('JOURNAL_UNREADABLE', 'daemon exited with code 3 and has not restarted cleanly');

  // 3. liveness and polling: current poll age is the beat's age plus the poll age it reported, not the reported value alone
  const beat = last('heartbeat');
  if (!beat) add('HEARTBEAT_MISSING', 'no usable heartbeat event seen');
  else {
    const beatAge = ageOf(beat.at);
    if (beatAge > heartbeatS * grace) add('HEARTBEAT_MISSING', `last heartbeat ${Math.round(beatAge)} s ago, limit ${heartbeatS * grace} s (process death looks like this)`);
    const reported = beat.lastPollOkAgeS;
    if (!isNum(reported) || reported < 0) add('POLL_STALLED', 'heartbeat reports no successful chain poll or an unreadable poll age');
    else if (beatAge + reported > staleS) add('POLL_STALLED', `last successful poll is about ${Math.round(beatAge + reported)} s old, limit ${staleS} s`);
    if (beat.held !== undefined && (!isNum(beat.held) || beat.held < 0)) add('EVENT_INVALID', 'heartbeat held count is not a non-negative number');
    else if ((beat.held ?? 0) > 0) add('HELD_REPLY', `${beat.held} reply held awaiting chain evidence; a person is needed after the stuck limit`);
  }
  const stuck = last('earlier-reply-stuck');
  if (stuck && (!beat || stuck.at >= beat.at - heartbeatS * 1000)) add('HELD_REPLY_STUCK', 'earlier-reply-stuck reported recently');

  const recent = (name) => evs.filter((e) => e.ev === name && ageOf(e.at) <= windowS);
  if (recent('model-unavailable').length) add('MODEL_UNAVAILABLE', `${recent('model-unavailable').length} model failure(s) in the window; applicants were told to write again`);
  if (recent('send-ambiguous').length) add('AMBIGUOUS_TX', `${recent('send-ambiguous').length} send(s) with unknown broadcast outcome in the window`);

  // 4. the chain read of the oldest pending request: explicit, fresh and sane, or an alert
  if (!pending || typeof pending !== 'object' || pending.ok !== true || !isNum(pending.readAt)) add('PENDING_UNREADABLE', 'no successful, timestamped chain read of the pending queue');
  else if (pending.readAt > now + skewS * 1000) add('FUTURE_EVIDENCE', 'pending queue read is dated in the future');
  else if (ageOf(pending.readAt) > freshS) add('PENDING_STALE', `pending queue read is ${Math.round(ageOf(pending.readAt))} s old, limit ${freshS} s`);
  else if (pending.oldestAgeS !== null) {
    if (!isNum(pending.oldestAgeS) || pending.oldestAgeS < 0) add('PENDING_INVALID', 'oldest pending age is missing, negative or not a number');
    else if (pending.oldestAgeS + ageOf(pending.readAt) > expect.pendingBudgetS) add('PENDING_AGE', `oldest pending request is about ${Math.round(pending.oldestAgeS + ageOf(pending.readAt))} s old, budget ${expect.pendingBudgetS} s`);
  }
  return { status: alerts.length ? 'ALERT' : 'OK', alerts };
}
