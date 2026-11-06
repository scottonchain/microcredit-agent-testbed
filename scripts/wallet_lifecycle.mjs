// Scenario-wallet lifecycle: control check before a run, terminal cleanup back to the funding wallet.
//
// Decision and journal logic with injected ports. This module imports no network library, holds no key
// and never signs: a runner supplies `ports` that wrap its own signer.
//
// THE JOURNAL IS NOT PUBLIC EVIDENCE. It deliberately persists the signed raw transaction of every sweep
// (so an unsettled sweep is rebroadcast byte for byte, never re-signed). Keep the file private (mode 0600).
// Use `publicView(journal)` for anything that leaves the runner: it drops the raw bytes. Error text from
// providers or signers is never stored (it can carry credentials); only a short code is.
//
// Ports (all async):
//   controls(wallet)                         -> boolean   the orchestrator holds this signer (no signing to prove it)
//   tokenBalance(address)                    -> bigint    test token, base units
//   gasBalance(address)                      -> bigint    native token, wei
//   gasCostEstimate()                        -> bigint    wei needed for one token transfer
//   gasSweepFee()                            -> bigint    wei kept back to pay for the gas-return transaction
//   nonceOf(address)                         -> number    pending transaction count
//   isContract(address)                      -> boolean
//   prepareSweep(wallet, to, amount, nonce)  -> { hash, raw }   signs inside the runner; sends nothing
//   prepareGasSweep(wallet, to, amount, nonce) -> { hash, raw }
//   broadcast(raw)                           -> void      sends the identical signed bytes
//   verifyPrepared(raw, { kind })            -> decoded   MANDATORY. Decodes the serialized signed transaction itself
//                                                         (not producer metadata): { kind: 'erc20'|'native', hash (recomputed),
//                                                         from (recovered signer), chainId, nonce, recipient, amount, maxFeeWei,
//                                                         contract (erc20 only), nativeValue (erc20: must be 0) }
//
// RAW FORMAT: a signed transaction is one canonical string, 0x + lowercase hex of whole bytes. A port may return a
// Uint8Array; it is converted to that string before anything is stored, so the journal holds one lossless form and a
// resume broadcasts exactly the bytes that were signed. Anything else is not accepted as a signed intent.
//
// NOTHING IS BROADCAST UNTIL THE INTENT IS VERIFIED. The signed intent is stored first (private bytes are never lost),
// then the component compares the decoded transaction field by field with the requested intent (signer, hash, chain,
// nonce, token contract or native value, recipient = the funding wallet, amount, fee at most `maxFeeWei`). A missing
// verifier, an unnamed chain, token or fee bound, a decode error or any difference leaves the intent stored as
// 'unverified', the wallet unknown and the run open, with zero broadcasts; a resume verifies again before sending.
//   receipt(hash)                            -> { status:1|0, from, to, amount, nonce, chainId, token?, rpc } | null   (`rpc` = the provider's raw receipt, bound by the chain gate)
//
// Run status: open -> (failed_cleanup | pending_reconciliation) -> closed | closed_with_exceptions.
// `closed` means every wallet was emptied. `closed_with_exceptions` means every remaining balance is a named,
// approved residual. Nothing else closes a run, and a failed reconciliation stays failed until a later
// reconciliation matches.

import fs from 'node:fs';
import nodePath from 'node:path';
import crypto from 'node:crypto';

export const SCHEMA = 1;
export const walletStates = new Set(['pending', 'empty', 'swept', 'needs_gas', 'signer_lost', 'locked_contract', 'dust_accepted', 'failed', 'unknown']);
export const emptiedStates = new Set(['empty', 'swept']);
export const gasStates = new Set(['pending', 'returned', 'residual', 'signer_lost', 'failed', 'unknown']);
const addrRe = /^0x[0-9a-fA-F]{40}$/;
const idRe = /^[A-Za-z0-9._-]{1,64}$/;

export class SaveFailed extends Error {}

const RAW_MAX_HEX = 262144;
// One lossless, canonical form for signed bytes: '0x' + lowercase hex of whole bytes. Returns null when the value is
// not a non-empty byte string in a form that converts without loss.
export function canonicalRaw(raw) {
  let hex;
  if (raw instanceof Uint8Array) hex = Buffer.from(raw.buffer, raw.byteOffset, raw.byteLength).toString('hex');
  else if (typeof raw === 'string' && /^0x(?:[0-9a-fA-F]{2})+$/.test(raw)) hex = raw.slice(2).toLowerCase();
  else return null;
  if (hex.length === 0 || hex.length > RAW_MAX_HEX) return null;
  return '0x' + hex;
}
function normalizePrepared(p) {
  if (!p || typeof p !== 'object') return null;
  if (typeof p.hash !== 'string' || p.hash.length === 0 || p.hash.length > 200) return null;
  const raw = canonicalRaw(p.raw);
  return raw ? { hash: p.hash, raw } : null;
}

function code(e) {
  if (e instanceof SaveFailed) return 'save_error';
  return 'port_error'; // never the message: it may contain credentials or private endpoints
}

