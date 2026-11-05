// Local only: an in-memory chain and provider. No network, no key.
import test from 'node:test';
import assert from 'node:assert/strict';
import { keccak256, encodeFunctionData, encodeEventTopics, encodeAbiParameters, parseAbi, toHex, pad } from 'viem';
import { createChainGate, classifyCode, policyProblems, EIP7702_PREFIX, IMPLEMENTATION_SLOT, L1_ORACLE } from './chain_state.mjs';

const FROM = '0x' + '11'.repeat(20); const TO = '0x' + 'ff'.repeat(20); const TOKEN = '0x' + 'dd'.repeat(20); const IMPL = '0x' + 'ab'.repeat(20);
const TOKEN_CODE = '0x6080aa'; const IMPL_CODE = '0x6080bb';
const abi = parseAbi(['function transfer(address,uint256) returns (bool)', 'function balanceOf(address) view returns (uint256)', 'event Transfer(address indexed from, address indexed to, uint256 value)', 'function getL1Fee(bytes) view returns (uint256)']);
const policy = (o = {}) => ({
  chainId: 84532, approvedProviderIds: ['provider-a'], maxAnchorAgeSec: 60, maxFutureSkewSec: 5, confirmations: 2,
  token: { address: TOKEN, codeHash: keccak256(TOKEN_CODE), proxy: { implementation: IMPL, implementationCodeHash: keccak256(IMPL_CODE) } },
  fee: { maxExposureWei: 10n ** 15n, operatorFeeBoundWei: 1000n, l1MultiplePpm: 1_250_000, reserveWei: 0n },
  ...o,
});
const NOW = 1_800_000_000;
const BLOCK = { number: 500, hash: '0x' + '0a'.repeat(32), timestamp: NOW - 5 };
const word = n => toHex(n, { size: 32 });

let defaultTx = () => undefined;
function chain(o = {}) {
  const s = {
    providerId: 'provider-a', chainId: 84532, block: { ...BLOCK }, blocks: { 500: { ...BLOCK } },
    code: { [FROM]: '0x', [TO]: '0x', [TOKEN]: TOKEN_CODE, [IMPL]: IMPL_CODE },
    storage: { [IMPLEMENTATION_SLOT]: pad(IMPL, { size: 32 }) },
    latest: 3, pending: 3, tokenBalance: 8n, native: 10n ** 16n, l1: 40_000n, fail: {}, calls: [], ...o,
  };
  const guard = name => { if (s.fail[name]) throw new Error(name + ' failed'); };
  const rpc = {
    async providerId() { guard('providerId'); return s.providerId; },
    async chainId() { guard('chainId'); return s.chainId; },
    async getBlock(x) { guard('getBlock'); s.calls.push(['getBlock', x]); return x === 'latest' ? s.block : s.blocks[x]; },
    async getCode(a, at) { guard('getCode:' + a); s.calls.push(['getCode', a, at]); return s.code[a] ?? '0x'; },
    async getStorageAt(a, slot, at) { guard('getStorageAt'); s.calls.push(['getStorageAt', a, at]); return s.storage[slot] ?? '0x' + '00'.repeat(32); },
    async getTransactionCount(a, tag, at) { guard('nonce'); s.calls.push(['nonce', tag, at]); return tag === 'pending' ? s.pending : s.latest; },
    async getTransaction(h) { guard('getTransaction'); return s.tx === undefined ? defaultTx(h) : s.tx; },
    async getBalance(a, at) { guard('getBalance'); s.calls.push(['getBalance', a, at]); return s.native; },
    async call(tx, at) {
      guard('call:' + tx.to); s.calls.push(['call', tx.to, at]);
      if (tx.to.toLowerCase() === TOKEN) return word(s.tokenBalance);
      if (tx.to.toLowerCase() === L1_ORACLE) { if (s.l1 === null) throw new Error('oracle unavailable'); return word(s.l1); }
      throw new Error('unexpected call');
    },
  };
  return { rpc, s };
}
const HASH1 = '0x' + '11'.repeat(32); const HASH2 = '0x' + '22'.repeat(32);
const intent = (o = {}) => ({ kind: 'erc20', hash: HASH1, from: FROM, recipient: TO, amount: 8n, nonce: 3, raw: '0x02f8abcd', maxFeeWei: 60_000_000n, contract: TOKEN, ...o });
const gate = (c, p = policy()) => createChainGate({ rpc: c.rpc, policy: p, now: () => NOW });

test('classifyCode: EOA, an EIP-7702 delegation designator, a contract, and garbage', () => {
  assert.equal(classifyCode('0x'), 'eoa');
  assert.equal(classifyCode(EIP7702_PREFIX + 'ab'.repeat(20)), 'delegated');
  assert.equal(classifyCode(EIP7702_PREFIX.toUpperCase().replace('0X', '0x') + 'AB'.repeat(20)), 'delegated');
  assert.equal(classifyCode(EIP7702_PREFIX + 'ab'.repeat(19)), 'contract'); // wrong length is not a designator
  assert.equal(classifyCode('0x6080'), 'contract');
  for (const bad of [undefined, null, 5, 'zz', '0xabc']) assert.equal(classifyCode(bad), 'invalid');
});

test('a clean token sweep passes: one pinned block hash, envelope with L1 and operator parts, reserve checked', async () => {
  const c = chain(); const r = await gate(c).preflight(intent());
  assert.equal(r.ok, true, JSON.stringify(r.reasons));
  assert.equal(r.envelope.l1QuoteWei, 40_000n); assert.equal(r.envelope.l1MarginedWei, 50_000n); // 1.25x, rounded up
  assert.equal(r.envelope.allInWei, 60_000_000n + 50_000n + 1000n);
  const pinned = c.s.calls.filter(x => x[0] !== 'nonce' && x[0] !== 'getBlock').map(x => x[x.length - 1]);
  assert.ok(pinned.length >= 6 && pinned.every(h => h === BLOCK.hash), 'every state read is pinned to the one anchor hash');
});

