import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { EventEmitter } from 'node:events';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { runWithLifecycle, lifecycleEnabled, checkpoint, publicReport, exitCodeFor, ENV_FLAG } from './lifecycle_runner.mjs';
import { loadJournal } from './wallet_lifecycle.mjs';
import { makeChain, roster, addr, FUND, OTHER, TOKEN, CHAIN_ID } from './lifecycle_fixtures.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'lr-'));
const sleep = ms => new Promise(r => setTimeout(r, ms));

// A run with counters on everything that has a side effect.
function setup({ n = 2, chain: co = {}, over = {}, fundGas = 1000n, scenario = async () => {} } = {}) {
  const dir = tmp();
  const chain = makeChain({ fund: 1000n, ...co });
  const calls = { fund: 0, scenario: 0, ports: 0 };
  const ports = Object.fromEntries(Object.entries(chain.ports).map(([k, f]) => [k, (...a) => { calls.ports++; return f(...a); }]));
  const signals = new EventEmitter();
  const cfg = {
    enabled: true, runId: 'r1', fundingWallet: FUND, roster: roster(n), ports, signals,
    journalPath: path.join(dir, 'private', 'journal.json'), token: TOKEN, chainId: CHAIN_ID, timeoutMs: 5000, settleGraceMs: 100,
    fund: async () => {
      calls.fund++;
      const tokens = {}; const gas = {};
      for (let i = 1; i <= n; i++) { tokens[addr(i)] = BigInt(10 * i); gas[addr(i)] = fundGas; }
      await chain.placeFunds({ tokens, gas });
    },
    scenario: async (ctx) => { calls.scenario++; return scenario(ctx, { chain, signals }); },
    ...over,
  };
  return { dir, chain, calls, cfg, signals };
}
const totalTokens = n => { let t = 0n; for (let i = 1; i <= n; i++) t += BigInt(10 * i); return t; };

// ---------- disabled by default ----------
test('disabled by default: no port call, no file, no handler, nothing funded', async () => {
  const t = setup();
  const before = t.signals.listenerCount('SIGTERM');
  for (const cfg of [{ ...t.cfg, enabled: undefined }, { ...t.cfg, enabled: false }, { ...t.cfg, enabled: 'true' }, undefined]) {
    const r = await runWithLifecycle(cfg);
    assert.equal(r.status, 'disabled'); assert.equal(r.ran, false); assert.equal(exitCodeFor(r), 0);
  }
  assert.equal(t.calls.ports, 0); assert.equal(t.calls.fund, 0); assert.equal(t.calls.scenario, 0);
  assert.equal(fs.existsSync(path.join(t.dir, 'private')), false);
  assert.equal(t.signals.listenerCount('SIGTERM'), before);
  assert.equal(lifecycleEnabled({}), false); assert.equal(lifecycleEnabled({ [ENV_FLAG]: '0' }), false); assert.equal(lifecycleEnabled({ [ENV_FLAG]: '1' }), true);
});

test('configuration problems refuse before any side effect', async () => {
  const t = setup();
  for (const bad of [{ journalPath: 'relative.json' }, { journalPath: path.join(t.dir, 'evidence', 'j.json') }, { roster: [] }, { fund: undefined }, { ports: {} }]) {
    const r = await runWithLifecycle({ ...t.cfg, ...bad });
    assert.equal(r.status, 'refused_config'); assert.equal(r.ok, false);
  }
  assert.equal(t.calls.fund, 0); assert.equal(t.calls.ports, 0);
});

// ---------- control refusal before funding ----------
test('missing, throwing or wrong control refuses funding before any transfer; the inventory is kept', async () => {
  for (const chainOpts of [{ lost: ['w2'] }]) {
    const t = setup({ n: 3, chain: chainOpts });
    const r = await runWithLifecycle(t.cfg);
    assert.equal(r.status, 'refused_control'); assert.deepEqual(r.missing, ['w2']);
    assert.equal(t.calls.fund, 0); assert.equal(t.calls.scenario, 0);
    const s = t.chain.state(); assert.equal(s.signs, 0); assert.deepEqual(s.broadcasts, []); assert.equal(s.fund, '1000');
    const j = loadJournal(t.cfg.journalPath);
    assert.deepEqual(Object.keys(j.wallets), ['w1', 'w2', 'w3']); // complete inventory retained
    assert.equal(j.wallets.w2.state, 'signer_lost');
    assert.equal(exitCodeFor(r), 2);
  }
  const t2 = setup({ over: {} });
  t2.cfg.ports = { ...t2.cfg.ports, controls: async () => { throw new Error('hsm down'); } };
  const r2 = await runWithLifecycle(t2.cfg);
  assert.equal(r2.status, 'refused_control'); assert.equal(t2.calls.fund, 0);
  const t3 = setup({ over: {} });
  t3.cfg.ports = { ...t3.cfg.ports, controls: async () => 'yes' }; // truthy but not true: not control
  assert.equal((await runWithLifecycle(t3.cfg)).status, 'refused_control');
});