export function validateJournal(j) {
  const problems = [];
  if (!j || typeof j !== 'object') return ['journal is not an object'];
  if (j.schema !== SCHEMA) problems.push('unsupported schema');
  if (!addrRe.test(j.fundingWallet || '')) problems.push('funding wallet must be a public address');
  if (!j.wallets || typeof j.wallets !== 'object') return problems.concat('wallets missing');
  const ids = new Set(); const addrs = new Set();
  for (const [key, w] of Object.entries(j.wallets)) {
    if (!idRe.test(key) || w.id !== key) problems.push(`wallet key and id disagree or are invalid: ${key}`);
    if (ids.has(w.id)) problems.push(`duplicate id ${w.id}`);
    ids.add(w.id);
    if (!addrRe.test(w.address || '')) problems.push(`bad address for ${key}`);
    const a = String(w.address).toLowerCase();
    if (addrs.has(a)) problems.push(`duplicate address ${w.address}`);
    addrs.add(a);
    if (a === String(j.fundingWallet).toLowerCase()) problems.push('the funding wallet is not a scenario wallet');
    if (!walletStates.has(w.state)) problems.push(`unknown state ${w.state} for ${key}`);
    if (w.gas && !gasStates.has(w.gas.state)) problems.push(`unknown gas state for ${key}`);
  }
  return problems;
}

export function newJournal(runId, fundingWallet, wallets, now) {
  const wmap = {};
  for (const w of wallets) {
    if (!idRe.test(w.id || '')) throw new Error(`invalid or empty wallet id: ${JSON.stringify(w.id)}`);
    if (wmap[w.id]) throw new Error(`duplicate id ${w.id}`);
    wmap[w.id] = { id: w.id, address: w.address, role: w.role || 'scenario', state: 'pending', events: [] };
  }
  const j = { schema: SCHEMA, runId, fundingWallet, createdAt: now, status: 'open', control: null, gasPhase: 'not_run', persistence: { failed: false }, reconciliation: null, wallets: wmap };
  const problems = validateJournal(j);
  if (problems.length) throw new Error(problems[0]);
  return j;
}

// Journals are written before the effect they describe. Written atomically, fsynced, owner-only.
// The temp file has a unique unpredictable name and is created exclusively (O_EXCL, which also refuses a
// pre-placed file or symlink), forced to 0600 whatever the umask or any existing file, and the containing
// directory is fsynced after the rename so the published intent survives a crash.
export function saveJournal(path, journal) {
  const dir = nodePath.dirname(path);
  const tmp = path + '.' + process.pid + '.' + crypto.randomBytes(8).toString('hex') + '.tmp';
  const fd = fs.openSync(tmp, 'wx', 0o600);
  try {
    try {
      fs.fchmodSync(fd, 0o600);
      if ((fs.fstatSync(fd).mode & 0o077) !== 0) throw new Error('journal temp file is not private');
      // writeSync may write fewer bytes than asked without throwing: loop until the whole buffer is written, and
      // fail on zero progress, so a truncated journal is never fsynced, renamed and reported as durable.
      const buf = Buffer.from(JSON.stringify(journal, null, 1), 'utf8');
      let off = 0;
      while (off < buf.length) {
        const n = fs.writeSync(fd, buf, off, buf.length - off);
        if (!Number.isInteger(n) || n <= 0) throw new Error('journal write made no progress');
        off += n;
      }
      fs.fsyncSync(fd);
    } finally { fs.closeSync(fd); }
    fs.renameSync(tmp, path);
  } catch (e) {
    try { fs.unlinkSync(tmp); } catch { /* already renamed or gone */ }
    throw e;
  }
  const dfd = fs.openSync(dir, 'r');
  try { fs.fsyncSync(dfd); } finally { fs.closeSync(dfd); }
}
export function loadJournal(path) {
  const j = JSON.parse(fs.readFileSync(path, 'utf8'));
  const problems = validateJournal(j);
  if (problems.length) throw new Error('invalid journal: ' + problems[0]);
  // Journals written before reconciliations carried a fingerprint cannot be shown to describe the current
  // state. Move such a reconciliation aside: the run is pending until a fresh cumulative one is recorded.
  if (j.reconciliation && !j.reconciliation.fingerprint) {
    (j.staleReconciliations = j.staleReconciliations || []).push({ ...j.reconciliation, legacy: true });
    j.reconciliation = null;
    if (j.status === 'closed' || j.status === 'closed_with_exceptions') j.status = 'pending_reconciliation';
  }
  return j;
}

// What may leave the runner: no raw signed bytes.
export function publicView(journal) {
  const copy = JSON.parse(JSON.stringify(journal));
  for (const w of Object.values(copy.wallets)) {
    if (w.sweep) delete w.sweep.raw;
    if (w.gas && w.gas.sweep) delete w.gas.sweep.raw;
  }
  return copy;
}