test('a native transfer passes and needs balance for value plus the envelope', async () => {
  const c = chain({ native: 10n ** 9n }); const g = gate(c);
  assert.equal((await g.preflight(intent({ kind: 'native', amount: 10n ** 9n - 100_000_000n, contract: undefined, maxFeeWei: 21_000n * 50n }))).ok, true);
  const r = await g.preflight(intent({ kind: 'native', amount: 10n ** 9n, contract: undefined, maxFeeWei: 21_000n * 50n }));
  assert.deepEqual(r.reasons, ['insufficient_native_reserve']);
});

const HOLDS = [
  ['provider not approved', { providerId: 'unknown' }, 'provider_not_approved'],
  ['chain differs', { chainId: 8453 }, 'chain_differs'],
  ['stale anchor', { block: { ...BLOCK, timestamp: NOW - 3600 } }, 'anchor_stale'],
  ['malformed anchor', { block: { number: 'x', hash: 'nope', timestamp: 1 } }, 'anchor_invalid'],
  ['sender carries an EIP-7702 delegation', { code: { [FROM]: EIP7702_PREFIX + 'cd'.repeat(20), [TO]: '0x', [TOKEN]: TOKEN_CODE, [IMPL]: IMPL_CODE } }, 'sender_code_delegated'],
  ['sender is a contract', { code: { [FROM]: '0x6001', [TO]: '0x', [TOKEN]: TOKEN_CODE, [IMPL]: IMPL_CODE } }, 'sender_code_contract'],
  ['recipient is delegated', { code: { [FROM]: '0x', [TO]: EIP7702_PREFIX + 'cd'.repeat(20), [TOKEN]: TOKEN_CODE, [IMPL]: IMPL_CODE } }, 'recipient_code_delegated'],
  ['recipient is a contract', { code: { [FROM]: '0x', [TO]: '0x6001', [TOKEN]: TOKEN_CODE, [IMPL]: IMPL_CODE } }, 'recipient_code_contract'],
  ['nonce already used', { latest: 4, pending: 4 }, 'nonce_already_used'],
  ['nonce gap', { latest: 2, pending: 2 }, 'nonce_gap'],
  ['conflicting pending transaction', { latest: 3, pending: 4 }, 'conflicting_pending_transaction'],
  ['token code upgraded', { code: { [FROM]: '0x', [TO]: '0x', [TOKEN]: '0x6080cc', [IMPL]: IMPL_CODE } }, 'token_code_hash_differs'],
  ['proxy implementation swapped', { storage: { [IMPLEMENTATION_SLOT]: pad('0x' + 'cd'.repeat(20), { size: 32 }) } }, 'token_implementation_differs'],
  ['implementation code changed', { code: { [FROM]: '0x', [TO]: '0x', [TOKEN]: TOKEN_CODE, [IMPL]: '0x6080dd' } }, 'implementation_code_hash_differs'],
  ['not enough tokens', { tokenBalance: 7n }, 'insufficient_token_balance'],
  ['fee spike pushes the envelope over the authorization', { l1: 10n ** 15n }, 'fee_exposure_exceeds_authorization'],
  ['native reserve too small', { native: 1000n }, 'insufficient_native_reserve'],
];
for (const [label, o, reason] of HOLDS) {
  test(`hold: ${label}`, async () => {
    const r = await gate(chain(o)).preflight(intent());
    assert.equal(r.ok, false); assert.ok(r.reasons.includes(reason), JSON.stringify(r.reasons));
  });
}

test('hold: another token contract than the pinned one', async () => {
  const r = await gate(chain()).preflight(intent({ contract: '0x' + 'ee'.repeat(20) }));
  assert.ok(r.reasons.includes('token_differs'));
});

test('hold: an unavailable fee oracle never becomes a zero L1 fee', async () => {
  const r = await gate(chain({ l1: null })).preflight(intent());
  assert.equal(r.ok, false); assert.ok(r.reasons.includes('l1_fee_read_failed'));
});

test('hold: every read that fails is a hold, not a pass', async () => {
  for (const name of ['providerId', 'chainId', 'getBlock', 'getCode:' + FROM, 'getCode:' + TO, 'getCode:' + TOKEN, 'getStorageAt', 'nonce', 'getBalance', 'call:' + TOKEN, 'call:' + L1_ORACLE]) {
    const r = await gate(chain({ fail: { [name]: true } })).preflight(intent());
    assert.equal(r.ok, false, name); assert.ok(r.reasons.length >= 1, name);
  }
});

test('hold: a reorg between the first and the last read (the anchor block changes hash)', async () => {
  const c = chain(); c.s.blocks[500] = { ...BLOCK, hash: '0x' + '0b'.repeat(32) };
  const r = await gate(c).preflight(intent());
  assert.ok(r.reasons.includes('anchor_changed'));
});

test('an incomplete policy refuses every send, naming what is missing', async () => {
  for (const [label, p, key] of [
    ['no chain', { ...policy(), chainId: undefined }, 'chainId'], ['no providers', { ...policy(), approvedProviderIds: [] }, 'approvedProviderIds'],
    ['no token hash', { ...policy(), token: { address: TOKEN } }, 'token.address/codeHash'],
    ['no operator bound (zero is not assumed)', { ...policy(), fee: { maxExposureWei: 1n, l1MultiplePpm: 1_000_000 } }, 'fee.'],
    ['a zero operator bound without named evidence', { ...policy(), fee: { ...policy().fee, operatorFeeBoundWei: 0n } }, 'fee.'],
    ['no future-skew policy', { ...policy(), maxFutureSkewSec: undefined }, 'maxFutureSkewSec'], ['a huge future-skew', { ...policy(), maxFutureSkewSec: 3600 }, 'maxFutureSkewSec'],
    ['multiple below 1x', { ...policy(), fee: { ...policy().fee, l1MultiplePpm: 900_000 } }, 'fee.'],
    ['no confirmations', { ...policy(), confirmations: 0 }, 'confirmations'],
  ]) {
    assert.ok(policyProblems(p).some(x => x.startsWith(key)), label);
    const r = await gate(chain(), p).preflight(intent());
    assert.equal(r.ok, false, label); assert.ok(r.reasons[0].startsWith('policy_incomplete'), label);
  }
});

