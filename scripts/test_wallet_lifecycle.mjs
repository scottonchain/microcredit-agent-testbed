import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  newJournal, saveJournal, loadJournal, validateJournal, publicView, verifyControl, runCleanup, finalize, reconcile, terminalVerify,
} from './wallet_lifecycle.mjs';

const FUND = '0x' + 'f'.repeat(40);
const OTHER = '0x' + 'e'.repeat(40);
const addr = n => '0x' + n.toString(16).padStart(40, '0');
const key = a => a.toLowerCase();

// In-memory chain with a switch for each failure path. No network, no keys.
function makeChain({ tokens = {}, gas = {}, lost = [], contracts = [], rpcFailFor = [], receiptDelay = {}, gasFee = 10n, gasCost = 100n, redirect = false, throwMessage = null } = {}) {
  const st = {
    tokens: { ...tokens }, gas: { ...gas }, fund: 0n, fundGas: 0n, mined: new Map(), pending: new Map(), broadcasts: [], signs: 0, nonces: {},
    lost: new Set(lost), contracts: new Set(contracts.map(key)), rpcFail: new Set(rpcFailFor.map(key)), delay: { ...receiptDelay },
  };
  const ports = {
    async controls(w) { return !st.lost.has(w.id); },
    async tokenBalance(a) { if (st.rpcFail.has(key(a))) throw new Error(throwMessage || 'rpc'); return st.tokens[key(a)] || 0n; },
    async gasBalance(a) { if (st.rpcFail.has(key(a))) throw new Error('rpc'); return st.gas[key(a)] || 0n; },
    async gasCostEstimate() { return gasCost; },
    async gasSweepFee() { return gasFee; },
    async nonceOf(a) { return st.nonces[key(a)] || 0; },
    async isContract(a) { return st.contracts.has(key(a)); },
    async prepareSweep(w, to, amount, nonce) {
      st.signs++; const hash = '0xt' + st.signs;
      st.pending.set(hash, { kind: 'token', from: key(w.address), to: redirect ? OTHER : to, amount, nonce, id: w.id });
      return { hash, raw: 'raw:' + hash };
    },
    async prepareGasSweep(w, to, amount, nonce) {
      st.signs++; const hash = '0xg' + st.signs;
      st.pending.set(hash, { kind: 'gas', from: key(w.address), to, amount, nonce, id: w.id });
      return { hash, raw: 'raw:' + hash };
    },
    async broadcast(raw) {
      const hash = raw.slice(4); st.broadcasts.push(hash);
      const tx = st.pending.get(hash); if (!tx) throw new Error('unknown tx');
      if (st.mined.has(hash)) return; // identical bytes: no second effect
      if (st.delay[tx.id] > 0) { st.delay[tx.id]--; return; }
      st.mined.set(hash, { status: 1, from: tx.from, to: tx.to, amount: tx.amount, nonce: tx.nonce });
      st.nonces[tx.from] = (st.nonces[tx.from] || 0) + 1;
      if (tx.kind === 'token') { st.tokens[tx.from] = (st.tokens[tx.from] || 0n) - tx.amount; if (key(tx.to) === key(FUND)) st.fund += tx.amount; }
      else { st.gas[tx.from] = (st.gas[tx.from] || 0n) - tx.amount - gasFee; st.fundGas += tx.amount; }
    },
    async receipt(hash) { return st.mined.get(hash) || null; },
  };
  return { st, ports };
}

const roster = n => Array.from({ length: n }, (_, i) => ({ id: 'w' + (i + 1), address: addr(i + 1), role: 'client' }));
const tmpPath = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'wl-')), 'journal.json');
const E = { ephemeral: true };

test('success: tokens and gas return, then a matching reconciliation closes the run', async () => {
  const ws = roster(3);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 50n, [addr(2)]: 7n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n, [addr(3)]: 5n } });
  const j = newJournal('r1', FUND, ws, 't0');
  assert.deepEqual(await verifyControl(j, ports, E), { ok: true, missing: [] });
  await runCleanup(j, ports, E);
  assert.equal(j.status, 'pending_reconciliation'); // not closed before reconciliation
  assert.equal(st.fund, 57n);
  assert.deepEqual(Object.values(j.wallets).map(w => w.state), ['swept', 'swept', 'empty']);
  assert.equal(reconcile(j, 0n, st.fund, E).matches, true);
  assert.equal(j.status, 'closed_with_exceptions'); // wallet 3 kept 5 wei: below the return fee, a named gas residual
  assert.equal(j.summary.exceptions.length, 1);
  assert.equal(j.summary.exceptions[0].gas, 'residual');
  assert.equal(j.wallets.w1.gas.state, 'returned');
});