// A persistent write that must succeed before a broadcast. A failure marks the journal and stops the effect.
function durable(journal, opts) {
  try { opts.save(journal); return true; }
  catch { journal.persistence = { failed: true }; return false; }
}

function resolveOptions(journal, options) {
  if (typeof options.save !== 'function' && options.ephemeral !== true) {
    throw new Error('a persistent save function is required (pass ephemeral: true only in tests)');
  }
  return {
    dust: 0n, gasDust: 0n, gasReserveMultiple: 2, token: null, save: () => {}, ...options,
    fundingWallet: journal.fundingWallet,
    approvedContracts: new Set([...(options.approvedContracts || [])].map(a => String(a).toLowerCase())),
  };
}

function ev(w, e) { w.events.push(e); }

export async function verifyControl(journal, ports, options = {}) {
  const opts = resolveOptions(journal, options);
  const missing = [];
  for (const w of Object.values(journal.wallets)) {
    let ok = false;
    try { ok = (await ports.controls(w)) === true; } catch { ok = false; }
    if (!ok) { w.state = 'signer_lost'; ev(w, { ev: 'control_check_failed' }); missing.push(w.id); }
    else ev(w, { ev: 'control_ok' });
  }
  journal.control = { checked: Object.keys(journal.wallets).length, missing };
  durable(journal, opts);
  return { ok: missing.length === 0, missing };
}

// The chain gate (accepted B1 component) is a MANDATORY port object: every member is required, and without all of them nothing
// is sent and no receipt is accepted. It is checked here, never assumed.
const GATE_FNS = ['preflight', 'restoreEnvelope', 'reconcileReceipt', 'encodeEnvelope', 'decodeEnvelope'];
function chainGateComplete(g) { return !!g && typeof g === 'object' && GATE_FNS.every(f => typeof g[f] === 'function') && typeof g.policyDigest === 'string' && g.policyDigest.length > 0; }
async function callGate(fn) { try { const r = await fn(); return r && typeof r === 'object' ? r : { ok: false, reasons: ['chain_gate_invalid_result'] }; } catch { return { ok: false, reasons: ['chain_gate_error'] }; } }
const firstReason = r => String((r && Array.isArray(r.reasons) && r.reasons[0]) || 'unknown').replace(/[^A-Za-z0-9_:.,-]/g, '').slice(0, 80) || 'unknown';
const DEC = /^(?:0|[1-9][0-9]{0,77})$/;
// the intent the gate sees is built from the DECODED bytes (verifier output), plus the stored raw bytes, and is frozen
function gateIntent(d, sweep, resend) {
  return Object.freeze({ kind: d.kind, hash: sweep.hash, from: d.from, recipient: d.recipient, amount: d.amount, nonce: d.nonce, raw: sweep.raw, maxFeeWei: d.maxFeeWei, contract: d.contract, resend: resend === true });
}

// The receipt must bind to the prepared intent AND, through the mandatory chain gate, to the retained fee envelope and the
// canonical chain. Returns 'swept' | 'failed' | 'mismatch' | 'unknown'; a mismatch records short reason codes only.
async function settle(ports, intent, expect, opts, ctx) {
  let r;
  try { r = await ports.receipt(intent.hash); } catch { return 'unknown'; }
  if (r === null || r === undefined) return 'unknown';
  if (r.status !== 1) return 'failed';
  const same = x => String(x).toLowerCase();
  if (same(r.from) !== same(expect.from) || same(r.to) !== same(expect.to) || BigInt(r.amount) !== BigInt(expect.amount) || Number(r.nonce) !== Number(expect.nonce)) return 'mismatch';
  // when the caller names a token or a chain, a receipt that does not state the same one is not accepted
  if (expect.token && (r.token === undefined || same(r.token) !== same(expect.token))) return 'mismatch';
  if (expect.chainId !== undefined && expect.chainId !== null && (r.chainId === undefined || Number(r.chainId) !== Number(expect.chainId))) return 'mismatch';
  const gate = opts && opts.chainGate;
  if (!chainGateComplete(gate)) { intent.mismatchReasons = ['chain_gate_missing']; return 'mismatch'; }
  if (!intent.envelope) { intent.mismatchReasons = ['envelope_missing']; return 'mismatch'; }
  let env; try { env = gate.decodeEnvelope(intent.envelope); } catch { intent.mismatchReasons = ['envelope_record_invalid']; return 'mismatch'; }
  const v = await verifyIntentFull(ports, ctx.kind, ctx.from, intent, opts);
  if (v.why) { intent.mismatchReasons = [v.why]; return 'mismatch'; }
  const gi = gateIntent(v.d, intent, false);
  const rs = await callGate(() => gate.restoreEnvelope(gi, env));
  if (!rs.ok) { const why = firstReason(rs); if (/read_failed|unverifiable|provenance_read/.test(why)) return 'unknown'; intent.mismatchReasons = [why]; return 'mismatch'; }
  let before; let after;
  try {
    if (typeof intent.preNative !== 'string' || !DEC.test(intent.preNative)) throw new Error('pre');
    before = BigInt(intent.preNative); after = await ports.gasBalance(ctx.from);
    if (typeof after !== 'bigint' || after < 0n) throw new Error('post');
  } catch { return 'unknown'; }
  // `receipt.rpc` is the provider's raw receipt (hash, block, gas, fee components, logs) that the gate binds; the flat summary fields
  // above are only the legacy comparison. A port that supplies no raw receipt makes the gate refuse.
  const rc = await callGate(() => gate.reconcileReceipt({ intent: gi, receipt: r.rpc, envelope: rs.envelope, balances: { before, after } }));
  if (rc.ok) return 'swept';
  const why = (Array.isArray(rc.reasons) ? rc.reasons : ['chain_gate_invalid_result']).map(x => String(x).replace(/[^A-Za-z0-9_:.,-]/g, '').slice(0, 80)).slice(0, 6);
  // mined but not yet deep enough: nothing is wrong, nothing to resend; keep waiting (the bytes are already on chain)
  if (why.length === 1 && why[0] === 'not_enough_confirmations') { intent.awaitingConfirmations = true; return 'unknown'; }
  if (why.some(x => /read_failed|head_invalid|provenance_read/.test(x)) && !why.some(x => /differs|exceeds|not_canonical|lineage|invalid|missing/.test(x.replace(/read_failed|head_invalid/, '')))) return 'unknown';
  intent.mismatchReasons = why; return 'mismatch';
}