test('gasReturnAmount keeps the whole all-in envelope, never just the L2 ceiling', () => {
  const env = { allInWei: 111_000n };
  const g = gate(chain(), policy({ fee: { ...policy().fee, reserveWei: 9_000n } }));
  assert.equal(g.gasReturnAmount({ balanceWei: 1_000_000n, envelope: env }), 1_000_000n - 120_000n);
  assert.equal(g.gasReturnAmount({ balanceWei: 120_000n, envelope: env }), 0n);
  assert.equal(g.gasReturnAmount({ balanceWei: 125_000n, envelope: env, gasDustWei: 6_000n }), 0n);
});

// ---- Codex B1 review 6669021623, finding 1: a missing, null or malformed answer is a hold, never a skipped check ----
const READS = {
  'latest nonce': c => { c.rpc.getTransactionCount = async (a, tag) => (tag === 'latest' ? undefined : 3); },
  'pending nonce': c => { c.rpc.getTransactionCount = async (a, tag) => (tag === 'pending' ? undefined : 3); },
  'null nonce': c => { c.rpc.getTransactionCount = async () => null; },
  'malformed nonce': c => { c.rpc.getTransactionCount = async () => 'three'; },
  'negative nonce': c => { c.rpc.getTransactionCount = async () => -1; },
  'token balance': c => { const f = c.rpc.call; c.rpc.call = async (tx, at) => (tx.to.toLowerCase() === TOKEN ? undefined : f(tx, at)); },
  'short token balance word': c => { const f = c.rpc.call; c.rpc.call = async (tx, at) => (tx.to.toLowerCase() === TOKEN ? '0x08' : f(tx, at)); },
  'L1 fee': c => { const f = c.rpc.call; c.rpc.call = async (tx, at) => (tx.to.toLowerCase() === L1_ORACLE ? undefined : f(tx, at)); },
  'L1 fee not a word': c => { const f = c.rpc.call; c.rpc.call = async (tx, at) => (tx.to.toLowerCase() === L1_ORACLE ? 'oops' : f(tx, at)); },
  'native balance': c => { c.rpc.getBalance = async () => undefined; },
  'native balance not a quantity': c => { c.rpc.getBalance = async () => 'rich'; },
  'sender code': c => { const f = c.rpc.getCode; c.rpc.getCode = async (a, at) => (a === FROM ? undefined : f(a, at)); },
  'recipient code': c => { const f = c.rpc.getCode; c.rpc.getCode = async (a, at) => (a === TO ? null : f(a, at)); },
  'token code': c => { const f = c.rpc.getCode; c.rpc.getCode = async (a, at) => (a === TOKEN ? undefined : f(a, at)); },
  'token code empty (not a token)': c => { const f = c.rpc.getCode; c.rpc.getCode = async (a, at) => (a === TOKEN ? '0x' : f(a, at)); },
  'implementation slot': c => { c.rpc.getStorageAt = async () => undefined; },
  'implementation slot short': c => { c.rpc.getStorageAt = async () => '0x1234'; },
  'implementation code': c => { const f = c.rpc.getCode; c.rpc.getCode = async (a, at) => (a === IMPL ? undefined : f(a, at)); },
  'block': c => { c.rpc.getBlock = async () => undefined; },
  'block hash': c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => ({ ...(await f(x)), hash: '0x1234' }); },
  'block number NaN': c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => ({ ...(await f(x)), number: NaN }); },
  'block timestamp missing': c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => ({ ...(await f(x)), timestamp: undefined }); },
  'chain id': c => { c.rpc.chainId = async () => undefined; },
  'provider id': c => { c.rpc.providerId = async () => undefined; },
};
for (const [label, break_] of Object.entries(READS)) {
  test(`preflight hold: ${label} resolves undefined, null or malformed (not thrown)`, async () => {
    const c = chain(); break_(c);
    const r = await gate(c).preflight(intent());
    assert.equal(r.ok, false, JSON.stringify(r)); assert.ok(r.reasons.length >= 1);
    assert.ok(r.reasons.every(x => /^[a-z0-9_:.,/-]+$/i.test(x)), 'sanitized reasons only');
  });
}
test('preflight: zero is a value, missing is not (a zero token balance holds as insufficient, an undefined one as invalid)', async () => {
  assert.ok((await gate(chain({ tokenBalance: 0n })).preflight(intent())).reasons.includes('insufficient_token_balance'));
  const c = chain(); const f = c.rpc.call; c.rpc.call = async (tx, at) => (tx.to.toLowerCase() === TOKEN ? undefined : f(tx, at));
  assert.ok((await gate(c).preflight(intent())).reasons.includes('token_balance_invalid'));
});
test('preflight: ok:true requires a complete envelope bound to this intent, provider, chain, anchor and policy', async () => {
  const r = await gate(chain()).preflight(intent());
  assert.equal(r.ok, true); assert.deepEqual(Object.keys(r.envelope.binding).sort(), ['anchorHash', 'anchorNumber', 'chainId', 'intentHash', 'policyDigest', 'providerId']);
  assert.equal(r.envelope.binding.intentHash, HASH1); assert.equal(r.envelope.binding.anchorHash, BLOCK.hash);
});
test('preflight hold: an intent without a hash, a bad amount, a bad nonce or a bad raw never passes', async () => {
  for (const o of [{ hash: undefined }, { hash: '0x12' }, { amount: -1n }, { amount: undefined }, { nonce: 'x' }, { raw: 'nope' }, { raw: undefined }, { maxFeeWei: undefined }, { kind: 'multicall' }]) {
    const r = await gate(chain()).preflight(intent(o)); assert.equal(r.ok, false, JSON.stringify(Object.keys(o)));
  }
});

