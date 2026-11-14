// Read-only, block-bound snapshot of the CreditDesk pending queue (source only; nothing here has been run against a node).
// One snapshot = one provider, one chain id, one block: chainId check, latest block (number and hash), pending() and thread(applicant)
// pinned to that same block number, then the block hash is read again and must be unchanged. Nothing is ever combined across
// providers or blocks, and a failure is a failure, never an empty queue. Only times leave: applicant addresses and message text
// are decoded to be skipped and are dropped. No key, no signer, no write call.
const CHAIN_ID = 84532;
export const SEL_PENDING = '0xe20ccec3'; // pending()            (toFunctionSelector, checked against the CreditDesk ABI at PR 458 head)
export const SEL_THREAD = '0xd0aac15e'; //  thread(address)
const MAX_PENDING = 200, MAX_MSGS = 1000, MAX_RESULT_HEX = 2 * 1024 * 1024;
const HEX = /^0x(?:[0-9a-f]{2})*$/i, ADDR = /^0x[0-9a-fA-F]{40}$/, H32 = /^0x[0-9a-f]{64}$/;
const isNum = (x) => typeof x === 'number' && Number.isFinite(x);
const word = (hex, i) => hex.slice(2 + i * 64, 2 + (i + 1) * 64);
const big = (w) => BigInt('0x' + w);
const MAXSAFE = BigInt(Number.MAX_SAFE_INTEGER);

// ---- strict ABI decoders: exact length, in-bounds offsets, caps; any doubt is a failure ----
export function decodePending(hex) {
  if (typeof hex !== 'string' || !HEX.test(hex) || hex.length > MAX_RESULT_HEX) return { ok: false, why: 'BAD_HEX' };
  const words = (hex.length - 2) / 64; if (!Number.isInteger(words) || words < 2) return { ok: false, why: 'BAD_LENGTH' };
  if (big(word(hex, 0)) !== 32n) return { ok: false, why: 'BAD_OFFSET' };
  const n = big(word(hex, 1)); if (n > BigInt(MAX_PENDING)) return { ok: false, why: 'TOO_MANY' };
  if (words !== 2 + Number(n)) return { ok: false, why: 'BAD_LENGTH' };
  const out = [];
  for (let i = 0; i < Number(n); i++) { const w = word(hex, 2 + i); if (!/^0{24}[0-9a-f]{40}$/i.test(w)) return { ok: false, why: 'BAD_ADDRESS' }; out.push('0x' + w.slice(24)); }
  return { ok: true, addresses: out };
}
// thread(address) returns tuple[]{uint8 from, uint40 at, string text}. Only (from, at) are kept; the text is bounds-checked and discarded.
export function decodeThreadTimes(hex) {
  if (typeof hex !== 'string' || !HEX.test(hex) || hex.length > MAX_RESULT_HEX) return { ok: false, why: 'BAD_HEX' };
  const total = (hex.length - 2) / 2; if (total % 32 !== 0 || total < 64) return { ok: false, why: 'BAD_LENGTH' };
  const byteAt = (b) => 2 + b * 2; const wordAtByte = (b) => hex.slice(byteAt(b), byteAt(b + 32));
  const readBig = (b) => { if (b < 0 || b + 32 > total) throw new RangeError('out of bounds'); return big(wordAtByte(b)); };
  try {
    if (readBig(0) !== 32n) return { ok: false, why: 'BAD_OFFSET' };
    const n = readBig(32); if (n > BigInt(MAX_MSGS)) return { ok: false, why: 'TOO_MANY' };
    const base = 64, msgs = [];
    for (let i = 0; i < Number(n); i++) {
      const off = readBig(base + 32 * i); if (off > MAXSAFE) return { ok: false, why: 'BAD_OFFSET' };
      const t = base + Number(off); if (t < base + 32 * Number(n) || t + 96 > total) return { ok: false, why: 'BAD_OFFSET' };
      const from = readBig(t), at = readBig(t + 32), so = readBig(t + 64);
      if (from > 1n) return { ok: false, why: 'BAD_FROM' };
      if (at >= 1n << 40n) return { ok: false, why: 'BAD_TIME' };
      if (so > MAXSAFE || t + Number(so) + 32 > total) return { ok: false, why: 'BAD_STRING' };
      const len = readBig(t + Number(so)); if (len > MAXSAFE || t + Number(so) + 32 + Math.ceil(Number(len) / 32) * 32 > total) return { ok: false, why: 'BAD_STRING' }; // the padded string must be fully present
      msgs.push({ from: Number(from), at: Number(at) });
    }
    return { ok: true, messages: msgs };
  } catch { return { ok: false, why: 'OUT_OF_BOUNDS' }; }
}

