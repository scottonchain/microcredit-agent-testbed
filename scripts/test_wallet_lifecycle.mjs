import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  newJournal, saveJournal, loadJournal, validateJournal, publicView, verifyControl, runCleanup as runCleanupRaw, finalize, reconcile, terminalVerify, resolveMismatch, canonicalRaw,
} from './wallet_lifecycle.mjs';

const FUND = '0x' + 'f'.repeat(40);
const OTHER = '0x' + 'e'.repeat(40);
const addr = n => '0x' + n.toString(16).padStart(40, '0');
const key = a => a.toLowerCase();
const TOKEN = '0x' + 'd'.repeat(40);
const CHAIN = 84532;
const encodeRaw = hash => '0x' + Buffer.from('raw:' + hash).toString('hex');
const decodeRaw = raw => Buffer.from(String(raw).slice(2), 'hex').toString().slice(4);

// In-memory chain with a switch for each failure path. No network, no keys.
function makeChain({ tokens = {}, gas = {}, lost = [], contracts = [], rpcFailFor = [], receiptDelay = {}, gasFee = 10n, gasCost = 100n, redirect = false, redirectGas = false, throwMessage = null, verifierLies = false, verifier = true, feeOver = false, returnBytes = false } = {}) {
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
      return { hash, raw: returnBytes ? Buffer.from('raw:' + hash) : encodeRaw(hash) };
    },
    async prepareGasSweep(w, to, amount, nonce) {
      st.signs++; const hash = '0xg' + st.signs;
      st.pending.set(hash, { kind: 'gas', from: key(w.address), to: redirectGas ? OTHER : to, amount, nonce, id: w.id });
      return { hash, raw: returnBytes ? Buffer.from('raw:' + hash) : encodeRaw(hash) };
    },
    async broadcast(raw) {
      const hash = decodeRaw(raw); st.broadcasts.push(hash);
      const tx = st.pending.get(hash); if (!tx) throw new Error('unknown tx');
      if (st.mined.has(hash)) return; // identical bytes: no second effect
      if (st.delay[tx.id] > 0) { st.delay[tx.id]--; return; }
      st.mined.set(hash, { status: 1, from: tx.from, to: tx.to, amount: tx.amount, nonce: tx.nonce, chainId: CHAIN, token: tx.kind === 'token' ? TOKEN : undefined });
      st.nonces[tx.from] = (st.nonces[tx.from] || 0) + 1;
      if (tx.kind === 'token') { st.tokens[tx.from] = (st.tokens[tx.from] || 0n) - tx.amount; if (key(tx.to) === key(FUND)) st.fund += tx.amount; }
      else { st.gas[tx.from] = (st.gas[tx.from] || 0n) - tx.amount - gasFee; st.fundGas += tx.amount; }
    },
    async verifyPrepared(raw, { kind }) {
      const hash = decodeRaw(raw); const tx = st.pending.get(hash); if (!tx) throw new Error('undecodable');
      const honest = { kind: tx.kind === 'token' ? 'erc20' : 'native', hash, from: tx.from, chainId: CHAIN, nonce: tx.nonce, recipient: tx.to, amount: tx.amount, maxFeeWei: feeOver ? 5000n : 1000n, contract: tx.kind === 'token' ? TOKEN : undefined, nativeValue: 0n };
      return verifierLies ? { ...honest, recipient: FUND } : honest;
    },
    async receipt(hash) { const m = st.mined.get(hash); return m ? { ...m, rpc: { status: m.status } } : null; },
  };
  if (!verifier) delete ports.verifyPrepared;
  return { st, ports };
}