// ---- finding 3: future anchors ----
test('preflight hold: an impossible future anchor is rejected under the stated skew, a small skew is tolerated', async () => {
  assert.ok((await gate(chain({ block: { ...BLOCK, timestamp: NOW + 999_999 } })).preflight(intent())).reasons.includes('anchor_in_future'));
  assert.equal((await gate(chain({ block: { ...BLOCK, timestamp: NOW + 3 } })).preflight(intent())).ok, true); // within the 5 s skew
  assert.ok((await gate(chain({ block: { ...BLOCK, timestamp: NOW + 30 } })).preflight(intent())).reasons.includes('anchor_in_future'));
});

// ---- receipt reconciliation ----
// A real lineage: A (499, the preflight anchor) <- B500 (inclusion) <- B501 (head). Every block carries parentHash.
const A = { number: 499, hash: '0x' + 'a9'.repeat(32), parentHash: '0x' + 'a8'.repeat(32), timestamp: NOW - 30 };
const B500 = { number: 500, hash: '0x' + 'b0'.repeat(32), parentHash: A.hash, timestamp: NOW - 20 };
const B501 = { number: 501, hash: '0x' + 'b1'.repeat(32), parentHash: B500.hash, timestamp: NOW - 10 };
const topics = (from, to) => encodeEventTopics({ abi, eventName: 'Transfer', args: { from, to } });
const log = (o = {}) => ({ address: TOKEN, topics: topics(FROM, TO), data: encodeAbiParameters([{ type: 'uint256' }], [8n]), ...o });
const FEE = 40_000n * 1000n + 30_000n;
const receipt = (o = {}) => ({ status: 1, transactionHash: HASH1, from: FROM, to: TOKEN, blockHash: B500.hash, blockNumber: 500, gasUsed: 40_000n, effectiveGasPrice: 1000n, l1Fee: 30_000n, operatorFee: 0n, logs: [log()], ...o });
const bal = (fee, extra = 0n) => ({ before: 10n ** 16n, after: 10n ** 16n - fee - extra });
const transferInput = (to = TO, amount = 8n) => encodeFunctionData({ abi, functionName: 'transfer', args: [to, amount] });
const txFor = (i, o = {}) => ({ hash: HASH1, from: FROM, to: i.kind === 'erc20' ? TOKEN : TO, nonce: 3, value: i.kind === 'native' ? i.amount : 0n, input: i.kind === 'erc20' ? transferInput(TO, i.amount) : '0x', blockHash: B500.hash, ...o });
// preflight at the anchor (block 499), then the chain advances: inclusion in 500, head 501. The SAME gate instance
// retains the envelope, as it must in production.
async function setup(i = intent(), { pol = policy(), o = {} } = {}) {
  const c = chain({ block: { ...A }, blocks: { 499: { ...A } }, ...o });
  const g = createChainGate({ rpc: c.rpc, policy: pol, now: () => NOW });
  const pre = await g.preflight(i); assert.equal(pre.ok, true, JSON.stringify(pre.reasons));
  c.s.block = { ...B501 }; c.s.blocks = { 499: { ...A }, 500: { ...B500 }, 501: { ...B501 } }; c.s.tx = txFor(i);
  return { c, g, envelope: pre.envelope };
}
async function REC(i, r, { b = bal(FEE), mutate, envelope, pol } = {}) {
  const s = await setup(i, { pol }); if (mutate) mutate(s.c);
  return s.g.reconcileReceipt({ intent: i, receipt: r, envelope: envelope === undefined ? s.envelope : envelope, balances: b });
}

test('receipt: a matching, bound, canonical, confirmed transfer reconciles with fee components and the balance delta', async () => {
  const r = await REC(intent(), receipt());
  assert.equal(r.ok, true, JSON.stringify(r.reasons)); assert.equal(r.fee.totalWei, FEE);
});

const RECEIPT_HOLDS = [
  ['reverted', receipt({ status: 0 }), 'receipt_not_successful'],
  ['another sender', receipt({ from: TO }), 'receipt_sender_differs'],
  ['another transaction hash (same sender, value and fee)', receipt({ transactionHash: HASH2 }), 'receipt_hash_differs'],
  ['another outer target', receipt({ to: '0x' + '99'.repeat(20) }), 'receipt_target_differs'],
  ['block hash not canonical', receipt({ blockHash: '0x' + '0c'.repeat(32) }), 'block_not_canonical'],
  ['transfer to another recipient', receipt({ logs: [log({ topics: topics(FROM, '0x' + 'ee'.repeat(20)) })] }), 'transfer_log_differs'],
  ['transfer of another amount', receipt({ logs: [log({ data: encodeAbiParameters([{ type: 'uint256' }], [9n]) })] }), 'transfer_log_differs'],
  ['no transfer log', receipt({ logs: [] }), 'transfer_log_count'],
  ['two transfer logs', receipt({ logs: [log(), log()] }), 'transfer_log_count'],
  ['a foreign log', receipt({ logs: [log(), log({ address: '0x' + '99'.repeat(20) })] }), 'foreign_logs'],
  ['L1 fee not reported', receipt({ l1Fee: undefined }), 'l1_fee_not_reported'],
  ['actual fee above the envelope', receipt({ effectiveGasPrice: 10n ** 12n }), 'actual_fee_exceeds_envelope'],
  ['fee fields malformed', receipt({ gasUsed: 'many' }), 'fee_fields_invalid'],
];
for (const [label, r, reason] of RECEIPT_HOLDS) {
  test(`receipt hold: ${label}`, async () => {
    const out = await REC(intent(), r, { b: bal(0n) });
    assert.equal(out.ok, false); assert.ok(out.reasons.includes(reason), JSON.stringify(out.reasons));
  });
}

