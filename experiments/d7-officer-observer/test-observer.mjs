import { evaluate, RANGES, DEFAULTS } from './observer.mjs';
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

// ranges: every knob rejected below min and above max, accepted at min and max (CONFIG_INVALID only; other alerts are not the point)
const cfgOnly = (e) => codes(evaluate({ now: NOW, events: [{ t: iso(7000), ev: 'start' }, beat(60)], pending: emptyQueue, runtimeSha: '9c181672', expect: e })).includes('CONFIG_INVALID');
const base = { runtimeSha: '9c181672', heartbeatS: 60, pendingBudgetS: 600 };
// the documented ranges are pinned here as literals, so changing the module's table cannot quietly change what is tested
const EXPECTED_RANGES = { heartbeatS: [10, 3600], pendingBudgetS: [60, 86400], graceBeats: [1, 10, true], pollStaleS: [60, 86400], eventWindowS: [10, 86400], clockSkewS: [1, 300], pendingFreshS: [10, 3600] };
ok(JSON.stringify(RANGES) === JSON.stringify(EXPECTED_RANGES), 'the module range table equals the documented table');
for (const [k, [lo, hi, int]] of Object.entries(EXPECTED_RANGES)) {
  // pick a base where the relation checks cannot interfere: heartbeatS 60, grace 3, pollStaleS 600, eventWindowS 3600
  const mk = (v) => ({ ...base, [k]: v });
  const loOk = k === 'heartbeatS' ? lo : lo, hiOk = hi;
  if (k === 'pollStaleS') { ok(!cfgOnly({ ...base, heartbeatS: 10, pollStaleS: lo }), `pollStaleS min ${lo} accepted (heartbeatS 10)`); }
  else if (k === 'eventWindowS') { ok(!cfgOnly({ ...base, heartbeatS: 10, eventWindowS: lo }), `eventWindowS min ${lo} accepted (heartbeatS 10)`); }
  else if (k === 'heartbeatS') { ok(!cfgOnly(mk(lo)), `heartbeatS min ${lo} accepted`); }
  else ok(!cfgOnly(mk(lo)), `${k} min ${lo} accepted`);
  ok(cfgOnly(mk(lo - (int ? 1 : Math.max(lo * 0.1, 0.001)))), `${k} below min ${lo} rejected`);
  if (k === 'heartbeatS') ok(cfgOnly({ ...base, heartbeatS: hi + 1 }), `${k} above max ${hi} rejected`);
  else ok(cfgOnly(mk(hi + (int ? 1 : Math.max(hi * 0.1, 1)))), `${k} above max ${hi} rejected`);
}
ok(!cfgOnly({ ...base, heartbeatS: 3600, graceBeats: 1, pollStaleS: 3600 }), 'heartbeatS 3600 with grace 1 is exactly the silence cap and accepted');
ok(!cfgOnly({ ...base, pendingBudgetS: 86400 }), 'pendingBudgetS max accepted');
ok(cfgOnly({ ...base, heartbeatS: 1000, graceBeats: 4, pollStaleS: 1000 }), 'silence cap alone: 1000 x 4 = 4000 s rejected when every other relation holds');
ok(!cfgOnly({ ...base, heartbeatS: 900, graceBeats: 4, pollStaleS: 900 }), 'silence cap alone: 900 x 4 = 3600 s accepted');
ok(cfgOnly({ ...base, graceBeats: 11 }), 'graceBeats 11 rejected at a small heartbeat where the cap is not the reason');
ok(cfgOnly({ ...base, clockSkewS: 301 }), 'clockSkewS 301 rejected');
ok(cfgOnly({ ...base, pendingBudgetS: 86401 }), 'pendingBudgetS 86401 rejected');
ok(!cfgOnly({ ...base, graceBeats: 10, heartbeatS: 360 }), 'grace 10 at heartbeat 360 is exactly 3600 and accepted');
ok(!cfgOnly({ ...base, pollStaleS: 86400, eventWindowS: 86400, pendingFreshS: 3600, clockSkewS: 300, graceBeats: 10, heartbeatS: 360 }), 'all maxima together accepted');
// the exact probes from the reviews: each used to return OK for a bad input and is now CONFIG_INVALID
const probe = (e, ev, pend) => evaluate({ now: NOW, events: [{ t: iso(90000), ev: 'start' }, ev], pending: pend ?? emptyQueue, runtimeSha: '9c181672', expect: { ...base, ...e } });
ok(codes(probe({ graceBeats: 1e9 }, beat(86400))).join() === 'CONFIG_INVALID', 'probe: graceBeats 1e9 with a 24 h-old heartbeat');
ok(codes(probe({ pollStaleS: 1e12 }, beat(60, { lastPollOkAgeS: 1e6 }))).join() === 'CONFIG_INVALID', 'probe: pollStaleS 1e12');
ok(codes(probe({ pendingBudgetS: 1e12 }, beat(60), { ok: true, oldestAgeS: 1e7, readAt: NOW })).join() === 'CONFIG_INVALID', 'probe: pendingBudgetS 1e12');
ok(codes(probe({ pendingFreshS: 1e12 }, beat(60), { ok: true, oldestAgeS: null, readAt: NOW - 1e9 })).join() === 'CONFIG_INVALID', 'probe: pendingFreshS 1e12');
ok(codes(probe({ eventWindowS: 1e-9 }, beat(60))).join() === 'CONFIG_INVALID', 'probe: eventWindowS 1e-9');
ok(codes(probe({ clockSkewS: 1e12 }, beat(-1e9))).join() === 'CONFIG_INVALID', 'probe: clockSkewS 1e12 with a far-future heartbeat');
// fractional grace is explicitly rejected, as are non-integers just inside the range
for (const g of [1.5, 2.5, 0.5, 3.0000001]) ok(cfgOnly({ ...base, graceBeats: g }), `fractional graceBeats ${g} rejected`);
ok(!cfgOnly({ ...base, graceBeats: 3 }), 'integer graceBeats accepted');
// relations between knobs, including through defaults
ok(cfgOnly({ ...base, heartbeatS: 3600 }), 'heartbeatS 3600 with the default grace 3 exceeds the silence cap');
ok(cfgOnly({ ...base, heartbeatS: 1000 }), 'heartbeatS 1000 with default grace 3 (3000 s) and default pollStaleS 600 < heartbeatS is rejected');
ok(cfgOnly({ ...base, heartbeatS: 360, graceBeats: 10, pollStaleS: 300 }), 'pollStaleS below heartbeatS rejected');
ok(cfgOnly({ ...base, heartbeatS: 300, eventWindowS: 299 }), 'eventWindowS below heartbeatS rejected');
ok(!cfgOnly({ ...base, heartbeatS: 300, eventWindowS: 300 }), 'eventWindowS equal to heartbeatS accepted');
ok(!cfgOnly({ ...base }), 'defaults alone are inside every range and relation');
ok(!cfgOnly({ ...base, heartbeatS: 600, graceBeats: 6 }), 'heartbeat 600 x grace 6 = 3600 accepted');
ok(cfgOnly({ ...base, heartbeatS: 601, graceBeats: 6 }), 'heartbeat 601 x grace 6 = 3606 rejected');
ok(Object.values(DEFAULTS).every((v) => typeof v === 'number'), 'defaults are numbers');
// event ordering is pinned: newest timestamp wins whatever the array order
const ordered = [{ t: iso(7000), ev: 'start' }, beat(900), beat(60)];
const shuffled = [beat(60), { t: iso(7000), ev: 'start' }, beat(900)];
ok(JSON.stringify(run({ events: ordered })) === JSON.stringify(run({ events: shuffled })), 'array order does not change the result');
ok(run({ events: [beat(60), beat(900)] }).status === 'OK', 'a stale heartbeat listed last no longer causes a false alert');
ok(run({ events: [beat(900), beat(60, { held: 2 })] }).alerts.some((a) => a.code === 'HELD_REPLY'), 'the newest heartbeat by time is the one used');
ok(!has(run({ events: [{ t: iso(500), ev: 'start' }, { t: iso(900), ev: 'state-unreadable' }, beat(60)] }), 'JOURNAL_UNREADABLE'), 'unreadable-then-start clears regardless of array order');
console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