test('closed (no exceptions) only when every wallet was emptied and the gas was returned', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 9n, [addr(2)]: 1n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n } });
  const j = newJournal('r1b', FUND, ws, 't0');
  await runCleanup(j, ports, E);
  reconcile(j, 0n, st.fund, E);
  assert.equal(j.status, 'closed');
  assert.equal(j.summary.exceptions.length, 0);
});

test('lost signer: funds stay put, the state is exact and the run never closes', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 40n, [addr(2)]: 9n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n }, lost: ['w2'] });
  const j = newJournal('r2', FUND, ws, 't0');
  assert.deepEqual(await verifyControl(j, ports, E), { ok: false, missing: ['w2'] });
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w2.state, 'signer_lost');
  assert.equal(j.wallets.w2.residual.tokens, '9');
  assert.equal(j.status, 'failed_cleanup');
  reconcile(j, 0n, st.fund, E);
  assert.equal(j.status, 'failed_cleanup');
});

test('lost gas signer after the tokens are gone: open, not closed', async () => {
  const ws = roster(1);
  const { ports } = makeChain({ tokens: {}, gas: { [addr(1)]: 1000n }, lost: ['w1'] });
  const j = newJournal('r2b', FUND, ws, 't0');
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w1.state, 'empty');
  assert.equal(j.wallets.w1.gas.state, 'signer_lost');
  assert.equal(j.status, 'failed_cleanup');
});

test('insufficient gas: needs_gas with the numbers, nothing sent, run open', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 30n }, gas: { [addr(1)]: 50n } });
  const j = newJournal('r3', FUND, ws, 't0');
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w1.state, 'needs_gas');
  assert.equal(j.wallets.w1.residual.gasNeeded, '200');
  assert.equal(st.signs, 0);
  assert.equal(j.status, 'failed_cleanup');
});

test('rpc failure on a balance read: unknown, never empty, never closed; the error text is not stored', async () => {
  const ws = roster(2);
  const { ports } = makeChain({ tokens: { [addr(1)]: 5n, [addr(2)]: 5n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n }, rpcFailFor: [addr(2)], throwMessage: 'secret=abc123 https://private-rpc' });
  const j = newJournal('r4', FUND, ws, 't0');
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w2.state, 'unknown');
  assert.equal(j.status, 'failed_cleanup');
  assert.ok(!JSON.stringify(j).includes('abc123') && !JSON.stringify(j).includes('private-rpc'));
});

test('duplicate retry: later runs sign and change nothing', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 20n, [addr(2)]: 20n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n } });
  const j = newJournal('r5', FUND, ws, 't0');
  await runCleanup(j, ports, E);
  const signs = st.signs, fund = st.fund;
  await runCleanup(j, ports, E);
  await runCleanup(j, ports, E);
  assert.equal(st.signs, signs);
  assert.equal(st.fund, fund);
  reconcile(j, 0n, st.fund, E);
  assert.equal(j.status, 'closed');
});

test('uncertain sweep: unknown, the same bytes are retried and nothing is signed twice', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 25n }, gas: { [addr(1)]: 1000n }, receiptDelay: { w1: 2 } });
  const j = newJournal('r6', FUND, ws, 't0');
  await runCleanup(j, ports, { ...E, skipGas: true });
  assert.equal(j.wallets.w1.state, 'unknown');
  assert.equal(j.status, 'failed_cleanup');
  assert.equal(st.signs, 1);
  assert.equal(st.fund, 0n);
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(st.fund, 25n);
  assert.equal([...st.pending.keys()].filter(h => h.startsWith('0xt')).length, 1);
});

