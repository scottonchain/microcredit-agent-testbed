// Regression tests for the mobile passkey focus failure (D7 app). Pure modules only: no browser, chain or network.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { FocusError, isForeground, guardedGet } from './app/src/foreground.js';
import { createGate } from './app/src/gate.js';
import { submitTracked } from './app/src/phases.js';
import { friendly, failureTitle } from './app/src/errors.js';

// A minimal document/window with controllable visibility and focus.
function fakeDoc({ visible = true, focused = true } = {}) {
  const d = { visibilityState: visible ? 'visible' : 'hidden', _focused: focused, hasFocus() { return this._focused; }, ls: {}, wl: {} };
  const bus = (o) => ({ addEventListener(n, f) { (o[n] ||= new Set()).add(f); }, removeEventListener(n, f) { o[n]?.delete(f); } });
  Object.assign(d, bus(d.ls)); d.defaultView = bus(d.wl);
  d.fire = (name) => (name === 'focus' ? d.wl.focus : d.ls[name])?.forEach((f) => f());
  d.listeners = () => Object.values(d.ls).reduce((n, s) => n + s.size, 0) + Object.values(d.wl).reduce((n, s) => n + s.size, 0);
  return d;
}

// ---- native prompt return / focus loss
test('a hidden or unfocused page is not in front', () => {
  assert.equal(isForeground(fakeDoc()), true);
  assert.equal(isForeground(fakeDoc({ visible: false })), false);
  assert.equal(isForeground(fakeDoc({ focused: false })), false);
});
test('focus loss: an unfocused page fails at once with FocusError, the passkey call is never made, no listener is left', async () => {
  const d = fakeDoc({ focused: false }); const state = { approved: false }; let calls = 0;
  const get = guardedGet(async () => { calls++; return 'assertion'; }, d, state);
  await assert.rejects(get({}), (e) => e instanceof FocusError && e.name === 'FocusError');
  assert.equal(calls, 0); assert.equal(state.approved, false); assert.equal(d.listeners(), 0);
});
test('negative regression: focus returning after a failed attempt does NOT resume the approval without a fresh tap', async () => {
  for (const mode of [{ focused: false }, { visible: false }]) {
    const d = fakeDoc(mode); const state = { approved: false }; let calls = 0;
    const get = guardedGet(async () => { calls++; return 'assertion'; }, d, state);
    await assert.rejects(get({}), FocusError);
    d._focused = true; d.visibilityState = 'visible'; d.fire('focus'); d.fire('visibilitychange');
    await new Promise((r) => setImmediate(r));
    assert.equal(calls, 0, 'no credential call may follow a focus event on its own');
    assert.equal(state.approved, false);
  }
});
test('a fresh tap after focus is back makes exactly one credential call', async () => {
  const d = fakeDoc({ focused: false }); const state = { approved: false }; let calls = 0;
  const get = guardedGet(async () => { calls++; return 'assertion'; }, d, state);
  await assert.rejects(get({}), FocusError);
  d._focused = true;
  assert.equal(await get({}), 'assertion'); assert.equal(calls, 1);
});
test('the passkey call runs once the page is in front and marks the approval only after it resolves', async () => {
  const d = fakeDoc(); const state = { approved: false }; let seenDuring = null;
  const get = guardedGet(async (o) => { seenDuring = state.approved; return { ok: o }; }, d, state);
  assert.deepEqual(await get(1), { ok: 1 }); assert.equal(seenDuring, false); assert.equal(state.approved, true);
});
test('a refused passkey call does not count as approval', async () => {
  const state = { approved: false };
  const get = guardedGet(async () => { throw Object.assign(new Error('The operation either timed out or was not allowed'), { name: 'NotAllowedError' }); }, fakeDoc(), state);
  await assert.rejects(get({})); assert.equal(state.approved, false);
});

