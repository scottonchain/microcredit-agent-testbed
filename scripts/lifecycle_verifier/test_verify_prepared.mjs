// Local tests only: keys are generated in memory per run and never stored; nothing is sent anywhere.
import test from 'node:test';
import assert from 'node:assert/strict';
import { generatePrivateKey, privateKeyToAccount } from 'viem/accounts';
import { encodeFunctionData, parseTransaction, serializeTransaction, keccak256, parseAbi, hexToBigInt, toRlp, toHex } from 'viem';
import { verifyPrepared, UnsupportedTransaction, MAX_BYTES } from './verify_prepared.mjs';
import { newJournal, runCleanup } from '../wallet_lifecycle.mjs';

const FUND = '0x' + 'f'.repeat(40);
const OTHER = '0x' + 'e'.repeat(40);
const TOKEN = '0x' + 'd'.repeat(40);
const CHAIN = 84532;
const SECP_N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141n;
const abi = parseAbi(['function transfer(address to, uint256 amount) returns (bool)', 'function approve(address spender, uint256 amount) returns (bool)']);
const acct = privateKeyToAccount(generatePrivateKey());

const base = (o = {}) => ({ type: 'eip1559', chainId: CHAIN, nonce: 3, to: TOKEN, value: 0n, gas: 60000n, maxFeePerGas: 1000n, maxPriorityFeePerGas: 10n, data: encodeFunctionData({ abi, functionName: 'transfer', args: [FUND, 8n] }), ...o });
const sign = async (o, who = acct) => (await who.signTransaction(base(o))).toLowerCase();
const rejects = async (raw, reason) => assert.rejects(() => verifyPrepared(raw), e => e instanceof UnsupportedTransaction && (reason === undefined || e.reason === reason), String(reason));

test('decodes an ERC-20 transfer from the bytes alone: hash recomputed, signer recovered, every field derived', async () => {
  const raw = await sign({});
  const d = await verifyPrepared(raw, { kind: 'native' }); // the lie in the second argument is ignored
  assert.equal(d.kind, 'erc20'); assert.equal(d.hash, keccak256(raw)); assert.equal(d.from, acct.address.toLowerCase());
  assert.equal(d.chainId, CHAIN); assert.equal(d.nonce, 3); assert.equal(d.recipient, FUND); assert.equal(d.amount, 8n);
  assert.equal(d.contract, TOKEN); assert.equal(d.nativeValue, 0n); assert.equal(d.maxFeeWei, 60000n * 1000n);
});

test('decodes a plain native transfer; the fee bound is gas times the fee cap', async () => {
  const raw = await sign({ to: FUND, value: 777n, data: '0x', gas: 21000n, maxFeePerGas: 50n });
  const d = await verifyPrepared(raw);
  assert.equal(d.kind, 'native'); assert.equal(d.recipient, FUND); assert.equal(d.amount, 777n); assert.equal(d.contract, undefined); assert.equal(d.maxFeeWei, 21000n * 50n);
});

test('a token transfer that also carries native value reports it (the component refuses it)', async () => {
  const d = await verifyPrepared(await sign({ value: 5n }));
  assert.equal(d.nativeValue, 5n);
});

test('a different signer is recovered, never the requested one', async () => {
  const other = privateKeyToAccount(generatePrivateKey());
  assert.notEqual((await verifyPrepared(await sign({}, other))).from, acct.address.toLowerCase());
});

test('malformed and non-canonical byte strings are rejected', async () => {
  const raw = await sign({});
  for (const bad of [undefined, null, 5, '', '0x', raw.toUpperCase().replace('0X', '0x'), raw.slice(0, -1), raw.slice(0, -2), raw + '00', raw + 'ff', '0x02', '0x02c0', 'zz'])
    await rejects(bad);
  await rejects('0x' + '02' + 'ab'.repeat(MAX_BYTES), 'raw_too_large');
});

test('trailing bytes and alternate encodings of the same fields are rejected', async () => {
  const raw = await sign({});
  await rejects(raw + '00'); await rejects(raw + raw.slice(2));
});

test('unsupported envelopes are rejected: legacy, EIP-2930, EIP-4844-shaped and unknown types', async () => {
  const legacy = (await acct.signTransaction({ type: 'legacy', chainId: CHAIN, nonce: 3, to: FUND, value: 1n, gas: 21000n, gasPrice: 5n })).toLowerCase();
  await rejects(legacy, 'only_eip1559_supported');
  const t2930 = (await acct.signTransaction({ type: 'eip2930', chainId: CHAIN, nonce: 3, to: FUND, value: 1n, gas: 21000n, gasPrice: 5n, accessList: [] })).toLowerCase();
  await rejects(t2930, 'only_eip1559_supported');
  await rejects('0x03' + (await sign({})).slice(4), undefined);
  await rejects('0x7f' + (await sign({})).slice(4), 'only_eip1559_supported');
});