const qty = (v) => typeof v === 'string' && /^0x[0-9a-f]+$/i.test(v) ? Number(BigInt(v) <= MAXSAFE ? BigInt(v) : -1n) : NaN;
const hexn = (n) => '0x' + n.toString(16);
const fail = (why) => ({ ok: false, why });

// One snapshot against one provider. rpc(method, params) is injected and may throw; now() is the caller's clock.
export async function takeSnapshot(rpc, { desk, now, maxPending = MAX_PENDING } = {}) {
  try {
    if (typeof desk !== 'string' || !ADDR.test(desk) || typeof rpc !== 'function' || typeof now !== 'function') return fail('BAD_ARGS');
    if (qty(await rpc('eth_chainId', [])) !== CHAIN_ID) return fail('WRONG_CHAIN');
    const head = await rpc('eth_getBlockByNumber', ['latest', false]);
    const N = qty(head && head.number), ts = qty(head && head.timestamp);
    if (!head || !Number.isSafeInteger(N) || N < 0 || !Number.isSafeInteger(ts) || ts <= 0 || typeof head.hash !== 'string' || !H32.test(head.hash)) return fail('BAD_BLOCK');
    const at = hexn(N);
    const pendingHex = await rpc('eth_call', [{ to: desk, data: SEL_PENDING }, at]);
    const p = decodePending(pendingHex); if (!p.ok) return fail('PENDING_' + p.why);
    if (p.addresses.length > maxPending) return fail('TOO_MANY_PENDING');
    const entries = [];
    for (const a of p.addresses) {
      const data = SEL_THREAD + '0'.repeat(24) + a.slice(2).toLowerCase();
      const t = decodeThreadTimes(await rpc('eth_call', [{ to: desk, data }, at])); if (!t.ok) return fail('THREAD_' + t.why);
      const lastAsk = t.messages.filter((m) => m.from === 0).reduce((m, x) => Math.max(m, x.at), 0);
      if (lastAsk <= 0) return fail('THREAD_NO_REQUEST'); // a pending applicant must have an applicant message
      entries.push({ requestedAtMs: lastAsk * 1000 });
    }
    const again = await rpc('eth_getBlockByNumber', [at, false]);
    if (!again || again.hash !== head.hash) return fail('HASH_CHANGED'); // a reorg or a different node answered in between
    const readAtMs = now(); if (!isNum(readAtMs)) return fail('BAD_CLOCK');
    return { ok: true, snapshot: { pending: entries, readAtMs, blockNumber: N, blockTimeMs: ts * 1000, pendingBlockNumber: N } };
  } catch { return fail('RPC_ERROR'); }
}

// Providers in order, each tried as a whole with bounded retries; the first complete snapshot wins; fields are never mixed.
export async function readWithFallback(endpoints, makeRpc, { desk, now, sleep, attempts = 2, backoffMs = [500, 1500] } = {}) {
  if (!Array.isArray(endpoints) || endpoints.length === 0 || endpoints.length > 4 || typeof makeRpc !== 'function' || typeof sleep !== 'function') return fail('BAD_ARGS');
  const tried = [];
  for (const ep of endpoints) {
    for (let k = 0; k < attempts; k++) {
      let r; try { r = await takeSnapshot(makeRpc(ep.url), { desk, now }); } catch { r = fail('RPC_ERROR'); }
      if (r.ok) return { ok: true, snapshot: r.snapshot, endpoint: ep.label };
      tried.push({ endpoint: ep.label, why: r.why });
      if (k + 1 < attempts) await sleep(backoffMs[Math.min(k, backoffMs.length - 1)]);
    }
  }
  return { ok: false, why: 'ALL_ENDPOINTS_FAILED', tried };
}

// JSON-RPC over fetch: https only, no credentials in the URL, bounded time and size, id and shape checked.
export function validEndpointUrl(u) { try { const x = new URL(u); return x.protocol === 'https:' && !x.username && !x.password && !x.search && !x.hash && x.hostname.length > 0; } catch { return false; } }
export function makeJsonRpc(url, fetchImpl, { timeoutMs = 8000, maxBytes = 1048576 } = {}) {
  if (!validEndpointUrl(url) || typeof fetchImpl !== 'function') throw new TypeError('bad endpoint');
  let id = 0;
  return async (method, params) => {
    id += 1; const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), timeoutMs);
    try {
      const res = await fetchImpl(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id, method, params }), signal: ctl.signal });
      if (!res || !res.ok) throw new Error('http');
      const text = await res.text(); if (typeof text !== 'string' || text.length > maxBytes) throw new Error('size');
      const j = JSON.parse(text);
      if (!j || j.jsonrpc !== '2.0' || j.id !== id || 'error' in j || !('result' in j)) throw new Error('shape');
      return j.result;
    } finally { clearTimeout(timer); }
  };
}
