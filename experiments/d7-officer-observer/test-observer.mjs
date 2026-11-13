import { evaluate } from './observer.mjs';
let pass = 0, fail = 0;
const ok = (c, n) => { if (c) pass++; else { fail++; console.log('FAIL', n); } };
const NOW = Date.parse('2026-12-01T12:00:00Z');
const iso = (agoS) => new Date(NOW - agoS * 1000).toISOString();
const expect = { runtimeSha: '9c181672', heartbeatS: 300, pendingBudgetS: 600, pollStaleS: 600, graceBeats: 3 };
const beat = (agoS, o = {}) => ({ t: iso(agoS), ev: 'heartbeat', uptimeS: 5000, intervalS: 300, pollOk: 50, pollErr: 0, handled: 3, reverted: 0, deferred: 0, unavailable: 0, held: 0, handleErr: 0, lastPollOkAgeS: 20, lastPollErrAgeS: null, lastHandledAgeS: 900, inflight: 0, ...o });
const emptyQueue = { ok: true, oldestAgeS: null, readAt: NOW - 10000 };
const run = (o = {}) => evaluate({ now: NOW, events: [{ t: iso(7000), ev: 'start' }, beat(60)], pending: emptyQueue, runtimeSha: '9c181672', expect, ...o });
const codes = (r) => r.alerts.map((a) => a.code).sort();
const has = (r, c) => codes(r).includes(c);

