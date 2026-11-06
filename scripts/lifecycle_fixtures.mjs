// Local-only fixtures for the runner tests: an in-process chain whose state can live in a file, so a
// disposable child process can be killed and a second one can resume against the same "chain". Generated
// unfunded identities only. No network, no keys, no signing: "signatures" are labelled strings.

import fs from 'node:fs';

export const FUND = '0x' + 'f'.repeat(40);
export const OTHER = '0x' + 'e'.repeat(40);
export const TOKEN = '0x' + 'd'.repeat(40);
export const CHAIN_ID = 84532;
// signed bytes in the canonical form the component stores: 0x + lowercase hex; the "signature" labels the tx hash
export const encodeRaw = hash => '0x' + Buffer.from('raw:' + hash).toString('hex');
export const decodeRaw = raw => Buffer.from(String(raw).slice(2), 'hex').toString().slice(4);
export const MAX_FEE = 1000n;
export const addr = n => '0x' + n.toString(16).padStart(40, '0');
const k = a => String(a).toLowerCase();
const big = o => Object.fromEntries(Object.entries(o).map(([a, v]) => [a, v.toString()]));

export function roster(n) { return Array.from({ length: n }, (_, i) => ({ id: 'w' + (i + 1), address: addr(i + 1), role: 'client' })); }

