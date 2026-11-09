// Offline proof for the officer service hardening: sole-writer lease with fencing, persisted pending operations,
// reconcile-before-replay, bounded timeouts and backoff, and honest status. No network, no keys, no chain.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createLease, StaleWriter } from './service/lease.mjs';
import { openJournal, reconcile } from './service/pending.mjs';
import { recordPoll, readStatus } from './service/status.mjs';
import { withTimeout, backoffMs, Timeout } from './service/timing.mjs';
import { createWorker } from './service/worker.mjs';

const tmp = () => mkdtempSync(join(tmpdir(), 'svc-'));
const clock = (t0 = 1_000_000) => { let t = t0; const f = () => t; f.adv = (ms) => { t += ms; }; return f; };

// ---- lease and fencing
test('a live lease is not taken by a second owner', () => {
  const dir = tmp(), now = clock();
  const a = createLease({ dir, owner: 'A', ttlMs: 1000, now }), b = createLease({ dir, owner: 'B', ttlMs: 1000, now });
  assert.deepEqual(a.acquire(), { ok: true, token: 1 });
  const r = b.acquire(); assert.equal(r.ok, false); assert.equal(r.reason, 'held'); assert.equal(b.token, null);
});
test('after expiry a new owner gets a higher token and the old writer is refused before any write', () => {
  const dir = tmp(), now = clock();
  const a = createLease({ dir, owner: 'A', ttlMs: 1000, now }), b = createLease({ dir, owner: 'B', ttlMs: 1000, now });
  a.acquire(); now.adv(1500);
  assert.deepEqual(b.acquire(), { ok: true, token: 2 });
  assert.throws(() => a.assertHolder(), StaleWriter);
  assert.throws(() => a.renew(), StaleWriter);
  assert.equal(b.assertHolder(), 2);
});
test('a worker that paused past its expiry and was not replaced is also refused until it re-acquires', () => {
  const dir = tmp(), now = clock(); const a = createLease({ dir, owner: 'A', ttlMs: 1000, now });
  a.acquire(); now.adv(1500);
  assert.throws(() => a.assertHolder(), StaleWriter);
  assert.equal(a.acquire().ok, true);
  assert.equal(a.assertHolder(), 2);
});
test('release keeps the token monotonic', () => {
  const dir = tmp(), now = clock(); const a = createLease({ dir, owner: 'A', ttlMs: 1000, now }), b = createLease({ dir, owner: 'B', ttlMs: 1000, now });
  a.acquire(); a.release(); assert.deepEqual(b.acquire(), { ok: true, token: 2 });
});
test('renew extends the lease for the same owner and keeps its token', () => {
  const dir = tmp(), now = clock(); const a = createLease({ dir, owner: 'A', ttlMs: 1000, now });
  a.acquire(); now.adv(900); assert.equal(a.renew(), 1); now.adv(900); assert.equal(a.assertHolder(), 1);
});
test('a lock file left by a crashed process is broken after it goes stale', () => {
  const dir = tmp(), now = clock(); writeFileSync(join(dir, 'lease.lock'), '999');
  const a = createLease({ dir, owner: 'A', ttlMs: 1000, now: () => Date.now() + 60_000 });
  assert.equal(a.acquire().ok, true);
});

