// Offline test of the desk daemon's observability events (heartbeat and exit). No chain, no key, no model: a stub JSON-RPC
// server answers the daemon's reads (test-stub-desk.mjs), and the daemon runs in MODE=rules with a throwaway key.
//   node test-daemon-observability.mjs
import { run } from './test-stub-desk.mjs';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const HB_KEYS = ['t', 'ev', 'uptimeS', 'intervalS', 'pollOk', 'pollErr', 'handled', 'reverted', 'deferred', 'unavailable', 'handleErr', 'lastPollOkAgeS', 'lastPollErrAgeS', 'lastHandledAgeS', 'inflight'];
const EX_KEYS = ['t', 'ev', 'reason', 'uptimeS', 'lastPollOkAgeS', 'signal', 'kind', 'code'];

// 1. healthy poll, SIGTERM
{ const r = await run({ how: 'term' }); const hb = r.lines.filter((l) => l.ev === 'heartbeat'); const ex = r.lines.filter((l) => l.ev === 'exit');
  ok(r.lines[0].ev === 'start', 'start event first');
  ok(hb.length >= 1 && hb.length <= 8, 'heartbeat is rate bounded and present: ' + hb.length);
  ok(hb.every((h) => Object.keys(h).every((k) => HB_KEYS.includes(k))), 'heartbeat has only whitelisted keys');
  ok(hb.some((h) => h.pollOk > 0) && hb.every((h) => h.pollErr === 0), 'poll success counted, no poll errors');
  // the first heartbeat can fire before the first poll has returned (pollOk 0, age null: no successful poll yet); every heartbeat that counts a successful poll must carry a small age
  ok(hb.filter((h) => h.pollOk > 0).length > 0 && hb.filter((h) => h.pollOk > 0).every((h) => h.lastPollOkAgeS !== null && h.lastPollOkAgeS < 2), 'last poll age small and present once a poll has succeeded');
  ok(hb.filter((h) => h.lastPollOkAgeS !== null).every((h) => h.lastPollOkAgeS < 2) && hb.slice(1).some((h) => h.lastPollOkAgeS !== null), 'a poll age is never stale and is present after the first heartbeat');
  ok(hb.every((h) => h.handled === 0 && h.reverted === 0 && h.lastHandledAgeS === null), 'no request handled is reported as such, apart from poll success');
  ok(ex.length === 1 && ex[0].reason === 'signal' && ex[0].signal === 'SIGTERM', 'one controlled exit event for SIGTERM');
  ok(Object.keys(ex[0] || {}).every((k) => EX_KEYS.includes(k)), 'exit event has only whitelisted keys');
  ok(r.res && r.res.code === 143, 'exit code 128+15 kept: ' + JSON.stringify(r.res)); }

// 2. RPC down: process alive, polls failing, no raw error text in heartbeat
{ const r = await run({ fail: true, how: 'term', ms: 4500 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat'); // the RPC client retries a failing read for about a second before it throws
  ok(hb.length >= 2, 'heartbeat continues while RPC fails');
  ok(hb.some((h) => h.pollErr > 0 && h.lastPollErrAgeS !== null) && hb.every((h) => h.pollOk === 0 && h.lastPollOkAgeS === null), 'poll failure distinguished from process alive');
  ok(!JSON.stringify(hb).includes('SECRET-RPC-TEXT'), 'heartbeat carries no raw error text'); }

// 3. unhandled rejection: class only, never the message
{ const r = await run({ how: 'none', preload: "setTimeout(() => Promise.reject(new TypeError('LEAK-ME-12345')), 500);" }); const ex = r.lines.filter((l) => l.ev === 'exit');
  ok(ex.length === 1 && ex[0].reason === 'unhandled-rejection' && ex[0].kind === 'TypeError', 'unhandled rejection exit event with error class');
  ok(!r.raw.includes('LEAK-ME-12345'), 'exit event carries no error message');
  ok(r.res && r.res.code === 1, 'exit code 1 kept'); }

// 4. SIGKILL: nothing can be written; the evidence is a heartbeat that stops
{ const r = await run({ how: 'kill' }); ok(!r.lines.some((l) => l.ev === 'exit'), 'SIGKILL writes no exit event (documented limit)'); ok(r.lines.some((l) => l.ev === 'heartbeat'), 'heartbeats exist before the kill'); }

// 5. a confirmed reply counts as handled; a reply whose receipt is reverted does not
{ const r = await run({ how: 'term', applicant: true, status: '0x1', ms: 2500 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat');
  ok(r.sent === 1 && r.lines.some((l) => l.ev === 'feedback' && l.ok === true), 'control: the daemon sent one reply and it mined successfully');
  ok(hb.reduce((n, h) => n + h.handled, 0) === 1 && hb.every((h) => h.reverted === 0), 'confirmed reply counted as handled');
  ok(hb.some((h) => h.lastHandledAgeS !== null), 'last handled age set after a confirmed reply'); }
{ const r = await run({ how: 'term', applicant: true, status: '0x0', ms: 2500 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat');
  ok(r.sent === 1 && r.lines.some((l) => l.ev === 'feedback' && l.ok === false), 'the daemon sent one reply and its receipt was reverted');
  ok(hb.reduce((n, h) => n + h.reverted, 0) === 1 && hb.every((h) => h.handled === 0 && h.lastHandledAgeS === null), 'reverted reply is counted as reverted, never as handled, and sets no last handled age');
  ok(!r.lines.some((l) => l.ev === 'error'), 'a reverted receipt does not change the daemon behavior (no new error path)'); }

// 6. invalid heartbeat configuration is bounded, not a flood
for (const [name, extraEnv, floor, expectMax] of [['non-numeric', { HEARTBEAT_MS: 'abc' }, null, 0], ['empty', { HEARTBEAT_MS: '' }, null, 0], ['NaN', { HEARTBEAT_MS: 'NaN' }, null, 0], ['below the floor', { HEARTBEAT_MS: '5' }, null, 0], ['huge', { HEARTBEAT_MS: '99999999999999' }, null, 0], ['non-numeric floor', { HEARTBEAT_MS: '5' }, 'xyz', 0], ['floor above 60 s', { HEARTBEAT_MS: '5' }, '999999', 0]]) {
  const r = await run({ how: 'term', env: extraEnv, floor, ms: 900 }); const hb = r.lines.filter((l) => l.ev === 'heartbeat');
  ok(hb.length <= expectMax, `${name} heartbeat setting does not flood (${hb.length} heartbeats in 0.9 s)`);
  ok(r.lines.some((l) => l.ev === 'exit' && l.reason === 'signal'), `${name}: daemon still runs and exits cleanly`); }

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