// The pre-broadcast gate. The serialized signed bytes are decoded by the injected verifier and every field is compared
// with the intent this component requested; the result of the same prepare call is never trusted as its own proof.
// Returns null when the intent may be sent, otherwise a short reason code.
async function verifyIntentFull(ports, kind, from, sweep, opts) {
  const no = why => ({ why, d: null });
  if (typeof ports.verifyPrepared !== 'function') return no('verifier_missing');
  if (!Number.isInteger(opts.chainId)) return no('chain_unnamed');
  if (kind === 'erc20' && !addrRe.test(opts.token || '')) return no('token_unnamed');
  let fee;
  try { fee = BigInt(opts.maxFeeWei); if (fee < 0n) throw new Error('neg'); } catch { return no('fee_bound_unnamed'); }
  const raw = canonicalRaw(sweep.raw);
  if (!raw) return no('raw_not_canonical');
  let d;
  try { d = await ports.verifyPrepared(raw, { kind }); } catch { return no('verifier_error'); }
  if (!d || typeof d !== 'object') return no('verifier_result_invalid');
  const same = x => String(x).toLowerCase();
  try {
    if (d.kind !== kind) return no('kind_differs');
    if (same(d.hash) !== same(sweep.hash)) return no('hash_differs');
    if (same(d.from) !== same(from)) return no('signer_differs');
    if (Number(d.chainId) !== opts.chainId || !Number.isInteger(Number(d.chainId))) return no('chain_differs');
    if (Number(d.nonce) !== Number(sweep.nonce) || !Number.isInteger(Number(d.nonce))) return no('nonce_differs');
    if (same(d.recipient) !== same(opts.fundingWallet)) return no('recipient_differs');
    if (BigInt(d.amount) !== BigInt(sweep.amount)) return no('amount_differs');
    if (kind === 'erc20') {
      if (same(d.contract) !== same(opts.token)) return no('token_differs');
      if (BigInt(d.nativeValue) !== 0n) return no('native_value_present');
    } else if (d.contract !== undefined && d.contract !== null) return no('contract_call_present');
    const f = BigInt(d.maxFeeWei);
    if (f < 0n || f > fee) return no('fee_over_bound');
  } catch { return no('verifier_result_invalid'); }
  return { why: null, d };
}

async function verifyIntent(ports, kind, from, sweep, opts) { return (await verifyIntentFull(ports, kind, from, sweep, opts)).why; }