test('a non-empty access list is rejected', async () => {
  await rejects(await sign({ accessList: [{ address: TOKEN, storageKeys: ['0x' + '00'.repeat(32)] }] }), 'access_list_not_supported');
});

test('contract creation, zero gas and a priority fee above the cap are rejected', async () => {
  await rejects(await sign({ to: null, data: '0x6000' }), 'contract_creation_or_bad_recipient');
  await rejects(await sign({ gas: 0n }), 'gas_or_fee_invalid');
  // viem refuses to serialize a tip above the cap, so encode the envelope by hand from a valid signed one
  const t0 = parseTransaction(await sign({}));
  const n = x => (x === 0n || x === 0 ? '0x' : toHex(x));
  const body = toRlp([n(t0.chainId), n(t0.nonce), n(2000n), n(1000n), n(t0.gas), t0.to, n(0n), t0.data, [], n(t0.yParity), t0.r, t0.s]);
  await assert.rejects(() => verifyPrepared(('0x02' + body.slice(2)).toLowerCase()), e => e instanceof UnsupportedTransaction);
});

test('calldata other than exactly one transfer is rejected: approve, extra bytes, short data, dirty padding, batch-like data', async () => {
  const ok = encodeFunctionData({ abi, functionName: 'transfer', args: [FUND, 8n] });
  await rejects(await sign({ data: encodeFunctionData({ abi, functionName: 'approve', args: [FUND, 8n] }) }), 'selector_not_transfer');
  await rejects(await sign({ data: ok + '00' }), 'calldata_not_a_single_transfer');
  await rejects(await sign({ data: ok + '00'.repeat(32) }), 'calldata_not_a_single_transfer');
  await rejects(await sign({ data: ok.slice(0, -2) }), undefined);
  await rejects(await sign({ data: '0x' + ok.slice(10) }), undefined);
  await rejects(await sign({ data: ok.slice(0, 10) + 'ff' + ok.slice(12) }), 'dirty_address_padding');
  await rejects(await sign({ data: '0xac9650d8' + '00'.repeat(96) }), undefined); // multicall-like
});

test('an altered transfer selector or argument changes the decoded fields: the bytes are the only source', async () => {
  const d1 = await verifyPrepared(await sign({ data: encodeFunctionData({ abi, functionName: 'transfer', args: [OTHER, 8n] }) }));
  assert.equal(d1.recipient, OTHER);
  const d2 = await verifyPrepared(await sign({ data: encodeFunctionData({ abi, functionName: 'transfer', args: [FUND, 9n] }) }));
  assert.equal(d2.amount, 9n);
});

test('signature checks: a high-S (malleable) twin recovers the same signer yet is rejected; out-of-range r or s is rejected', async () => {
  const raw = await sign({});
  const t = parseTransaction(raw);
  const s = hexToBigInt(t.s); const lows = s <= SECP_N / 2n;
  assert.ok(lows, 'viem signs low-S');
  const twin = serializeTransaction({ ...t }, { r: t.r, s: '0x' + (SECP_N - s).toString(16).padStart(64, '0'), yParity: t.yParity === 0 ? 1 : 0 }).toLowerCase();
  await rejects(twin, 'signature_out_of_range_or_malleable');
  const zeroS = serializeTransaction({ ...t }, { r: t.r, s: '0x' + '00'.repeat(32), yParity: t.yParity }).toLowerCase();
  await rejects(zeroS, 'signature_out_of_range_or_malleable');
  const bigR = serializeTransaction({ ...t }, { r: '0x' + 'ff'.repeat(32), s: t.s, yParity: t.yParity }).toLowerCase();
  await rejects(bigR, 'signature_out_of_range_or_malleable');
});

test('an unsigned envelope is rejected', async () => {
  await rejects(serializeTransaction(base()).toLowerCase(), 'missing_signature');
});

// ---- the component's gate, with the real decoder, on really signed transactions ----
// A generated identity per wallet in an in-process "chain" (a map). No key leaves memory; no network.
function signedChain({ mutate = {} } = {}) {
  const wallets = {}; const mined = {}; const st = { broadcasts: [], signs: 0, nonces: {}, fund: 0n };
  const keyOf = id => (wallets[id] ??= privateKeyToAccount(generatePrivateKey()));
  const ports = {
    async controls() { return true; },
    async tokenBalance() { return 8n; },
    async gasBalance() { return 10_000_000n; },
    async gasCostEstimate() { return 100n; }, async gasSweepFee() { return 10n; },
    async nonceOf(a) { return st.nonces[a.toLowerCase()] ?? 0; },
    async isContract() { return false; },
    async prepareSweep(w, to, amount, nonce) {
      st.signs++;
      const raw = await keyOf(w.id).signTransaction(base({ nonce, ...mutate, data: encodeFunctionData({ abi, functionName: 'transfer', args: [mutate.recipient ?? to, mutate.amount ?? amount] }) }));
      return { hash: keccak256(raw), raw };
    },
    async prepareGasSweep(w, to, amount, nonce) {
      st.signs++;
      const raw = await keyOf(w.id).signTransaction(base({ nonce, to, value: amount, data: '0x', gas: 21000n, maxFeePerGas: 10n }));
      return { hash: keccak256(raw), raw };
    },
    async broadcast(raw) { st.broadcasts.push(raw); },
    async receipt() { return null; },
    verifyPrepared,
  };
  return { ports, st, keyOf };
}
const mk = (keyOf, ids) => ids.map(id => ({ id, address: keyOf(id).address, role: 'client' }));
const OPTS = { ephemeral: true, chainId: CHAIN, token: TOKEN, maxFeeWei: 100_000_000n, skipGas: true };