// ---- messages: focus vs cancellation vs unknown outcome
const noNothingSent = (s) => assert.doesNotMatch(s, /Nothing was sent/i);
test('the reported technical error is shown as a focus problem, never as a cancellation', () => {
  for (const e of [Object.assign(new Error('The document is not focused.'), { name: 'NotAllowedError' }), new FocusError(), { message: 'NotAllowedError: The document is not focused' }, { cause: { message: 'The document is not focused' } }]) {
    const s = friendly(e);
    assert.match(s, /not in front/); assert.doesNotMatch(s, /Cancelled/); noNothingSent(s);
  }
});
test('a real cancellation before approval says this attempt sent nothing and offers to try again', () => {
  const e = Object.assign(new Error('The operation either timed out or was not allowed'), { name: 'NotAllowedError', phase: 'approval' });
  const s = friendly(e); assert.match(s, /did not send anything/); assert.match(s, /tap the button again/i); noNothingSent(s);
});
test('after approval, a failure is described as unconfirmed, not as nothing sent', () => {
  const s = friendly(Object.assign(new Error('rejected'), { phase: 'approved' }));
  assert.match(s, /could not confirm/); assert.doesNotMatch(s, /did not send anything/); noNothingSent(s);
});
test('a timeout after submission says it may still go through (the old text said nothing was sent)', () => {
  const s = friendly(Object.assign(new Error('Timed out while waiting for User Operation receipt'), { phase: 'submitted', name: 'WaitForUserOperationReceiptTimeoutError' }));
  assert.match(s, /may still go through/); assert.doesNotMatch(s, /did not send anything/); noNothingSent(s);
});
test('contract refusals and network messages are unchanged', () => {
  assert.match(friendly({ reason: 'NoCredit' }), /no credit yet/i);
  assert.match(friendly(new Error('429 Too Many Requests')), /rate limited/);
  assert.match(friendly(new Error('Failed to fetch')), /Cannot reach/);
});
test('setup errors without a phase no longer claim anything was or was not sent', () => {
  const s = friendly(Object.assign(new Error('x'), { name: 'NotAllowedError' })); noNothingSent(s); assert.match(s, /Cancelled/);
});

// ---- phases: what a failed send is tagged with
const fakeBundler = (over) => ({ sendUserOperation: async () => '0xhash', waitForUserOperationReceipt: async () => ({ success: true }), ...over });
test('a failure while waiting for approval is tagged approval', async () => {
  const state = { approved: false };
  await assert.rejects(submitTracked(fakeBundler({ sendUserOperation: async () => { throw new Error('x'); } }), 'a', [], null, state), (e) => e.phase === 'approval');
});
test('a failure after the passkey approved is tagged approved', async () => {
  const state = { approved: false };
  await assert.rejects(submitTracked(fakeBundler({ sendUserOperation: async () => { state.approved = true; throw new Error('bundler down'); } }), 'a', [], null, state), (e) => e.phase === 'approved');
});
test('a failure waiting for the result is tagged submitted and carries the user operation hash', async () => {
  await assert.rejects(submitTracked(fakeBundler({ waitForUserOperationReceipt: async () => { throw new Error('timeout'); } }), 'a', [], null, { approved: false }), (e) => e.phase === 'submitted' && e.userOpHash === '0xhash');
});
test('a stale approval from an earlier attempt does not leak into the next one', async () => {
  const state = { approved: true };
  await assert.rejects(submitTracked(fakeBundler({ sendUserOperation: async () => { throw new Error('x'); } }), 'a', [], null, state), (e) => e.phase === 'approval');
});
test('the stages are reported in order and a good send returns the hash and receipt', async () => {
  const seen = []; const r = await submitTracked(fakeBundler(), 'a', [], (s) => seen.push(s), { approved: false });
  assert.deepEqual(seen, ['sign', 'submit']); assert.equal(r.hash, '0xhash'); assert.equal(r.receipt.success, true);
});