// THE ONLY SEND PATH. For a first send and for every rebroadcast of an unsettled intent, in this order: the cryptographic decoder
// (fields derived from the signed bytes, compared with the requested intent), the policy snapshot, the chain-state gate, and for
// a first send the retained fee envelope is made durable WITH the exact intent before anything is sent. A failure at any step
// returns a reason and calls the provider's send port zero times. A rebroadcast restores the saved envelope through the gate
// (re-verified against the chain, never trusted from the file) and sends the identical stored bytes; it never signs.
async function gatedSend(ports, journal, opts, ctx, sweep) {
  const v = await verifyIntentFull(ports, ctx.kind, ctx.from, sweep, opts);
  if (v.why) return { why: v.why };
  const gate = opts.chainGate;
  if (!chainGateComplete(gate)) return { why: 'chain_gate_missing' };
  if (sweep.policyDigest !== undefined && sweep.policyDigest !== gate.policyDigest) return { why: 'policy_changed' };
  const resend = sweep.stage === 'sending';
  if (resend) {
    let env; try { env = gate.decodeEnvelope(sweep.envelope); } catch { return { why: 'chain:envelope_record_invalid' }; }
    const rs = await callGate(() => gate.restoreEnvelope(gateIntent(v.d, sweep, false), env));
    if (!rs.ok) return { why: 'chain:' + firstReason(rs) };
    const pf = await callGate(() => gate.preflight(gateIntent(v.d, sweep, true)));
    if (!pf.ok) return { why: 'chain:' + firstReason(pf) };
  } else {
    const pf = await callGate(() => gate.preflight(gateIntent(v.d, sweep, false)));
    if (!pf.ok) return { why: 'chain:' + firstReason(pf) };
    let enc; try { enc = gate.encodeEnvelope(pf.envelope); } catch { return { why: 'chain:envelope_not_encodable' }; }
    let pre; try { pre = String(pf.balances && pf.balances.native); if (!DEC.test(pre)) throw new Error('pre'); } catch { return { why: 'chain:balance_evidence_invalid' }; }
    const saved = { envelope: sweep.envelope, policyDigest: sweep.policyDigest, preNative: sweep.preNative, gateAnchor: sweep.gateAnchor, stage: sweep.stage };
    sweep.envelope = enc; sweep.policyDigest = gate.policyDigest; sweep.preNative = pre; sweep.gateAnchor = { number: pf.anchor && pf.anchor.number, hash: pf.anchor && pf.anchor.hash }; sweep.stage = 'sending';
    if (!durable(journal, opts)) { Object.assign(sweep, saved); for (const k of Object.keys(saved)) if (saved[k] === undefined) delete sweep[k]; return { why: 'journal_not_durable' }; }
  }
  try { await ports.broadcast(sweep.raw); } catch { /* the bytes may already be mined; the receipt decides, not this error */ }
  return { sent: true };
}

async function settleWithRetry(ports, sweep, expect, journal, opts, ctx) {
  delete sweep.awaitingConfirmations;
  let o = await settle(ports, sweep, expect, opts, ctx);
  if (o === 'unknown' && sweep.awaitingConfirmations) return 'unknown'; // already mined: never rebroadcast, only wait
  if (o === 'unknown') {
    // no byte is ever (re)broadcast unless the intent is durably on disk right now and passes every gate
    if (!durable(journal, opts)) return 'unknown';
    const s = await gatedSend(ports, journal, opts, ctx, sweep);
    if (s.why) { sweep.verifyReason = s.why; return 'unverified'; }
    delete sweep.verifyReason;
    o = await settle(ports, sweep, expect, opts, ctx);
  }
  return o;
}