const roster = n => Array.from({ length: n }, (_, i) => ({ id: 'w' + (i + 1), address: addr(i + 1), role: 'client' }));
const tmpPath = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'wl-')), 'journal.json');
const fakeGate = () => {
  const calls = { preflight: [], restore: [], reconcile: [] };
  return { policyDigest: '0x' + '11'.repeat(32), calls,
    async preflight(i) { calls.preflight.push(i); return { ok: true, anchor: { number: 1, hash: '0x' + 'aa'.repeat(32) }, envelope: { fake: true, hash: i.hash }, balances: { native: '1000' } }; },
    async restoreEnvelope(i, env) { calls.restore.push(i); return { ok: true, envelope: env }; },
    async reconcileReceipt(a) { calls.reconcile.push(a); return { ok: true, fee: {} }; },
    async reconcileRevert(a) { calls.reconcile.push(a); return { ok: true, fee: { totalWei: 0n } }; },
    encodeEnvelope: e => ({ v: 1, fake: true, hash: e.hash }), decodeEnvelope: r => { if (!r || r.v !== 1) throw new Error('envelope_record_invalid'); return { fake: true, hash: r.hash }; } };
};
const D = { chainId: CHAIN, token: TOKEN, maxFeeWei: 1000n, chainGate: fakeGate() }; // the named chain, token, fee bound and chain gate every run must carry
const E = { ephemeral: true, ...D };
const runCleanup = (j, p, o = {}) => runCleanupRaw(j, p, { ...D, ...o });

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
  ports.broadcast = async raw => { const h = decodeRaw(raw); if (first && h.startsWith('0xt')) { first = false; const tx = st.pending.get(h); st.broadcasts.push(h); st.mined.set(h, { status: 0, from: tx.from, to: tx.to, amount: tx.amount, nonce: tx.nonce, chainId: CHAIN, token: TOKEN }); st.nonces[tx.from] = (st.nonces[tx.from] || 0) + 1; return; } return orig(raw); }; // a revert that the (fixture) gate verifies: the fields bind, nothing moves
  const j = newJournal('r9', FUND, ws, 't0');
  await runCleanup(j, ports, { ...E, skipGas: true });
  assert.equal(j.wallets.w1.state, 'failed');
  assert.equal(j.status, 'failed_cleanup');
  await runCleanup(j, ports, E);
  assert.equal(j.wallets.w1.state, 'swept');
  assert.equal(st.fund, 8n);
  assert.equal(j.wallets.w1.failedSweeps.length, 1); // the verified revert is kept as history, not silently overwritten
});

test('a status that is not exactly 1 or 0 is never a revert: the original intent stays, nothing is signed again', async () => {
  for (const bad of [{ status: '0x1' }, { status: undefined }, { status: null }, { status: 2 }, { status: false }, {}]) {
    const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
    const realReceipt = ports.receipt;
    ports.receipt = async h => { const r = await realReceipt(h); return r ? { ...r, ...bad, rpc: { status: bad.status } } : r; };
    const j = newJournal('rb', FUND, roster(1), 't0');
    await runCleanup(j, ports, { ...E, skipGas: true });
    const orig = JSON.stringify(j.wallets.w1.sweep && [j.wallets.w1.sweep.hash, j.wallets.w1.sweep.raw]);
    assert.notEqual(j.wallets.w1.sweep.outcome, 'failed', JSON.stringify(bad));
    assert.equal(j.wallets.w1.state, 'unknown');
    await runCleanup(j, ports, { ...E, skipGas: true });
    assert.equal(st.signs, 1, JSON.stringify(bad)); // never signed again
    assert.equal(JSON.stringify([j.wallets.w1.sweep.hash, j.wallets.w1.sweep.raw]), orig);
  }
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

test('a token receipt mismatch survives second and third passes, a reload and a zero reconciliation until dispositioned', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n }, redirect: true, verifierLies: true });
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('m1', FUND, ws, 't0');
  await runCleanup(j, ports, { save });
  assert.equal(j.wallets.w1.state, 'unknown');
  for (let i = 0; i < 2; i++) {
    await runCleanup(j, ports, { save });
    assert.equal(j.wallets.w1.state, 'unknown'); // a zero balance does not turn it into 'empty'
    assert.equal(j.wallets.w1.sweep.outcome, 'mismatch');
    reconcile(j, 0n, 0n, { save }); // the zero-sweep reconciliation cannot erase it either
    assert.equal(j.status, 'failed_cleanup');
  }
  const re = loadJournal(p);
  await runCleanup(re, ports, { save });
  assert.equal(re.wallets.w1.sweep.outcome, 'mismatch');
  assert.equal(re.status, 'failed_cleanup');
  assert.throws(() => resolveMismatch(re, 'w1', { evidence: '' }, { save }), /needs a wallet id/);
  resolveMismatch(re, 'w1', { evidence: 'explorer shows the transfer went to another address; owner decided', decidedBy: 'owner' }, { save });
  assert.equal(re.reconciliation, null);
  await runCleanup(re, ports, { save });
  reconcile(re, 0n, st.fund, { save });
  assert.equal(re.wallets.w1.sweep.outcome, 'dispositioned');
  assert.equal(re.status, 'closed');
});

