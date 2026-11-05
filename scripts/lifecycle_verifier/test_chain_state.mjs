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
const topics = (from, to) => encodeEventTopics({ abi, eventName: 'Transfer', args: { from, to } });
const log = (o = {}) => ({ address: TOKEN, topics: topics(FROM, TO), data: encodeAbiParameters([{ type: 'uint256' }], [8n]), ...o });
const FEE = 40_000n * 1000n + 30_000n;
const receipt = (o = {}) => ({ status: 1, transactionHash: HASH1, from: FROM, to: TOKEN, blockHash: BLOCK.hash, blockNumber: 500, gasUsed: 40_000n, effectiveGasPrice: 1000n, l1Fee: 30_000n, operatorFee: 0n, logs: [log()], ...o });
const bal = (fee, extra = 0n) => ({ before: 10n ** 16n, after: 10n ** 16n - fee - extra });
const transferInput = (to = TO, amount = 8n) => encodeFunctionData({ abi, functionName: 'transfer', args: [to, amount] });
const txFor = (i, o = {}) => ({ hash: HASH1, from: FROM, to: i.kind === 'erc20' ? TOKEN : TO, nonce: 3, value: i.kind === 'native' ? i.amount : 0n, input: i.kind === 'erc20' ? transferInput(TO, i.amount) : '0x', blockHash: BLOCK.hash, ...o });
// A chain whose head is two blocks ahead, plus the envelope preflight produced for this intent.
async function setup(i = intent(), o = {}) {
  const B501 = { ...BLOCK, number: 501, hash: '0x' + '0b'.repeat(32) };
  const c = chain({ block: { ...B501 }, blocks: { 500: { ...BLOCK }, 501: { ...B501 } }, ...o });
  const pre = await gate(c).preflight(i); assert.equal(pre.ok, true, JSON.stringify(pre.reasons));
  c.s.tx = txFor(i); return { c, envelope: pre.envelope };
}
async function REC(i, r, { b = bal(FEE), mutateChain, envelope, policyOverride } = {}) {
  const { c, envelope: env } = await setup(i);
  if (mutateChain) mutateChain(c);
  return gate(c, policyOverride).reconcileReceipt({ intent: i, receipt: r, envelope: envelope === undefined ? env : envelope, balances: b });
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

// ---- finding 2: bound to the transaction, its outer target and its fields, fetched by hash ----
test('receipt hold: the Codex repro, a native intent whose receipt is a DIFFERENT transaction to the token with a matching fee and value', async () => {
  const i = intent({ kind: 'native', amount: 777n, contract: undefined });
  const fee = 21_000n * 1000n + 30_000n;
  const out = await REC(i, receipt({ transactionHash: HASH2, to: TOKEN, gasUsed: 21_000n, logs: [] }), { b: bal(fee, 777n) });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('receipt_hash_differs') && out.reasons.includes('receipt_target_differs'), JSON.stringify(out.reasons));
});
test('receipt: a native transfer binds to the recipient as outer target and reconciles value plus fee', async () => {
  const i = intent({ kind: 'native', amount: 777n, contract: undefined }); const fee = 21_000n * 1000n + 30_000n;
  const ok = await REC(i, receipt({ to: TO, gasUsed: 21_000n, logs: [] }), { b: bal(fee, 777n) });
  assert.equal(ok.ok, true, JSON.stringify(ok.reasons));
  assert.ok((await REC(i, receipt({ to: TO, gasUsed: 21_000n, logs: [log()] }), { b: bal(fee, 777n) })).reasons.includes('unexpected_logs_on_native_transfer'));
});
const TX_HOLDS = [
  ['the fetched transaction has another hash', { hash: HASH2 }, 'transaction_hash_differs'],
  ['another sender', { from: TO }, 'transaction_sender_differs'],
  ['another target', { to: '0x' + '99'.repeat(20) }, 'transaction_target_differs'],
  ['another nonce', { nonce: 9 }, 'transaction_nonce_differs'],
  ['native value on a token transfer', { value: 1n }, 'transaction_value_differs'],
  ['other calldata (another recipient)', { input: transferInput('0x' + 'ee'.repeat(20)) }, 'transaction_calldata_differs'],
  ['other calldata (another amount)', { input: transferInput(TO, 9n) }, 'transaction_calldata_differs'],
  ['mined in another block', { blockHash: '0x' + '0d'.repeat(32) }, 'transaction_block_differs'],
];
for (const [label, o, reason] of TX_HOLDS) {
  test(`receipt hold: ${label}`, async () => {
    const out = await REC(intent(), receipt(), { mutateChain: c => { c.s.tx = txFor(intent(), o); } });
    assert.ok(out.reasons.includes(reason), JSON.stringify(out.reasons));
  });
}
test('receipt hold: the transaction cannot be fetched', async () => {
  const out = await REC(intent(), receipt(), { mutateChain: c => { c.rpc.getTransaction = async () => { throw new Error('gone'); }; } });
  assert.ok(out.reasons.includes('transaction_read_failed'));
  const out2 = await REC(intent(), receipt(), { mutateChain: c => { c.s.tx = null; } });
  assert.ok(out2.reasons.includes('transaction_read_failed'));
});