test('duplicate or malformed inventory refuses before any port is called', async () => {
  const dup = roster(2).map(w => ({ ...w, id: 'same' }));
  const sameAddr = roster(2).map(w => ({ ...w, address: addr(1) }));
  const empty = [{ id: '', address: addr(1) }];
  for (const r0 of [dup, sameAddr, empty, [{ id: 'f', address: FUND }]]) {
    const t = setup({ over: { roster: r0 } });
    const r = await runWithLifecycle(t.cfg);
    assert.equal(r.status, 'refused_inventory'); assert.equal(t.calls.fund, 0); assert.equal(t.calls.ports, 0);
  }
});

// ---------- success, failure, timeout, cancel ----------
test('success: terminal cleanup then an exact reconciliation closes the run; private journal, public report', async () => {
  const t = setup({ n: 3 });
  const r = await runWithLifecycle(t.cfg);
  assert.equal(r.status, 'closed'); assert.equal(r.ok, true); assert.equal(exitCodeFor(r), 0);
  assert.equal(t.calls.fund, 1); assert.equal(t.calls.scenario, 1);
  assert.equal(t.chain.state().fund, '1000'); // everything came back
  const j = loadJournal(t.cfg.journalPath);
  assert.equal(j.reconciliation.matches, true); assert.equal(j.reconciliation.swept, totalTokens(3).toString());
  assert.equal(fs.statSync(t.cfg.journalPath).mode & 0o777, 0o600);
  assert.equal(fs.existsSync(t.cfg.journalPath + '.lock'), false); // single-owner lock released
  const pub = JSON.stringify(r.report) + JSON.stringify(r.checkpoint);
  assert.ok(!pub.includes('raw:')); assert.ok(!/priv|secret|mnemonic/i.test(pub));
  assert.ok(JSON.stringify(j).includes('raw:') || Object.values(j.wallets).every(w => !w.sweep)); // raw bytes live only in the private file
  assert.deepEqual(r.checkpoint.unresolved, []);
});

test('scenario exception: cleanup enters once, the failure is preserved, never a silent pass', async () => {
  const t = setup({ n: 2, scenario: async () => { throw new Error('postgres://u:p@h/db'); } });
  const r = await runWithLifecycle(t.cfg);
  assert.equal(r.scenario, 'failed'); assert.equal(r.ok, false); assert.equal(exitCodeFor(r), 2);
  assert.equal(r.status, 'closed'); // funds did come back
  assert.equal(t.chain.state().signs, 4);  // 2 token sweeps + 2 gas returns, each signed once
  assert.ok(!JSON.stringify(r).includes('postgres://')); assert.ok(!fs.readFileSync(t.cfg.journalPath, 'utf8').includes('postgres://'));
});

test('timeout: a scenario that ignores the abort is left behind, cleanup still runs, success is not reported', async () => {
  const t = setup({ over: { timeoutMs: 50, settleGraceMs: 50 }, scenario: () => new Promise(() => {}) });
  const r = await runWithLifecycle(t.cfg);
  assert.equal(r.scenario, 'timeout'); assert.equal(r.ok, false);
  assert.equal(loadJournal(t.cfg.journalPath).runner.scenarioNotSettled, true);
  assert.equal(r.status, 'closed'); assert.equal(t.chain.state().fund, '1000');
});

