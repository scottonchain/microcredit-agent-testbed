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
//   events:      array of parsed log lines ({ t, ev, ... }) newest last
//   pending:     the chain-read outcome, always explicit: { ok: true, oldestAgeS: number|null, readAt: ms }
//                oldestAgeS null means a successful read found NO pending request; a failed read is { ok: false } or
//                anything else. Undefined or missing is unknown, never "empty".
//   runtimeSha:  the sha the host says it is running, or null if unreported
//   expect:      required { runtimeSha, heartbeatS, pendingBudgetS }; optional finite positive numbers
//                { graceBeats (3), pollStaleS (600), eventWindowS (3600), clockSkewS (60), pendingFreshS (120) }
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const pos = (x) => isNum(x) && x > 0;

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
  if (!expect || typeof expect !== 'object') bad.push('expect');
  else {
    if (typeof expect.runtimeSha !== 'string' || expect.runtimeSha.length === 0) bad.push('expect.runtimeSha');
    for (const k of ['heartbeatS', 'pendingBudgetS']) if (!pos(expect[k])) bad.push(`expect.${k}`);
    for (const k of ['graceBeats', 'pollStaleS', 'eventWindowS', 'clockSkewS', 'pendingFreshS']) if (expect[k] !== undefined && !pos(expect[k])) bad.push(`expect.${k}`);
  }
  if (bad.length) return { status: 'ALERT', alerts: [{ code: 'CONFIG_INVALID', detail: `invalid or missing: ${bad.join(', ')}` }] };

  const heartbeatS = expect.heartbeatS, grace = expect.graceBeats ?? 3, skewS = expect.clockSkewS ?? 60;
  const staleS = expect.pollStaleS ?? 600, windowS = expect.eventWindowS ?? 3600, freshS = expect.pendingFreshS ?? 120;

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