// ---- finding 3: inclusion and head re-validated at the end ----
test('receipt hold: the inclusion block is replaced while the head is read (the Codex repro)', async () => {
  const out = await REC(intent(), receipt(), { mutateChain: c => {
    const f = c.rpc.getBlock; let swapped = false;
    c.rpc.getBlock = async x => { const r = await f(x); if (x === 'latest' && !swapped) { swapped = true; c.s.blocks[500] = { ...BLOCK, hash: '0x' + '0e'.repeat(32) }; } return r; };
  } });
  assert.equal(out.ok, false); assert.ok(out.reasons.includes('inclusion_changed_during_check'), JSON.stringify(out.reasons));
});
test('receipt hold: the head moves backwards, or changes hash at the same height, during the check', async () => {
  const back = await REC(intent(), receipt(), { mutateChain: c => { const f = c.rpc.getBlock; let n = 0; c.rpc.getBlock = async x => { const r = await f(x); if (x === 'latest' && ++n === 2) return { ...r, number: 500 }; return r; }; } });
  assert.ok(back.reasons.includes('head_changed_during_check'));
  const swap = await REC(intent(), receipt(), { mutateChain: c => { const f = c.rpc.getBlock; let n = 0; c.rpc.getBlock = async x => { const r = await f(x); if (x === 'latest' && ++n === 2) return { ...r, hash: '0x' + '0f'.repeat(32) }; return r; }; } });
  assert.ok(swap.reasons.includes('head_changed_during_check'));
});
test('receipt hold: a missing, NaN or future head never satisfies confirmations', async () => {
  for (const [label, break_] of [['undefined head', c => { c.rpc.getBlock = async x => (x === 'latest' ? undefined : c.s.blocks[x]); }], ['NaN head number', c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => (x === 'latest' ? { ...(await f(x)), number: NaN } : f(x)); }]]) {
    const out = await REC(intent(), receipt(), { mutateChain: break_ });
    assert.equal(out.ok, false, label);
  }
  const future = await REC(intent(), receipt(), { mutateChain: c => { const f = c.rpc.getBlock; c.rpc.getBlock = async x => (x === 'latest' ? { ...(await f(x)), timestamp: NOW + 99999 } : f(x)); } });
  assert.ok(future.reasons.includes('head_in_future'));
});
test('receipt hold: too few confirmations, and a balance that moved by something else', async () => {
  const { c, envelope } = await setup(); c.s.block = { ...BLOCK };
  c.s.blocks[500] = { ...BLOCK };
  assert.ok((await gate(c).reconcileReceipt({ intent: intent(), receipt: receipt(), envelope, balances: bal(FEE) })).reasons.includes('not_enough_confirmations'));
  assert.ok((await REC(intent(), receipt(), { b: bal(FEE, 1n) })).reasons.includes('sender_balance_delta_differs'));
  const { c: c2, envelope: e2 } = await setup();
  assert.ok((await gate(c2).reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: e2 })).reasons.includes('balances_missing'));
});

