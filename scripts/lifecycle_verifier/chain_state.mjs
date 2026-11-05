// Chain-state gate for the wallet lifecycle: what the signed bytes cannot show. It runs AFTER the cryptographic
// decoder (verify_prepared.mjs) and BEFORE every send and rebroadcast, and reconciles the receipt AFTER.
//
// It holds no key, signs nothing and opens no connection of its own: every read goes through an injected `rpc` port,
// and every read is pinned to ONE block hash taken at the start, so the answers describe a single state of the chain.
// Local tests use an in-memory rpc. A real provider adapter is a separate, reviewed deliverable; this module is not
// evidence that any live provider was read.
//
// What it checks (any failure, unknown value or missing configuration HOLDS the send; nothing is assumed):
//   provenance  the provider identifies itself with an approved id, reports the pinned chain id, and the anchor block
//               is fresh and still canonical when re-read at the end
//   code        sender and recipient must have NO code: an EIP-7702 delegation designator (0xef0100 + address) is state a
//               type-2 envelope cannot show, so it is classified and held, as is any contract; the token's runtime code
//               hash must equal the pinned hash and, for an EIP-1967 proxy, so must its implementation address and code
//   nonce       latest and pending transaction counts both equal the intent's nonce (a gap, a used nonce or a
//               conflicting pending transaction holds)
//   balances    token balance covers the amount; native balance covers the all-in fee envelope (plus the value for a
//               native transfer)
//   fee         the all-in envelope is the execution ceiling (gas * fee cap, from the decoder) PLUS the L1 data fee
//               quoted at the anchor block for the exact serialized payload (times a stated multiple) PLUS an explicit
//               operator-fee bound from configuration. A multiple is a safety margin on an estimate, not a protocol cap;
//               a missing oracle answer, a missing operator bound or an envelope above the separately authorized
//               maximum exposure holds the send.
// After a send, `reconcileReceipt` checks status, canonical inclusion and confirmations, exactly one matching Transfer
// log, that the fee components fit the envelope, and that the sender's native balance moved by the fee (and value).

import { keccak256, encodeFunctionData, parseAbi, hexToBigInt, decodeEventLog, isAddress } from 'viem';

export const EIP7702_PREFIX = '0xef0100';
export const IMPLEMENTATION_SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'; // EIP-1967
export const L1_ORACLE = '0x420000000000000000000000000000000000000f'; // OP-stack GasPriceOracle predeploy
const erc20 = parseAbi(['function balanceOf(address) view returns (uint256)', 'event Transfer(address indexed from, address indexed to, uint256 value)']);
const oracle = parseAbi(['function getL1Fee(bytes) view returns (uint256)']);
const lc = x => String(x).toLowerCase();
const big = x => { const v = BigInt(x); if (v < 0n) throw new Error('negative'); return v; };

// 'eoa' | 'delegated' (a 23-byte EIP-7702 designator) | 'contract' | 'invalid'
export function classifyCode(code) {
  if (typeof code !== 'string' || !/^0x(?:[0-9a-fA-F]{2})*$/.test(code)) return 'invalid';
  if (code === '0x') return 'eoa';
  const c = lc(code);
  if (c.startsWith(EIP7702_PREFIX) && c.length === 2 + 2 * 23) return 'delegated';
  return 'contract';
}

// What a configuration must state. Returns problems; a gate built from an incomplete policy refuses every send.
export function policyProblems(p) {
  const out = [];
  if (!p || typeof p !== 'object') return ['policy missing'];
  if (!Number.isInteger(p.chainId)) out.push('chainId');
  if (!Array.isArray(p.approvedProviderIds) || p.approvedProviderIds.length === 0) out.push('approvedProviderIds');
  if (!Number.isInteger(p.maxAnchorAgeSec) || p.maxAnchorAgeSec <= 0) out.push('maxAnchorAgeSec');
  if (!Number.isInteger(p.confirmations) || p.confirmations < 1) out.push('confirmations');
  const t = p.token;
  if (!t || !isAddress(t.address || '', { strict: false }) || !/^0x[0-9a-f]{64}$/.test(t.codeHash || '')) out.push('token.address/codeHash');
  if (t && t.proxy != null && (!isAddress(t.proxy.implementation || '', { strict: false }) || !/^0x[0-9a-f]{64}$/.test(t.proxy.implementationCodeHash || ''))) out.push('token.proxy');
  const f = p.fee;
  try {
    if (!f) throw new Error('fee');
    big(f.maxExposureWei); big(f.operatorFeeBoundWei);
    if (!Number.isInteger(f.l1MultiplePpm) || f.l1MultiplePpm < 1_000_000) throw new Error('multiple');
    if (f.reserveWei !== undefined) big(f.reserveWei);
  } catch { out.push('fee.maxExposureWei/operatorFeeBoundWei/l1MultiplePpm'); }
  return out;
}