// bound to the transaction, its outer target and its fields, fetched by hash
test('receipt hold: the earlier repro, a native intent whose receipt is a DIFFERENT transaction to the token with a matching fee and value', async () => {
  const i = intent({ kind: 'native', amount: 777n, contract: undefined }); const fee = 21_000n * 1000n + 30_000n;
  const out = await REC(i, receipt({ transactionHash: HASH2, to: TOKEN, gasUsed: 21_000n, logs: [] }), { b: bal(fee, 777n) });
  assert.ok(out.reasons.includes('receipt_hash_differs') && out.reasons.includes('receipt_target_differs'), JSON.stringify(out.reasons));
});
test('receipt: a native transfer binds to the recipient as outer target and reconciles value plus fee', async () => {
  const i = intent({ kind: 'native', amount: 777n, contract: undefined }); const fee = 21_000n * 1000n + 30_000n;
  const ok = await REC(i, receipt({ to: TO, gasUsed: 21_000n, logs: [] }), { b: bal(fee, 777n) });
  assert.equal(ok.ok, true, JSON.stringify(ok.reasons));
  assert.ok((await REC(i, receipt({ to: TO, gasUsed: 21_000n, logs: [log()] }), { b: bal(fee, 777n) })).reasons.includes('unexpected_logs_on_native_transfer'));
});
const TX_HOLDS = [
  ['the fetched transaction has another hash', { hash: HASH2 }, 'transaction_hash_differs'], ['another sender', { from: TO }, 'transaction_sender_differs'],
  ['another target', { to: '0x' + '99'.repeat(20) }, 'transaction_target_differs'], ['another nonce', { nonce: 9 }, 'transaction_nonce_differs'],
  ['native value on a token transfer', { value: 1n }, 'transaction_value_differs'],
  ['other calldata (another recipient)', { input: transferInput('0x' + 'ee'.repeat(20)) }, 'transaction_calldata_differs'],
  ['other calldata (another amount)', { input: transferInput(TO, 9n) }, 'transaction_calldata_differs'],
  ['mined in another block', { blockHash: '0x' + '0d'.repeat(32) }, 'transaction_block_differs'],
];
for (const [label, o, reason] of TX_HOLDS) {
  test(`receipt hold: ${label}`, async () => {
    const out = await REC(intent(), receipt(), { mutate: c => { c.s.tx = txFor(intent(), o); } });
    assert.ok(out.reasons.includes(reason), JSON.stringify(out.reasons));
  });
}
test('receipt hold: the transaction cannot be fetched', async () => {
  assert.ok((await REC(intent(), receipt(), { mutate: c => { c.rpc.getTransaction = async () => { throw new Error('gone'); }; } })).reasons.includes('transaction_read_failed'));
  assert.ok((await REC(intent(), receipt(), { mutate: c => { c.s.tx = null; } })).reasons.includes('transaction_read_failed'));
});

// ---- Codex B1 delta review 6670289006 ----
test('finding 1: the chain id and provider are read again at reconciliation (the repro: chainId() becomes 1 after a valid preflight)', async () => {
  const out = await REC(intent(), receipt(), { mutate: c => { c.rpc.chainId = async () => 1; } });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('chain_differs'), JSON.stringify(out.reasons));
  const prov = await REC(intent(), receipt(), { mutate: c => { c.rpc.providerId = async () => 'provider-b'; } });
  assert.ok(prov.reasons.includes('provider_differs_from_envelope'));
  const flip = await REC(intent(), receipt(), { mutate: c => { const f = c.rpc.chainId; let n = 0; c.rpc.chainId = async () => (++n === 1 ? f() : 1); } });
  assert.ok(flip.reasons.includes('provenance_changed_during_check'), JSON.stringify(flip.reasons));
});

test('finding 2: a hash-shaped anchor is not evidence: a caller envelope with another anchor is refused, and a restored one is checked against the chain', async () => {
  const { c, g, envelope } = await setup();
  const forged = { ...envelope, binding: { ...envelope.binding, anchorHash: '0x' + '77'.repeat(32), anchorNumber: 999999 } };
  const out = await g.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: forged, balances: bal(FEE) });
  assert.ok(out.reasons.includes('envelope_differs_from_retained'), JSON.stringify(out.reasons)); assert.equal(out.ok, false);
  // restore path (after a restart): the anchor must be canonical on the chain NOW
  const g2 = createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW });
  const bad = await g2.restoreEnvelope(intent(), forged); assert.equal(bad.ok, false); assert.ok(bad.reasons.includes('anchor_not_canonical'), JSON.stringify(bad.reasons));
  const good = await g2.restoreEnvelope(intent(), envelope); assert.equal(good.ok, true, JSON.stringify(good.reasons));
  const rec = await g2.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: good.envelope, balances: bal(FEE) });
  assert.equal(rec.ok, true, JSON.stringify(rec.reasons));
});
test('finding 2: the anchor must precede the inclusion block in number and time', async () => {
  const { c, g, envelope } = await setup();
  c.s.blocks[499] = { ...A, timestamp: NOW - 5 }; // anchor stamped after the inclusion block: impossible
  const out = await g.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope, balances: bal(FEE) });
  assert.ok(out.reasons.includes('anchor_not_canonical') || out.reasons.includes('anchor_not_before_inclusion'), JSON.stringify(out.reasons));
  // an envelope whose anchor is the inclusion block itself (not before it)
  const g2 = createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW });
  const same = { ...envelope, binding: { ...envelope.binding, anchorHash: B500.hash, anchorNumber: 500 } };
  const r = await g2.restoreEnvelope(intent(), same); assert.equal(r.ok, true);
  const out2 = await g2.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: r.envelope, balances: bal(FEE) });
  assert.ok(out2.reasons.includes('anchor_not_before_inclusion'), JSON.stringify(out2.reasons));
});