// ---- repeated taps
test('the gate lets one flow in and ignores the rest until it leaves', () => {
  const g = createGate(); assert.equal(g.tryEnter(), true); assert.equal(g.tryEnter(), false); assert.equal(g.tryEnter(), false); assert.equal(g.busy, true);
  g.leave(); assert.equal(g.busy, false); assert.equal(g.tryEnter(), true);
});
test('five rapid taps start exactly one signing flow, and a failure releases the gate', async () => {
  const g = createGate(); let started = 0;
  const run = async (fn) => { if (!g.tryEnter()) return null; try { return await fn(); } finally { g.leave(); } };
  const flow = async () => { started++; await new Promise((r) => setTimeout(r, 5)); throw new Error('boom'); };
  const results = await Promise.allSettled([1, 2, 3, 4, 5].map(() => run(flow)));
  assert.equal(started, 1); assert.equal(results.filter((x) => x.status === 'rejected').length, 1); assert.equal(g.busy, false);
  assert.equal(await run(async () => 'next'), 'next');
});

// ---- the app wiring (source-level guards: main.js uses the gate and the chat send carries its note)
const main = readFileSync(new URL('./app/src/main.js', import.meta.url), 'utf8');
const core = readFileSync(new URL('./app/src/core.js', import.meta.url), 'utf8');
test('main.js runs every signing flow through the single-flight gate', () => {
  assert.match(main, /async function run\(title, calls, opts\) \{\s*if \(!signing\.tryEnter\(\)\) return null;\s*try \{ return await runInner\(title, calls, opts\); \} finally \{ signing\.leave\(\); \}/);
  assert.equal((main.match(/runInner\(/g) || []).length, 2); // the definition and the single call inside run
});
test('a failed chat send says earlier messages were recorded and must not be re-sent', () => {
  assert.match(main, /run\('Send your message'[\s\S]{0,200}failNote: 'Messages already shown in this chat were recorded earlier/);
  assert.match(main, /failNote \? `<p class="muted">\$\{esc\(failNote\)\}<\/p>` : ''/);
});
test('core.js makes the passkey call through guardedGet and sends through submitTracked', () => {
  assert.match(core, /guardedGet\(\(o\) => navigator\.credentials\.get\(o\), document, signState\)/);
  assert.match(core, /toWebAuthnAccount\(\{ credential: cred, getFn \}\)/);
  assert.match(core, /submitTracked\(bundlerClient, account, calls, onStage, signState\)/);
});
test('no automatic retry of a signing attempt was added', () => {
  assert.doesNotMatch(main + core, /setTimeout\([^)]*sendUserOperation/);
  assert.equal((core.match(/sendUserOperation/g) || []).length, 0); // only phases.js calls it, once
  assert.equal((readFileSync(new URL('./app/src/phases.js', import.meta.url), 'utf8').match(/sendUserOperation\(/g) || []).length, 1);
});

// ---- failure sheet title follows the outcome
test('failureTitle: unknown outcomes are not titled "It did not go through"', () => {
  assert.equal(failureTitle({ phase: 'approved' }), 'Still checking this attempt');
  assert.equal(failureTitle({ phase: 'submitted' }), 'Still checking this attempt');
  for (const e of [{ phase: 'approval' }, new FocusError(), {}, null, undefined]) assert.equal(failureTitle(e), 'It did not go through');
});
test('main.js wiring: the catch sheet title comes from failureTitle; the plain title stays only for a definite revert', () => {
  const main = readFileSync(new URL('./app/src/main.js', import.meta.url), 'utf8');
  assert.match(main, /import \{ friendly, failureTitle \} from '\.\/errors\.js'/);
  assert.match(main, /sheet\(\{ title: failureTitle\(e\), body: `<div class="note bad">\$\{esc\(friendly\(e\)\)\}/);
  assert.equal((main.match(/title: 'It did not go through'/g) || []).length, 1, 'only the definite-revert sheet keeps the plain title');
  assert.match(main, /title: 'It did not go through', body: `<div class="note bad">\$\{esc\(friendly\(\{ reason: lastErr \}\)\)\}/);
});
test('app code never waits for focus to come back (no resume path)', () => {
  for (const f of ['foreground.js', 'core.js', 'main.js', 'phases.js']) {
    const src = readFileSync(new URL('./app/src/' + f, import.meta.url), 'utf8');
    assert.doesNotMatch(src, /waitForeground|addEventListener\(['"]visibilitychange|addEventListener\(['"]focus/, f);
  }
});