test('interruption and resume from the journal on disk', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 11n, [addr(2)]: 13n }, gas: { [addr(1)]: 1000n, [addr(2)]: 1000n } });
  const p = tmpPath();
  const save = jj => saveJournal(p, jj);
  const j = newJournal('r7', FUND, ws, 't0');
  const partial = { ...ports };
  let calls = 0;
  partial.prepareSweep = async (...a) => { if (++calls === 2) throw new Error('process killed'); return ports.prepareSweep(...a); };
  await runCleanup(j, partial, { save, skipGas: true });
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(j.wallets.w2.state, 'unknown');
  assert.equal(fs.statSync(p).mode & 0o777, 0o600);
  const resumed = loadJournal(p);
  await runCleanup(resumed, ports, { save });
  reconcile(resumed, 0n, st.fund, { save });
  assert.equal(resumed.status, 'closed');
  assert.equal(st.fund, 24n);
});

test('contract balance and dust: an unapproved contract keeps the run open; approved ones close with exceptions', async () => {
  const ws = roster(2);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 20580000n, [addr(2)]: 3n }, gas: { [addr(2)]: 1000n }, contracts: [addr(1)] });
  const j = newJournal('r8', FUND, ws, 't0');
  await runCleanup(j, ports, { ...E, dust: 5n });
  assert.equal(j.wallets.w1.state, 'locked_contract');
  assert.equal(j.wallets.w2.state, 'dust_accepted');
  reconcile(j, 0n, st.fund, E);
  assert.equal(j.status, 'failed_cleanup'); // contract not approved
  await runCleanup(j, ports, { ...E, dust: 5n, approvedContracts: [addr(1)] });
  reconcile(j, 0n, st.fund, { ...E, approvedContracts: [addr(1)] });
  assert.equal(j.status, 'closed_with_exceptions');
  assert.deepEqual(j.summary.exceptions.map(e => e.state).filter(Boolean).sort(), ['dust_accepted', 'locked_contract']);
});

test('a reverted sweep keeps the run open and a later run can retry it', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const orig = ports.broadcast;
  let first = true;
  ports.broadcast = async raw => { if (first && raw.startsWith('raw:0xt')) { first = false; st.mined.set(raw.slice(4), { status: 0 }); return; } return orig(raw); };
  const j = newJournal('r9', FUND, ws, 't0');
  await runCleanup(j, ports, { ...E, skipGas: true });
  assert.equal(j.wallets.w1.state, 'failed');
  assert.equal(j.status, 'failed_cleanup');
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(st.fund, 8n);
});

test('reconciliation failure is sticky, persisted, and cleared only by a later matching one', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('r10', FUND, ws, 't0');
  await runCleanup(j, ports, { save });
  assert.equal(reconcile(j, 0n, st.fund - 1n, { save }).matches, false);
  assert.equal(j.status, 'failed_cleanup');
  finalize(j, { save }); // the codex repro: finalize must not reopen the closure
  await runCleanup(j, ports, { save }); // nor must another cleanup pass
  assert.equal(j.status, 'failed_cleanup');
  assert.equal(loadJournal(p).status, 'failed_cleanup'); // survives a reload
  assert.equal(loadJournal(p).reconciliation.matches, false);
  reconcile(j, 0n, st.fund, { save });
  assert.equal(j.status, 'closed');
  assert.equal(j.reconciliationHistory.length, 2);
});

test('a skipped gas phase can never close a run', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const j = newJournal('r11', FUND, ws, 't0');
  await runCleanup(j, ports, { ...E, skipGas: true });
  reconcile(j, 0n, st.fund, E);
  assert.equal(j.gasPhase, 'skipped');
  assert.equal(j.status, 'failed_cleanup');
});

test('wrong recipient: a receipt for another address is a mismatch, never a sweep', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n }, redirect: true });
  const j = newJournal('r12', FUND, ws, 't0');
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w1.state, 'unknown');
  assert.equal(j.wallets.w1.swept, undefined);
  assert.equal(st.fund, 0n);
  assert.equal(j.status, 'failed_cleanup');
});

