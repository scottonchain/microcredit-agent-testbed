// Local only: an in-memory chain and provider. No network, no key.
import test from 'node:test';
import assert from 'node:assert/strict';
import { keccak256, encodeFunctionData, encodeEventTopics, encodeAbiParameters, parseAbi, toHex, pad } from 'viem';
import { createChainGate, classifyCode, policyProblems, EIP7702_PREFIX, IMPLEMENTATION_SLOT, L1_ORACLE } from './chain_state.mjs';

const FROM = '0x' + '11'.repeat(20); const TO = '0x' + 'ff'.repeat(20); const TOKEN = '0x' + 'dd'.repeat(20); const IMPL = '0x' + 'ab'.repeat(20);
const TOKEN_CODE = '0x6080aa'; const IMPL_CODE = '0x6080bb';
const abi = parseAbi(['function balanceOf(address) view returns (uint256)', 'event Transfer(address indexed from, address indexed to, uint256 value)', 'function getL1Fee(bytes) view returns (uint256)']);
const policy = (o = {}) => ({
  chainId: 84532, approvedProviderIds: ['provider-a'], maxAnchorAgeSec: 60, confirmations: 2,
  token: { address: TOKEN, codeHash: keccak256(TOKEN_CODE), proxy: { implementation: IMPL, implementationCodeHash: keccak256(IMPL_CODE) } },
  fee: { maxExposureWei: 10n ** 15n, operatorFeeBoundWei: 1000n, l1MultiplePpm: 1_250_000, reserveWei: 0n },
  ...o,
});
const NOW = 1_800_000_000;
const BLOCK = { number: 500, hash: '0x' + '0a'.repeat(32), timestamp: NOW - 5 };
const word = n => toHex(n, { size: 32 });

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
const intent = (o = {}) => ({ kind: 'erc20', from: FROM, recipient: TO, amount: 8n, nonce: 3, raw: '0x02f8abcd', maxFeeWei: 60_000_000n, contract: TOKEN, ...o });
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

// ---- receipt reconciliation ----
const topics = (from, to) => encodeEventTopics({ abi, eventName: 'Transfer', args: { from, to } });
const log = (o = {}) => ({ address: TOKEN, topics: topics(FROM, TO), data: encodeAbiParameters([{ type: 'uint256' }], [8n]), ...o });
const receipt = (o = {}) => ({ status: 1, from: FROM, to: TOKEN, blockHash: BLOCK.hash, blockNumber: 500, gasUsed: 40_000n, effectiveGasPrice: 1000n, l1Fee: 30_000n, logs: [log()], ...o });
const env = { allInWei: 60_000_000n + 50_000n + 1000n };
const bal = (fee, extra = 0n) => ({ before: 10n ** 16n, after: 10n ** 16n - fee - extra });
const REC = async (c, r, b = bal(40_000n * 1000n + 30_000n), i = intent()) => gate(c).reconcileReceipt({ intent: i, receipt: r, envelope: env, balances: b });

test('receipt: a matching, canonical, confirmed transfer reconciles with fee components and the balance delta', async () => {
  const c = chain({ block: { ...BLOCK, number: 501 } });
  const r = await REC(c, receipt());
  assert.equal(r.ok, true, JSON.stringify(r.reasons)); assert.equal(r.fee.totalWei, 40_000n * 1000n + 30_000n);
});

const RECEIPT_HOLDS = [
  ['reverted', receipt({ status: 0 }), 'receipt_not_successful'],
  ['another sender', receipt({ from: TO }), 'receipt_sender_differs'],
  ['block hash not canonical', receipt({ blockHash: '0x' + '0c'.repeat(32) }), 'block_not_canonical'],
  ['transfer to another recipient', receipt({ logs: [log({ topics: topics(FROM, '0x' + 'ee'.repeat(20)) })] }), 'transfer_log_differs'],
  ['transfer of another amount', receipt({ logs: [log({ data: encodeAbiParameters([{ type: 'uint256' }], [9n]) })] }), 'transfer_log_differs'],
  ['no transfer log', receipt({ logs: [] }), 'transfer_log_count'],
  ['two transfer logs', receipt({ logs: [log(), log()] }), 'transfer_log_count'],
  ['a foreign log', receipt({ logs: [log(), log({ address: '0x' + '99'.repeat(20) })] }), 'foreign_logs'],
  ['L1 fee not reported', receipt({ l1Fee: undefined }), 'l1_fee_not_reported'],
  ['actual fee above the envelope', receipt({ effectiveGasPrice: 10n ** 12n }), 'actual_fee_exceeds_envelope'],
];
for (const [label, r, reason] of RECEIPT_HOLDS) {
  test(`receipt hold: ${label}`, async () => {
    const out = await REC(chain({ block: { ...BLOCK, number: 501 } }), r, bal(0n));
    assert.equal(out.ok, false); assert.ok(out.reasons.includes(reason), JSON.stringify(out.reasons));
  });
}
test('receipt hold: too few confirmations and a sender balance that moved by something else', async () => {
  assert.ok((await REC(chain(), receipt())).reasons.includes('not_enough_confirmations'));
  const c = chain({ block: { ...BLOCK, number: 501 } });
  assert.ok((await REC(c, receipt(), bal(40_000n * 1000n + 30_000n, 1n))).reasons.includes('sender_balance_delta_differs'));
  assert.ok((await gate(c).reconcileReceipt({ intent: intent(), receipt: receipt(), envelope: env })).reasons.includes('balances_missing'));
});
test('receipt: a native transfer reconciles value plus fee and rejects any token logs', async () => {
  const c = chain({ block: { ...BLOCK, number: 501 } }); const i = intent({ kind: 'native', amount: 777n, contract: undefined });
  const fee = 21_000n * 1000n + 30_000n;
  const ok = await REC(c, receipt({ gasUsed: 21_000n, logs: [] }), bal(fee, 777n), i);
  assert.equal(ok.ok, true, JSON.stringify(ok.reasons));
  assert.ok((await REC(c, receipt({ gasUsed: 21_000n, logs: [log()] }), bal(fee, 777n), i)).reasons.includes('unexpected_logs_on_native_transfer'));
});