test('SIGTERM during the scenario cancels it; cleanup enters once even with a second signal', async () => {
  const t = setup({ n: 2, scenario: async ({ signal }, { signals }) => { setTimeout(() => signals.emit('SIGTERM'), 20); await new Promise(res => signal.addEventListener('abort', res)); } });
  // a second signal arrives while cleanup runs
  const real = t.cfg.ports.prepareSweep;
  t.cfg.ports = { ...t.cfg.ports, prepareSweep: async (...a) => { t.signals.emit('SIGINT'); return real(...a); } };
  const r = await runWithLifecycle(t.cfg);
  assert.equal(r.scenario, 'cancelled'); assert.equal(r.interrupted, 'SIGTERM'); assert.equal(exitCodeFor(r), 143);
  assert.ok(r.extraSignals >= 1);
  assert.equal(r.status, 'closed'); assert.equal(t.chain.state().signs, 4); // 4 signatures in all, cleanup not re-entered
  assert.equal(t.signals.listenerCount('SIGTERM'), 0); assert.equal(t.signals.listenerCount('SIGINT'), 0);
});

test('SIGINT before funding starts: nothing is funded', async () => {
  const t = setup();
  const fundFn = t.cfg.fund;
  t.cfg.fund = async () => { t.signals.emit('SIGINT'); await fundFn(); };
  const r = await runWithLifecycle(t.cfg);
  assert.equal(r.scenario, 'cancelled'); assert.equal(t.calls.scenario, 0);
  assert.equal(r.status, 'closed'); assert.equal(exitCodeFor(r), 130);
  assert.equal(t.chain.state().fund, '1000');
});

test('a failed funding step is treated as funded: cleanup still runs', async () => {
  const t = setup();
  const fundFn = t.cfg.fund;
  t.cfg.fund = async () => { await fundFn(); throw new Error('rpc dropped after the transfer'); };
  const r = await runWithLifecycle(t.cfg);
  assert.equal(r.scenario, 'fund_failed'); assert.equal(r.ok, false); assert.equal(t.calls.scenario, 0);
  assert.equal(t.chain.state().fund, '1000');
});

// ---------- wrong receipts, uncertainty, residuals ----------
test('wrong recipient, token, chain or status: sticky mismatch/failure, a zero balance is not recovery', async () => {
  for (const [opts, expectState] of [[{ redirect: true }, 'unknown'], [{ wrongToken: true }, 'unknown'], [{ wrongChain: true }, 'unknown'], [{ revert: ['w1'] }, 'failed']]) {
    const t = setup({ n: 2, chain: opts });
    const r = await runWithLifecycle(t.cfg);
    assert.notEqual(r.status, 'closed', JSON.stringify(opts)); assert.equal(r.ok, false);
    const j = loadJournal(t.cfg.journalPath);
    if (expectState === 'unknown') assert.equal(j.wallets.w1.state, 'unknown', JSON.stringify(opts));
    else assert.ok(!['empty', 'swept'].includes(j.wallets.w1.state), JSON.stringify(opts));
    // a later pass cannot turn it into recovery
    const again = await runWithLifecycle(t.cfg);
    assert.equal(again.resumed, true); assert.notEqual(again.status, 'closed', JSON.stringify(opts));
  }
});

test('dropped transaction: the original intent is held; no new nonce or signature on uncertainty', async () => {
  const t = setup({ n: 1, chain: { drop: ['w1'] } });
  const r1 = await runWithLifecycle(t.cfg);
  const signs1 = t.chain.state().signs; const hash = loadJournal(t.cfg.journalPath).wallets.w1.sweep.hash;
  assert.equal(r1.ok, false); assert.equal(r1.checkpoint.unresolved[0].sweepHash, hash);
  for (let i = 0; i < 3; i++) await runWithLifecycle(t.cfg);
  assert.equal(t.chain.state().signs, signs1); // never signed again
  assert.equal(loadJournal(t.cfg.journalPath).wallets.w1.sweep.hash, hash);
  assert.equal(t.calls.fund, 1);
});