async function cleanOne(w, journal, ports, opts) {
  // A recorded receipt mismatch is never erased by a retry, a zero balance or a zero reconciliation.
  if ((w.sweep && w.sweep.outcome === 'mismatch') || (w.gas && w.gas.sweep && w.gas.sweep.outcome === 'mismatch')) {
    w.state = 'unknown'; ev(w, { ev: 'receipt_mismatch_unresolved' }); durable(journal, opts); return;
  }
  // 1) a recorded, unsettled sweep is settled first, from the recorded intent; it is never signed again
  if (w.sweep && !['swept', 'failed', 'mismatch', 'dispositioned'].includes(w.sweep.outcome)) {
    const o = await settleWithRetry(ports, w.sweep, { from: w.address, to: opts.fundingWallet, amount: w.sweep.amount, nonce: w.sweep.nonce, token: opts.token, chainId: opts.chainId }, journal, opts, { kind: 'erc20', from: w.address });
    if (o === 'unverified') { w.sweep.outcome = 'unverified'; w.state = 'unknown'; ev(w, { ev: 'sweep_unverified_not_sent', hash: w.sweep.hash, reason: w.sweep.verifyReason }); durable(journal, opts); return; }
    if (o === 'unknown') { w.state = 'unknown'; ev(w, { ev: 'sweep_outcome_unknown', hash: w.sweep.hash }); durable(journal, opts); return; }
    w.sweep.outcome = o;
    ev(w, { ev: 'sweep_settled', hash: w.sweep.hash, outcome: o });
    if (o === 'swept') { w.swept = (w.swept || []).concat([{ hash: w.sweep.hash, amount: w.sweep.amount }]); delete w.sweep; }
    else { w.state = o === 'mismatch' ? 'unknown' : 'failed'; durable(journal, opts); if (o === 'mismatch') return; }
    durable(journal, opts);
  }

  // 2) fresh balances every time: a cached 'empty' or 'swept' never closes a wallet by itself
  let tokens, gas;
  try { tokens = await ports.tokenBalance(w.address); gas = await ports.gasBalance(w.address); }
  catch { w.state = 'unknown'; ev(w, { ev: 'balance_read_failed' }); durable(journal, opts); return; }

  if (await ports.isContract(w.address)) {
    if (tokens > 0n) { w.state = 'locked_contract'; w.residual = { tokens: tokens.toString(), gas: gas.toString() }; ev(w, { ev: 'contract_balance_declared', tokens: tokens.toString() }); }
    else { w.state = 'empty'; delete w.residual; }
    durable(journal, opts); return;
  }
  if (tokens === 0n) { w.state = w.swept && w.swept.length ? 'swept' : 'empty'; delete w.residual; durable(journal, opts); return; }
  if (tokens <= opts.dust) { w.state = 'dust_accepted'; w.residual = { tokens: tokens.toString() }; ev(w, { ev: 'dust_accepted', tokens: tokens.toString() }); durable(journal, opts); return; }
  if (!(await ports.controls(w))) { w.state = 'signer_lost'; w.residual = { tokens: tokens.toString(), gas: gas.toString() }; ev(w, { ev: 'signer_lost', tokens: tokens.toString() }); durable(journal, opts); return; }

  const need = (await ports.gasCostEstimate()) * BigInt(opts.gasReserveMultiple);
  if (gas < need) { w.state = 'needs_gas'; w.residual = { tokens: tokens.toString(), gas: gas.toString(), gasNeeded: need.toString() }; ev(w, { ev: 'insufficient_gas', have: gas.toString(), need: need.toString() }); durable(journal, opts); return; }

  // 3) intent, hash and bytes are durable BEFORE the first broadcast; if that write fails, nothing is sent
  const nonce = await ports.nonceOf(w.address);
  const prepared = normalizePrepared(await ports.prepareSweep(w, opts.fundingWallet, tokens, nonce));
  if (!prepared) { w.state = 'unknown'; ev(w, { ev: 'prepare_output_invalid_not_sent' }); durable(journal, opts); return; }
  w.sweep = { hash: prepared.hash, raw: prepared.raw, amount: tokens.toString(), nonce, outcome: 'prepared' };
  ev(w, { ev: 'sweep_prepared', hash: prepared.hash, amount: tokens.toString(), nonce });
  if (!durable(journal, opts)) { w.state = 'unknown'; ev(w, { ev: 'intent_not_durable_not_sent' }); return; }
  const sent = await gatedSend(ports, journal, opts, { kind: 'erc20', from: w.address }, w.sweep);
  if (sent.why) { w.sweep.outcome = 'unverified'; w.sweep.verifyReason = sent.why; w.state = 'unknown'; ev(w, { ev: 'sweep_unverified_not_sent', hash: prepared.hash, reason: sent.why }); durable(journal, opts); return; }
  const o = await settleWithRetry(ports, w.sweep, { from: w.address, to: opts.fundingWallet, amount: w.sweep.amount, nonce, token: opts.token, chainId: opts.chainId }, journal, opts, { kind: 'erc20', from: w.address });
  if (o === 'unverified') { w.sweep.outcome = 'unverified'; w.state = 'unknown'; ev(w, { ev: 'sweep_unverified_not_sent', hash: prepared.hash, reason: w.sweep.verifyReason }); durable(journal, opts); return; }
  if (o === 'unknown') { w.sweep.outcome = 'unknown'; w.state = 'unknown'; ev(w, { ev: 'sweep_outcome_unknown', hash: prepared.hash }); durable(journal, opts); return; }
  w.sweep.outcome = o;
  ev(w, { ev: 'sweep_settled', hash: prepared.hash, outcome: o });
  if (o === 'swept') { w.state = 'swept'; w.swept = (w.swept || []).concat([{ hash: prepared.hash, amount: w.sweep.amount }]); delete w.sweep; }
  else w.state = o === 'mismatch' ? 'unknown' : 'failed';
  durable(journal, opts);
}