// ---- journal and reconcile-before-replay
test('an operation is journaled before it is sent and cannot be begun twice while open', () => {
  const j = openJournal(join(tmp(), 'j.json')); j.begin('reply:0xa', { applicant: '0xa' }, 1);
  assert.equal(j.open().length, 1); assert.throws(() => j.begin('reply:0xa', { applicant: '0xa' }, 1), /in flight/);
  j.sent('reply:0xa', '0xtx'); j.done('reply:0xa', 'success'); assert.equal(j.open().length, 0);
  j.begin('reply:0xa', { applicant: '0xa' }, 2); // a later conversation with the same applicant is allowed once the first is done
});
test('reconcile decisions: confirmed, reverted, waiting, replay-allowed and hold', async () => {
  const j = openJournal(join(tmp(), 'j.json'));
  for (const a of ['c', 'r', 'w', 'n', 'h']) j.begin('reply:' + a, { applicant: a }, 1);
  j.sent('reply:c', 'txc'); j.sent('reply:r', 'txr'); j.sent('reply:w', 'txw');
  const receipts = { txc: { status: 'success' }, txr: { status: 'reverted' }, txw: null };
  const applied = { c: true, r: false, w: false, n: false, h: null };
  const out = await reconcile(j, { getReceipt: async (t) => receipts[t], alreadyApplied: async (op) => applied[op.info.applicant] });
  const by = Object.fromEntries(out.map((x) => [x.id, x.decision]));
  assert.deepEqual(by, { 'reply:c': 'confirm', 'reply:r': 'failed', 'reply:w': 'wait', 'reply:n': 'replay-allowed', 'reply:h': 'hold' });
});
test('a sent operation whose receipt is unknown but whose effect is on chain is confirmed, never replayed', async () => {
  const j = openJournal(join(tmp(), 'j.json')); j.begin('reply:x', { applicant: 'x' }, 1); j.sent('reply:x', 'tx');
  const out = await reconcile(j, { getReceipt: async () => null, alreadyApplied: async () => true });
  assert.equal(out[0].decision, 'confirm');
});
test('a reconcile failure (RPC down) holds or waits; it never allows a replay', async () => {
  const j = openJournal(join(tmp(), 'j.json')); j.begin('reply:x', { applicant: 'x' }, 1);
  const out = await reconcile(j, { getReceipt: async () => { throw new Error('rpc'); }, alreadyApplied: async () => { throw new Error('rpc'); } });
  assert.equal(out[0].decision, 'hold');
});
test('an unreadable journal stops the service instead of starting empty', () => {
  const p = join(tmp(), 'j.json'); writeFileSync(p, '{not json'); assert.throws(() => openJournal(p).open(), /unreadable/);
});

// ---- status honesty
test('status: missing or corrupt is unknown; old is stale; recent is ok; a failed recent poll is degraded', () => {
  const dir = tmp(), p = join(dir, 's.json'), now = clock();
  assert.equal(readStatus(p, { now }).state, 'unknown');
  writeFileSync(p, 'garbage'); assert.equal(readStatus(p, { now }).state, 'unknown');
  recordPoll(p, { now, ok: true }); assert.equal(readStatus(p, { now }).state, 'ok');
  now.adv(121_000); assert.equal(readStatus(p, { now }).state, 'stale');
  recordPoll(p, { now, ok: false }); assert.equal(readStatus(p, { now }).state, 'degraded');
});
test('status never changes by itself: reading it does not write and carries only the allowed fields', () => {
  const p = join(tmp(), 's.json'), now = clock(); recordPoll(p, { now, lastReplyAt: 5, openOps: 2 });
  const before = readFileSync(p, 'utf8'); readStatus(p, { now }); readStatus(p, { now });
  assert.equal(readFileSync(p, 'utf8'), before);
  assert.deepEqual(Object.keys(JSON.parse(before)).sort(), ['lastPollAt', 'lastPollOk', 'lastReplyAt', 'openOps', 'v']);
});

// ---- timeouts and backoff
test('withTimeout rejects a hung call and clears its timer on success', async () => {
  await assert.rejects(withTimeout(new Promise(() => {}), 20, 'rpc'), (e) => e instanceof Timeout && /rpc timed out/.test(e.message));
  assert.equal(await withTimeout(Promise.resolve(7), 1000, 'x'), 7);
});
test('backoff grows, is capped, and jitter stays inside its bounds', () => {
  const lo = (n) => backoffMs(n, { rng: () => 0 }), hi = (n) => backoffMs(n, { rng: () => 1 });
  assert.equal(lo(0), 800); assert.equal(hi(0), 1200); assert.ok(lo(3) > lo(2));
  for (let n = 0; n < 40; n++) assert.ok(hi(n) <= 60_000);
});

