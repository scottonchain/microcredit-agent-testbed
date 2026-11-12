// Offline fault-injection test of the desk daemon: what an applicant is told and what the daemon sends when the model cannot
// decide, and that an unconfirmed reply is never sent twice. Stub RPC and a fake `claude` command (test-stub-desk.mjs); no
// chain, no real key, no model, no live transaction.
//   node test-daemon-model-failure.mjs
import { run } from './test-stub-desk.mjs';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

let pass = 0, fail = 0;
const ok = (c, m) => { if (c) pass++; else { fail++; console.log('FAIL', m); } };
const FREE = 'I need about 3 dollars for my phone shop, I can pay it back soon';
const ASK = 'I need $3 for my phone shop. I can pay it back in two weeks.'; // the structured ask the app writes
const claude = { mode: 'claude', applicant: true, threadText: FREE, ms: 2500 };
const last = (r) => r.replies[r.replies.length - 1];
const sum = (r, k) => r.lines.filter((l) => l.ev === 'heartbeat').reduce((n, h) => n + (h[k] || 0), 0);
const NOTHING = /Nothing new has been granted, and any loan or line you already have is unchanged/;

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
  ok(re && NOTHING.test(re.text) && re.amount === 0n, `${name}: the reply says nothing new was granted and the backing stays 0`);
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

// I. a receipt that never shows: UNKNOWN HOLDS. Age never authorizes another send; after STUCK_AFTER_MS it is reported for a person
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 600_000, env: { RECEIPT_TIMEOUT_MS: '1000', STUCK_AFTER_MS: '1500' }, how: 'term', ms: 5500 });
  ok(r.sent === 1, `unknown receipt: still exactly one send long after the hold would have expired (${r.sent})`);
  ok(r.lines.some((l) => l.ev === 'earlier-reply-stuck'), 'unknown receipt: reported as stuck for a person');
  ok(!r.lines.some((l) => /resend/.test(l.ev)), 'unknown receipt: no resend event exists');
  ok(r.lines.filter((l) => l.ev === 'heartbeat').some((h) => h.held === 1), 'unknown receipt: the heartbeat counts one held reply'); }

// J. the original mines AFTER the old resend threshold: still one send, and it is settled as mined
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 3500, pendingLagMs: 800, env: { RECEIPT_TIMEOUT_MS: '1000', STUCK_AFTER_MS: '1500' }, how: 'term', ms: 6500 });
  ok(r.sent === 1, `late mining: exactly one send (${r.sent})`);
  ok(r.lines.some((l) => l.ev === 'earlier-reply-settled' && l.result === 'mined'), 'late mining: settled as mined'); }

// K. our nonce went to a different transaction and our hash has no receipt: it can never execute, so a resend is allowed
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 600_000, dropAfterMs: 1500, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 5000 });
  ok(r.lines.some((l) => l.ev === 'earlier-reply-dropped'), 'dropped: recognised because the nonce was used by another transaction');
  ok(r.sent >= 2, `dropped: a resend is allowed after that proof (${r.sent})`); }

// L. restart after the broadcast and before the receipt: the new process reads the saved state and sends nothing for that request
{ const first = await run({ mode: 'rules', applicant: true, receiptDelayMs: 3000, pendingLagMs: 800, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'kill', ms: 1800, keep: true });
  ok(first.sent === 1, `restart: the first process sent once (${first.sent})`);
  const second = await run({ mode: 'rules', applicant: true, reuse: first, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 4500 });
  ok(second.sent === 1, `restart: the second process sent nothing more (${second.sent})`);
  ok(second.lines.filter((l) => l.ev === 'heartbeat').some((h) => h.deferred >= 1 || h.held >= 1), 'restart: the second process held the unresolved reply');
  second.srv.close(); }

// M. the broadcast call throws (accepted by the node, response lost): no fallback send, the outcome is reconciled by nonce
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 2500, pendingLagMs: 800, throwAfterBroadcast: true, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 5000 });
  ok(r.sent === 1, `throw after broadcast: exactly one send, no fallback (${r.sent})`);
  ok(r.lines.some((l) => l.ev === 'send-ambiguous'), 'throw after broadcast: held as ambiguous');
  ok(!r.lines.some((l) => l.ev === 'backing-unchanged'), 'throw after broadcast: the backing-unchanged fallback was not used');
  ok(r.lines.some((l) => l.ev === 'earlier-reply-settled' && l.result === 'mined'), 'throw after broadcast: the transaction found at our nonce is a reply to this applicant, so it is settled as sent'); }