// opts: lost (wallet ids the orchestrator cannot sign for), contracts, redirect (wrong recipient), drop (ids whose
// broadcasts vanish), gasFee, gasCost, hooks { after_prepare, before_broadcast, after_broadcast } (async, by name).
export function makeChain({ file = null, tokens = {}, gas = {}, fund = 0n, lost = [], contracts = [], redirect = false, drop = [], revert = [], wrongToken = false, gasFee = 10n, gasCost = 100n, hooks = {}, wrongChain = false, verifierLies = false, verifier = true, returnBytes = false, feeOver = false } = {}) {
  let mem = {
    tokens: big(tokens), gas: big(gas), fund: fund.toString(), fundGas: '0', mined: {}, pending: {}, broadcasts: [], signs: 0, nonces: {},
    lost: lost.slice(), contracts: contracts.map(k), drop: drop.slice(),
  };
  const load = () => (file && fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : mem);
  const store = s => { mem = s; if (file) { const t = file + '.tmp'; fs.writeFileSync(t, JSON.stringify(s)); fs.renameSync(t, file); } };
  if (file && !fs.existsSync(file)) store(mem);
  const B = (s, a) => BigInt(s.tokens[k(a)] || '0');
  const hook = async name => { if (hooks[name]) await hooks[name](); };

  const ports = {
    async controls(w) { return !load().lost.includes(w.id); },
    async tokenBalance(a) { const s = load(); return k(a) === k(FUND) ? BigInt(s.fund) : B(s, a); },
    async gasBalance(a) { return BigInt(load().gas[k(a)] || '0'); },
    async gasCostEstimate() { return gasCost; },
    async gasSweepFee() { return gasFee; },
    async nonceOf(a) { return load().nonces[k(a)] || 0; },
    async isContract(a) { return load().contracts.includes(k(a)); },
    async prepareSweep(w, to, amount, nonce) {
      const s = load(); s.signs++; const hash = '0xt' + s.signs;
      s.pending[hash] = { kind: 'token', from: k(w.address), to: redirect ? OTHER : to, amount: amount.toString(), nonce, id: w.id };
      store(s); await hook('after_prepare');
      return { hash, raw: returnBytes ? Buffer.from('raw:' + hash) : encodeRaw(hash) };
    },
    async prepareGasSweep(w, to, amount, nonce) {
      const s = load(); s.signs++; const hash = '0xg' + s.signs;
      s.pending[hash] = { kind: 'gas', from: k(w.address), to, amount: amount.toString(), nonce, id: w.id };
      store(s); await hook('after_prepare');
      return { hash, raw: returnBytes ? Buffer.from('raw:' + hash) : encodeRaw(hash) };
    },
    async broadcast(raw) {
      await hook('before_broadcast');
      const s = load(); const hash = decodeRaw(raw); s.broadcasts.push(hash);
      const tx = s.pending[hash]; if (!tx) { store(s); throw new Error('unknown tx'); }
      if (s.mined[hash] || s.drop.includes(tx.id)) { store(s); return; }
      const reverted = revert.includes(tx.id);
      s.mined[hash] = { status: reverted ? 0 : 1, from: tx.from, to: tx.to, amount: tx.amount, nonce: tx.nonce, chainId: wrongChain ? 1 : CHAIN_ID, token: tx.kind === 'token' ? (wrongToken ? OTHER : TOKEN) : undefined };
      s.nonces[tx.from] = (s.nonces[tx.from] || 0) + 1;
      if (reverted) { store(s); await hook('after_broadcast'); return; }
      const amt = BigInt(tx.amount);
      if (tx.kind === 'token') { s.tokens[tx.from] = (BigInt(s.tokens[tx.from] || '0') - amt).toString(); if (k(tx.to) === k(FUND)) s.fund = (BigInt(s.fund) + amt).toString(); }
      else { s.gas[tx.from] = (BigInt(s.gas[tx.from] || '0') - amt - gasFee).toString(); s.fundGas = (BigInt(s.fundGas) + amt).toString(); }
      store(s); await hook('after_broadcast');
    },
    // decodes the serialized bytes (here a labelled string) and reports what they say; verifierLies makes the decoder
    // report the requested intent while the chain still executes the redirected one (tests the receipt check as a second line)
    async verifyPrepared(raw, { kind }) {
      const s = load(); const hash = decodeRaw(raw); const tx = s.pending[hash]; if (!tx) throw new Error('undecodable');
      const honest = { kind: tx.kind === 'token' ? 'erc20' : 'native', hash, from: tx.from, chainId: wrongChain ? 1 : CHAIN_ID, nonce: tx.nonce, recipient: tx.to, amount: tx.amount, maxFeeWei: feeOver ? '5000' : MAX_FEE.toString(), contract: tx.kind === 'token' ? (wrongToken ? OTHER : TOKEN) : undefined, nativeValue: '0' };
      return verifierLies ? { ...honest, recipient: FUND, chainId: CHAIN_ID, contract: tx.kind === 'token' ? TOKEN : undefined } : honest;
    },
    async receipt(hash) {
      const r = load().mined[hash]; if (!r) return null;
      return { status: r.status, from: r.from, to: r.to, amount: BigInt(r.amount), nonce: r.nonce, chainId: r.chainId, token: r.token, rpc: { status: r.status } };
    },
  };
  // placing scenario funds on the chain is the caller's "fund" step
  const placeFunds = async (perWallet) => {
    const s = load();
    for (const [a, v] of Object.entries(perWallet.tokens || {})) { s.tokens[k(a)] = (BigInt(s.tokens[k(a)] || '0') + v).toString(); s.fund = (BigInt(s.fund) - v).toString(); }
    for (const [a, v] of Object.entries(perWallet.gas || {})) s.gas[k(a)] = (BigInt(s.gas[k(a)] || '0') + v).toString();
    store(s);
  };
  const deposit = (a, v, g = 0n) => { const s = load(); s.tokens[k(a)] = (BigInt(s.tokens[k(a)] || '0') + v).toString(); s.gas[k(a)] = (BigInt(s.gas[k(a)] || '0') + g).toString(); store(s); };
  if (!verifier) delete ports.verifyPrepared;
  return { ports, placeFunds, deposit, state: () => load() };
}

// A permissive stand-in for the chain gate, used by the legacy component and runner tests (which exercise their own
// behaviours, not the gate). It records its calls. The REAL gate is exercised in scripts/lifecycle_verifier/test_b2_integration.mjs.
export function fakeChainGate({ policyDigest = '0x' + '11'.repeat(32) } = {}) {
  const calls = { preflight: [], restore: [], reconcile: [] };
  return {
    policyDigest, calls,
    async preflight(i) { calls.preflight.push(i); return { ok: true, anchor: { number: 1, hash: '0x' + 'aa'.repeat(32) }, envelope: { fake: true, hash: i.hash }, balances: { native: '1000' } }; },
    async restoreEnvelope(i, env) { calls.restore.push(i); return { ok: true, envelope: env }; },
    async reconcileReceipt(a) { calls.reconcile.push(a); return { ok: true, fee: {} }; },
    async reconcileRevert(a) { calls.reconcile.push(a); return { ok: true, fee: { totalWei: 0n } }; },
    encodeEnvelope: e => ({ v: 1, fake: true, hash: e.hash }),
    decodeEnvelope: r => { if (!r || r.v !== 1) throw new Error('envelope_record_invalid'); return { fake: true, hash: r.hash }; },
  };
}