test('a gas-return receipt mismatch is just as sticky', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: {}, gas: { [addr(1)]: 1000n }, redirectGas: true, verifierLies: true });
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('m2', FUND, ws, 't0');
  await runCleanup(j, ports, { save });
  assert.equal(j.wallets.w1.gas.state, 'unknown');
  for (let i = 0; i < 2; i++) {
    await runCleanup(j, ports, { save });
    assert.equal(j.wallets.w1.gas.sweep.outcome, 'mismatch');
    reconcile(j, 0n, st.fund, { save });
    assert.equal(j.status, 'failed_cleanup');
  }
  const re = loadJournal(p);
  await runCleanup(re, ports, { save });
  assert.equal(re.status, 'failed_cleanup');
  assert.equal(re.wallets.w1.gas.sweep.outcome, 'mismatch');
});

test('permanently failing storage: repeated cleanup passes broadcast nothing, tokens or gas', async () => {
  const bad = () => { throw new Error('disk'); };
  for (const scenario of [{ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } }, { tokens: {}, gas: { [addr(1)]: 1000n } }]) {
    const { st, ports } = makeChain(scenario);
    const j = newJournal('d1', FUND, roster(1), 't0');
    for (let i = 0; i < 3; i++) await runCleanup(j, ports, { save: bad });
    assert.equal(st.broadcasts.length, 0);
    assert.equal(st.fund, 0n);
    assert.equal(j.status, 'failed_cleanup');
    assert.equal(j.persistence.failed, true);
  }
});

test('a reconciliation goes stale when a later sweep happens, across a reload; a rerun is required', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('s1', FUND, ws, 't0');
  await runCleanup(j, ports, { save });
  reconcile(j, 0n, st.fund, { save });
  assert.equal(j.status, 'closed');
  st.tokens[key(addr(1))] = 5n; st.gas[key(addr(1))] = 1000n; // a later deposit plus gas
  await runCleanup(j, ports, { save });
  assert.equal(st.fund, 13n);
  assert.notEqual(j.status, 'closed'); // the old reconciliation (8) no longer describes the run
  assert.equal(j.status, 'pending_reconciliation');
  assert.equal(j.staleReconciliations.length, 1);
  const re = loadJournal(p);
  finalize(re, { save });
  assert.equal(re.status, 'pending_reconciliation');
  reconcile(re, 0n, st.fund, { save });
  assert.equal(re.status, 'closed');
  assert.equal(re.reconciliation.swept, '13');
});

test('a failed final save never returns a terminal status; the last durable journal recovers', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('f1', FUND, ws, 't0');
  await runCleanup(j, ports, { save });
  assert.equal(j.status, 'pending_reconciliation');
  reconcile(j, 0n, st.fund, { save: () => { throw new Error('disk'); } });
  assert.equal(j.status, 'failed_cleanup');
  assert.equal(j.persistence.failed, true);
  finalize(j, { save: () => { throw new Error('disk'); } });
  assert.equal(j.status, 'failed_cleanup');
  // the last durable file never claimed closure; reloading it and reconciling with working storage closes
  const re = loadJournal(p);
  assert.equal(re.status, 'pending_reconciliation');
  assert.equal(re.persistence.failed, false);
  reconcile(re, 0n, st.fund, { save });
  assert.equal(re.status, 'closed');
  assert.equal(loadJournal(p).status, 'closed');
});

test('a final terminalVerify save failure is not a success either', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('f2', FUND, ws, 't0');
  await runCleanup(j, ports, { save });
  reconcile(j, 0n, st.fund, { save });
  assert.equal(j.status, 'closed');
  await terminalVerify(j, ports, { save: () => { throw new Error('disk'); } });
  assert.equal(j.status, 'failed_cleanup');
});

