// Offline tests for service/adapter.mjs: real viem encoding, hashing and signing with a throwaway key; fake public client.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { generatePrivateKey, privateKeyToAccount } from 'viem/accounts';
import { parseTransaction, keccak256, recoverTransactionAddress, decodeFunctionData } from 'viem';
import { createChainAdapter } from './service/adapter.mjs';
import { createLease } from './service/lease.mjs';
import { openJournal } from './service/pending.mjs';
import { createWorker } from './service/worker.mjs';
import { readStatus } from './service/status.mjs';

const deskAbi = [
  { type: 'function', name: 'pending', stateMutability: 'view', inputs: [], outputs: [{ type: 'address[]' }] },
  { type: 'function', name: 'reply', stateMutability: 'nonpayable', inputs: [{ name: 'applicant', type: 'address' }, { name: 'text', type: 'string' }, { name: 'backingTotal', type: 'uint256' }], outputs: [] },
];
const DESK = '0x28e1d776d9f9f60b90cfb8075ebb9d0f07c82462', A1 = '0x1111111111111111111111111111111111111111', A2 = '0x2222222222222222222222222222222222222222';
const account = privateKeyToAccount(generatePrivateKey());

function fakeClient({ pending = [] } = {}) {
  const c = { pending: [...pending], sent: [], receipts: {}, nonce: 7, fail: {}, calls: { estimate: 0 } };
  c.readContract = async ({ functionName }) => { if (c.fail.read) throw new Error('rpc down'); if (functionName === 'pending') return [...c.pending]; throw new Error('unexpected'); };
  c.getTransactionCount = async ({ blockTag }) => { assert.equal(blockTag, 'pending'); return c.nonce; };
  c.estimateGas = async () => { c.calls.estimate++; return 90_000n; };
  c.estimateFeesPerGas = async () => ({ maxFeePerGas: 2_000_000_000n, maxPriorityFeePerGas: 1_000_000_000n });
  c.sendRawTransaction = async ({ serializedTransaction }) => {
    if (c.fail.send) throw new Error('send failed');
    const hash = keccak256(serializedTransaction); c.sent.push(serializedTransaction); c.receipts[hash] = { status: 'success' };
    const tx = parseTransaction(serializedTransaction); const { args } = decodeFunctionData({ abi: deskAbi, data: tx.data });
    c.pending = c.pending.filter((a) => a.toLowerCase() !== args[0].toLowerCase()); c.nonce++; return hash;
  };
  c.getTransactionReceipt = async ({ hash }) => { const r = c.receipts[hash]; if (!r) { const e = new Error('Transaction receipt not found'); e.name = 'TransactionReceiptNotFoundError'; throw e; } return r; };
  return c;
}
const mk = (client, decide) => createChainAdapter({ publicClient: client, account, desk: DESK, deskAbi, chainId: 84532, decide: decide || (async () => ({ text: 'hello', backing: 5_000_000n })) });

test('prepare signs a real transaction: the journaled hash equals the hash of the bytes later broadcast, signed by the officer, to the desk', async () => {
  const c = fakeClient({ pending: [A1] }); const a = mk(c);
  const p = await a.prepare(A1, 1);
  assert.equal(c.sent.length, 0, 'nothing is broadcast by prepare');
  await p.broadcast(); assert.equal(c.sent.length, 1);
  assert.equal(keccak256(c.sent[0]), p.txHash);
  const tx = parseTransaction(c.sent[0]);
  assert.equal(tx.to.toLowerCase(), DESK); assert.equal(tx.nonce, 7); assert.equal(tx.chainId, 84532);
  assert.equal((await recoverTransactionAddress({ serializedTransaction: c.sent[0] })).toLowerCase(), account.address.toLowerCase());
  const { functionName, args } = decodeFunctionData({ abi: deskAbi, data: tx.data }); assert.equal(functionName, 'reply'); assert.equal(args[1], 'hello'); assert.equal(args[2], 5_000_000n);
});
test('the prepared object exposes no raw bytes', async () => {
  const p = await mk(fakeClient({ pending: [A1] })).prepare(A1, 1);
  assert.deepEqual(Object.keys(p).sort(), ['broadcast', 'nonce', 'txHash']);
  assert.doesNotMatch(JSON.stringify(p, (k, v) => (typeof v === 'bigint' ? String(v) : v)), /0x02[0-9a-f]{100,}/);
});
test('applied means the applicant left pending(); an RPC error throws and is never turned into false', async () => {
  const c = fakeClient({ pending: [A1] }); const a = mk(c);
  assert.equal(await a.applied(A1), false); assert.equal(await a.applied(A2), true);
  assert.equal(await a.applied(A1.toUpperCase().replace('0X', '0x')), false);
  c.fail.read = true; await assert.rejects(a.applied(A1), /rpc down/);
});
test('receipt: null while unmined, status once mined, other errors propagate', async () => {
  const c = fakeClient({ pending: [A1] }); const a = mk(c);
  assert.equal(await a.receipt('0xabc'), null);
  const p = await a.prepare(A1, 1); await p.broadcast(); assert.deepEqual(await a.receipt(p.txHash), { status: 'success' });
  c.getTransactionReceipt = async () => { throw new Error('boom'); }; await assert.rejects(a.receipt('0x1'), /boom/);
});
test('decide runs inside prepare, once per prepare, and its failure produces no transaction', async () => {
  const c = fakeClient({ pending: [A1] }); let n = 0;
  const a = mk(c, async () => { n++; throw new Error('model timeout'); });
  await assert.rejects(a.prepare(A1, 1), /model timeout/); assert.equal(n, 1); assert.equal(c.sent.length, 0); assert.equal(c.calls.estimate, 0);
});

// ---- adapter + worker + journal end to end (offline)
function stack(client, now = Date.now) {
  const dir = mkdtempSync(join(tmpdir(), 'svc-ad-'));
  const lease = createLease({ dir: join(dir, 'lease'), owner: 'A', ttlMs: 60_000, now }), journal = openJournal(join(dir, 'j.json'));
  const worker = createWorker({ lease, journal, statusPath: join(dir, 's.json'), chain: mk(client), now, callTimeoutMs: 2000, receiptTimeoutMs: 2000 });
  return { dir, lease, journal, worker };
}
test('end to end: one pending applicant gets exactly one signed reply, journal ends clean, status ok', async () => {
  const c = fakeClient({ pending: [A1] }); const s = stack(c);
  const r = await s.worker.pollOnce(); assert.deepEqual(r.replied, [A1]); assert.equal(c.sent.length, 1); assert.equal(s.journal.open().length, 0);
  assert.equal(readStatus(join(s.dir, 's.json')).state, 'ok');
  await s.worker.pollOnce(); assert.equal(c.sent.length, 1);
});
test('end to end: a broadcast failure keeps the hash; the next poll waits and does not sign a second reply to the same applicant', async () => {
  const c = fakeClient({ pending: [A1] }); const s = stack(c);
  c.fail.send = true; const r1 = await s.worker.pollOnce(); assert.ok(r1.error); assert.equal(s.journal.open()[0].state, 'sent');
  c.fail.send = false; const est = c.calls.estimate; const r2 = await s.worker.pollOnce();
  assert.deepEqual(r2.waited, ['reply:' + A1]); assert.equal(c.sent.length, 0); assert.equal(c.calls.estimate, est, 'no new transaction was even built');
});