test('resume: an interrupted run goes straight to cleanup, never funds or runs the scenario again, and reconciles cumulatively', async () => {
  const t = setup({ n: 2, chain: { drop: ['w1', 'w2'] } });
  const r1 = await runWithLifecycle(t.cfg);
  assert.equal(r1.ok, false);
  const s = t.chain.state(); s.drop = []; // the network recovers: the same bytes now land
  const hashes = Object.values(loadJournal(t.cfg.journalPath).wallets).map(w => w.sweep.hash);
  fs.writeFileSync('/dev/null', ''); // no-op, keeps the intent explicit
  // rewrite the chain state with the drop list cleared (file-less fixture: mutate in place)
  Object.assign(t.chain.state(), {});
  t.chain.state().drop.length = 0;
  const r2 = await runWithLifecycle(t.cfg);
  assert.equal(r2.resumed, true); assert.equal(t.calls.fund, 1); assert.equal(t.calls.scenario, 1);
  assert.equal(r2.status, 'closed'); assert.equal(r2.ok, false); // a resumed run never reports scenario success
  assert.deepEqual(Object.values(loadJournal(t.cfg.journalPath).wallets).flatMap(w => (w.swept || []).map(x => x.hash)).sort(), hashes.sort());
  assert.equal(t.chain.state().fund, '1000');
});

test('a later deposit during cleanup reopens the wallet, is swept, and the closure covers it', async () => {
  let deposited = false;
  const t = setup({ n: 1 });
  const chainHooks = t.chain;
  const real = t.cfg.ports.broadcast;
  t.cfg.ports = { ...t.cfg.ports, broadcast: async (raw) => { await real(raw); if (!deposited && raw.includes('0xg')) { deposited = true; chainHooks.deposit(addr(1), 5n, 1000n); } } };
  const r = await runWithLifecycle(t.cfg);
  assert.equal(deposited, true);
  assert.equal(r.status, 'closed');
  assert.equal(t.chain.state().fund, '1005');
  assert.equal(loadJournal(t.cfg.journalPath).reconciliation.swept, '15');
});

test('lost signer, no gas, an unapproved contract: explicit open status, never closed', async () => {
  const lostLater = setup({ n: 2, scenario: async (_c, { chain }) => { chain.state().lost.push('w2'); } });
  const a = await runWithLifecycle(lostLater.cfg);
  assert.equal(a.status, 'failed_cleanup'); assert.equal(a.checkpoint.unresolved.find(u => u.id === 'w2').state, 'signer_lost');
  const noGas = setup({ n: 2, fundGas: 0n });
  const b = await runWithLifecycle(noGas.cfg);
  assert.equal(b.status, 'failed_cleanup'); assert.equal(b.checkpoint.unresolved.find(u => u.id === 'w1').state, 'needs_gas');
  assert.equal(noGas.chain.state().signs, 0); // nothing signed without gas
  const locked = setup({ n: 1, chain: { contracts: [addr(1)] } });
  const c = await runWithLifecycle(locked.cfg);
  assert.equal(c.status, 'failed_cleanup');
  const approved = setup({ n: 1, chain: { contracts: [addr(1)] }, over: { approvedContracts: [addr(1)] } });
  const d = await runWithLifecycle(approved.cfg);
  assert.equal(d.status, 'closed_with_exceptions'); assert.equal(d.ok, false); assert.equal(d.acceptedWithExceptions, true); assert.equal(exitCodeFor(d), 3);
});

// ---------- persistence faults ----------
test('the first journal write failing refuses funding; a lock is not left behind', async () => {
  const t = setup();
  const real = fs.openSync;
  fs.openSync = (p, ...a) => { if (String(p).includes('journal.json.') && String(p).endsWith('.tmp')) throw new Error('EACCES'); return real(p, ...a); };
  let r; try { r = await runWithLifecycle(t.cfg); } finally { fs.openSync = real; }
  assert.equal(r.status, 'refused_not_persistent'); assert.equal(t.calls.fund, 0);
  assert.equal(fs.existsSync(t.cfg.journalPath + '.lock'), false);
});

test('storage failing after funding: no broadcast from an unpersisted intent, no successful terminal result', async () => {
  const t = setup({ n: 2 });
  let failing = false;
  const fundFn = t.cfg.fund;
  t.cfg.fund = async () => { await fundFn(); failing = true; };
  const real = fs.renameSync;
  fs.renameSync = (a, b) => { if (failing && String(b).endsWith('journal.json')) throw new Error('EIO'); return real(a, b); };
  let r; try { r = await runWithLifecycle(t.cfg); } finally { fs.renameSync = real; }
  assert.equal(t.chain.state().broadcasts.length, 0);
  assert.notEqual(r.status, 'closed'); assert.equal(r.ok, false); assert.equal(r.checkpoint.persistenceFailed, true);
  assert.equal(t.chain.state().fund, String(1000n - totalTokens(2)));
  // the last durable journal still loads and a later run with working storage recovers everything
  const again = await runWithLifecycle(t.cfg);
  assert.equal(again.resumed, true); assert.equal(again.status, 'closed'); assert.equal(t.chain.state().fund, '1000');
});