test('finding 3: only allInWei changed (the repro), with an actual fee of 800,030,000 and a matching balance delta', async () => {
  const { g, envelope } = await setup();
  const inflated = { ...envelope, allInWei: 1_000_000_000n };
  const big = receipt({ gasUsed: 800_000n, effectiveGasPrice: 1000n, l1Fee: 30_000n }); // 800,000,000 execution + 30,000 L1
  const out = await g.reconcileReceipt({ intent: intent(), receipt: big, envelope: inflated, balances: bal(800_030_000n) });
  assert.equal(out.ok, false);
  for (const r of ['envelope_differs_from_retained', 'actual_execution_exceeds_signed_ceiling', 'actual_fee_exceeds_envelope']) assert.ok(out.reasons.includes(r), r + ' ' + JSON.stringify(out.reasons));
  // even with the retained envelope, the same actual fee is above the signed execution ceiling and the envelope
  const honest = await g.reconcileReceipt({ intent: intent(), receipt: big, envelope, balances: bal(800_030_000n) });
  assert.ok(honest.reasons.includes('actual_execution_exceeds_signed_ceiling') && honest.reasons.includes('actual_fee_exceeds_envelope'), JSON.stringify(honest.reasons));
});
test('finding 3: a restored envelope must follow from the signed intent and the policy (ceiling, margin, operator bound, sum)', async () => {
  const { c, envelope } = await setup();
  const g2 = createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW });
  for (const [label, o, reason] of [
    ['execution ceiling swapped', { executionCeilingWei: 10n ** 12n, allInWei: 10n ** 12n + envelope.l1MarginedWei + envelope.operatorBoundWei }, 'envelope_execution_ceiling_differs_from_signed'],
    ['L1 margin changed', { l1MarginedWei: envelope.l1MarginedWei + 1n, allInWei: envelope.allInWei + 1n }, 'envelope_l1_margin_inconsistent'],
    ['operator bound changed', { operatorBoundWei: 5n, allInWei: envelope.allInWei - 995n }, 'envelope_operator_bound_differs_from_policy'],
    ['total changed', { allInWei: envelope.allInWei + 1n }, 'envelope_total_inconsistent'],
    ['over the authorization', { allInWei: 10n ** 16n }, 'envelope_exceeds_authorization'],
  ]) {
    const r = await g2.restoreEnvelope(intent(), { ...envelope, ...o });
    assert.equal(r.ok, false, label); assert.ok(r.reasons.includes(reason), label + ' ' + JSON.stringify(r.reasons));
  }
});
test('finding 3: component bounds apply to the actual cost on their own (L1 above the margined quote, operator above its bound)', async () => {
  const l1 = await REC(intent(), receipt({ l1Fee: 60_000n }), { b: bal(40_000n * 1000n + 60_000n) });
  assert.ok(l1.reasons.includes('actual_l1_exceeds_envelope'), JSON.stringify(l1.reasons));
  const op = await REC(intent(), receipt({ operatorFee: 2000n }), { b: bal(FEE + 2000n) });
  assert.ok(op.reasons.includes('actual_operator_exceeds_bound'), JSON.stringify(op.reasons));
});

test('finding 4: the inclusion block is replaced and the head advances to 502 on the LAST head read (the repro): not ok', async () => {
  const out = await REC(intent(), receipt(), { mutate: c => {
    const f = c.rpc.getBlock; let heads = 0;
    c.rpc.getBlock = async x => {
      if (x === 'latest' && ++heads === 1) { // the (only, final) head read triggers a reorg: new 500, new 501, new head 502
        const n500 = { ...B500, hash: '0x' + 'c0'.repeat(32) }; const n501 = { ...B501, hash: '0x' + 'c1'.repeat(32), parentHash: n500.hash }; const n502 = { number: 502, hash: '0x' + 'c2'.repeat(32), parentHash: n501.hash, timestamp: NOW - 5 };
        c.s.blocks[500] = n500; c.s.blocks[501] = n501; c.s.blocks[502] = n502; return n502;
      }
      return f(x);
    };
  } });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('inclusion_not_in_head_lineage') || out.reasons.includes('block_not_canonical'), JSON.stringify(out.reasons));
});
test('finding 4: the confirmation proof is a hash lineage: a head whose parent chain skips the inclusion block, a broken parent link and a short head all hold', async () => {
  const unrelated = await REC(intent(), receipt(), { mutate: c => { c.s.block = { ...B501, parentHash: '0x' + 'dd'.repeat(32) }; } });
  assert.ok(unrelated.reasons.includes('inclusion_not_in_head_lineage'), JSON.stringify(unrelated.reasons));
  const broken = await REC(intent(), receipt(), { pol: policy({ confirmations: 3 }), mutate: c => { const b502 = { number: 502, hash: '0x' + 'f2'.repeat(32), parentHash: B501.hash, timestamp: NOW - 4 }; c.s.blocks[502] = b502; c.s.blocks[501] = { ...B501, parentHash: '0x' + 'ee'.repeat(32) }; c.s.block = { ...b502 }; } });
  assert.ok(broken.reasons.includes('head_lineage_broken') || broken.reasons.includes('inclusion_not_in_head_lineage'), JSON.stringify(broken.reasons));
  const short = await REC(intent(), receipt(), { mutate: c => { c.s.block = { ...B500 }; c.s.blocks[501] = undefined; } });
  assert.ok(short.reasons.includes('not_enough_confirmations'));
  const longChain = await REC(intent(), receipt(), { pol: policy({ confirmations: 4 }), mutate: c => {
    let prev = B501; for (let n = 502; n <= 510; n++) { const b = { number: n, hash: '0x' + (n - 502 + 0x20).toString(16).padStart(2, '0').repeat(32), parentHash: prev.hash, timestamp: NOW - 4 }; c.s.blocks[n] = b; prev = b; } c.s.block = { ...prev };
  } });
  assert.equal(longChain.ok, true, JSON.stringify(longChain.reasons)); // a head far ahead is proven by the same walk
});
test('a missing, NaN, future or parent-less head never satisfies confirmations', async () => {
  for (const [label, brk] of [
    ['undefined head', c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => (x === 'latest' ? undefined : f(x)); }],
    ['NaN head number', c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => (x === 'latest' ? { ...(await f(x)), number: NaN } : f(x)); }],
    ['head without a parentHash', c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => (x === 'latest' ? { ...(await f(x)), parentHash: undefined } : f(x)); }],
  ]) assert.equal((await REC(intent(), receipt(), { mutate: brk })).ok, false, label);
  const future = await REC(intent(), receipt(), { mutate: c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => (x === 'latest' ? { ...(await f(x)), timestamp: NOW + 99999 } : f(x)); } });
  assert.ok(future.reasons.includes('head_in_future'));
});