// ---- finding 4: reconciliation needs the bound envelope and every actual cost component ----
test('receipt hold: no envelope (the Codex repro), or one bound to another intent, policy or provider', async () => {
  assert.deepEqual((await REC(intent(), receipt(), { envelope: null })).reasons, ['envelope_missing']);
  assert.deepEqual((await REC(intent(), receipt(), { envelope: { allInWei: 10n ** 18n } })).reasons, ['envelope_missing']);
  const { c, envelope } = await setup();
  const mk = o => ({ ...envelope, binding: { ...envelope.binding, ...o } });
  for (const [label, o, reason] of [['another intent', { intentHash: HASH2 }, 'envelope_not_bound_to_this_intent_or_policy'], ['another policy', { policyDigest: '0x' + '00'.repeat(32) }, 'envelope_not_bound_to_this_intent_or_policy'], ['another chain', { chainId: 1 }, 'envelope_not_bound_to_this_intent_or_policy'], ['another provider', { providerId: 'provider-b' }, 'provider_differs_from_envelope'], ['no anchor', { anchorHash: undefined }, 'envelope_anchor_missing']]) {
    const out = await gate(c).reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: mk(o), balances: bal(FEE) });
    assert.ok(out.reasons.includes(reason), label + ' ' + JSON.stringify(out.reasons));
  }
});
test('receipt: an operator fee that the receipt does not report is not silently zero', async () => {
  const out = await REC(intent(), receipt({ operatorFee: undefined }));
  assert.ok(out.reasons.includes('operator_fee_not_reported'), JSON.stringify(out.reasons));
  // only a policy that names verified-not-applicable evidence lets an unreported operator fee count as zero
  const zero = policy({ fee: { ...policy().fee, operatorFeeBoundWei: 0n, operatorFeeEvidence: 'verified_not_applicable', operatorFeeEvidenceRef: 'a recorded observation of the pinned chain at a named block' } });
  const B501 = { ...BLOCK, number: 501, hash: '0x' + '0b'.repeat(32) };
  const c = chain({ block: { ...B501 }, blocks: { 500: { ...BLOCK }, 501: { ...B501 } } });
  const g = createChainGate({ rpc: c.rpc, policy: zero, now: () => NOW }); const pre = await g.preflight(intent()); assert.equal(pre.ok, true, JSON.stringify(pre.reasons));
  c.s.tx = txFor(intent());
  const ok = await g.reconcileReceipt({ intent: intent(), receipt: receipt({ operatorFee: undefined }), envelope: pre.envelope, balances: bal(FEE) });
  assert.equal(ok.ok, true, JSON.stringify(ok.reasons));
});
test('receipt hold: an actual fee above the authorized exposure even when the envelope is generous, and an incomplete policy', async () => {
  const { c, envelope } = await setup();
  const roomy = { ...envelope, allInWei: 10n ** 30n };
  const out = await gate(c).reconcileReceipt({ intent: intent(), receipt: receipt({ effectiveGasPrice: 10n ** 13n }), envelope: roomy, balances: bal(40_000n * 10n ** 13n + 30_000n) });
  assert.ok(out.reasons.includes('actual_fee_exceeds_authorization'), JSON.stringify(out.reasons));
  const bad = await gate(c, { ...policy(), confirmations: 0 }).reconcileReceipt({ intent: intent(), receipt: receipt(), envelope, balances: bal(FEE) });
  assert.ok(bad.reasons[0].startsWith('policy_incomplete'));
});