test('a failed final save is not a success', async () => {
  const t = setup({ n: 1 });
  const base = t.cfg.scenario;
  let phase = 0;
  const real = fs.renameSync;
  // fail only the final reconciliation write: the one after both sweeps have settled
  t.cfg.ports = { ...t.cfg.ports, receipt: async (h) => { const r = await t.chain.ports.receipt(h); if (r && h.startsWith('0xg')) phase = 1; return r; } };
  fs.renameSync = (a, b) => { if (phase === 1 && String(b).endsWith('journal.json')) { phase = 2; return real(a, b); } if (phase === 2 && String(b).endsWith('journal.json')) throw new Error('EIO'); return real(a, b); };
  let r; try { r = await runWithLifecycle(t.cfg); } finally { fs.renameSync = real; }
  assert.equal(phase, 2, 'the final write really was the one that failed');
  assert.notEqual(r.status, 'closed'); assert.equal(r.ok, false);
  assert.notEqual(loadJournal(t.cfg.journalPath).status, 'closed');
  void base;
});

// ---------- one owner ----------
test('concurrent start: the second runner is refused and funds nothing; a stale lock is reclaimed', async () => {
  let release;
  const gate = new Promise(r => { release = r; });
  const t = setup({ scenario: async () => { await gate; } });
  const first = runWithLifecycle(t.cfg);
  await sleep(100);
  const second = await runWithLifecycle({ ...t.cfg, signals: new EventEmitter() });
  assert.equal(second.status, 'refused_concurrent');
  release();
  const r1 = await first;
  assert.equal(r1.ok, true); assert.equal(t.calls.fund, 1);
  // a lock from a process that no longer exists is reclaimed
  const t2 = setup();
  fs.mkdirSync(path.dirname(t2.cfg.journalPath), { recursive: true });
  fs.writeFileSync(t2.cfg.journalPath + '.lock', JSON.stringify({ pid: 2 ** 22 + 12345 }));
  assert.equal((await runWithLifecycle(t2.cfg)).ok, true);
  // a closed journal cannot be run over
  const again = await runWithLifecycle(t2.cfg);
  assert.equal(again.status, 'refused_already_closed'); assert.equal(t2.calls.fund, 1);
});

