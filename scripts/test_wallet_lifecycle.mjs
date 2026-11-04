import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  newJournal, saveJournal, loadJournal, verifyControl, runCleanup, finalize, reconcile, closedStates,
} from './wallet_lifecycle.mjs';

const FUND = '0x' + 'f'.repeat(40);
const addr = n => '0x' + n.toString(16).padStart(40, '0');

// A small in-memory chain with switches for each failure path. No network, no keys.
function makeChain({ wallets, tokens = {}, gas = {}, lost = [], contracts = [], rpcFailFor = [], receiptDelay = {}, gasFee = 10n, gasCost = 100n } = {}) {
  const st = {
    tokens: { ...tokens }, gas: { ...gas }, fund: 0n, mined: new Map(), pending: new Map(), broadcasts: [], signs: 0, nonces: {},
    lost: new Set(lost), contracts: new Set(contracts), rpcFail: new Set(rpcFailFor), delay: { ...receiptDelay },
  };
  const key = a => a.toLowerCase();
  const ports = {
    async controls(w) { return !st.lost.has(w.id); },
    async tokenBalance(a) { if (st.rpcFail.has(key(a))) throw new Error('rpc'); return st.tokens[key(a)] || 0n; },
    async gasBalance(a) { if (st.rpcFail.has(key(a))) throw new Error('rpc'); return st.gas[key(a)] || 0n; },
    async gasCostEstimate() { return gasCost; },
    async gasSweepFee() { return gasFee; },
    async nonceOf(a) { return st.nonces[key(a)] || 0; },
    async isContract(a) { return st.contracts.has(key(a)); },
    async prepareSweep(w, to, amount, nonce) {
      st.signs++; const hash = '0xt' + st.signs;
      st.pending.set(hash, { kind: 'token', from: key(w.address), amount, nonce, id: w.id });
      return { hash, raw: 'raw:' + hash };
    },
    async prepareGasSweep(w, to, amount, nonce) {
      st.signs++; const hash = '0xg' + st.signs;
      st.pending.set(hash, { kind: 'gas', from: key(w.address), amount, nonce, id: w.id });
      return { hash, raw: 'raw:' + hash };
    },
    async broadcast(raw) {
      const hash = raw.slice(4); st.broadcasts.push(hash);
      const tx = st.pending.get(hash); if (!tx) throw new Error('unknown tx');
      if (st.mined.has(hash)) return; // identical bytes: no second effect
      if (st.delay[tx.id] > 0) { st.delay[tx.id]--; return; } // accepted but not mined yet
      st.mined.set(hash, { status: 1 });
      if (tx.kind === 'token') { st.tokens[tx.from] = (st.tokens[tx.from] || 0n) - tx.amount; st.fund += tx.amount; st.nonces[tx.from] = (st.nonces[tx.from] || 0) + 1; }
      else { st.gas[tx.from] = (st.gas[tx.from] || 0n) - tx.amount - gasFee; st.nonces[tx.from] = (st.nonces[tx.from] || 0) + 1; }
    },
    async receipt(hash) { return st.mined.get(hash) || null; },
  };
  return { st, ports };
}

const roster = n => Array.from({ length: n }, (_, i) => ({ id: 'w' + (i + 1), address: addr(i + 1), role: 'client' }));
const tmpJournalPath = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'wl-')), 'journal.json');

test('success: tokens and gas return to the funding wallet and the run closes', async () => {
  const ws = roster(3);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 50n, [addr(2)]: 7n, [addr(3)]: 0n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n, [addr(3)]: 5n } });
  const j = newJournal('r1', FUND, ws, 't0');
  assert.deepEqual(await verifyControl(j, ports), { ok: true, missing: [] });
  await runCleanup(j, ports);
  assert.equal(j.status, 'closed');
  assert.equal(st.fund, 57n);
  assert.deepEqual(Object.values(j.wallets).map(w => w.state), ['swept', 'swept', 'empty']);
  const r = reconcile(j, 0n, st.fund);
  assert.equal(r.matches, true);
  assert.equal(j.status, 'closed');
  assert.equal(st.gas[addr(1)], 0n); // recoverable gas returned, the fee reserve spent on the return itself
  assert.equal(j.wallets.w1.gas.state, 'returned');
  assert.equal(j.wallets.w1.gas.returned, '990');
  assert.equal(j.wallets.w3.gas.state, 'residual'); // 5 wei is below the return fee: a declared exception
});

test('lost signer: funds stay put, the state is exact and the run is never closed', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 40n, [addr(2)]: 9n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n }, lost: ['w2'] });
  const j = newJournal('r2', FUND, ws, 't0');
  const c = await verifyControl(j, ports);
  assert.deepEqual(c, { ok: false, missing: ['w2'] });
  await runCleanup(j, ports);
  assert.equal(j.wallets.w2.state, 'signer_lost');
  assert.equal(j.wallets.w2.residual.tokens, '9');
  assert.equal(j.status, 'failed_cleanup');
  assert.equal(st.fund, 40n);
  assert.deepEqual(j.summary.openWallets.map(w => w.id), ['w2']);
});

test('insufficient gas: needs_gas with the numbers, nothing sent, run open', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 30n }, gas: { [addr(1)]: 50n } });
  const j = newJournal('r3', FUND, ws, 't0');
  await runCleanup(j, ports);
  assert.equal(j.wallets.w1.state, 'needs_gas');
  assert.equal(j.wallets.w1.residual.gasNeeded, '200');
  assert.equal(st.signs, 0);
  assert.equal(j.status, 'failed_cleanup');
});