// N1. a journal file that exists but cannot be read or validated stops the daemon: it sends nothing (fail closed)
for (const [name, content] of [['truncated JSON', '{"v":2,"replies":[["a#1",{"applicant":'], ['wrong schema', '{"v":2,"replies":[["a#1",{"applicant":5}]]}'], ['wrong version', '{"v":1,"replies":[]}']]) {
  const r = await run({ mode: 'rules', applicant: true, stateFile: content, how: 'none', ms: 700 });
  ok(r.res && r.res.code === 3, `corrupt journal (${name}): the daemon stops with exit code 3 (${JSON.stringify(r.res)})`);
  ok(r.sent === 0 && r.lines.some((l) => l.ev === 'state-unreadable'), `corrupt journal (${name}): nothing sent, reason logged`); }
// a missing journal file is a normal first start
{ const r = await run({ mode: 'rules', applicant: true, how: 'term', ms: 1500 }); ok(r.sent === 1, 'no journal file yet: normal first start sends the reply'); }

// N2. the receipt read is stale but the block that used our nonce holds OUR transaction: it is sent, never resent
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 1500, receiptHidden: true, pendingLagMs: 600_000, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 5500 });
  ok(r.sent === 1, `stale receipt, nonce used by our transaction: exactly one send (${r.sent})`);
  ok(r.lines.some((l) => l.ev === 'earlier-reply-settled' && l.result === 'mined'), 'stale receipt: settled from the block that holds our transaction'); }

// N3. the nonce moved, but the RPC cannot show which transaction used it: that is NOT proof of a drop, so it holds
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 600_000, dropAfterMs: 1200, noHistory: true, env: { RECEIPT_TIMEOUT_MS: '1000', STUCK_AFTER_MS: '1500' }, how: 'term', ms: 5500 });
  ok(r.sent === 1, `nonce advanced without evidence of who used it: still exactly one send (${r.sent})`);
  ok(r.lines.some((l) => l.ev === 'earlier-reply-stuck'), 'nonce advanced without evidence: reported as stuck for a person'); }

// N4. a newer request arrives before the older reply is settled: the older entry is kept, and the new request is answered
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 600_000, threadSecondAfterMs: 1800, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 5000 });
  const j = JSON.parse(readFileSync(join(r.dir, 'd.log.state.json'), 'utf8')); const keys = j.replies.map((e) => e[0]).sort();
  ok(r.sent === 2, `newer request: answered with its own transaction (${r.sent} sends)`);
  ok(keys.length === 2 && keys[0].endsWith('#1') && keys[1].endsWith('#2') && j.replies.every((e) => e[1].mined === false), `newer request: both unresolved entries are in the journal (${keys.map((k) => k.slice(-2)).join(',')})`); }

// N5. only errors that prove nothing was broadcast are treated that way; an unfamiliar error that merely mentions a nonce is ambiguous
{ const r = await run({ mode: 'rules', applicant: true, receiptDelayMs: 2500, pendingLagMs: 800, sendError: 'text', env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 5000 });
  ok(r.sent === 1 && r.lines.some((l) => l.ev === 'send-ambiguous'), `error text that mentions a nonce is ambiguous: held, one send (${r.sent})`); }
{ const r = await run({ mode: 'rules', applicant: true, sendError: 'low', receiptDelayMs: 600_000, env: { RECEIPT_TIMEOUT_MS: '1000' }, how: 'term', ms: 5000 }); // the desk keeps listing the applicant, so the next poll tries again
  ok(r.sent === 1 && !r.lines.some((l) => l.ev === 'send-ambiguous'), `a node refusal for a too-low nonce proves nothing was broadcast: answered on the next poll, one send (${r.sent})`); }

console.log(`${pass} passed, ${fail} failed`); process.exit(fail ? 1 : 0);