async function gasOne(w, journal, ports, opts) {
  if (w.gas && w.gas.sweep && w.gas.sweep.outcome === 'mismatch') { w.gas.state = 'unknown'; ev(w, { ev: 'gas_receipt_mismatch_unresolved' }); durable(journal, opts); return; }
  if (!['swept', 'empty', 'dust_accepted'].includes(w.state)) return;
  w.gas = w.gas || { state: 'pending' };
  const g = w.gas;
  if (g.sweep && !['swept', 'failed', 'mismatch', 'dispositioned'].includes(g.sweep.outcome)) {
    const o = await settleWithRetry(ports, g.sweep, { from: w.address, to: opts.fundingWallet, amount: g.sweep.amount, nonce: g.sweep.nonce, chainId: opts.chainId }, journal, opts, { kind: 'native', from: w.address });
    if (o === 'unverified') { g.sweep.outcome = 'unverified'; g.state = 'unknown'; ev(w, { ev: 'gas_return_unverified_not_sent', hash: g.sweep.hash, reason: g.sweep.verifyReason }); durable(journal, opts); return; }
    if (o === 'unknown') { g.state = 'unknown'; ev(w, { ev: 'gas_return_outcome_unknown', hash: g.sweep.hash }); durable(journal, opts); return; }
    g.sweep.outcome = o;
    ev(w, { ev: 'gas_return_settled', hash: g.sweep.hash, outcome: o });
    if (o === 'swept') { g.state = 'returned'; g.returned = g.sweep.amount; delete g.sweep; durable(journal, opts); return; }
    g.state = o === 'mismatch' ? 'unknown' : 'failed';
    durable(journal, opts); if (o === 'mismatch') return;
  }
  let have;
  try { have = await ports.gasBalance(w.address); } catch { g.state = 'unknown'; ev(w, { ev: 'gas_read_failed' }); durable(journal, opts); return; }
  if (have === 0n) { if (g.state !== 'returned') { g.state = 'returned'; g.returned = g.returned || '0'; } durable(journal, opts); return; } // nothing left to return
  const fee = await ports.gasSweepFee();
  const amount = have - fee;
  if (amount <= opts.gasDust) { g.state = 'residual'; g.residual = have.toString(); ev(w, { ev: 'gas_residual', wei: have.toString() }); durable(journal, opts); return; }
  if (!(await ports.controls(w))) { g.state = 'signer_lost'; g.residual = have.toString(); ev(w, { ev: 'gas_signer_lost', wei: have.toString() }); durable(journal, opts); return; }
  const nonce = await ports.nonceOf(w.address);
  const prepared = normalizePrepared(await ports.prepareGasSweep(w, opts.fundingWallet, amount, nonce));
  if (!prepared) { g.state = 'unknown'; ev(w, { ev: 'gas_prepare_output_invalid_not_sent' }); durable(journal, opts); return; }
  g.sweep = { hash: prepared.hash, raw: prepared.raw, amount: amount.toString(), nonce, outcome: 'prepared' };
  ev(w, { ev: 'gas_return_prepared', hash: prepared.hash, amount: amount.toString(), nonce });
  if (!durable(journal, opts)) { g.state = 'unknown'; ev(w, { ev: 'gas_intent_not_durable_not_sent' }); return; }
  const sentG = await gatedSend(ports, journal, opts, { kind: 'native', from: w.address }, g.sweep);
  if (sentG.why) { g.sweep.outcome = 'unverified'; g.sweep.verifyReason = sentG.why; g.state = 'unknown'; ev(w, { ev: 'gas_return_unverified_not_sent', hash: prepared.hash, reason: sentG.why }); durable(journal, opts); return; }
  const o = await settleWithRetry(ports, g.sweep, { from: w.address, to: opts.fundingWallet, amount: g.sweep.amount, nonce, chainId: opts.chainId }, journal, opts, { kind: 'native', from: w.address });
  if (o === 'unverified') { g.sweep.outcome = 'unverified'; g.state = 'unknown'; ev(w, { ev: 'gas_return_unverified_not_sent', hash: prepared.hash, reason: g.sweep.verifyReason }); durable(journal, opts); return; }
  if (o === 'unknown') { g.sweep.outcome = 'unknown'; g.state = 'unknown'; ev(w, { ev: 'gas_return_outcome_unknown', hash: prepared.hash }); durable(journal, opts); return; }
  g.sweep.outcome = o;
  ev(w, { ev: 'gas_return_settled', hash: prepared.hash, outcome: o });
  if (o === 'swept') { g.state = 'returned'; g.returned = g.sweep.amount; delete g.sweep; } else g.state = o === 'mismatch' ? 'unknown' : 'failed';
  durable(journal, opts);
}

// Whole run. Safe to call again after any interruption. `skipGas` is allowed but recorded: a run with the gas
// phase skipped can never close.
export async function runCleanup(journal, ports, options = {}) {
  const opts = resolveOptions(journal, options);
  for (const w of Object.values(journal.wallets)) {
    try { await cleanOne(w, journal, ports, opts); }
    catch (e) { w.state = 'unknown'; ev(w, { ev: 'cleanup_error', code: code(e) }); durable(journal, opts); } // w.sweep (hash, bytes, nonce) is kept
  }
  if (options.skipGas) journal.gasPhase = 'skipped';
  else {
    for (const w of Object.values(journal.wallets)) {
      try { await gasOne(w, journal, ports, opts); }
      catch (e) { w.gas = { ...(w.gas || {}), state: 'unknown' }; ev(w, { ev: 'gas_cleanup_error', code: code(e) }); durable(journal, opts); } // g.sweep is kept
    }
    journal.gasPhase = 'complete';
  }
  return finalize(journal, options);
}

function walletClass(w, approved) {
  if (emptiedStates.has(w.state)) return { open: false, exception: null };
  if (w.state === 'dust_accepted') return { open: false, exception: 'dust' };
  if (w.state === 'locked_contract') return approved.has(String(w.address).toLowerCase()) ? { open: false, exception: 'approved_contract' } : { open: true, exception: null };
  return { open: true, exception: null };
}
function gasClass(w) {
  if (!w.gas || w.gas.state === 'returned') return { open: false, exception: null };
  if (w.gas.state === 'residual') return { open: false, exception: 'gas_residual' };
  return { open: true, exception: null }; // pending, signer_lost, failed, unknown
}

function fingerprint(journal) {
  return JSON.stringify(Object.values(journal.wallets).map(w => [w.id, w.state, (w.swept || []).map(x => [x.hash, x.amount]), w.sweep ? [w.sweep.hash, w.sweep.outcome] : null, w.residual || null, w.gas ? [w.gas.state, w.gas.returned || null, w.gas.residual || null, w.gas.sweep ? [w.gas.sweep.hash, w.gas.sweep.outcome] : null] : null]));
}

