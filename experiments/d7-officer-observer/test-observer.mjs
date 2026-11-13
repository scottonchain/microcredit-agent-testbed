import { evaluate } from './observer.mjs';
let pass = 0, fail = 0;
const ok = (c, n) => { if (c) pass++; else { fail++; console.log('FAIL', n); } };
const NOW = Date.parse('2026-12-01T12:00:00Z');
const iso = (agoS) => new Date(NOW - agoS * 1000).toISOString();
const expect = { runtimeSha: '9c181672', heartbeatS: 300, pendingBudgetS: 600, pollStaleS: 600, graceBeats: 3 };
const beat = (agoS, o = {}) => ({ t: iso(agoS), ev: 'heartbeat', uptimeS: 5000, intervalS: 300, pollOk: 50, pollErr: 0, handled: 3, reverted: 0, deferred: 0, unavailable: 0, held: 0, handleErr: 0, lastPollOkAgeS: 20, lastPollErrAgeS: null, lastHandledAgeS: 900, inflight: 0, ...o });
const run = (o = {}) => evaluate({ now: NOW, events: [{ t: iso(7000), ev: 'start' }, beat(60)], oldestPendingAgeS: null, runtimeSha: '9c181672', expect, ...o });
const codes = (r) => r.alerts.map((a) => a.code).sort();

ok(run().status === 'OK', 'healthy is OK');
ok(codes(run({ events: [] })).join() === 'HEARTBEAT_MISSING', 'no events: heartbeat missing');
// drill: missed heartbeat / process death
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, beat(1000)] })).includes('HEARTBEAT_MISSING'), 'drill: heartbeat stopped for 1000 s alerts');
ok(!codes(run({ events: [{ t: iso(7000), ev: 'start' }, beat(899)] })).includes('HEARTBEAT_MISSING'), 'just inside 3 beats does not alert');
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, beat(901)] })).includes('HEARTBEAT_MISSING'), 'just outside 3 beats alerts');
// drill: unreadable journal exit
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, beat(400), { t: iso(300), ev: 'state-unreadable', why: 'parse' }] })).includes('JOURNAL_UNREADABLE'), 'drill: unreadable journal alerts');
ok(!codes(run({ events: [{ t: iso(900), ev: 'state-unreadable', why: 'parse' }, { t: iso(500), ev: 'start' }, beat(60)] })).includes('JOURNAL_UNREADABLE'), 'clean restart after unreadable clears it');
// drill: model unavailable
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(120), ev: 'model-unavailable', applicant: 'x', why: 'timeout' }, beat(60, { unavailable: 1 })] })).includes('MODEL_UNAVAILABLE'), 'drill: model unavailable alerts');
ok(!codes(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(9000), ev: 'model-unavailable' }, beat(60)] })).includes('MODEL_UNAVAILABLE'), 'old model failure outside window does not alert');
// drill: ambiguous tx and held reply
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(100), ev: 'send-ambiguous', why: 'receipt' }, beat(60, { deferred: 1, held: 1 })] })).join() === 'AMBIGUOUS_TX,HELD_REPLY', 'drill: ambiguous tx and held count');
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(200), ev: 'earlier-reply-stuck', ageS: 400 }, beat(60, { held: 1 })] })).includes('HELD_REPLY_STUCK'), 'stuck reported');
// poll health and pending age: a heartbeat alone is not enough
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, beat(60, { lastPollOkAgeS: 5000 })] })).includes('POLL_STALLED'), 'beating but not polling alerts');
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, beat(60, { lastPollOkAgeS: null })] })).includes('POLL_STALLED'), 'never polled alerts');
ok(codes(run({ oldestPendingAgeS: 601 })).join() === 'PENDING_AGE', 'pending older than budget alerts even with a healthy heartbeat');
ok(run({ oldestPendingAgeS: 600 }).status === 'OK', 'pending at budget is OK');
ok(codes(run({ oldestPendingAgeS: Number.NaN })).includes('PENDING_AGE_UNREADABLE'), 'unreadable pending age alerts, never silently OK');
// runtime hash
ok(codes(run({ runtimeSha: 'a322d588' })).join() === 'RUNTIME_HASH_MISMATCH', 'old runtime blob alerts');
ok(codes(run({ runtimeSha: null })).join() === 'RUNTIME_HASH_MISMATCH', 'unreported runtime alerts');
// robustness: garbage input never throws and never reads as OK
ok(evaluate({ now: NOW, events: [{ t: 'bad', ev: 'heartbeat' }], oldestPendingAgeS: null, runtimeSha: '9c181672', expect }).status === 'ALERT', 'unparseable heartbeat time is an alert');
ok(evaluate({ now: NOW, events: null, oldestPendingAgeS: null, runtimeSha: '9c181672', expect }).status === 'ALERT', 'null events is an alert');
console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