test('rpc failure on a balance read: unknown, never empty, never closed', async () => {
  const ws = roster(2);
  const { ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 5n, [addr(2)]: 5n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n }, rpcFailFor: [addr(2)] });
  const j = newJournal('r4', FUND, ws, 't0');
  await runCleanup(j, ports);
  assert.equal(j.wallets.w2.state, 'unknown');
  assert.equal(j.status, 'failed_cleanup');
});

test('duplicate retry: a second run after success signs nothing and changes nothing', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 20n, [addr(2)]: 20n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n } });
  const j = newJournal('r5', FUND, ws, 't0');
  await runCleanup(j, ports);
  const signs = st.signs, fund = st.fund;
  await runCleanup(j, ports);
  await runCleanup(j, ports);
  assert.equal(st.signs, signs);
  assert.equal(st.fund, fund);
  assert.equal(j.status, 'closed');
});

test('sweep timeout, uncertain outcome: unknown, the same bytes are retried and nothing is signed twice', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 25n }, gas: { [addr(1)]: 1000n }, receiptDelay: { w1: 2 } });
  const j = newJournal('r6', FUND, ws, 't0');
  await runCleanup(j, ports, { skipGas: true });
  // first run: two broadcasts accepted but unmined -> unknown, status open, exactly one signature
  assert.equal(j.wallets.w1.state, 'unknown');
  assert.equal(j.status, 'failed_cleanup');
  assert.equal(st.signs, 1);
  assert.equal(st.fund, 0n);
  // resume: the recorded hash is checked first, the identical bytes are rebroadcast, it settles
  await runCleanup(j, ports);
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(st.fund, 25n);
  const tokenSigns = [...st.pending.keys()].filter(h => h.startsWith('0xt')).length;
  assert.equal(tokenSigns, 1);
  assert.equal(j.status, 'closed');
});

test('interruption and resume from the journal on disk', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 11n, [addr(2)]: 13n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n } });
  const p = tmpJournalPath();
  const j = newJournal('r7', FUND, ws, 't0');
  // crash after the first wallet: the journal on disk carries the first sweep's state
  const save = jj => saveJournal(p, jj);
  const partial = { ...ports };
  let calls = 0;
  partial.prepareSweep = async (...a) => { if (++calls === 2) throw new Error('process killed'); return ports.prepareSweep(...a); };
  await runCleanup(j, partial, { save, skipGas: true });
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(j.wallets.w2.state, 'unknown');
  const resumed = loadJournal(p);
  await runCleanup(resumed, ports, { save });
  assert.equal(resumed.status, 'closed');
  assert.equal(st.fund, 24n);
  assert.equal(resumed.wallets.w1.swept.length, 1);
});

test('contract balance and dust are declared exceptions, not silent closure', async () => {
  const ws = roster(2);
  const { ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 20580000n, [addr(2)]: 3n }, gas: { [addr(2)]: 1000n }, contracts: [addr(1)] });
  const j = newJournal('r8', FUND, ws, 't0');
  await runCleanup(j, ports, { dust: 5n });
  assert.equal(j.wallets.w1.state, 'locked_contract');
  assert.equal(j.wallets.w2.state, 'dust_accepted');
  assert.equal(j.status, 'closed'); // exceptions are named, not blocking
  assert.deepEqual(j.summary.exceptions.map(e => e.state).sort(), ['dust_accepted', 'locked_contract']);
});

test('a failed (reverted) sweep keeps the run open and a later run can retry it', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const orig = ports.broadcast;
  let first = true;
  ports.broadcast = async raw => { if (first && raw.startsWith('raw:0xt')) { first = false; const h = raw.slice(4); st.mined.set(h, { status: 0 }); return; } return orig(raw); };
  const j = newJournal('r9', FUND, ws, 't0');
  await runCleanup(j, ports, { skipGas: true });
  assert.equal(j.wallets.w1.state, 'failed');
  assert.equal(j.status, 'failed_cleanup');
  await runCleanup(j, ports);
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(st.fund, 8n);
});

test('reconciliation mismatch keeps the run open', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ wallets: ws, tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const j = newJournal('r10', FUND, ws, 't0');
  await runCleanup(j, ports);
  assert.equal(j.status, 'closed');
  const r = reconcile(j, 0n, st.fund - 1n);
  assert.equal(r.matches, false);
  assert.equal(j.status, 'failed_cleanup');
});

test('journal input checks: funding wallet is not a scenario wallet, duplicates refused, only public data stored', () => {
  assert.throws(() => newJournal('x', FUND, [{ id: 'a', address: FUND }], 't'), /funding wallet/);
  assert.throws(() => newJournal('x', FUND, [{ id: 'a', address: addr(1) }, { id: 'b', address: addr(1) }], 't'), /duplicate/);
  assert.throws(() => newJournal('x', 'not-an-address', [], 't'), /public address/);
  const j = newJournal('x', FUND, roster(1), 't');
  const text = JSON.stringify(j);
  assert.ok(!/privateKey|mnemonic|seed|secret/i.test(text));
  assert.ok(closedStates.has('swept') && !closedStates.has('unknown') && !closedStates.has('needs_gas') && !closedStates.has('signer_lost'));
  assert.equal(finalize(newJournal('y', FUND, roster(1), 't')).status, 'failed_cleanup'); // pending is not closed
});