test('a journal written before reconciliations had a fingerprint cannot close a changed run', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('l1', FUND, ws, 't0');
  await runCleanup(j, ports, { save });
  reconcile(j, 0n, st.fund, { save });
  assert.equal(j.status, 'closed');
  // rewrite the file exactly as the previous version laid it out: no fingerprint, no history
  const old = JSON.parse(fs.readFileSync(p, 'utf8'));
  delete old.reconciliation.fingerprint; delete old.reconciliationHistory; delete old.staleReconciliations;
  fs.writeFileSync(p, JSON.stringify(old));
  const re = loadJournal(p);
  assert.equal(re.reconciliation, null);                 // migrated aside on load
  assert.equal(re.status, 'pending_reconciliation');     // an old "closed" is no longer trusted
  assert.equal(re.staleReconciliations[0].legacy, true);
  st.tokens[key(addr(1))] = 5n; st.gas[key(addr(1))] = 1000n;
  await runCleanup(re, ports, { save });
  assert.equal(st.fund, 13n);
  assert.equal(re.status, 'pending_reconciliation');
  reconcile(re, 0n, st.fund, { save });
  assert.equal(re.status, 'closed');
  assert.equal(re.reconciliation.swept, '13');
  // finalize alone also refuses a fingerprint-less reconciliation handed to it directly
  const j2 = loadJournal(p);
  j2.reconciliation = { swept: '8', fundingGain: '8', matches: true };
  finalize(j2, { save });
  assert.equal(j2.status, 'pending_reconciliation');
});

test('saveJournal is private even when a world-readable temp file already exists, and it fsyncs the directory', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wl-perm-'));
  const p = path.join(dir, 'journal.json');
  fs.writeFileSync(p + '.tmp', 'stale', { mode: 0o644 });
  fs.chmodSync(p + '.tmp', 0o644);
  fs.writeFileSync(p, 'old', { mode: 0o644 });
  fs.chmodSync(p, 0o644);
  const j = newJournal('p1', FUND, roster(1), 't0');
  const fsyncs = []; const real = fs.fsyncSync;
  fs.fsyncSync = fd => { fsyncs.push(fs.fstatSync(fd).isDirectory()); return real(fd); };
  try { saveJournal(p, j); } finally { fs.fsyncSync = real; }
  assert.equal(fs.statSync(p).mode & 0o777, 0o600);
  assert.deepEqual(fsyncs, [false, true]);               // file content, then the containing directory
  assert.equal(fs.readFileSync(p + '.tmp', 'utf8'), 'stale'); // the predictable name is never used or leaked into
  assert.deepEqual(fs.readdirSync(dir).sort(), ['journal.json', 'journal.json.tmp']); // no temp file left behind
  assert.equal(JSON.parse(fs.readFileSync(p, 'utf8')).runId, 'p1');
});

test('saveJournal removes its temp file when the write fails', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wl-fail-'));
  const p = path.join(dir, 'journal.json');
  const j = newJournal('p2', FUND, roster(1), 't0');
  const real = fs.renameSync;
  fs.renameSync = () => { throw new Error('rename'); };
  try { assert.throws(() => saveJournal(p, j)); } finally { fs.renameSync = real; }
  assert.deepEqual(fs.readdirSync(dir), []);
});

function withWriteSync(impl, fn) {
  const real = fs.writeSync; fs.writeSync = impl(real);
  try { return fn(); } finally { fs.writeSync = real; }
}

test('a short write that makes progress is completed; the journal on disk is whole and valid', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wl-short-'));
  const p = path.join(dir, 'journal.json');
  const j = newJournal('s1', FUND, roster(2), 't0');
  let calls = 0;
  withWriteSync(real => (fd, buf, off, len) => { calls++; return real(fd, buf, off, Math.min(len, 7)); }, () => saveJournal(p, j));
  assert.ok(calls > 3);
  assert.equal(loadJournal(p).runId, 's1');
});

test('zero progress or a partial write followed by an error fails the save and keeps the previous valid journal', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wl-zero-'));
  const p = path.join(dir, 'journal.json');
  const j1 = newJournal('first', FUND, roster(1), 't0');
  saveJournal(p, j1);
  const j2 = newJournal('second', FUND, roster(1), 't1');
  assert.throws(() => withWriteSync(real => (fd, buf, off, len) => real(fd, buf, off, Math.min(len, 5)) && 0, () => saveJournal(p, j2)));
  assert.equal(loadJournal(p).runId, 'first');
  let n = 0;
  assert.throws(() => withWriteSync(real => (fd, buf, off, len) => { if (n++ === 1) throw new Error('EIO'); return real(fd, buf, off, Math.min(len, 5)); }, () => saveJournal(p, j2)));
  assert.equal(loadJournal(p).runId, 'first');
  assert.deepEqual(fs.readdirSync(dir), ['journal.json']); // no temp file left behind
});

