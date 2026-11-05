// Chain-state gate for the wallet lifecycle: what the signed bytes cannot show. DELIVERED CODE, NOT YET CALLED by
// wallet_lifecycle.mjs or lifecycle_runner.mjs: it guards nothing until a later step consumes it as a mandatory port.
//
// It holds no key, signs nothing and opens no connection of its own: every read goes through an injected `rpc` port.
// Local tests use an in-memory rpc. A real provider adapter is a separate, reviewed deliverable; nothing here is evidence
// that any live provider was read, and no policy value is evidence about Base Sepolia.
//
// PROVENANCE LIMIT: `rpc.providerId()` is an assertion by the injected port, not independent proof of which route
// answered; the real provider adapter must prove the approved route and the block-hash semantics. Every state read of a
// pass is pinned to ONE block hash (EIP-1898) EXCEPT the pending transaction count, which a node cannot pin; that read is
// a separate freshness and race limit, and the control for it is exclusive custody (one signer for these wallets).
//
// preflight(intent) - before every send and rebroadcast. Any failure, thrown or returned, missing, null, malformed, zero
// where a value is required, or different from what is pinned, HOLDS the send. ok:true needs every read and a complete
// envelope. Checks: provider id and chain; anchor fresh and not in the future beyond a stated skew, re-read at the end;
// no code on sender or recipient (an EIP-7702 delegation designator is classified and held); token runtime code hash
// (and EIP-1967 implementation) pinned; latest and pending nonce equal the intent's; token balance; all-in fee envelope
// = decoder execution ceiling + L1 data fee quoted at the anchor for the exact payload times a stated margin + an
// explicit operator-fee bound, bounded by a separately authorized maximum exposure, and covered by the native balance.
//
// reconcileReceipt(...) - after inclusion. The caller's envelope is never authority: the gate retains the complete frozen
// preflight result and uses only that (a caller copy that differs in any field holds; after a restart the record comes
// back only through restoreEnvelope, which re-derives its numbers from the signed intent and the policy, asks the oracle for
// the exact payload's L1 quote AT the retained anchor and requires the same answer, and checks that the anchor block is
// canonical on the pinned chain now). It reads the provider and chain id
// again, binds the receipt to THIS transaction (hash, sender, outer target, and the transaction fetched by hash: nonce,
// value, calldata), checks the anchor precedes inclusion in number and time, requires every actual fee component (an
// unreported operator fee is zero only with named verified-not-applicable evidence) and bounds each component: execution
// cost by the signed ceiling, L1 by the margined quote, operator by its bound, the total by the envelope and the
// authorization. Confirmations rest on a parent-hash lineage walked from the head just read down to the inclusion block,
// so a reorg that the last head read triggers cannot pass.

import { keccak256, encodeFunctionData, parseAbi, hexToBigInt, decodeEventLog, isAddress } from 'viem';

export const EIP7702_PREFIX = '0xef0100';
export const IMPLEMENTATION_SLOT = '0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'; // EIP-1967
export const L1_ORACLE = '0x420000000000000000000000000000000000000f'; // OP-stack GasPriceOracle predeploy
const erc20 = parseAbi(['function balanceOf(address) view returns (uint256)', 'function transfer(address,uint256) returns (bool)', 'event Transfer(address indexed from, address indexed to, uint256 value)']);
const oracle = parseAbi(['function getL1Fee(bytes) view returns (uint256)']);
const lc = x => String(x).toLowerCase();
const HASH = /^0x[0-9a-f]{64}$/;
const WORD = /^0x[0-9a-fA-F]{64}$/;
const MAX_SKEW_SEC = 60;
const big = x => { const v = BigInt(x); if (v < 0n) throw new Error('negative'); return v; };

// 'eoa' | 'delegated' (a 23-byte EIP-7702 designator) | 'contract' | 'invalid'
export function classifyCode(code) {
  if (typeof code !== 'string' || !/^0x(?:[0-9a-fA-F]{2})*$/.test(code)) return 'invalid';
  if (code === '0x') return 'eoa';
  const c = lc(code);
  if (c.startsWith(EIP7702_PREFIX) && c.length === 2 + 2 * 23) return 'delegated';
  return 'contract';
}

