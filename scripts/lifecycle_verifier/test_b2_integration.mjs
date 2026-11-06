// B2 integration evidence. LOCAL ONLY: generated throwaway keys, an in-memory chain, no network, no real provider.
// The REAL cryptographic decoder (verifyPrepared), the REAL chain gate (createChainGate) and the REAL component (runCleanup,
// saveJournal, loadJournal) run together against sim_chain.mjs, which holds real signed transactions. A "restart" builds a NEW
// gate and NEW ports over the same chain state and reloads the journal from disk, which is all a fresh process would have.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { keccak256 } from 'viem';
import { createChainGate } from './chain_state.mjs';
import { makeSim, CHAIN_ID, TOKEN, TOKEN_CODE, FUND } from './sim_chain.mjs';
import { newJournal, runCleanup, saveJournal, loadJournal } from '../wallet_lifecycle.mjs';

const policy = (o = {}) => ({
  chainId: CHAIN_ID, approvedProviderIds: ['provider-a'], maxAnchorAgeSec: 60, maxFutureSkewSec: 5, confirmations: 2,
  token: { address: TOKEN, codeHash: keccak256(TOKEN_CODE) },
  fee: { maxExposureWei: 10n ** 15n, operatorFeeBoundWei: 1000n, l1MultiplePpm: 1_250_000, reserveWei: 0n },
  ...o,
});
const tmp = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'b2-')), 'journal.json');

// one scenario: a sim chain, one wallet, a journal on disk, and a way to "restart"
function scenario({ wallets = ['w1'], autoMine = 2, pol = policy(), ports: portOverride, saveHook } = {}) {
  const sim = makeSim({ wallets });
  sim.st.autoMine = autoMine;
  const file = tmp();
  const start = (p = pol) => {
    const gate = createChainGate({ rpc: sim.rpc(), policy: p, now: sim.now });
    const base = sim.ports();
    const ports = { ...base, ...(portOverride ? portOverride(base, sim) : {}) };
    const save = j => { if (saveHook) saveHook(j); saveJournal(file, j); };
    return { gate, ports, save, opts: { save, chainId: CHAIN_ID, token: TOKEN, maxFeeWei: 60_000_000n, chainGate: gate, gasReserveMultiple: 2 } };
  };
  const fresh = () => newJournal('run-b2', FUND, wallets.map(id => ({ id, address: sim.accounts[id].address })), '2026-11-06T00:00:00Z');
  const run = async (journal, env = start()) => runCleanup(journal, env.ports, env.opts);
  return { sim, file, start, fresh, run };
}
const tokenBalanceOf = (sim, a) => sim.st.tokens[a.toLowerCase()] ?? 0n;

test('happy path: token sweep then gas return, real decoder + real gate + real component, journal survives JSON', async () => {
  const s = scenario();
  const j = await s.run(s.fresh());
  const w = j.wallets.w1;
  assert.equal(w.state, 'swept', JSON.stringify(w.events));
  assert.equal(w.gas.state, 'returned', JSON.stringify(w.events));
  assert.equal(tokenBalanceOf(s.sim, FUND), 8n);
  assert.equal(tokenBalanceOf(s.sim, s.sim.accounts.w1.address), 0n);
  assert.equal(s.sim.st.signs, 2); // one token transfer, one gas return
  assert.equal(s.sim.st.broadcasts.length, 2);
  // reload from disk: the journal is plain JSON, no bigint, and carries no envelope once settled
  const back = loadJournal(s.file);
  assert.equal(back.wallets.w1.state, 'swept');
  assert.ok(!JSON.stringify(back).includes('"__big"'));
});

test('the retained envelope and the stage are DURABLE before the first provider send call', async () => {
  let seen;
  const s = scenario({ ports: (base, sim) => ({ async broadcast(raw) { if (!seen) { const onDisk = JSON.parse(fs.readFileSync(s.file, 'utf8')); seen = onDisk.wallets.w1.sweep; } return base.broadcast(raw); } }) });
  await s.run(s.fresh());
  assert.ok(seen, 'broadcast was called');
  assert.equal(seen.stage, 'sending');
  assert.equal(seen.envelope.v, 1);
  for (const k of ['executionCeilingWei', 'l1QuoteWei', 'l1MarginedWei', 'operatorBoundWei', 'allInWei']) assert.match(seen.envelope[k], /^(?:0|[1-9][0-9]*)$/);
  assert.match(seen.preNative, /^[0-9]+$/);
  assert.equal(seen.envelope.binding.intentHash, seen.hash);
});

