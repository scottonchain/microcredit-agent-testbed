// The cryptographic decoder behind the wallet lifecycle's mandatory `verifyPrepared(raw)` port.
//
// It reads ONE thing, the serialized signed transaction, and derives every field from those bytes: the hash is
// recomputed (keccak256 of the exact bytes), the signer is recovered from the signature, and the transfer is decoded
// from the calldata. It is handed no expected values and returns none of its own: the component compares the result
// with the intent it requested. It holds no key, opens no connection and sends nothing.
//
// Supported forms, and nothing else (anything else is rejected, never "generically supported"):
//   - EIP-1559 (type 0x02) with an empty access list and a low-S, in-range signature in canonical encoding
//   - an ERC-20 `transfer(address,uint256)` call to one contract with zero native value and exactly 68 bytes of calldata
//   - a plain native transfer with empty calldata
// Rejected: legacy, EIP-2930, EIP-4844, EIP-7702 and unknown types, trailing or alternate encodings, contract creation,
// any other selector or extra calldata (batch, multicall, approve, transferFrom), dirty address padding, a non-empty
// access list, high-S (malleable) or out-of-range signatures, zero gas, a priority fee above the fee cap, and any
// transaction larger than MAX_BYTES.

import { parseTransaction, serializeTransaction, recoverTransactionAddress, keccak256, isAddress } from 'viem';

export const MAX_BYTES = 4096;
const SECP_N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141n;
const HALF_N = 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0n;
const TRANSFER_SELECTOR = '0xa9059cbb';
const hexRe = /^0x(?:[0-9a-f]{2})+$/; // canonical lowercase, whole bytes (the component stores this form)

export class UnsupportedTransaction extends Error {
  constructor(reason) { super(reason); this.name = 'UnsupportedTransaction'; this.reason = reason; }
}
const no = reason => { throw new UnsupportedTransaction(reason); };

// raw -> { kind, hash, from, chainId, nonce, recipient, amount, maxFeeWei, contract?, nativeValue }
// A second argument (the component passes { kind }) is deliberately ignored: the form comes from the bytes.
export async function verifyPrepared(raw) {
  if (typeof raw !== 'string' || !hexRe.test(raw)) no('raw_not_canonical_hex');
  if ((raw.length - 2) / 2 > MAX_BYTES) no('raw_too_large');
  if (!raw.startsWith('0x02')) no('only_eip1559_supported');
  let t;
  try { t = parseTransaction(raw); } catch { no('unparseable'); }
  if (t.type !== 'eip1559') no('only_eip1559_supported');
  if (t.r === undefined || t.s === undefined || (t.yParity !== 0 && t.yParity !== 1)) no('missing_signature');
  const r = BigInt(t.r); const s = BigInt(t.s);
  if (r <= 0n || r >= SECP_N || s <= 0n || s > HALF_N) no('signature_out_of_range_or_malleable');
  // canonical re-serialization rejects trailing bytes and any alternate encoding of the same fields
  let again;
  try { again = serializeTransaction(t, { r: t.r, s: t.s, yParity: t.yParity }); } catch { no('not_reserializable'); }
  if (again.toLowerCase() !== raw) no('noncanonical_encoding');
  if ((t.accessList || []).length !== 0) no('access_list_not_supported');
  if (t.blobVersionedHashes || t.authorizationList) no('blob_or_authorization_not_supported');
  if (!Number.isSafeInteger(t.chainId) || t.chainId <= 0) no('chain_missing');
  if (!Number.isSafeInteger(t.nonce ?? 0)) no('nonce_invalid');
  if (!t.to || !isAddress(t.to, { strict: false })) no('contract_creation_or_bad_recipient');
  const gas = t.gas; const cap = t.maxFeePerGas; const tip = t.maxPriorityFeePerGas ?? 0n;
  if (typeof gas !== 'bigint' || gas <= 0n || typeof cap !== 'bigint' || cap < 0n || tip < 0n || tip > cap) no('gas_or_fee_invalid');
  const value = t.value ?? 0n;
  const data = (t.data ?? '0x').toLowerCase();

  let form;
  if (data === '0x') {
    form = { kind: 'native', recipient: t.to.toLowerCase(), amount: value, nativeValue: value };
  } else {
    // transfer(address,uint256): selector + 32-byte address word (12 zero bytes then the address) + 32-byte amount, nothing else
    if (data.length !== 2 + 2 * 68) no('calldata_not_a_single_transfer');
    if (data.slice(0, 10) !== TRANSFER_SELECTOR) no('selector_not_transfer');
    const word = data.slice(10, 74);
    if (!/^0{24}[0-9a-f]{40}$/.test(word)) no('dirty_address_padding');
    form = { kind: 'erc20', contract: t.to.toLowerCase(), recipient: '0x' + word.slice(24), amount: BigInt('0x' + data.slice(74)), nativeValue: value };
  }
  const from = (await recoverTransactionAddress({ serializedTransaction: raw })).toLowerCase();
  return {
    ...form, hash: keccak256(raw), from, chainId: t.chainId, nonce: t.nonce ?? 0, maxFeeWei: gas * cap,
  };
}
