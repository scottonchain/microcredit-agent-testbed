// Offline fault-injection test of the desk daemon: what an applicant is told and what the daemon sends when the model cannot
// decide, and that an unconfirmed reply is never sent twice. Stub RPC and a fake `claude` command (test-stub-desk.mjs); no
// chain, no real key, no model, no live transaction.
//   node test-daemon-model-failure.mjs
import { run } from './test-stub-desk.mjs';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const FREE = 'I need about 3 dollars for my phone shop, I can pay it back soon';
const ASK = 'I need $3 for my phone shop. I can pay it back in two weeks.'; // the structured ask the app writes
const claude = { mode: 'claude', applicant: true, threadText: FREE, ms: 2500 };
const last = (r) => r.replies[r.replies.length - 1];
const sum = (r, k) => r.lines.filter((l) => l.ev === 'heartbeat').reduce((n, h) => n + (h[k] || 0), 0);
const NOTHING = /Nothing has been granted/;

// A. control: a working model grants what it decided, so the cases below prove the model, not the stub, is what changed
{ const r = await run({ ...claude, fakeClaude: 'ok', how: 'term' });
  ok(r.sent === 1 && last(r) && last(r).amount === 3_000_000n && /backs you with \$3/.test(last(r).text), 'control: a working model grants 3 dollars with its own words');
  ok(!r.lines.some((l) => l.ev === 'model-unavailable'), 'control: no unavailable event'); }

// B-E. the model cannot decide: say so, grant nothing, change nothing
for (const [name, opts, why] of [
  ['model exits with failure', { fakeClaude: 'exit1' }, 'error'],
  ['model call times out', { fakeClaude: 'sleep', env: { MODEL_TIMEOUT_MS: '1000' }, ms: 3800 }, 'error'],
  ['model returns an empty reply', { fakeClaude: 'empty' }, 'empty'],
  ['spend budget reached (cooldown path)', { fakeClaude: 'ok', env: { OFFICER_BUDGET_USD_PER_HOUR: '0' } }, 'skipped'],
]) {
  const r = await run({ ...claude, how: 'term', ...opts }); const re = last(r);
  ok(r.sent === 1, `${name}: exactly one reply is sent (${r.sent})`);
  ok(re && NOTHING.test(re.text) && re.amount === 0n, `${name}: the reply says nothing was granted and the backing stays 0`);
  ok(r.lines.some((l) => l.ev === 'model-unavailable' && l.why === why), `${name}: unavailable event with reason ${why}`);
  ok(!r.lines.some((l) => l.ev === 'replied' && l.backing > 0), `${name}: no approval was logged`);
  ok(sum(r, 'unavailable') >= 1 && sum(r, 'handled') === 1, `${name}: heartbeat counts one unavailable answer and one confirmed reply`);
  ok(!JSON.stringify(r.lines.filter((l) => l.ev === 'heartbeat' || l.ev === 'model-unavailable')).includes('SECRET'), `${name}: new events carry no raw model error text`);
}

// F. by design the structured ask is decided by the rules, so a model failure keeps that decision (unchanged behavior, pinned here)
{ const r = await run({ ...claude, threadText: ASK, fakeClaude: 'exit1', how: 'term' });
  ok(r.sent === 1 && last(r).amount === 3_000_000n && !NOTHING.test(last(r).text), 'structured ask: still decided by the rules when the model fails'); }

// G. MODE=rules is the intended rules officer and is unchanged
{ const r = await run({ ...claude, mode: 'rules', how: 'term' });
  ok(r.sent === 1 && last(r).amount === 3_000_000n && !NOTHING.test(last(r).text), 'MODE=rules: unchanged, the rules officer decides'); }

// H. ambiguous send: the receipt wait times out, the desk still lists the applicant, the reply then mines: no second send
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 2500, pendingLagMs: 900, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 4500 });
  ok(r.sent === 1, `ambiguous receipt: exactly one send while the first is unconfirmed (${r.sent})`);
  ok(r.lines.filter((l) => l.ev === 'error').length === 1, 'ambiguous receipt: the wait timed out once and was recorded');
  ok(sum(r, 'deferred') >= 1, `ambiguous receipt: later polls deferred instead of resending (${sum(r, 'deferred')})`);
  ok(r.lines.some((l) => l.ev === 'earlier-reply-settled' && l.result === 'mined'), 'ambiguous receipt: the earlier reply is settled as mined'); }

// H2. the thread grows by the officer's own reply once it mined, while a lagging read still lists the applicant: that is the same
// request, not a new one (a guard keyed on the thread length answered it twice)
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 300, pendingLagMs: 1200, threadGrows: true, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 4500 });
  ok(r.sent === 1, `officer reply lengthens the thread: still exactly one send (${r.sent})`);
  ok(sum(r, 'deferred') >= 1, 'officer reply lengthens the thread: later polls deferred'); }

// I. a receipt that never shows: a resend is allowed only after the hold, and the number of sends stays bounded
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 600_000, env: { RECEIPT_TIMEOUT_MS: '1000', RESEND_AFTER_MS: '1500' }, how: 'term', ms: 4500 });
  ok(r.lines.some((l) => l.ev === 'earlier-reply-unknown-resend'), 'unknown receipt: resend only after the hold, and it is logged');
  ok(r.sent >= 2 && r.sent <= 4, `unknown receipt: a bounded number of sends (${r.sent})`); }

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