// Strict parsers: a missing, null or malformed answer is NOT a value. They throw a bare marker; callers turn it into a
// sanitized hold reason and never echo provider text.
const bad = () => { throw new Error('invalid'); };
const wordToBig = v => (typeof v === 'string' && WORD.test(v) ? hexToBigInt(v) : bad());
const count = v => {
  if (typeof v === 'bigint' && v >= 0n && v <= BigInt(Number.MAX_SAFE_INTEGER)) return Number(v);
  if (Number.isSafeInteger(v) && v >= 0) return v;
  if (typeof v === 'string' && /^0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)$/.test(v) && v.length <= 16) return Number(hexToBigInt(v));
  return bad();
};
const quantity = v => {
  if (typeof v === 'bigint' && v >= 0n) return v;
  if (Number.isSafeInteger(v) && v >= 0) return BigInt(v);
  if (typeof v === 'string' && /^0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)$/.test(v)) return hexToBigInt(v);
  return bad();
};
const blockFields = (b, withParent = false) => {
  if (!b || typeof b !== 'object' || typeof b.hash !== 'string' || !HASH.test(b.hash)) bad();
  const out = { number: count(b.number), hash: b.hash, timestamp: count(b.timestamp) };
  if (withParent) { if (typeof b.parentHash !== 'string' || !HASH.test(b.parentHash)) bad(); out.parentHash = b.parentHash; }
  return out;
};
const deepFreeze = o => { if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.freeze(o); Object.values(o).forEach(deepFreeze); } return o; };

// What a configuration must state. Returns problems; a gate built from an incomplete policy refuses every send.
export function policyProblems(p) {
  const out = [];
  if (!p || typeof p !== 'object') return ['policy missing'];
  if (!Number.isInteger(p.chainId)) out.push('chainId');
  if (!Array.isArray(p.approvedProviderIds) || p.approvedProviderIds.length === 0) out.push('approvedProviderIds');
  if (!Number.isInteger(p.maxAnchorAgeSec) || p.maxAnchorAgeSec <= 0) out.push('maxAnchorAgeSec');
  if (!Number.isInteger(p.maxFutureSkewSec) || p.maxFutureSkewSec < 0 || p.maxFutureSkewSec > MAX_SKEW_SEC) out.push('maxFutureSkewSec');
  if (!Number.isInteger(p.confirmations) || p.confirmations < 1) out.push('confirmations');
  const t = p.token;
  if (!t || !isAddress(t.address || '', { strict: false }) || !/^0x[0-9a-f]{64}$/.test(t.codeHash || '')) out.push('token.address/codeHash');
  if (t && t.proxy != null && (!isAddress(t.proxy.implementation || '', { strict: false }) || !/^0x[0-9a-f]{64}$/.test(t.proxy.implementationCodeHash || ''))) out.push('token.proxy');
  const f = p.fee;
  try {
    if (!f) throw new Error('fee');
    big(f.maxExposureWei); const op = big(f.operatorFeeBoundWei);
    if (!Number.isInteger(f.l1MultiplePpm) || f.l1MultiplePpm < 1_000_000) throw new Error('multiple');
    if (f.reserveWei !== undefined) big(f.reserveWei);
    // an operator-fee bound of zero is a claim about the chain, so it must name its evidence
    if (op === 0n && !(f.operatorFeeEvidence === 'verified_not_applicable' && typeof f.operatorFeeEvidenceRef === 'string' && f.operatorFeeEvidenceRef.length > 0)) throw new Error('operator evidence');
  } catch { out.push('fee.maxExposureWei/operatorFeeBoundWei/l1MultiplePpm/operatorFeeEvidence'); }
  return out;
}

// A stable digest of the policy, so an envelope can be bound to the policy it was computed under.
export function policyDigest(p) {
  const norm = v => (typeof v === 'bigint' ? v.toString() : Array.isArray(v) ? v.map(norm) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map(k => [k, norm(v[k])])) : v);
  return keccak256(new TextEncoder().encode(JSON.stringify(norm(p))));
}