test('gate with the real decoder: an honest signed token sweep passes the gate and only the stored bytes are sent', async () => {
  const chain = signedChain({ mutate: {} });
  const j = newJournal('rv', FUND, mk(chain.keyOf, ['w1']), 't0');
  await runCleanup(j, chain.ports, OPTS);
  assert.ok(chain.st.broadcasts.length >= 1); // sent; the local fixture has no receipt, so the one retry sends the same bytes again
  assert.ok(chain.st.broadcasts.every(r => r === j.wallets.w1.sweep.raw), 'only the identical stored bytes were ever sent');
  assert.equal(chain.st.signs, 1);
  assert.equal(j.wallets.w1.sweep.outcome, 'unknown'); // never reported as swept without a receipt
});

for (const [label, mutate, reason] of [
  ['wrong recipient', { recipient: OTHER }, 'recipient_differs'],
  ['wrong amount', { amount: 9n }, 'amount_differs'],
  ['wrong token contract', { to: OTHER }, 'token_differs'],
  ['wrong chain', { chainId: 1 }, 'chain_differs'],
  ['wrong nonce', { nonce: 9 }, 'nonce_differs'],
  ['nonzero native value on a token transfer', { value: 1n }, 'native_value_present'],
  ['excessive fee', { maxFeePerGas: 10n ** 12n }, 'fee_over_bound'],
]) {
  test(`gate with the real decoder: ${label} on a really signed transaction is stored, never broadcast`, async () => {
    const ids = ['w1']; const probe = signedChain({ mutate });
    const j = newJournal('rg-' + label, FUND, mk(probe.keyOf, ids), 't0');
    await runCleanup(j, probe.ports, OPTS);
    assert.equal(probe.st.broadcasts.length, 0, 'zero broadcasts');
    assert.equal(j.wallets.w1.sweep.outcome, 'unverified'); assert.equal(j.wallets.w1.sweep.verifyReason, reason);
    assert.match(j.wallets.w1.sweep.raw, /^0x02[0-9a-f]+$/);
  });
}

test('gate with the real decoder: a signature from a different key than the wallet is a signer difference', async () => {
  const probe = signedChain();
  const stranger = privateKeyToAccount(generatePrivateKey());
  const ws = [{ id: 'w1', address: stranger.address, role: 'client' }]; // the wallet claims one address, the signer holds another
  const j = newJournal('rg-signer', FUND, ws, 't0');
  await runCleanup(j, probe.ports, OPTS);
  assert.equal(probe.st.broadcasts.length, 0);
  assert.equal(j.wallets.w1.sweep.verifyReason, 'signer_differs');
});

test('gate with the real decoder: garbage that parses as nothing is rejected as a decoder error, nothing sent', async () => {
  const probe = signedChain();
  const base0 = probe.ports.prepareSweep;
  probe.ports.prepareSweep = async (w, to, amount, nonce) => { const p = await base0(w, to, amount, nonce); return { hash: p.hash, raw: p.raw + '00' }; }; // trailing byte
  const j = newJournal('rg-trailing', FUND, [{ id: 'w1', address: probe.keyOf('w1').address, role: 'client' }], 't0');
  await runCleanup(j, probe.ports, OPTS);
  assert.equal(probe.st.broadcasts.length, 0);
  assert.equal(j.wallets.w1.sweep.verifyReason, 'verifier_error');
});

test('a non-minimal RLP integer (a leading zero in the nonce) is the same fields in another encoding: rejected as non-canonical', async () => {
  const t0 = parseTransaction(await sign({}));
  const n = x => (x === 0n || x === 0 ? '0x' : toHex(x));
  const alt = '0x02' + toRlp([n(t0.chainId), '0x0003', n(t0.maxPriorityFeePerGas), n(t0.maxFeePerGas), n(t0.gas), t0.to, n(0n), t0.data, [], n(t0.yParity), t0.r, t0.s]).slice(2);
  let parsed = true; try { parseTransaction(alt); } catch { parsed = false; }
  if (parsed) await rejects(alt.toLowerCase(), 'noncanonical_encoding');
  else await rejects(alt.toLowerCase(), 'unparseable');
  assert.ok(true, parsed ? 'parser accepted it, the re-serialization check caught it' : 'parser itself refused it');
});