test('a journal that cannot be made durable at the send stage sends nothing', async () => {
  const s = scenario({ saveHook: j => { const sw = j.wallets.w1.sweep; if (sw && sw.stage === 'sending') throw new Error('disk full'); } });
  const j = await s.run(s.fresh());
  assert.equal(s.sim.st.broadcasts.length, 0);
  assert.notEqual(j.wallets.w1.state, 'swept');
});

// every chain-state failure holds BEFORE the provider send: zero broadcast calls
const HOLDS = {
  'wrong chain': sim => { sim.st.chainId = 1; },
  'provider not approved': sim => { sim.st.providerId = 'provider-x'; },
  'oracle (L1 quote) unreadable': sim => { sim.st.l1Fail = true; },
  'block read fails': sim => { sim.st.readFail.add('getBlock'); },
  'nonce read fails': sim => { sim.st.readFail.add('nonce'); },
  'token code changed': sim => { sim.st.code[TOKEN.toLowerCase()] = '0x6080ff'; },
  'native balance below the all-in envelope': sim => { for (const k of Object.keys(sim.st.native)) if (k !== FUND.toLowerCase()) sim.st.native[k] = 50_000_000n; },
};
for (const [name, mutate] of Object.entries(HOLDS)) {
  test(`hold before send, zero provider send calls: ${name}`, async () => {
    const s = scenario();
    mutate(s.sim);
    const j = await s.run(s.fresh());
    assert.equal(s.sim.st.broadcasts.length, 0, name);
    assert.notEqual(j.wallets.w1.state, 'swept');
    assert.equal(tokenBalanceOf(s.sim, FUND), 0n);
  });
}

test('hold before send: the fee exposure authorization is below the all-in envelope', async () => {
  const s = scenario({ pol: policy({ fee: { maxExposureWei: 1_000_000n, operatorFeeBoundWei: 1000n, l1MultiplePpm: 1_250_000, reserveWei: 0n } }) });
  await s.run(s.fresh());
  assert.equal(s.sim.st.broadcasts.length, 0);
});

test('hold before send: an incomplete policy (operator fee bound zero without evidence)', async () => {
  const s = scenario({ pol: policy({ fee: { maxExposureWei: 10n ** 15n, operatorFeeBoundWei: 0n, l1MultiplePpm: 1_250_000, reserveWei: 0n } }) });
  await s.run(s.fresh());
  assert.equal(s.sim.st.broadcasts.length, 0);
});

test('hold before send: a stale anchor', async () => {
  const s = scenario();
  const env = s.start();
  const gate = createChainGate({ rpc: s.sim.rpc(), policy: policy(), now: () => s.sim.now() + 10_000 });
  await runCleanup(s.fresh(), env.ports, { ...env.opts, chainGate: gate });
  assert.equal(s.sim.st.broadcasts.length, 0);
});

test('the decoder still guards the gate: signed bytes that pay someone else are never sent', async () => {
  const stranger = '0x' + '77'.repeat(20);
  const s = scenario({ ports: (base, sim) => ({ async prepareSweep(w, to, amount, nonce) { return base.prepareSweep(w, stranger, amount, nonce); } }) });
  const j = await s.run(s.fresh());
  assert.equal(s.sim.st.broadcasts.length, 0);
  assert.equal(j.wallets.w1.sweep.outcome, 'unverified');
  assert.match(j.wallets.w1.sweep.verifyReason, /recipient_differs/);
});

test('gas return that would eat the fee reserve is refused by the gate (token funds are still swept)', async () => {
  const s = scenario({ ports: () => ({ async gasSweepFee() { return 1n; } }) });
  const j = await s.run(s.fresh());
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(s.sim.st.broadcasts.length, 1); // the token sweep only
  assert.equal(j.wallets.w1.gas.state, 'unknown');
  assert.match(String(j.wallets.w1.gas.sweep.verifyReason), /insufficient_native_reserve/);
});