export function createChainGate({ rpc, policy, now = () => Math.floor(Date.now() / 1000) }) {
  const problems = policyProblems(policy);
  const digest = problems.length ? null : policyDigest(policy);
  // The complete preflight result stays INSIDE the gate, frozen. A caller-held copy is never authority: reconcile uses
  // the retained envelope and refuses a caller envelope that differs from it in any field.
  const retained = new Map();

  async function anchored() {
    const providerId = await rpc.providerId();
    if (typeof providerId !== 'string' || !policy.approvedProviderIds.includes(providerId)) throw hold('provider_not_approved');
    let chain; try { chain = count(await rpc.chainId()); } catch { throw hold('chain_invalid'); }
    if (chain !== policy.chainId) throw hold('chain_differs');
    let b; try { b = blockFields(await rpc.getBlock('latest')); } catch { throw hold('anchor_invalid'); }
    if (b.timestamp > now() + policy.maxFutureSkewSec) throw hold('anchor_in_future');
    if (now() - b.timestamp > policy.maxAnchorAgeSec) throw hold('anchor_stale');
    return { providerId, ...b };
  }

  // intent: { kind: 'erc20'|'native', hash, from, recipient, amount, nonce, raw, maxFeeWei, contract? } (decoder output plus raw)
  async function preflight(intent) {
    if (problems.length) return { ok: false, reasons: ['policy_incomplete:' + problems.join(',')] };
    const reasons = [];
    try {
      let anchor;
      try { anchor = await anchored(); } catch (e) { return { ok: false, reasons: [e.holdReason || 'anchor_read_failed'] }; }
      const at = anchor.hash;
      const need = async (name, fn, parse = x => x) => {
        let raw;
        try { raw = await fn(); } catch { reasons.push(name + '_read_failed'); return undefined; }
        try { return parse(raw); } catch { reasons.push(name + '_invalid'); return undefined; }
      };
      if (typeof intent.hash !== 'string' || !HASH.test(lc(intent.hash))) reasons.push('intent_hash_missing');
      let amount; try { amount = big(intent.amount); } catch { reasons.push('intent_amount_invalid'); }
      let exec; try { exec = big(intent.maxFeeWei); } catch { reasons.push('intent_fee_invalid'); }
      if (typeof intent.raw !== 'string' || !/^0x(?:[0-9a-fA-F]{2})+$/.test(intent.raw)) reasons.push('intent_raw_invalid');

      const senderCode = await need('sender_code', () => rpc.getCode(intent.from, at), x => (classifyCode(x) === 'invalid' ? bad() : x));
      const recipCode = await need('recipient_code', () => rpc.getCode(intent.recipient, at), x => (classifyCode(x) === 'invalid' ? bad() : x));
      if (senderCode !== undefined && classifyCode(senderCode) !== 'eoa') reasons.push('sender_code_' + classifyCode(senderCode));
      if (recipCode !== undefined && classifyCode(recipCode) !== 'eoa') reasons.push('recipient_code_' + classifyCode(recipCode));

      const latest = await need('nonce', () => rpc.getTransactionCount(intent.from, 'latest', at), count);
      const pending = await need('pending_nonce', () => rpc.getTransactionCount(intent.from, 'pending'), count);
      let intentNonce; try { intentNonce = count(intent.nonce); } catch { reasons.push('intent_nonce_invalid'); }
      if (latest !== undefined && pending !== undefined && intentNonce !== undefined) {
        if (latest !== intentNonce) reasons.push(latest > intentNonce ? 'nonce_already_used' : 'nonce_gap');
        else if (pending !== latest) reasons.push('conflicting_pending_transaction');
      }

      if (intent.kind === 'erc20') {
        if (typeof intent.contract !== 'string' || lc(intent.contract) !== lc(policy.token.address)) reasons.push('token_differs');
        const code = await need('token_code', () => rpc.getCode(policy.token.address, at), x => (classifyCode(x) === 'invalid' || x === '0x' ? bad() : x));
        if (code !== undefined && keccak256(code) !== policy.token.codeHash) reasons.push('token_code_hash_differs');
        if (policy.token.proxy) {
          const slot = await need('token_implementation', () => rpc.getStorageAt(policy.token.address, IMPLEMENTATION_SLOT, at), x => (typeof x === 'string' && WORD.test(x) ? x : bad()));
          if (slot !== undefined && lc('0x' + slot.slice(-40)) !== lc(policy.token.proxy.implementation)) reasons.push('token_implementation_differs');
          const ic = await need('implementation_code', () => rpc.getCode(policy.token.proxy.implementation, at), x => (classifyCode(x) === 'invalid' || x === '0x' ? bad() : x));
          if (ic !== undefined && keccak256(ic) !== policy.token.proxy.implementationCodeHash) reasons.push('implementation_code_hash_differs');
        }
        let data; try { data = encodeFunctionData({ abi: erc20, functionName: 'balanceOf', args: [intent.from] }); } catch { reasons.push('intent_sender_invalid'); }
        const bal = data === undefined ? undefined : await need('token_balance', () => rpc.call({ to: policy.token.address, data }, at), wordToBig);
        if (bal !== undefined && amount !== undefined && bal < amount) reasons.push('insufficient_token_balance');
      } else if (intent.kind !== 'native') reasons.push('intent_kind_invalid');

      // all-in fee envelope: every part must be present
      let l1data; try { l1data = encodeFunctionData({ abi: oracle, functionName: 'getL1Fee', args: [intent.raw] }); } catch { reasons.push('intent_raw_invalid'); }
      const l1 = l1data === undefined ? undefined : await need('l1_fee', () => rpc.call({ to: L1_ORACLE, data: l1data }, at), wordToBig);
      const nativeBalance = await need('native_balance', () => rpc.getBalance(intent.from, at), quantity);
      let envelope;
      if (l1 !== undefined && exec !== undefined) {
        const l1Margined = (l1 * BigInt(policy.fee.l1MultiplePpm) + 999_999n) / 1_000_000n;
        const op = big(policy.fee.operatorFeeBoundWei);
        envelope = {
          executionCeilingWei: exec, l1QuoteWei: l1, l1MarginedWei: l1Margined, operatorBoundWei: op, allInWei: exec + l1Margined + op,
          binding: { intentHash: lc(intent.hash ?? ''), providerId: anchor.providerId, chainId: policy.chainId, anchorHash: anchor.hash, anchorNumber: anchor.number, policyDigest: digest },
        };
        if (envelope.allInWei > big(policy.fee.maxExposureWei)) reasons.push('fee_exposure_exceeds_authorization');
        if (nativeBalance !== undefined && amount !== undefined) {
          const needWei = envelope.allInWei + (intent.kind === 'native' ? amount : 0n) + big(policy.fee.reserveWei ?? 0);
          if (nativeBalance < needWei) reasons.push('insufficient_native_reserve');
        }
      }
      if (envelope === undefined) reasons.push('envelope_incomplete');
      if (nativeBalance === undefined && !reasons.includes('native_balance_read_failed') && !reasons.includes('native_balance_invalid')) reasons.push('native_balance_missing');

      // the anchor must still be canonical after every read (a reorg or a rolled-back read set holds the send)
      const again = await need('anchor_recheck', () => rpc.getBlock(anchor.number), blockFields);
      if (again !== undefined && (again.hash !== anchor.hash || again.number !== anchor.number)) reasons.push('anchor_changed');

      if (reasons.length) return { ok: false, reasons: [...new Set(reasons)], anchor };
      const kept = deepFreeze(JSON.parse(JSON.stringify(envelope, (k, v) => (typeof v === 'bigint' ? { __big: v.toString() } : v)), (k, v) => (v && typeof v === 'object' && '__big' in v ? BigInt(v.__big) : v)));
      retained.set(lc(intent.hash), kept);
      return { ok: true, anchor, envelope: kept, balances: { native: nativeBalance.toString() } };
    } catch {
      return { ok: false, reasons: ['preflight_error'] }; // a conversion that escaped the validators is still a hold, never provider text
    }
  }

  // The numbers of an envelope must follow from the signed intent, the policy and the oracle quote: nothing in them is a
  // free input. Returns reasons (empty when consistent).
  function envelopeProblems(intent, env) {
    const out = [];
    try {
      if (!env || typeof env !== 'object' || !env.binding) return ['envelope_missing'];
      const exec = big(intent.maxFeeWei); const op = big(policy.fee.operatorFeeBoundWei);
      if (env.executionCeilingWei !== exec) out.push('envelope_execution_ceiling_differs_from_signed');
      if (env.operatorBoundWei !== op) out.push('envelope_operator_bound_differs_from_policy');
      const margined = (big(env.l1QuoteWei) * BigInt(policy.fee.l1MultiplePpm) + 999_999n) / 1_000_000n;
      if (env.l1MarginedWei !== margined) out.push('envelope_l1_margin_inconsistent');
      if (env.allInWei !== exec + margined + op) out.push('envelope_total_inconsistent');
      if (env.allInWei > big(policy.fee.maxExposureWei)) out.push('envelope_exceeds_authorization');
      const b = env.binding;
      if (b.intentHash !== lc(intent.hash ?? '') || b.chainId !== policy.chainId || b.policyDigest !== digest) out.push('envelope_not_bound_to_this_intent_or_policy');
      if (!policy.approvedProviderIds.includes(b.providerId)) out.push('envelope_provider_not_approved');
      if (!HASH.test(b.anchorHash || '') || !Number.isSafeInteger(b.anchorNumber)) out.push('envelope_anchor_malformed');
    } catch { out.push('envelope_malformed'); }
    return out;
  }
  const same = (x, y) => JSON.stringify(x, (k, v) => (typeof v === 'bigint' ? v.toString() + 'n' : v)) === JSON.stringify(y, (k, v) => (typeof v === 'bigint' ? v.toString() + 'n' : v));

  // A durable record of a preflight envelope (the journal owner saved it before the send) can be brought back after a
  // restart ONLY through this verification: consistency with the signed intent and the policy, and an anchor that is
  // actually canonical on the pinned chain right now. Returns the frozen retained envelope.
  async function restoreEnvelope(intent, record) {
    if (problems.length) return { ok: false, reasons: ['policy_incomplete:' + problems.join(',')] };
    const reasons = envelopeProblems(intent, record);
    if (reasons.length) return { ok: false, reasons };
    try {
      const providerId = await rpc.providerId();
      if (providerId !== record.binding.providerId || !policy.approvedProviderIds.includes(providerId)) return { ok: false, reasons: ['provider_differs_from_envelope'] };
      if (count(await rpc.chainId()) !== policy.chainId) return { ok: false, reasons: ['chain_differs'] };
      let at; try { at = blockFields(await rpc.getBlock(record.binding.anchorNumber)); } catch { return { ok: false, reasons: ['anchor_not_canonical'] }; }
      if (at.hash !== record.binding.anchorHash || at.number !== record.binding.anchorNumber) return { ok: false, reasons: ['anchor_not_canonical'] };
      // the L1 quote is a chain fact, not arithmetic: ask the oracle for the exact payload AT the retained anchor and require
      // the same answer; an unreadable, malformed or different answer (including a non-archive provider) holds
      let quote;
      try { quote = wordToBig(await rpc.call({ to: L1_ORACLE, data: encodeFunctionData({ abi: oracle, functionName: 'getL1Fee', args: [intent.raw] }) }, record.binding.anchorHash)); } catch { return { ok: false, reasons: ['l1_quote_unverifiable_at_anchor'] }; }
      if (quote !== record.l1QuoteWei) return { ok: false, reasons: ['l1_quote_differs_from_oracle_at_anchor'] };
    } catch { return { ok: false, reasons: ['restore_read_failed'] }; }
    const kept = deepFreeze(JSON.parse(JSON.stringify(record, (k, v) => (typeof v === 'bigint' ? { __big: v.toString() } : v)), (k, v) => (v && typeof v === 'object' && '__big' in v ? BigInt(v.__big) : v)));
    retained.set(lc(intent.hash), kept);
    return { ok: true, envelope: kept };
  }

  // receipt: { status, transactionHash, from, to, blockHash, blockNumber, gasUsed, effectiveGasPrice, l1Fee?, operatorFee?, logs }
  // envelope: what preflight (or restoreEnvelope) returned; it is compared with the copy the gate retained, and the
  // retained copy decides. balances: { before, after } native, sender, wei. rpc.getTransaction(hash) -> { hash, from, to,
  // nonce, value, input, blockHash }. Blocks must carry parentHash: the confirmations are proven by a hash lineage walk.
  async function reconcileReceipt({ intent, receipt, envelope, balances }) {
    if (problems.length) return { ok: false, reasons: ['policy_incomplete:' + problems.join(',')] };
    const reasons = [];
    try {
      if (!receipt || receipt.status !== 1) return { ok: false, reasons: ['receipt_not_successful'] };
      const kept = retained.get(lc(intent.hash ?? ''));
      if (!envelope || !envelope.binding) return { ok: false, reasons: ['envelope_missing'] };
      if (!kept) return { ok: false, reasons: ['envelope_not_retained'] };
      if (!same(envelope, kept)) reasons.push('envelope_differs_from_retained');
      reasons.push(...envelopeProblems(intent, kept));
      const bnd = kept.binding;

      // current provenance, read again now rather than trusted from the caller's binding
      let providerId; let chainNow;
      try { providerId = await rpc.providerId(); chainNow = count(await rpc.chainId()); } catch { return { ok: false, reasons: [...reasons, 'provenance_read_failed'] }; }
      if (!policy.approvedProviderIds.includes(providerId) || providerId !== bnd.providerId) reasons.push('provider_differs_from_envelope');
      if (chainNow !== policy.chainId) reasons.push('chain_differs');

      // bind the receipt to the intended transaction
      if (lc(receipt.transactionHash ?? '') !== lc(intent.hash ?? '')) reasons.push('receipt_hash_differs');
      if (lc(receipt.from ?? '') !== lc(intent.from)) reasons.push('receipt_sender_differs');
      const target = intent.kind === 'erc20' ? policy.token.address : intent.recipient;
      if (lc(receipt.to ?? '') !== lc(target)) reasons.push('receipt_target_differs');
      let tx; try { tx = await rpc.getTransaction(receipt.transactionHash); } catch { tx = undefined; }
      if (!tx) reasons.push('transaction_read_failed');
      else {
        if (lc(tx.hash ?? '') !== lc(intent.hash ?? '')) reasons.push('transaction_hash_differs');
        if (lc(tx.from ?? '') !== lc(intent.from)) reasons.push('transaction_sender_differs');
        if (lc(tx.to ?? '') !== lc(target)) reasons.push('transaction_target_differs');
        try {
          if (count(tx.nonce) !== count(intent.nonce)) reasons.push('transaction_nonce_differs');
          const wantValue = intent.kind === 'native' ? big(intent.amount) : 0n;
          if (quantity(tx.value) !== wantValue) reasons.push('transaction_value_differs');
        } catch { reasons.push('transaction_fields_invalid'); }
        const wantInput = intent.kind === 'erc20' ? encodeFunctionData({ abi: erc20, functionName: 'transfer', args: [intent.recipient, big(intent.amount)] }) : '0x';
        if (typeof tx.input !== 'string' || lc(tx.input) !== lc(wantInput)) reasons.push('transaction_calldata_differs');
        if (tx.blockHash !== undefined && lc(tx.blockHash) !== lc(receipt.blockHash ?? '')) reasons.push('transaction_block_differs');
      }

      // inclusion block, the envelope's anchor, and a hash lineage from the confirming block back to inclusion
      let incl; try { incl = blockFields(await rpc.getBlock(count(receipt.blockNumber)), true); } catch { return { ok: false, reasons: [...reasons, 'block_read_failed'] }; }
      if (incl.hash !== receipt.blockHash) reasons.push('block_not_canonical');
      try {
        const an = blockFields(await rpc.getBlock(bnd.anchorNumber));
        if (an.hash !== bnd.anchorHash || an.number !== bnd.anchorNumber) reasons.push('anchor_not_canonical');
        else if (!(an.number < incl.number && an.timestamp <= incl.timestamp)) reasons.push('anchor_not_before_inclusion');
      } catch { reasons.push('anchor_read_failed'); }

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

      // actual cost, component by component, against the retained envelope and the signed ceiling
      let fee;
      try {
        const l2 = big(receipt.gasUsed) * big(receipt.effectiveGasPrice);
        if (receipt.l1Fee === undefined) reasons.push('l1_fee_not_reported');
        const l1 = receipt.l1Fee === undefined ? 0n : big(receipt.l1Fee);
        let op = 0n;
        if (receipt.operatorFee !== undefined) op = big(receipt.operatorFee);
        else if (policy.fee.operatorFeeEvidence !== 'verified_not_applicable') reasons.push('operator_fee_not_reported');
        fee = { l2Wei: l2, l1Wei: l1, operatorWei: op, totalWei: l2 + l1 + op };
        if (l2 > kept.executionCeilingWei) reasons.push('actual_execution_exceeds_signed_ceiling');
        if (l1 > kept.l1MarginedWei) reasons.push('actual_l1_exceeds_envelope');
        if (op > kept.operatorBoundWei) reasons.push('actual_operator_exceeds_bound');
        if (fee.totalWei > kept.allInWei) reasons.push('actual_fee_exceeds_envelope');
        if (fee.totalWei > big(policy.fee.maxExposureWei)) reasons.push('actual_fee_exceeds_authorization');
      } catch { reasons.push('fee_fields_invalid'); }
      if (fee && balances) {
        try {
          const moved = big(balances.before) - big(balances.after);
          if (moved !== fee.totalWei + (intent.kind === 'native' ? big(intent.amount) : 0n)) reasons.push('sender_balance_delta_differs');
        } catch { reasons.push('balances_invalid'); }
      } else if (!balances) reasons.push('balances_missing');

      // LAST: the head, then the confirming block and its parent lineage, read after the head so that nothing the head read
      // triggered can pass; the whole confirmation proof rests on block hashes, not on a number compared with a count
      let head; try { head = blockFields(await rpc.getBlock('latest'), true); } catch { return { ok: false, reasons: [...reasons, 'head_invalid'] }; }
      if (head.timestamp > now() + policy.maxFutureSkewSec) reasons.push('head_in_future');
      const confNumber = incl.number + policy.confirmations - 1;
      if (head.number < confNumber) reasons.push('not_enough_confirmations');
      else {
        try {
          // walk from the confirming block down to the inclusion block by parentHash; the confirming block must be the
          // head's ancestor (or the head itself), proven the same way, so the lineage ends at the head just read
          let cursor = head; let steps = 0;
          while (cursor.number > confNumber) {
            if (++steps > 256) throw new Error('walk');
            const parent = blockFields(await rpc.getBlock(cursor.number - 1), true);
            if (parent.hash !== cursor.parentHash || parent.number !== cursor.number - 1) { reasons.push('head_lineage_broken'); break; }
            cursor = parent;
          }
          if (!reasons.includes('head_lineage_broken')) {
            while (cursor.number > incl.number) {
              const parent = blockFields(await rpc.getBlock(cursor.number - 1), true);
              if (parent.hash !== cursor.parentHash || parent.number !== cursor.number - 1) { reasons.push('inclusion_not_in_head_lineage'); break; }
              cursor = parent;
            }
            if (!reasons.includes('inclusion_not_in_head_lineage') && cursor.hash !== receipt.blockHash) reasons.push('inclusion_not_in_head_lineage');
            // and on down to the preflight anchor: the anchor must be an ancestor in the SAME checked lineage, not a separate number lookup
            if (!reasons.includes('inclusion_not_in_head_lineage')) {
              if (incl.number - bnd.anchorNumber > 256) reasons.push('anchor_too_far_below_inclusion');
              else {
                while (cursor.number > bnd.anchorNumber) {
                  const parent = blockFields(await rpc.getBlock(cursor.number - 1), true);
                  if (parent.hash !== cursor.parentHash || parent.number !== cursor.number - 1) { reasons.push('anchor_not_in_head_lineage'); break; }
                  cursor = parent;
                }
                if (!reasons.includes('anchor_not_in_head_lineage') && cursor.hash !== bnd.anchorHash) reasons.push('anchor_not_in_head_lineage');
              }
            }
          }
        } catch { reasons.push('lineage_read_failed'); }
      }
      let providerEnd; let chainEnd;
      try { providerEnd = await rpc.providerId(); chainEnd = count(await rpc.chainId()); } catch { reasons.push('provenance_read_failed'); }
      if (providerEnd !== undefined && (providerEnd !== providerId || chainEnd !== chainNow)) reasons.push('provenance_changed_during_check');

      const uniq = [...new Set(reasons)];
      return uniq.length ? { ok: false, reasons: uniq, fee } : { ok: true, fee };
    } catch {
      return { ok: false, reasons: ['reconcile_error'] };
    }
  }

  // The amount a gas return may move: balance minus the all-in reserve, never balance minus the L2 ceiling alone.
  function gasReturnAmount({ balanceWei, envelope, gasDustWei = 0n }) {
    const keep = big(envelope.allInWei) + big(policy.fee.reserveWei ?? 0);
    const amount = big(balanceWei) - keep;
    return amount > big(gasDustWei) ? amount : 0n;
  }

  return { preflight, restoreEnvelope, reconcileReceipt, gasReturnAmount, policyProblems: problems, policyDigest: digest };
}

function hold(reason) { const e = new Error(reason); e.holdReason = reason; return e; }