// ---- the worker end to end (fake chain)
function fakeChain({ pending = [], applied = new Set() } = {}) {
  const c = { pending: [...pending], applied, txs: {}, replies: [], failNext: null, prepared: 0,
    async pending_() { return c.pending.filter((a) => !c.applied.has(a)); },
    async prepare(a, token) { const tx = '0x' + (c.replies.length + c.prepared++); return { txHash: tx, broadcast: async () => { if (c.failNext) { const e = c.failNext; c.failNext = null; throw e; } c.replies.push({ a, token, tx }); c.txs[tx] = { status: 'success' }; c.applied.add(a); } }; },
    async reply(a, token) { const p = await c.prepare(a, token); await p.broadcast(); return p.txHash; },
    async receipt(tx) { return c.txs[tx] || null; },
    async applied_(a) { return c.applied.has(a); } };
  return { chain: { pending: c.pending_, prepare: c.prepare, reply: c.reply, receipt: c.receipt, applied: c.applied_ }, state: c };
}
function mkWorker(dir, owner, now, fc, ttlMs = 1000) {
  const lease = createLease({ dir: join(dir, 'lease'), owner, ttlMs, now }), journal = openJournal(join(dir, 'journal.json'));
  return { lease, journal, w: createWorker({ lease, journal, statusPath: join(dir, 'status.json'), chain: fc.chain, now, callTimeoutMs: 200, receiptTimeoutMs: 200 }) };
}
test('worker: replies to a pending applicant once, journals it, and records an honest status', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] }); const { w, journal } = mkWorker(dir, 'A', now, fc);
  const r = await w.pollOnce(); assert.deepEqual(r.replied, ['0xa']);
  assert.equal(fc.state.replies.length, 1); assert.equal(fc.state.replies[0].token, 1); assert.equal(journal.open().length, 0);
  const s = readStatus(join(dir, 'status.json'), { now }); assert.equal(s.state, 'ok'); assert.equal(s.openOps, 0);
  await w.pollOnce(); assert.equal(fc.state.replies.length, 1); // nothing pending: no second write
});
test('STALE WRITER REFUSAL: after takeover the old worker makes zero chain writes', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: [] });
  const A = mkWorker(dir, 'A', now, fc), B = mkWorker(dir, 'B', now, fc);
  await A.w.pollOnce(); now.adv(1500); // A stalls past its expiry (a frozen container)
  await B.w.pollOnce(); assert.equal(B.lease.token, 2);
  fc.state.pending.push('0xnew');
  await assert.rejects(A.w.pollOnce(), StaleWriter); // A wakes up, tries to work
  assert.equal(fc.state.replies.length, 0, 'the stale writer wrote nothing');
  const r = await B.w.pollOnce(); assert.deepEqual(r.replied, ['0xnew']); assert.equal(fc.state.replies[0].token, 2);
});
test('a second instance started while the first holds the lease does no work and no writes', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] });
  const A = mkWorker(dir, 'A', now, fc), B = mkWorker(dir, 'B', now, fc);
  await A.w.pollOnce(); fc.state.pending.push('0xb');
  const rb = await B.w.pollOnce(); assert.equal(rb.ran, false); assert.equal(fc.state.replies.filter((x) => x.a === '0xb').length, 0);
});
test('RESTART RECOVERY: crash after the journal write and before the chain write; restart reconciles first, then handles it once', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] });
  const first = mkWorker(dir, 'A', now, fc); first.lease.acquire(); first.journal.begin('reply:0xa', { applicant: '0xa' }, first.lease.token); // process dies here
  now.adv(1500);
  const second = mkWorker(dir, 'A2', now, fc);
  const r = await second.w.pollOnce();
  assert.equal(fc.state.replies.length, 1, 'exactly one reply, not zero and not two'); assert.equal(second.journal.open().length, 0); assert.deepEqual(r.replied, ['0xa']);
});
test('RESTART RECOVERY: crash after the chain write; the effect is found on chain and confirmed, never replayed', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] });
  const first = mkWorker(dir, 'A', now, fc); first.lease.acquire(); first.journal.begin('reply:0xa', { applicant: '0xa' }, 1);
  await fc.chain.reply('0xa', 1); // the transaction landed, then the process died before journal.sent
  now.adv(1500);
  const second = mkWorker(dir, 'A2', now, fc); const r = await second.w.pollOnce();
  assert.equal(fc.state.replies.length, 1); assert.deepEqual(r.confirmed, ['reply:0xa']); assert.equal(second.journal.open().length, 0);
});
test('RESTART RECOVERY: RPC down during reconcile means hold: no replay, status degraded, and recovery once the RPC returns', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] });
  const first = mkWorker(dir, 'A', now, fc); first.lease.acquire(); first.journal.begin('reply:0xa', { applicant: '0xa' }, 1); now.adv(1500);
  const good = fc.chain.applied; fc.chain.applied = async () => { throw new Error('rpc down'); };
  const second = mkWorker(dir, 'A2', now, fc); const r1 = await second.w.pollOnce();
  assert.deepEqual(r1.held, ['reply:0xa']); assert.equal(fc.state.replies.length, 0);
  fc.chain.applied = good; const r2 = await second.w.pollOnce();
  assert.equal(fc.state.replies.length, 1); assert.deepEqual(r2.replied, ['0xa']);
});
test('a hung RPC call is bounded: the poll ends degraded with no write and no hang', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] }); fc.chain.pending = () => new Promise(() => {});
  const { w } = mkWorker(dir, 'A', now, fc); const r = await w.pollOnce();
  assert.equal(r.error, 'Timeout'); assert.equal(readStatus(join(dir, 'status.json'), { now }).state, 'degraded'); assert.equal(fc.state.replies.length, 0);
});
test('a failed broadcast leaves a SENT operation with its hash: it waits and is never blindly resent', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] }); const { w, journal } = mkWorker(dir, 'A', now, fc, 10_000_000);
  fc.state.failNext = new Error('send failed'); const r1 = await w.pollOnce();
  assert.ok(r1.error); assert.equal(journal.open().length, 1); assert.equal(journal.open()[0].state, 'sent'); assert.ok(journal.open()[0].txHash);
  const r2 = await w.pollOnce(); assert.deepEqual(r2.waited, ['reply:0xa']); assert.equal(fc.state.replies.length, 0, 'no resend while the hash may still be mined');
});
test('reconcile holds a recorded transaction that stays unmined past the bound, and never replays it', async () => {
  const j = openJournal(join(tmp(), 'j.json')); j.begin('reply:x', { applicant: 'x' }, 1); j.sent('reply:x', 'tx');
  const out = await reconcile(j, { getReceipt: async () => null, alreadyApplied: async () => false, now: () => Date.now() + 700_000, maxWaitMs: 600_000 });
  assert.equal(out[0].decision, 'hold');
  const early = await reconcile(j, { getReceipt: async () => null, alreadyApplied: async () => false, now: () => Date.now() + 1000, maxWaitMs: 600_000 });
  assert.equal(early[0].decision, 'wait');
});
test('RESTART RECOVERY: crash after the hash is journaled and before the broadcast; the transaction never landed, so it waits then is held for a person, never double-sent', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] });
  const first = mkWorker(dir, 'A', now, fc); first.lease.acquire(); first.journal.begin('reply:0xa', { applicant: '0xa' }, 1); first.journal.sent('reply:0xa', '0xdead');
  now.adv(1500); const second = mkWorker(dir, 'A2', now, fc); const r = await second.w.pollOnce();
  assert.deepEqual(r.waited, ['reply:0xa']); assert.equal(fc.state.replies.length, 0);
});
test('nothing here is wired into the live daemon', () => {
  const d = readFileSync(new URL('./desk-daemon.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(d, /service\/(lease|pending|status|timing|worker)/);
});

test('a worker that loses the lease mid-poll writes no status and makes no write (the status must not read ok)', async () => {
  const dir = tmp(), now = clock(), fc = fakeChain({ pending: ['0xa'] });
  const A = mkWorker(dir, 'A', now, fc), B = mkWorker(dir, 'B', now, fc);
  await A.w.pollOnce(); const before = readFileSync(join(dir, 'status.json'), 'utf8'); const writes = fc.state.replies.length;
  fc.state.pending.push('0xnew');
  const realPending = fc.chain.pending;
  fc.chain.pending = async () => { now.adv(1500); B.lease.acquire(); return realPending(); }; // A stalls past expiry and B takes over during the poll
  await assert.rejects(A.w.pollOnce(), StaleWriter);
  assert.equal(readFileSync(join(dir, 'status.json'), 'utf8'), before, 'status untouched by the stale worker');
  assert.equal(fc.state.replies.length, writes, 'no chain write after losing the lease');
});
test('the worker calls chain.receipt with the hash only', () => {
  const w = readFileSync(new URL('./service/worker.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(w, /chain\.receipt\([^)]*,\s*true/);
});