test('provider unavailable at first send, then recovery: the IDENTICAL stored bytes are rebroadcast after a restart, never re-signed', async () => {
  const s = scenario();
  s.sim.st.offline = true;
  let j = await s.run(s.fresh());
  assert.equal(j.wallets.w1.state, 'unknown');
  const raw = j.wallets.w1.sweep.raw;
  assert.equal(s.sim.st.signs, 1);
  assert.ok(s.sim.st.broadcasts.length >= 1);
  // restart: reload the journal from disk, build a NEW gate and NEW ports over the same chain
  s.sim.st.offline = false;
  j = loadJournal(s.file);
  j = await s.run(j, s.start());
  assert.equal(j.wallets.w1.state, 'swept', JSON.stringify(j.wallets.w1.events));
  assert.equal(j.wallets.w1.gas.state, 'returned');
  assert.equal(s.sim.st.signs, 2); // the token transfer was signed ONCE; only the gas return added a signature
  assert.ok(s.sim.st.broadcasts.filter(b => b === raw).length >= 2); // the same bytes, again
  assert.equal(tokenBalanceOf(s.sim, FUND), 8n);
});

test('mined but not yet confirmed: no rebroadcast, no mismatch; the next run finishes', async () => {
  const s = scenario({ autoMine: 1 });
  let j = await s.run(s.fresh());
  assert.equal(j.wallets.w1.state, 'unknown');
  assert.equal(s.sim.st.broadcasts.length, 1); // never resent: it is already on chain
  assert.notEqual(j.wallets.w1.sweep.outcome, 'mismatch');
  s.sim.mine(2);
  j = await s.run(loadJournal(s.file), s.start());
  assert.equal(j.wallets.w1.state, 'swept', JSON.stringify(j.wallets.w1.events));
  assert.equal(s.sim.st.signs, 2);
});

test('reorg drops the transaction: the retained envelope is re-verified and the same bytes are sent again', async () => {
  const s = scenario({ autoMine: 1 });
  let j = await s.run(s.fresh());
  const raw = j.wallets.w1.sweep.raw;
  assert.equal(j.wallets.w1.state, 'unknown');
  s.sim.reorg(1, { keepTxs: false }); // the including block is replaced; the tx is gone and balances roll back
  s.sim.st.autoMine = 2;
  j = await s.run(loadJournal(s.file), s.start());
  assert.equal(j.wallets.w1.state, 'swept', JSON.stringify(j.wallets.w1.events));
  assert.equal(s.sim.st.broadcasts.filter(b => b === raw).length, 2);
  assert.equal(s.sim.st.signs, 2);
});

test('reorg of the preflight anchor: the restored envelope is refused and nothing is rebroadcast', async () => {
  const s = scenario({ autoMine: 0 });
  let j = await s.run(s.fresh());
  assert.equal(j.wallets.w1.state, 'unknown');
  const sent = s.sim.st.broadcasts.length;
  s.sim.reorg(1); // block 100 (the anchor) is replaced
  s.sim.st.autoMine = 2;
  j = await s.run(loadJournal(s.file), s.start());
  assert.equal(s.sim.st.broadcasts.length, sent);
  assert.match(String(j.wallets.w1.sweep.verifyReason), /anchor_not_canonical/);
  assert.notEqual(j.wallets.w1.state, 'swept');
});

test('a resume under a different policy, chain or provider sends nothing', async () => {
  for (const [name, mutate, mkPolicy, expect] of [
    ['policy changed', () => {}, () => policy({ confirmations: 3 }), /policy_changed/],
    ['provider changed', sim => { sim.st.providerId = 'provider-b'; }, () => policy({ approvedProviderIds: ['provider-a', 'provider-b'] }), /provider_differs_from_envelope|policy_changed/],
    ['chain changed', sim => { sim.st.chainId = 1; }, () => policy(), /chain_differs/],
  ]) {
    const s = scenario({ autoMine: 0 });
    s.sim.st.offline = true;
    await s.run(s.fresh());
    const sent = s.sim.st.broadcasts.length;
    mutate(s.sim); s.sim.st.offline = false;
    const j = await s.run(loadJournal(s.file), s.start(mkPolicy()));
    assert.equal(s.sim.st.broadcasts.length, sent, name);
    assert.match(String(j.wallets.w1.sweep.verifyReason), expect, name);
  }
});