export function createChainGate({ rpc, policy, now = () => Math.floor(Date.now() / 1000) }) {
  const problems = policyProblems(policy);

  async function anchored() {
    const providerId = await rpc.providerId();
    if (!policy.approvedProviderIds.includes(providerId)) throw hold('provider_not_approved');
    if (Number(await rpc.chainId()) !== policy.chainId) throw hold('chain_differs');
    const b = await rpc.getBlock('latest');
    if (!b || !/^0x[0-9a-f]{64}$/.test(b.hash || '') || !Number.isSafeInteger(Number(b.number)) || !Number.isSafeInteger(Number(b.timestamp))) throw hold('anchor_invalid');
    if (now() - Number(b.timestamp) > policy.maxAnchorAgeSec) throw hold('anchor_stale');
    return { providerId, number: Number(b.number), hash: b.hash, timestamp: Number(b.timestamp) };
  }

  // intent: { kind: 'erc20'|'native', from, recipient, amount, nonce, raw, maxFeeWei, contract?, value? } (decoder output plus raw)
  async function preflight(intent) {
    const reasons = [];
    if (problems.length) return { ok: false, reasons: ['policy_incomplete:' + problems.join(',')] };
    let anchor;
    try { anchor = await anchored(); } catch (e) { return { ok: false, reasons: [e.holdReason || 'anchor_read_failed'] }; }
    const at = anchor.hash;
    const read = async (name, fn) => { try { return await fn(); } catch { reasons.push(name + '_read_failed'); return undefined; } };

    const senderClass = classifyCode(await read('sender_code', () => rpc.getCode(intent.from, at)));
    const recipClass = classifyCode(await read('recipient_code', () => rpc.getCode(intent.recipient, at)));
    if (senderClass !== 'eoa') reasons.push('sender_code_' + senderClass);
    if (recipClass !== 'eoa') reasons.push('recipient_code_' + recipClass);

    const latest = await read('nonce', () => rpc.getTransactionCount(intent.from, 'latest', at));
    const pending = await read('pending_nonce', () => rpc.getTransactionCount(intent.from, 'pending'));
    if (latest !== undefined && pending !== undefined) {
      if (Number(latest) !== Number(intent.nonce)) reasons.push(Number(latest) > Number(intent.nonce) ? 'nonce_already_used' : 'nonce_gap');
      else if (Number(pending) !== Number(latest)) reasons.push('conflicting_pending_transaction');
    }

    let tokenBalanceOk = true;
    if (intent.kind === 'erc20') {
      if (lc(intent.contract) !== lc(policy.token.address)) reasons.push('token_differs');
      const code = await read('token_code', () => rpc.getCode(policy.token.address, at));
      if (code !== undefined && keccak256(code) !== policy.token.codeHash) reasons.push('token_code_hash_differs');
      if (policy.token.proxy) {
        const slot = await read('token_implementation', () => rpc.getStorageAt(policy.token.address, IMPLEMENTATION_SLOT, at));
        const impl = slot === undefined ? undefined : '0x' + String(slot).slice(-40);
        if (impl !== undefined && lc(impl) !== lc(policy.token.proxy.implementation)) reasons.push('token_implementation_differs');
        const ic = await read('implementation_code', () => rpc.getCode(policy.token.proxy.implementation, at));
        if (ic !== undefined && keccak256(ic) !== policy.token.proxy.implementationCodeHash) reasons.push('implementation_code_hash_differs');
      }
      const data = encodeFunctionData({ abi: erc20, functionName: 'balanceOf', args: [intent.from] });
      const out = await read('token_balance', () => rpc.call({ to: policy.token.address, data }, at));
      if (out !== undefined) tokenBalanceOk = hexToBigInt(out) >= big(intent.amount); else tokenBalanceOk = false;
      if (!tokenBalanceOk && out !== undefined) reasons.push('insufficient_token_balance');
    }

    // all-in fee envelope
    let envelope;
    const l1Out = await read('l1_fee', () => rpc.call({ to: L1_ORACLE, data: encodeFunctionData({ abi: oracle, functionName: 'getL1Fee', args: [intent.raw] }) }, at));
    const nativeBalance = await read('native_balance', () => rpc.getBalance(intent.from, at));
    if (l1Out !== undefined) {
      const l1 = hexToBigInt(l1Out);
      const l1Margined = (l1 * BigInt(policy.fee.l1MultiplePpm) + 999_999n) / 1_000_000n;
      const exec = big(intent.maxFeeWei); const op = big(policy.fee.operatorFeeBoundWei);
      envelope = { executionCeilingWei: exec, l1QuoteWei: l1, l1MarginedWei: l1Margined, operatorBoundWei: op, allInWei: exec + l1Margined + op };
      if (envelope.allInWei > big(policy.fee.maxExposureWei)) reasons.push('fee_exposure_exceeds_authorization');
      if (nativeBalance !== undefined) {
        const need = envelope.allInWei + (intent.kind === 'native' ? big(intent.amount) : 0n) + big(policy.fee.reserveWei ?? 0);
        if (big(nativeBalance) < need) reasons.push('insufficient_native_reserve');
      }
    }

    // the anchor must still be canonical after every read (a reorg or a rolled-back read set holds the send)
    const again = await read('anchor_recheck', () => rpc.getBlock(anchor.number));
    if (again !== undefined && (!again || again.hash !== anchor.hash)) reasons.push('anchor_changed');

    return reasons.length ? { ok: false, reasons, anchor } : { ok: true, anchor, envelope, balances: { native: big(nativeBalance).toString() } };
  }

  // receipt: { status, from, to, blockHash, blockNumber, gasUsed, effectiveGasPrice, l1Fee?, operatorFee?, logs: [{address, topics, data}] }
  // balances: { before, after } native balances of the sender in wei, read at pinned blocks by the caller
  async function reconcileReceipt({ intent, receipt, envelope, balances }) {
    const reasons = [];
    if (!receipt || receipt.status !== 1) return { ok: false, reasons: ['receipt_not_successful'] };
    if (lc(receipt.from) !== lc(intent.from)) reasons.push('receipt_sender_differs');
    let blk;
    try { blk = await rpc.getBlock(Number(receipt.blockNumber)); } catch { return { ok: false, reasons: ['block_read_failed'] }; }
    if (!blk || blk.hash !== receipt.blockHash) reasons.push('block_not_canonical');
    let head;
    try { head = await rpc.getBlock('latest'); } catch { return { ok: false, reasons: [...reasons, 'head_read_failed'] }; }
    if (Number(head.number) - Number(receipt.blockNumber) + 1 < policy.confirmations) reasons.push('not_enough_confirmations');

    const transfers = []; let foreign = 0;
    for (const log of receipt.logs || []) {
      if (lc(log.address) !== lc(policy.token.address)) { foreign++; continue; }
      try { transfers.push(decodeEventLog({ abi: erc20, data: log.data, topics: log.topics })); } catch { reasons.push('undecodable_token_log'); }
    }
    if (intent.kind === 'erc20') {
      const t = transfers.filter(x => x.eventName === 'Transfer');
      if (transfers.length !== 1 || t.length !== 1) reasons.push('transfer_log_count');
      else if (lc(t[0].args.from) !== lc(intent.from) || lc(t[0].args.to) !== lc(intent.recipient) || t[0].args.value !== big(intent.amount)) reasons.push('transfer_log_differs');
      if (foreign) reasons.push('foreign_logs');
    } else if (transfers.length || foreign) reasons.push('unexpected_logs_on_native_transfer');

    let fee;
    try {
      const l2 = big(receipt.gasUsed) * big(receipt.effectiveGasPrice);
      const l1 = receipt.l1Fee === undefined ? 0n : big(receipt.l1Fee);
      const op = receipt.operatorFee === undefined ? 0n : big(receipt.operatorFee);
      fee = { l2Wei: l2, l1Wei: l1, operatorWei: op, totalWei: l2 + l1 + op };
      if (receipt.l1Fee === undefined) reasons.push('l1_fee_not_reported');
      if (envelope && fee.totalWei > envelope.allInWei) reasons.push('actual_fee_exceeds_envelope');
    } catch { reasons.push('fee_fields_invalid'); }
    if (fee && balances) {
      const moved = big(balances.before) - big(balances.after);
      const expected = fee.totalWei + (intent.kind === 'native' ? big(intent.amount) : 0n);
      if (moved !== expected) reasons.push('sender_balance_delta_differs');
    } else if (!balances) reasons.push('balances_missing');
    return reasons.length ? { ok: false, reasons, fee } : { ok: true, fee };
  }

  // The amount a gas return may move: balance minus the all-in reserve, never balance minus the L2 ceiling alone.
  function gasReturnAmount({ balanceWei, envelope, gasDustWei = 0n }) {
    const keep = big(envelope.allInWei) + big(policy.fee.reserveWei ?? 0);
    const amount = big(balanceWei) - keep;
    return amount > big(gasDustWei) ? amount : 0n;
  }

  return { preflight, reconcileReceipt, gasReturnAmount, policyProblems: problems };
}

function hold(reason) { const e = new Error(reason); e.holdReason = reason; return e; }