test('a short write on the intent save never lets a broadcast happen', async () => {
  const ws = roster(1);
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wl-intent-'));
  const p = path.join(dir, 'journal.json');
  const j = newJournal('i1', FUND, ws, 't0');
  saveJournal(p, j);
  const save = jj => saveJournal(p, jj);
  await withWriteSyncAsync(real => (fd, buf, off, len) => 0, () => runCleanup(j, ports, { save }));
  assert.equal(st.broadcasts.length, 0);
  assert.equal(j.persistence.failed, true);
  assert.notEqual(j.status, 'closed');
  assert.equal(loadJournal(p).runId, 'i1'); // the earlier valid journal is intact and loadable
});

async function withWriteSyncAsync(impl, fn) {
  const real = fs.writeSync; fs.writeSync = impl(real);
  try { return await fn(); } finally { fs.writeSync = real; }
}

// ---- signed-bytes format and the mandatory pre-broadcast verifier (Codex review of 2a9a531b) ----

test('canonicalRaw: one lossless form; garbage, odd hex, empty and oversize are not signed intents', () => {
  assert.equal(canonicalRaw('0xAB01'), '0xab01');
  assert.equal(canonicalRaw(new Uint8Array([171, 1])), '0xab01');
  assert.equal(canonicalRaw(Buffer.from([171, 1])), '0xab01');
  assert.equal(canonicalRaw(new Uint8Array(Buffer.from('0xab01'.slice(2), 'hex')).subarray(1)), '0x01'); // a view keeps only its own bytes
  for (const bad of ['', '0x', 'ab01', '0xabc', '0xzz', 'raw:0xt1', null, undefined, 5, {}, [1, 2], new Uint8Array(0), '0x' + 'ab'.repeat(200000)]) assert.equal(canonicalRaw(bad), null, String(bad).slice(0, 20));
});

for (const [kind, opts] of [['token', { tokens: { [addr(1)]: 8n } }], ['gas', { tokens: {}, gas: { [addr(1)]: 1000n } }]]) {
  test(`byte-array raw (${kind}): stored as one canonical string, survives a real JSON reload, rebroadcast byte for byte, one signature`, async () => {
    const { st, ports } = makeChain({ gas: { [addr(1)]: 1000n }, ...opts, returnBytes: true, receiptDelay: { w1: 1 } });
    const real = ports.broadcast; let offline = true; let seen = [];
    ports.broadcast = async raw => { seen.push(raw); if (offline) throw new Error('offline'); return real(raw); };
    const p = tmpPath(); const save = jj => saveJournal(p, jj);
    const j = newJournal('rb-' + kind, FUND, roster(1), 't0');
    await runCleanup(j, ports, { save });
    const w = j.wallets.w1; const sweep = kind === 'token' ? w.sweep : w.gas.sweep;
    assert.equal(typeof sweep.raw, 'string');
    assert.equal(sweep.raw, canonicalRaw(sweep.raw));
    const stored = loadJournal(p).wallets.w1; // real JSON reload
    const reloaded = kind === 'token' ? stored.sweep : stored.gas.sweep;
    assert.equal(reloaded.raw, sweep.raw);
    assert.equal(st.signs, 1);
    offline = false; st.delay = {}; seen = [];
    const resumed = loadJournal(p);
    await runCleanup(resumed, ports, { save });
    assert.equal(st.signs, kind === 'token' ? 2 : 1, 'the stored intent was not signed again (the token run signs one later gas return)');
    assert.ok(st.mined.has(sweep.hash), 'the recorded intent is the one that landed');
    const ofIntent = seen.filter(r => decodeRaw(r) === sweep.hash);
    assert.ok(ofIntent.length >= 1 && ofIntent.every(r => r === sweep.raw), 'the identical bytes were sent');
    assert.equal(st.fund + st.fundGas > 0n, true);
  });
}

function gateChain(over) {
  const c = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const real = c.ports.verifyPrepared;
  c.ports.verifyPrepared = async (raw, a) => ({ ...(await real(raw, a)), ...over });
  return c;
}
const rejections = {
  hash: { hash: '0xdeadbeef' }, signer: { from: addr(9) }, chain: { chainId: 1 }, nonce: { nonce: 7 }, recipient: { recipient: OTHER }, amount: { amount: 9n },
  fee: { maxFeeWei: 1001n }, kind: { kind: 'native' }, token: { contract: OTHER }, nativeValue: { nativeValue: 1n },
};
for (const [name, over] of Object.entries(rejections)) {
  test(`gate: a decoded transaction that differs in ${name} is stored, never broadcast, and the run stays open`, async () => {
    const { st, ports } = gateChain(over);
    const j = newJournal('g-' + name, FUND, roster(1), 't0');
    await runCleanup(j, ports, { ...E, skipGas: true });
    const w = j.wallets.w1;
    assert.equal(st.broadcasts.length, 0, 'zero broadcasts');
    assert.equal(w.sweep.outcome, 'unverified');
    assert.ok(typeof w.sweep.raw === 'string' && w.sweep.raw.startsWith('0x'), 'private bytes preserved');
    assert.equal(w.state, 'unknown');
    assert.notEqual(j.status, 'closed');
    // a resume with the same failing verifier still sends nothing and signs nothing new
    await runCleanup(j, ports, { ...E, skipGas: true });
    assert.equal(st.broadcasts.length, 0); assert.equal(st.signs, 1);
  });
}