// controls: a healthy system is OK, and every probe below changes exactly one thing
ok(run().status === 'OK', 'healthy is OK');
ok(codes(run({ events: [] })).includes('HEARTBEAT_MISSING'), 'no events: heartbeat missing');
// drills: missed heartbeat, process death, journal, model, ambiguous tx, held reply
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(1000)] }), 'HEARTBEAT_MISSING'), 'drill: heartbeat stopped 1000 s');
ok(!has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(899)] }), 'HEARTBEAT_MISSING'), 'just inside 3 beats');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(901)] }), 'HEARTBEAT_MISSING'), 'just outside 3 beats');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(400), { t: iso(300), ev: 'state-unreadable', why: 'parse' }] }), 'JOURNAL_UNREADABLE'), 'drill: unreadable journal');
ok(!has(run({ events: [{ t: iso(900), ev: 'state-unreadable', why: 'parse' }, { t: iso(500), ev: 'start' }, beat(60)] }), 'JOURNAL_UNREADABLE'), 'clean restart clears unreadable');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(120), ev: 'model-unavailable', applicant: 'x', why: 'timeout' }, beat(60, { unavailable: 1 })] }), 'MODEL_UNAVAILABLE'), 'drill: model unavailable');
ok(!has(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(9000), ev: 'model-unavailable' }, beat(60)] }), 'MODEL_UNAVAILABLE'), 'old model failure outside window');
ok(codes(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(100), ev: 'send-ambiguous', why: 'receipt' }, beat(60, { deferred: 1, held: 1 })] })).join() === 'AMBIGUOUS_TX,HELD_REPLY', 'drill: ambiguous tx and held count');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(200), ev: 'earlier-reply-stuck', ageS: 400 }, beat(60, { held: 1 })] }), 'HELD_REPLY_STUCK'), 'stuck reported');
// poll health: a heartbeat alone is not enough, and poll age is the beat age PLUS the reported poll age
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(60, { lastPollOkAgeS: 5000 })] }), 'POLL_STALLED'), 'beating but not polling');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(60, { lastPollOkAgeS: null })] }), 'POLL_STALLED'), 'never polled');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(500, { lastPollOkAgeS: 500 })] }), 'POLL_STALLED'), 'regression: 500 s-old beat reporting a 500 s-old poll is 1000 s, not under 600');
ok(!has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(200, { lastPollOkAgeS: 300 })] }), 'POLL_STALLED'), 'control: 200 + 300 s is inside 600');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(60, { lastPollOkAgeS: -5 })] }), 'POLL_STALLED'), 'negative poll age is unreadable');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(60, { lastPollOkAgeS: 'x' })] }), 'POLL_STALLED'), 'non-numeric poll age is unreadable');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(60, { held: 'many' })] }), 'EVENT_INVALID'), 'non-numeric held count flagged');
// pending queue read: explicit, fresh, sane
ok(codes(run({ pending: { ok: true, oldestAgeS: 601, readAt: NOW } })).join() === 'PENDING_AGE', 'pending older than budget even with a healthy heartbeat');
ok(run({ pending: { ok: true, oldestAgeS: 600, readAt: NOW } }).status === 'OK', 'pending exactly at budget is OK');
ok(has(run({ pending: { ok: true, oldestAgeS: 500, readAt: NOW - 130000 } }), 'PENDING_STALE'), 'stale read alerts');
ok(has(run({ pending: { ok: true, oldestAgeS: 500, readAt: NOW - 130000 } }), 'PENDING_STALE') && !has(run({ pending: { ok: true, oldestAgeS: 500, readAt: NOW - 130000 } }), 'PENDING_AGE'), 'stale read does not also claim an age');
ok(has(run({ pending: { ok: true, oldestAgeS: 560, readAt: NOW - 130000 } }), 'PENDING_STALE'), 'stale read near budget');
ok(has(run({ pending: { ok: true, oldestAgeS: 590, readAt: NOW - 50000 } }), 'PENDING_STALE') === false && has(run({ pending: { ok: true, oldestAgeS: 590, readAt: NOW - 50000 } }), 'PENDING_AGE'), 'fresh read adds its own age: 590 + 50 > 600');
ok(has(run({ pending: undefined }), 'PENDING_UNREADABLE'), 'regression: undefined pending is unknown, not empty');
ok(has(run({ pending: null }), 'PENDING_UNREADABLE'), 'null pending object is unreadable');
ok(has(run({ pending: { ok: false } }), 'PENDING_UNREADABLE'), 'failed chain read alerts');
ok(has(run({ pending: { ok: true, oldestAgeS: null } }), 'PENDING_UNREADABLE'), 'empty-queue claim without a read time alerts');
ok(has(run({ pending: { oldestAgeS: null, readAt: NOW } }), 'PENDING_UNREADABLE'), 'ok flag missing alerts');
ok(has(run({ pending: { ok: true, oldestAgeS: undefined, readAt: NOW } }), 'PENDING_INVALID'), 'oldest age omitted while ok alerts');
ok(has(run({ pending: { ok: true, oldestAgeS: -5, readAt: NOW } }), 'PENDING_INVALID'), 'negative pending age alerts');
ok(has(run({ pending: { ok: true, oldestAgeS: Number.NaN, readAt: NOW } }), 'PENDING_INVALID'), 'NaN pending age alerts');
ok(has(run({ pending: { ok: true, oldestAgeS: null, readAt: NOW + 999999000 } }), 'FUTURE_EVIDENCE'), 'queue read from the future alerts');
ok(run({ pending: { ok: true, oldestAgeS: null, readAt: NOW } }).status === 'OK', 'control: confirmed-empty fresh read is OK');
// runtime hash
ok(codes(run({ runtimeSha: 'a322d588' })).join() === 'RUNTIME_HASH_MISMATCH', 'old runtime blob alerts');
ok(codes(run({ runtimeSha: null })).join() === 'RUNTIME_HASH_MISMATCH', 'unreported runtime alerts');
// configuration: every missing or invalid value is CONFIG_INVALID, never green
const cfg = (e, o = {}) => evaluate({ now: NOW, events: [{ t: iso(7000), ev: 'start' }, beat(5000)], pending: { ok: true, oldestAgeS: 99999, readAt: NOW }, runtimeSha: 'a322d588', expect: e, ...o });
ok(codes(cfg({})).join() === 'CONFIG_INVALID', 'regression: expect = {} with a 5000 s-old beat is CONFIG_INVALID');
ok(codes(cfg({ heartbeatS: 300 })).join() === 'CONFIG_INVALID', 'regression: no pendingBudgetS is CONFIG_INVALID');
ok(codes(cfg({ heartbeatS: 300, pendingBudgetS: 600 })).join() === 'CONFIG_INVALID', 'regression: omitted runtimeSha expectation is CONFIG_INVALID, not a skipped hash check');
ok(codes(cfg({ ...expect, runtimeSha: '' })).join() === 'CONFIG_INVALID', 'empty runtimeSha expectation');
ok(codes(cfg(undefined)).join() === 'CONFIG_INVALID', 'expect undefined is CONFIG_INVALID, not a throw');
ok(codes(cfg(null)).join() === 'CONFIG_INVALID', 'expect null');
ok(codes(cfg('x')).join() === 'CONFIG_INVALID', 'expect a string');
ok(codes(cfg(expect, { now: Number.NaN })).join() === 'CONFIG_INVALID', 'regression: now = NaN is CONFIG_INVALID');
ok(codes(cfg(expect, { now: undefined })).join() === 'CONFIG_INVALID', 'now omitted');
ok(codes(cfg(expect, { now: '2026-12-01' })).join() === 'CONFIG_INVALID', 'now as a string');
for (const k of ['heartbeatS', 'pendingBudgetS']) for (const v of [0, -1, Number.NaN, Infinity, '300', null]) ok(codes(cfg({ ...expect, [k]: v })).join() === 'CONFIG_INVALID', `${k} = ${String(v)} is CONFIG_INVALID`);
for (const k of ['graceBeats', 'pollStaleS', 'eventWindowS', 'clockSkewS', 'pendingFreshS']) for (const v of [0, -5, Number.NaN, Infinity, 'x', null]) ok(codes(cfg({ ...expect, [k]: v })).join() === 'CONFIG_INVALID', `optional ${k} = ${String(v)} is CONFIG_INVALID`);
ok(cfg({ ...expect }).status === 'ALERT' && !codes(cfg({ ...expect })).includes('CONFIG_INVALID'), 'control: valid config is evaluated normally');
ok(run({ expect: { runtimeSha: '9c181672', heartbeatS: 300, pendingBudgetS: 600 } }).status === 'OK', 'control: optional values may be omitted');
// future evidence and clock skew
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(-999999), ev: 'heartbeat', lastPollOkAgeS: 1 }] }), 'FUTURE_EVIDENCE'), 'regression: heartbeat 999999 s in the future alerts');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, { t: iso(-999999), ev: 'heartbeat', lastPollOkAgeS: 1 }] }), 'HEARTBEAT_MISSING'), 'a future heartbeat is not liveness evidence');
ok(run({ events: [{ t: iso(7000), ev: 'start' }, beat(-30)] }).status === 'OK', 'control: 30 s of clock skew inside the 60 s bound is tolerated');
ok(has(run({ events: [{ t: iso(7000), ev: 'start' }, beat(-61)] }), 'FUTURE_EVIDENCE'), '61 s ahead exceeds the skew bound');
ok(has(run({ events: [{ t: iso(-5000), ev: 'state-unreadable' }, { t: iso(7000), ev: 'start' }, beat(60)] }), 'FUTURE_EVIDENCE'), 'future non-heartbeat event alerts too');
// malformed events never crash and never read as OK
ok(evaluate({ now: NOW, events: [{ t: 'bad', ev: 'heartbeat' }], pending: emptyQueue, runtimeSha: '9c181672', expect }).status === 'ALERT', 'unparseable time is an alert');
ok(has(evaluate({ now: NOW, events: null, pending: emptyQueue, runtimeSha: '9c181672', expect }), 'EVENT_INVALID'), 'regression: null events is EVENT_INVALID, not a throw');
ok(has(evaluate({ now: NOW, events: 'x', pending: emptyQueue, runtimeSha: '9c181672', expect }), 'EVENT_INVALID'), 'events as a string');
ok(has(run({ events: [null, { t: iso(7000), ev: 'start' }, beat(60)] }), 'EVENT_INVALID'), 'null entry among events flagged');
ok(run({ events: [null, { t: iso(7000), ev: 'start' }, beat(60)] }).status === 'ALERT', 'a malformed entry keeps the result ALERT');
ok(has(run({ events: [42, 'x', {}, { t: iso(7000), ev: 'start' }, beat(60)] }), 'EVENT_INVALID'), 'non-object and empty entries flagged');
ok(has(run({ events: [{ ev: 'heartbeat' }, { t: iso(7000), ev: 'start' }, beat(60)] }), 'EVENT_INVALID'), 'event without a time flagged');
ok(has(run({ events: [{ t: iso(7000) }, beat(60)] }), 'EVENT_INVALID'), 'event without a name flagged');
// the observer never throws, whatever it is given
for (const bad of [undefined, null, 5, 'x', [], {}]) { let threw = false, r; try { r = evaluate(bad); } catch { threw = true; } ok(!threw && r && r.status === 'ALERT', `evaluate(${JSON.stringify(bad)}) alerts without throwing`); }
const hostile = { now: NOW, get events() { throw new TypeError('boom'); }, pending: emptyQueue, runtimeSha: '9c181672', expect };
ok(codes(evaluate(hostile)).join() === 'OBSERVER_FAILURE', 'an internal throw becomes OBSERVER_FAILURE');
console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