test('receipt hold: a balance that moved by something else, and missing balances', async () => {
  assert.ok((await REC(intent(), receipt(), { b: bal(FEE, 1n) })).reasons.includes('sender_balance_delta_differs'));
  const { g, envelope } = await setup();
  assert.ok((await g.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope })).reasons.includes('balances_missing'));
});

// ---- envelope required, retained, bound ----
test('receipt hold: no envelope, a bare object, an envelope never retained by this gate, and one bound to another intent or policy', async () => {
  assert.deepEqual((await REC(intent(), receipt(), { envelope: null })).reasons, ['envelope_missing']);
  assert.deepEqual((await REC(intent(), receipt(), { envelope: { allInWei: 10n ** 18n } })).reasons, ['envelope_missing']);
  const { c, envelope } = await setup();
  const fresh = createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW }); // never ran this preflight
  assert.deepEqual((await fresh.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope, balances: bal(FEE) })).reasons, ['envelope_not_retained']);
  const other = createChainGate({ rpc: c.rpc, policy: policy({ confirmations: 3 }), now: () => NOW });
  const r = await other.restoreEnvelope(intent(), envelope); assert.ok(r.reasons.includes('envelope_not_bound_to_this_intent_or_policy'));
  const r2 = await createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW }).restoreEnvelope(intent({ hash: HASH2 }), envelope);
  assert.ok(r2.reasons.includes('envelope_not_bound_to_this_intent_or_policy'));
});
test('the retained envelope is frozen: mutating the returned object does not change what reconcile uses', async () => {
  const { g, envelope } = await setup();
  assert.throws(() => { 'use strict'; envelope.allInWei = 1n; }, TypeError);
  assert.throws(() => { 'use strict'; envelope.binding.anchorHash = '0x' + '00'.repeat(32); }, TypeError);
  assert.equal((await g.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope, balances: bal(FEE) })).ok, true);
});
test('receipt: an operator fee that the receipt does not report is not silently zero, unless the policy names verified-not-applicable evidence', async () => {
  const out = await REC(intent(), receipt({ operatorFee: undefined }));
  assert.ok(out.reasons.includes('operator_fee_not_reported'), JSON.stringify(out.reasons));
  const zero = policy({ fee: { ...policy().fee, operatorFeeBoundWei: 0n, operatorFeeEvidence: 'verified_not_applicable', operatorFeeEvidenceRef: 'a recorded observation of the pinned chain at a named block' } });
  const ok = await REC(intent(), receipt({ operatorFee: undefined }), { pol: zero });
  assert.equal(ok.ok, true, JSON.stringify(ok.reasons));
});
test('receipt hold: an incomplete policy refuses reconciliation too', async () => {
  const { c, envelope } = await setup();
  const bad = createChainGate({ rpc: c.rpc, policy: { ...policy(), confirmations: 0 }, now: () => NOW });
  assert.ok((await bad.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope, balances: bal(FEE) })).reasons[0].startsWith('policy_incomplete'));
});

test('the anchor must still be canonical at reconciliation (a reorg below the anchor after preflight holds)', async () => {
  const { c, g, envelope } = await setup();
  c.s.blocks[499] = { ...A, hash: '0x' + 'a7'.repeat(32) };
  const out = await g.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope, balances: bal(FEE) });
  assert.ok(out.reasons.includes('anchor_not_canonical'), JSON.stringify(out.reasons));
});
test('the whole span from the head down to the confirming block is a parent-hash lineage (a broken link far above inclusion holds)', async () => {
  const out = await REC(intent(), receipt(), { pol: policy({ confirmations: 2 }), mutate: c => {
    let prev = B501;
    for (let n = 502; n <= 508; n++) { const b = { number: n, hash: '0x' + (n - 502 + 0x30).toString(16).padStart(2, '0').repeat(32), parentHash: n === 505 ? '0x' + '99'.repeat(32) : prev.hash, timestamp: NOW - 4 }; c.s.blocks[n] = b; prev = b; }
    c.s.block = { ...prev };
  } });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('head_lineage_broken'), JSON.stringify(out.reasons));
});

