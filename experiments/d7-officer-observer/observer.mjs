// Read-only external observer for the credit-desk officer daemon (design draft, source only, nothing deployed).
// It decides OK or ALERT from signals the daemon already emits at the reviewed head (heartbeat, start, state-unreadable,
// earlier-reply-stuck, model-unavailable, send-ambiguous) plus two facts only an outside party can read from the chain:
// the age of the oldest pending desk request and the runtime hash the host reports. It holds no key, signs nothing and
// sends nothing; delivery of an alert to a named owner is the host's job and is checked by the drills in CUTOVER.md.
//
// evaluate({ now, events, oldestPendingAgeS, runtimeSha, expect }) -> { status, alerts: [{ code, detail }] }
//   now:                ms epoch of the check
//   events:             parsed log lines ({ t, ev, ... }) newest last, as many as the observer keeps
//   oldestPendingAgeS:  seconds since the oldest unanswered desk request was made, or null when none is pending (chain read)
//   runtimeSha:         the sha the host says it is running (the reviewed head), or null if unreported
//   expect:             { runtimeSha, heartbeatS (daemon interval), pendingBudgetS, pollStaleS, graceBeats }
const num = (x) => (typeof x === 'number' && Number.isFinite(x) ? x : null);

export function evaluate({ now, events, oldestPendingAgeS, runtimeSha, expect }) {
  const alerts = [];
  const add = (code, detail) => alerts.push({ code, detail });
  const heartbeatS = expect.heartbeatS, graceBeats = expect.graceBeats ?? 3;
  const evs = Array.isArray(events) ? events : [];
  const at = (e) => Date.parse(e.t);
  const last = (name) => { for (let i = evs.length - 1; i >= 0; i--) if (evs[i].ev === name && Number.isFinite(at(evs[i]))) return evs[i]; return null; };

  if (expect.runtimeSha && runtimeSha !== expect.runtimeSha) add('RUNTIME_HASH_MISMATCH', runtimeSha ? 'host reports a different runtime sha' : 'host did not report a runtime sha');

  const unreadable = last('state-unreadable');
  const start = last('start');
  if (unreadable && (!start || at(unreadable) >= at(start))) add('JOURNAL_UNREADABLE', 'daemon exited with code 3 and has not restarted cleanly');

  const beat = last('heartbeat');
  if (!beat) add('HEARTBEAT_MISSING', 'no heartbeat event seen');
  else {
    const ageS = (now - at(beat)) / 1000;
    if (ageS > heartbeatS * graceBeats) add('HEARTBEAT_MISSING', `last heartbeat ${Math.round(ageS)} s ago, limit ${heartbeatS * graceBeats} s (process death looks like this)`);
    // a restart after the last heartbeat with no new beat yet is not death; grace covers it
    const lastPoll = num(beat.lastPollOkAgeS);
    if (lastPoll === null || lastPoll > (expect.pollStaleS ?? 600)) add('POLL_STALLED', 'no successful chain poll within the stale limit at the last heartbeat');
    if ((num(beat.held) ?? 0) > 0) add('HELD_REPLY', `${beat.held} reply held awaiting chain evidence; a person is needed after the stuck limit`);
  }

  if (last('earlier-reply-stuck') && (!last('heartbeat') || at(last('earlier-reply-stuck')) >= at(last('heartbeat')) - heartbeatS * 1000)) add('HELD_REPLY_STUCK', 'earlier-reply-stuck reported recently');

  const recent = (name) => evs.filter((e) => e.ev === name && now - at(e) <= (expect.eventWindowS ?? 3600) * 1000);
  if (recent('model-unavailable').length > 0) add('MODEL_UNAVAILABLE', `${recent('model-unavailable').length} model failure(s) in the window; applicants were told to write again`);
  if (recent('send-ambiguous').length > 0) add('AMBIGUOUS_TX', `${recent('send-ambiguous').length} send(s) with unknown broadcast outcome in the window`);

  if (oldestPendingAgeS !== null && oldestPendingAgeS !== undefined) {
    if (num(oldestPendingAgeS) === null) add('PENDING_AGE_UNREADABLE', 'chain read of the oldest pending request failed');
    else if (oldestPendingAgeS > expect.pendingBudgetS) add('PENDING_AGE', `oldest pending request is ${Math.round(oldestPendingAgeS)} s old, budget ${expect.pendingBudgetS} s`);
  }
  return { status: alerts.length ? 'ALERT' : 'OK', alerts };
}