test('tampered journal: the stored bytes or the stored envelope changed on disk sends nothing', async () => {
  // envelope numbers edited (a larger L1 quote makes a "cheaper" looking margin inconsistent with the oracle and policy)
  const s = scenario({ autoMine: 0 });
  s.sim.st.offline = true;
  await s.run(s.fresh());
  const sent = s.sim.st.broadcasts.length;
  s.sim.st.offline = false;
  const disk = JSON.parse(fs.readFileSync(s.file, 'utf8'));
  disk.wallets.w1.sweep.envelope.allInWei = '1';
  fs.writeFileSync(s.file, JSON.stringify(disk));
  const j = await s.run(loadJournal(s.file), s.start());
  assert.equal(s.sim.st.broadcasts.length, sent);
  assert.match(String(j.wallets.w1.sweep.verifyReason), /envelope_total_inconsistent|envelope_/);

  // signed bytes replaced by different signed bytes (valid transaction, same signer, other recipient)
  const t = scenario({ autoMine: 0 });
  t.sim.st.offline = true;
  await t.run(t.fresh());
  const before = t.sim.st.broadcasts.length;
  t.sim.st.offline = false;
  const other = await t.sim.ports().prepareSweep({ id: 'w1' }, '0x' + '77'.repeat(20), 8n, 0);
  const d2 = JSON.parse(fs.readFileSync(t.file, 'utf8'));
  d2.wallets.w1.sweep.raw = other.raw; // hash left as it was
  fs.writeFileSync(t.file, JSON.stringify(d2));
  const j2 = await t.run(loadJournal(t.file), t.start());
  assert.equal(t.sim.st.broadcasts.length, before);
  assert.match(String(j2.wallets.w1.sweep.verifyReason), /hash_differs|recipient_differs/);
});

// receipt evidence is bound to the retained envelope and the canonical chain; a wrong receipt is a sticky mismatch, never a success
const TWEAKS = {
  'L1 fee not reported': r => { const { l1Fee, ...rest } = r; return rest; },
  'L1 fee above the margined envelope': r => ({ ...r, l1Fee: 10n ** 12n }),
  'effective gas price above the signed cap': r => ({ ...r, effectiveGasPrice: 5000n }),
  'operator fee above its bound': r => ({ ...r, operatorFee: 10n ** 9n }),
  'receipt for another transaction hash': r => ({ ...r, transactionHash: '0x' + '12'.repeat(32) }),
  'receipt block not canonical': r => ({ ...r, blockHash: '0x' + '34'.repeat(32) }),
  'extra foreign log': r => ({ ...r, logs: [...r.logs, { address: '0x' + '99'.repeat(20), topics: [], data: '0x' }] }),
};
for (const [name, tweak] of Object.entries(TWEAKS)) {
  test(`receipt evidence: ${name} is a mismatch and stays one`, async () => {
    const s = scenario();
    s.sim.st.receiptTweak = tweak;
    let j = await s.run(s.fresh());
    assert.equal(j.wallets.w1.sweep.outcome, 'mismatch', name);
    assert.equal(j.wallets.w1.state, 'unknown');
    assert.ok(j.wallets.w1.sweep.mismatchReasons.length > 0);
    s.sim.st.receiptTweak = null; // a later clean read does not erase it
    j = await s.run(loadJournal(s.file), s.start());
    assert.equal(j.wallets.w1.sweep.outcome, 'mismatch');
    assert.notEqual(j.status, 'closed');
  });
}

test('operator fee reported by the receipt within the bound is accepted', async () => {
  const s = scenario();
  s.sim.st.operatorFee = 500n;
  const j = await s.run(s.fresh());
  assert.equal(j.wallets.w1.state, 'swept', JSON.stringify(j.wallets.w1.sweep));
});

test('several wallets run through the same gate and each is swept once', async () => {
  const s = scenario({ wallets: ['w1', 'w2', 'w3'] });
  const j = await s.run(s.fresh());
  for (const id of ['w1', 'w2', 'w3']) assert.equal(j.wallets[id].state, 'swept', id);
  assert.equal(tokenBalanceOf(s.sim, FUND), 24n);
  assert.equal(s.sim.st.signs, 6);
});