// An explicit, evidence-backed disposition is the only way to clear an unresolved receipt mismatch.
export function resolveMismatch(journal, id, disposition, options = {}) {
  resolveOptions(journal, options);
  const w = journal.wallets[id];
  if (!w || !disposition || !disposition.evidence || !disposition.decidedBy) throw new Error('a mismatch needs a wallet id and a disposition with evidence and decidedBy');
  const hit = (w.sweep && w.sweep.outcome === 'mismatch') ? w.sweep : (w.gas && w.gas.sweep && w.gas.sweep.outcome === 'mismatch') ? w.gas.sweep : null;
  if (!hit) throw new Error('no unresolved mismatch for this wallet');
  hit.outcome = 'dispositioned';
  hit.disposition = { evidence: String(disposition.evidence).slice(0, 200), decidedBy: String(disposition.decidedBy).slice(0, 60) };
  ev(w, { ev: 'mismatch_dispositioned', hash: hit.hash });
  journal.reconciliation = null;
  durable(journal, options);
}

export function finalize(journal, options = {}) {
  const approved = new Set([...(options.approvedContracts || [])].map(a => String(a).toLowerCase()));
  const ws = Object.values(journal.wallets);
  const counts = {}; for (const w of ws) counts[w.state] = (counts[w.state] || 0) + 1;
  const open = []; const exceptions = [];
  for (const w of ws) {
    const a = walletClass(w, approved); const g = gasClass(w);
    if (a.open || g.open) open.push({ id: w.id, address: w.address, state: w.state, gas: w.gas ? w.gas.state : null, residual: w.residual || null });
    if (a.exception) exceptions.push({ id: w.id, state: w.state, residual: w.residual || null });
    if (g.exception) exceptions.push({ id: w.id, state: w.state, gas: w.gas.state, residual: w.gas.residual || null });
  }
  journal.summary = { counts, openWallets: open, exceptions };
  let rec = journal.reconciliation;
  const fp = fingerprint(journal);
  if (rec && rec.fingerprint !== fp) { // includes a legacy reconciliation that has no fingerprint
    // the state changed after this reconciliation: it no longer describes the run
    (journal.staleReconciliations = journal.staleReconciliations || []).push(rec);
    journal.reconciliation = null; rec = null;
  }
  if (open.length > 0 || journal.gasPhase !== 'complete' || journal.persistence.failed) journal.status = 'failed_cleanup';
  else if (!rec) journal.status = 'pending_reconciliation';
  else if (!rec.matches) journal.status = 'failed_cleanup'; // sticky: only a later matching reconciliation can change this
  else journal.status = exceptions.length === 0 ? 'closed' : 'closed_with_exceptions';
  if (typeof options.save === 'function' && !durable(journal, { save: options.save })) {
    // The terminal status must be durable before a caller can see it. A failed final save is never a success.
    journal.status = 'failed_cleanup';
  }
  return journal;
}

// The funding wallet's gain must equal the sum of settled token sweeps. The result is stored and persisted; a
// mismatch keeps the run failed until a later reconciliation (with fresh balances) matches.
export function reconcile(journal, fundingBefore, fundingAfter, options = {}) {
  resolveOptions(journal, options); // persistence is required
  const swept = Object.values(journal.wallets).flatMap(w => w.swept || []).reduce((a, s) => a + BigInt(s.amount), 0n);
  const gain = BigInt(fundingAfter) - BigInt(fundingBefore);
  const result = { swept: swept.toString(), fundingGain: gain.toString(), matches: gain === swept, fingerprint: fingerprint(journal) };
  journal.reconciliation = result;
  (journal.reconciliationHistory = journal.reconciliationHistory || []).push(result);
  finalize(journal, options);
  return result;
}

// Fresh terminal check: re-read every token balance. Anything above the approved dust that is not an approved
// contract reopens that wallet, whatever the cached states say (a later deposit is caught here).
export async function terminalVerify(journal, ports, options = {}) {
  const opts = resolveOptions(journal, options);
  const found = [];
  for (const w of Object.values(journal.wallets)) {
    let t;
    try { t = await ports.tokenBalance(w.address); } catch { w.state = 'unknown'; found.push({ id: w.id, read: 'failed' }); continue; }
    const approved = (await ports.isContract(w.address)) && opts.approvedContracts.has(String(w.address).toLowerCase());
    if (t > opts.dust && !approved) {
      // reopen a wallet that was counted as done; an explicit open reason (lost signer, no gas, failed, unknown) is kept
      if (['empty', 'swept', 'dust_accepted', 'locked_contract', 'pending'].includes(w.state)) w.state = 'pending';
      found.push({ id: w.id, tokens: t.toString() });
    }
  }
  journal.terminalCheck = { found };
  if (found.length) { journal.gasPhase = 'not_run'; journal.reconciliation = null; }
  finalize(journal, options);
  return found;
}