test('journal input checks: empty and duplicate ids, same id with two addresses, funding wallet, tampered file', () => {
  assert.throws(() => newJournal('x', FUND, [{ id: 'a', address: FUND }], 't'), /funding wallet/);
  assert.throws(() => newJournal('x', FUND, [{ id: 'a', address: addr(1) }, { id: 'b', address: addr(1) }], 't'), /duplicate/);
  assert.throws(() => newJournal('x', FUND, [{ id: 'same', address: addr(1) }, { id: 'same', address: addr(2) }], 't'), /duplicate id/);
  assert.throws(() => newJournal('x', FUND, [{ id: '', address: addr(1) }], 't'), /invalid or empty wallet id/);
  assert.throws(() => newJournal('x', 'not-an-address', [], 't'), /public address/);
  const j = newJournal('x', FUND, roster(2), 't');
  assert.deepEqual(validateJournal(j), []);
  j.wallets.w1.id = 'w2'; // a tampered file: key and id disagree
  assert.ok(validateJournal(j).length > 0);
  const p = tmpPath(); fs.writeFileSync(p, JSON.stringify(j));
  assert.throws(() => loadJournal(p), /invalid journal/);
});

test('gas intent survives a save failure after the broadcast, and resume never signs twice', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: {}, gas: { [addr(1)]: 1000n } });
  const p = tmpPath();
  let saves = 0;
  const flaky = jj => { saves++; if (saves >= 3) throw new Error('disk full'); saveJournal(p, jj); };
  const j = newJournal('r13', FUND, ws, 't0');
  await runCleanup(j, ports, { save: flaky });
  assert.equal(j.persistence.failed, true);
  assert.equal(j.status, 'failed_cleanup'); // never claims durability
  assert.equal(st.signs, 1);
  const onDisk = loadJournal(p); // last durable journal: the gas-return intent was written before the broadcast
  assert.ok(onDisk.wallets.w1.gas.sweep && onDisk.wallets.w1.gas.sweep.hash);
  const save = jj => saveJournal(p, jj);
  await runCleanup(onDisk, ports, { save });
  assert.equal(st.signs, 1); // checked and settled by the recorded hash, not re-signed
  assert.equal(onDisk.wallets.w1.gas.state, 'returned');
});

test('intent that cannot be made durable is never broadcast', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const j = newJournal('r14', FUND, ws, 't0');
  await runCleanup(j, ports, { save: () => { throw new Error('read-only disk'); }, skipGas: true });
  assert.equal(st.broadcasts.length, 0);
  assert.equal(st.fund, 0n);
  assert.equal(j.wallets.w1.state, 'unknown');
  assert.equal(j.status, 'failed_cleanup');
  assert.equal(j.persistence.failed, true);
});

test('persistence is required: no silent no-op save outside tests', async () => {
  const { ports } = makeChain({});
  const j = newJournal('r15', FUND, roster(1), 't0');
  await assert.rejects(() => runCleanup(j, ports, {}), /persistent save function is required/);
  await assert.rejects(() => verifyControl(j, ports, {}), /persistent save function is required/);
  assert.throws(() => reconcile(j, 0n, 0n, {}), /persistent save function is required/);
});

test('a later deposit to a closed wallet is caught by the fresh terminal check', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const j = newJournal('r16', FUND, ws, 't0');
  await runCleanup(j, ports, E);
  reconcile(j, 0n, st.fund, E);
  assert.equal(j.status, 'closed');
  st.tokens[key(addr(1))] = 5n; // someone sends tokens back to the scenario wallet
  const found = await terminalVerify(j, ports, E);
  assert.deepEqual(found, [{ id: 'w1', tokens: '5' }]);
  assert.equal(j.status, 'failed_cleanup');
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w1.state, 'needs_gas'); // its gas was already returned: the new deposit cannot be swept yet
  assert.equal(j.status, 'failed_cleanup');
  st.gas[key(addr(1))] = 1000n; // a separately authorized top-up
  await runCleanup(j, ports, E);
  reconcile(j, 0n, st.fund, E); // cumulative: 8 then 5
  assert.equal(j.status, 'closed');
  assert.equal(st.fund, 13n);
});

test('the public view drops raw signed bytes and the journal never holds key material', async () => {
  const ws = roster(1);
  const { ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n }, receiptDelay: { w1: 5 } });
  const j = newJournal('r17', FUND, ws, 't0');
  await runCleanup(j, ports, { ...E, skipGas: true });
  assert.ok(j.wallets.w1.sweep.raw); // kept privately so the same bytes can be rebroadcast
  const pub = publicView(j);
  assert.equal(pub.wallets.w1.sweep.raw, undefined);
  assert.equal(pub.wallets.w1.sweep.hash, j.wallets.w1.sweep.hash);
  assert.ok(!/privateKey|mnemonic|seed|secret/i.test(JSON.stringify(j)));
});