test('gate: garbage or non-canonical signed bytes are not stored as an intent and nothing is broadcast', async () => {
  for (const raw of ['raw:0xt1', 'zz', '0xabc', '', null, {}]) {
    const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
    ports.prepareSweep = async () => ({ hash: '0xt1', raw });
    const j = newJournal('g-garbage', FUND, roster(1), 't0');
    await runCleanup(j, ports, { ...E, skipGas: true });
    assert.equal(st.broadcasts.length, 0); assert.equal(j.wallets.w1.sweep, undefined); assert.equal(j.wallets.w1.state, 'unknown');
    assert.ok(j.wallets.w1.events.some(e => e.ev === 'prepare_output_invalid_not_sent'));
  }
});

test('gate: a missing verifier, or an unnamed chain, token or fee bound, fails closed with zero broadcasts', async () => {
  const cases = [{ label: 'verifier', chain: { verifier: false }, opts: E }, { label: 'chain', opts: { ephemeral: true, token: TOKEN, maxFeeWei: 1000n } },
    { label: 'token', opts: { ephemeral: true, chainId: CHAIN, maxFeeWei: 1000n } }, { label: 'fee', opts: { ephemeral: true, chainId: CHAIN, token: TOKEN } }];
  for (const c of cases) {
    const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n }, ...(c.chain || {}) });
    const j = newJournal('g-' + c.label, FUND, roster(1), 't0');
    await runCleanupRaw(j, ports, { ...c.opts, skipGas: true });
    assert.equal(st.broadcasts.length, 0, c.label);
    assert.equal(j.wallets.w1.sweep.outcome, 'unverified', c.label);
    assert.ok(j.wallets.w1.sweep.verifyReason, c.label);
  }
});

test('gate: a verifier error is a rejection; a later passing verifier sends the SAME stored bytes, signing nothing new', async () => {
  const { st, ports } = makeChain({ tokens: { [addr(1)]: 8n }, gas: { [addr(1)]: 1000n } });
  const real = ports.verifyPrepared; let broken = true;
  ports.verifyPrepared = async (raw, a) => { if (broken) throw new Error('decoder down'); return real(raw, a); };
  const p = tmpPath(); const save = jj => saveJournal(p, jj);
  const j = newJournal('g-resume', FUND, roster(1), 't0');
  await runCleanup(j, ports, { save });
  assert.equal(st.broadcasts.length, 0);
  const stored = loadJournal(p).wallets.w1.sweep; assert.equal(stored.outcome, 'unverified'); assert.equal(stored.verifyReason, 'verifier_error');
  broken = false;
  const resumed = loadJournal(p);
  await runCleanup(resumed, ports, { save });
  assert.equal(st.signs, 2, 'one token signature, plus one for the later gas return'); // the stored token intent was not signed again
  assert.equal(st.fund, 8n);
  assert.ok(st.broadcasts.includes(stored.hash));
  assert.equal(st.broadcasts.filter(h => h === stored.hash).length, 1);
});

test('gate: the gas return is gated the same way (wrong recipient on the native transfer sends nothing)', async () => {
  const { st, ports } = makeChain({ tokens: {}, gas: { [addr(1)]: 1000n } });
  const real = ports.verifyPrepared; ports.verifyPrepared = async (raw, a) => ({ ...(await real(raw, a)), recipient: OTHER });
  const j = newJournal('g-gas', FUND, roster(1), 't0');
  await runCleanup(j, ports, { ephemeral: true });
  assert.equal(st.broadcasts.length, 0);
  assert.equal(j.wallets.w1.gas.sweep.outcome, 'unverified');
  assert.notEqual(j.status, 'closed');
});