// ---- Codex third B1 review 6671519470 ----
test('finding 1: a restored envelope with a fabricated, self-consistent L1 quote is refused (the repro)', async () => {
  const { c, envelope } = await setup();
  const g2 = createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW });
  const forged = { ...envelope, l1QuoteWei: 800_000_000n, l1MarginedWei: 1_000_000_000n, allInWei: 1_060_001_000n };
  const r = await g2.restoreEnvelope(intent(), forged);
  assert.equal(r.ok, false); assert.deepEqual(r.reasons, ['l1_quote_differs_from_oracle_at_anchor']);
  // and it cannot be promoted into reconcile authority: a gate that never retained it holds
  const rec = await g2.reconcileReceipt({ intent: intent(), receipt: receipt({ l1Fee: 900_000_000n }), envelope: forged, balances: bal(40_000n * 1000n + 900_000_000n) });
  assert.equal(rec.ok, false); assert.deepEqual(rec.reasons, ['envelope_not_retained']);
});
test('finding 1: the quote is verified AT the retained anchor block, and an unreadable or malformed oracle answer holds', async () => {
  const { c, envelope } = await setup();
  const at = []; const f = c.rpc.call;
  c.rpc.call = async (tx, blk) => { if (tx.to.toLowerCase() === L1_ORACLE) at.push(blk); return f(tx, blk); };
  const ok = await createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW }).restoreEnvelope(intent(), envelope);
  assert.equal(ok.ok, true, JSON.stringify(ok.reasons)); assert.deepEqual(at, [envelope.binding.anchorHash]);
  for (const [label, brk] of [['throws', async () => { throw new Error('non-archive'); }], ['undefined', async () => undefined], ['short word', async () => '0x01']]) {
    c.rpc.call = async (tx, blk) => (tx.to.toLowerCase() === L1_ORACLE ? brk() : f(tx, blk));
    const r = await createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW }).restoreEnvelope(intent(), envelope);
    assert.deepEqual(r.reasons, ['l1_quote_unverifiable_at_anchor'], label);
  }
});

test('finding 2: the anchor must lie in the same checked lineage as inclusion and head (the repro: block 500 claims another parent)', async () => {
  const out = await REC(intent(), receipt(), { mutate: c => { c.s.blocks[500] = { ...B500, parentHash: '0x' + 'ee'.repeat(32) }; } });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('anchor_not_in_head_lineage'), JSON.stringify(out.reasons));
});
test('finding 2: a fork below inclusion (mixed responses: the number lookup says one thing, the parent walk another) holds', async () => {
  const out = await REC(intent(), receipt(), { mutate: c => {
    const f = c.rpc.getBlock; let n499 = 0;
    c.rpc.getBlock = async x => { if (x === 499 && ++n499 >= 2) return { ...A, hash: '0x' + 'a6'.repeat(32) }; return f(x); }; // the walk sees another block 499 than the canonical lookup
  } });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('anchor_not_in_head_lineage'), JSON.stringify(out.reasons));
});
test('finding 2: an anchor far below inclusion is refused rather than walked without bound; a distant but intact anchor within the cap passes', async () => {
  const { c, envelope } = await setup();
  const deepAnchor = { ...envelope, binding: { ...envelope.binding, anchorNumber: 100, anchorHash: '0x' + '10'.repeat(32) } };
  c.s.blocks[100] = { number: 100, hash: deepAnchor.binding.anchorHash, parentHash: '0x' + '0f'.repeat(32), timestamp: NOW - 400 };
  const g2 = createChainGate({ rpc: c.rpc, policy: policy(), now: () => NOW });
  const r = await g2.restoreEnvelope(intent(), deepAnchor); assert.equal(r.ok, true, JSON.stringify(r.reasons));
  const out = await g2.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: r.envelope, balances: bal(FEE) });
  assert.ok(out.reasons.includes('anchor_too_far_below_inclusion'), JSON.stringify(out.reasons));
});
test('finding 2: an intact anchor a few blocks below inclusion passes the full lineage', async () => {
  // rebuild: anchor 497 <- 498 <- 499 <- 500 <- 501, preflight at 497
  const a497 = { number: 497, hash: '0x' + '97'.repeat(32), parentHash: '0x' + '96'.repeat(32), timestamp: NOW - 50 };
  const a498 = { number: 498, hash: '0x' + '98'.repeat(32), parentHash: a497.hash, timestamp: NOW - 40 };
  const a499 = { ...A, parentHash: a498.hash };
  const c2 = chain({ block: { ...a497 }, blocks: { 497: { ...a497 } } });
  const g = createChainGate({ rpc: c2.rpc, policy: policy(), now: () => NOW });
  const pre = await g.preflight(intent()); assert.equal(pre.ok, true, JSON.stringify(pre.reasons));
  c2.s.block = { ...B501 }; c2.s.blocks = { 497: a497, 498: a498, 499: a499, 500: { ...B500 }, 501: { ...B501 } }; c2.s.tx = txFor(intent());
  const out = await g.reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: pre.envelope, balances: bal(FEE) });
  assert.equal(out.ok, true, JSON.stringify(out.reasons));
});
test('finding 2: a self-consistent fork below inclusion that ends at another block than the retained anchor holds (mixed responses at the anchor height)', async () => {
  const X = '0x' + '5a'.repeat(32);
  const out = await REC(intent(), receipt(), { mutate: c => {
    c.s.blocks[500] = { ...B500, parentHash: X };
    const f = c.rpc.getBlock; let n499 = 0;
    c.rpc.getBlock = async x => { if (x === 499 && ++n499 >= 2) return { ...A, hash: X }; return f(x); }; // first lookup canonical, the walk sees a consistent fork
  } });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('anchor_not_in_head_lineage') || out.reasons.includes('inclusion_not_in_head_lineage'), JSON.stringify(out.reasons));
});