// ---------- real processes: signals and crashes at each durable boundary ----------
function child(env) {
  const p = spawn(process.execPath, [path.join(here, 'lifecycle_runner_child.mjs')], { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  let out = ''; p.stdout.on('data', d => { out += d; });
  const exit = new Promise(res => p.on('exit', (code, signal) => res({ code, signal, out })));
  return { p, exit };
}
async function waitFor(file, ms = 8000) { for (let i = 0; i < ms / 25; i++) { if (fs.existsSync(file)) return; await sleep(25); } throw new Error('timeout waiting for ' + file); }
const chainOf = dir => JSON.parse(fs.readFileSync(path.join(dir, 'chain.json'), 'utf8'));
const jOf = dir => loadJournal(path.join(dir, 'private', 'journal.json'));

for (const sig of ['SIGTERM', 'SIGINT']) {
  test(`${sig} during the scenario in a disposable child: the scenario is cancelled and cleanup completes`, async () => {
    const dir = tmp();
    const c = child({ WORK_DIR: dir, N: '2', SCENARIO: 'hang' });
    await waitFor(path.join(dir, 'paused.in_scenario'));
    c.p.kill(sig);
    const r = await c.exit;
    assert.equal(r.code, sig === 'SIGINT' ? 130 : 143);
    assert.equal(jOf(dir).status, 'closed');
    assert.equal(chainOf(dir).fund, '1000');
    assert.equal(fs.statSync(path.join(dir, 'private', 'journal.json')).mode & 0o777, 0o600);
  });
}

for (const boundary of ['after_prepare', 'before_broadcast', 'after_broadcast']) {
  test(`SIGTERM at ${boundary}: the boundary completes, the child exits 143 with a closed journal and no duplicate signing`, async () => {
    const dir = tmp();
    const c = child({ WORK_DIR: dir, N: '2', PAUSE_AT: boundary });
    await waitFor(path.join(dir, 'paused.' + boundary));
    c.p.kill('SIGTERM'); await sleep(100); fs.writeFileSync(path.join(dir, 'resume'), '1');
    const r = await c.exit;
    assert.equal(r.code, 143);
    assert.equal(jOf(dir).status, 'closed');
    assert.equal(chainOf(dir).signs, 4); assert.equal(chainOf(dir).fund, '1000');
  });

  test(`SIGKILL at ${boundary}: a second process resumes from the last durable journal; every transfer lands exactly once`, async () => {
    const dir = tmp();
    const c = child({ WORK_DIR: dir, N: '2', PAUSE_AT: boundary });
    await waitFor(path.join(dir, 'paused.' + boundary));
    c.p.kill('SIGKILL'); await c.exit;
    const j1 = fs.existsSync(path.join(dir, 'private', 'journal.json')) ? jOf(dir) : null;
    assert.ok(j1); assert.notEqual(j1.status, 'closed');
    const hadIntent = Object.values(j1.wallets).some(w => w.sweep);
    const signsAtCrash = chainOf(dir).signs; const broadcastsAtCrash = chainOf(dir).broadcasts.length;
    fs.writeFileSync(path.join(dir, 'resume'), '1'); // later hooks do not pause
    const r2 = await child({ WORK_DIR: dir, N: '2' }).exit;
    const res = JSON.parse(r2.out.trim());
    assert.equal(res.resumed, true); assert.equal(res.status, 'closed'); assert.equal(r2.code, 2); // closed, but a resumed run is not a success
    const c2 = chainOf(dir);
    assert.equal(c2.fund, '1000');                                             // everything came back
    assert.equal(Object.keys(c2.mined).length, 4);                             // exactly one landed transfer per sweep
    if (boundary !== 'after_prepare') assert.ok(hadIntent);                    // the intent was durable before the broadcast
    if (boundary === 'before_broadcast' || boundary === 'after_broadcast') {
      const first = Object.values(j1.wallets).find(w => w.sweep);
      assert.ok(Object.values(c2.mined).some(m => m.amount === first.sweep.amount)); // the recorded bytes are the ones that landed
      assert.equal(c2.signs, 4);                                                // the interrupted intent was never signed a second time
    }
    if (boundary === 'after_broadcast') assert.equal(c2.broadcasts.length, broadcastsAtCrash + 3); // mined sweep not rebroadcast
    void signsAtCrash;
  });
}

test('a lost signer at start in a child refuses funding: exit 2 and nothing on the chain moves', async () => {
  const dir = tmp();
  const r = await child({ WORK_DIR: dir, N: '2', LOST: 'w1' }).exit;
  assert.equal(r.code, 2); assert.equal(JSON.parse(r.out.trim()).status, 'refused_control');
  assert.equal(chainOf(dir).signs, 0); assert.equal(chainOf(dir).fund, '1000');
});

test('with the lifecycle flag off the child runs no lifecycle and touches nothing', async () => {
  const dir = tmp();
  const r = await child({ WORK_DIR: dir, N: '2', ENABLED: '0' }).exit;
  assert.equal(r.code, 0); assert.equal(JSON.parse(r.out.trim()).status, 'disabled');
  assert.equal(chainOf(dir).signs, 0); assert.equal(fs.existsSync(path.join(dir, 'private')), false);
});

test('checkpoint and public report never carry raw bytes, errors or keys', async () => {
  const t = setup({ n: 1, chain: { drop: ['w1'] } });
  const r = await runWithLifecycle(t.cfg);
  const j = loadJournal(t.cfg.journalPath);
  assert.ok(JSON.stringify(j).includes('raw:'));                       // the private file has them
  assert.ok(!JSON.stringify(checkpoint(j)).includes('raw:'));
  assert.ok(!JSON.stringify(publicReport(j)).includes('raw:'));
  assert.ok(!JSON.stringify(r).includes('raw:'));
  assert.equal(r.checkpoint.unresolved.length, 1);
});
