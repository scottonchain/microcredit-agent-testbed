// Scenario-wallet lifecycle: control check before a run, terminal cleanup back to the funding wallet.
//
// Pure decision and journal logic with injected ports. This module imports no network library, holds no
// key and never signs: a runner supplies `ports` that wrap its own signer. It records only public
// addresses, roles, amounts and transaction hashes.
//
// Ports (all async):
//   controls(wallet)                     -> true | false   the orchestrator holds this signer (no signing to prove it)
//   tokenBalance(address)                -> bigint         test token, base units
//   gasBalance(address)                  -> bigint         native token, wei
//   gasCostEstimate()                    -> bigint         wei needed for one token transfer
//   nonceOf(address)                     -> number         pending transaction count
//   prepareSweep(wallet, to, amount, nonce) -> { hash, raw }   signs inside the runner; nothing is sent
//   broadcast(raw)                       -> void           sends the identical signed bytes (idempotent by hash)
//   receipt(hash)                        -> { status: 1 | 0 } | null
//   isContract(address)                  -> boolean        a contract balance is a declared exception
//   gasSweepFee()                        -> bigint         wei kept back to pay for the gas-return transaction
//   prepareGasSweep(wallet, to, amount, nonce) -> { hash, raw }  signs the return of recoverable native gas
//
// States per wallet: pending | empty | swept | needs_gas | signer_lost | locked_contract | dust_accepted |
//                    failed | unknown. Only `closedStates` count as closed. Anything else keeps the run OPEN.

import fs from 'node:fs';

export const closedStates = new Set(['empty', 'swept', 'dust_accepted', 'locked_contract']);
export const exceptionStates = new Set(['needs_gas', 'signer_lost', 'failed', 'unknown']);

export function newJournal(runId, fundingWallet, wallets, now) {
  if (!/^0x[0-9a-fA-F]{40}$/.test(fundingWallet)) throw new Error('funding wallet must be a public address');
  const seen = new Set();
  for (const w of wallets) {
    if (!/^0x[0-9a-fA-F]{40}$/.test(w.address)) throw new Error(`bad address for ${w.id}`);
    const k = w.address.toLowerCase();
    if (seen.has(k)) throw new Error(`duplicate wallet address ${w.address}`);
    if (k === fundingWallet.toLowerCase()) throw new Error('the funding wallet is not a scenario wallet');
    seen.add(k);
  }
  return {
    runId, fundingWallet, createdAt: now, status: 'open', control: null,
    wallets: Object.fromEntries(wallets.map(w => [w.id, { id: w.id, address: w.address, role: w.role || 'scenario', state: 'pending', events: [] }])),
  };
}

// Journals are written before the effect they describe, so a crash never loses an intent.
export function saveJournal(path, journal) {
  const tmp = path + '.tmp';
  const fd = fs.openSync(tmp, 'w');
  try { fs.writeSync(fd, JSON.stringify(journal, null, 1)); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  fs.renameSync(tmp, path);
}
export function loadJournal(path) { return JSON.parse(fs.readFileSync(path, 'utf8')); }

// Before a run: does the orchestrator control every signer? Records booleans and public addresses only.
export async function verifyControl(journal, ports, { save = () => {} } = {}) {
  const missing = [];
  for (const w of Object.values(journal.wallets)) {
    let ok = false;
    try { ok = (await ports.controls(w)) === true; } catch { ok = false; }
    if (!ok) { w.state = 'signer_lost'; w.events.push({ ev: 'control_check_failed' }); missing.push(w.id); }
    else w.events.push({ ev: 'control_ok' });
  }
  journal.control = { checked: Object.keys(journal.wallets).length, missing };
  save(journal);
  return { ok: missing.length === 0, missing };
}

function log(w, ev) { w.events.push(ev); }

async function settleSweep(w, ports, expected) {
  // The recorded transaction decides, never a guess. Returns 'swept' | 'failed' | 'unknown'.
  let r = null;
  try { r = await ports.receipt(expected.hash); } catch { return 'unknown'; }
  if (r === null) return 'unknown';
  return r.status === 1 ? 'swept' : 'failed';
}

// One wallet, resumable and idempotent. `opts`: { fundingWallet, dust, gasReserveMultiple, save, tries }
async function cleanOne(w, journal, ports, opts) {
  if (closedStates.has(w.state)) return;
  const sweep = w.sweep || null;

  // A recorded sweep that is not settled is checked before anything else; it is never re-signed.
  if (sweep && !['swept', 'failed'].includes(sweep.outcome)) {
    const outcome = await settleSweep(w, ports, sweep);
    if (outcome === 'unknown') {
      // rebroadcast the identical bytes (same hash), then look once more
      try { await ports.broadcast(sweep.raw); } catch { /* the bytes may already be mined */ }
      const again = await settleSweep(w, ports, sweep);
      if (again === 'unknown') { w.state = 'unknown'; log(w, { ev: 'sweep_outcome_unknown', hash: sweep.hash }); opts.save(journal); return; }
      sweep.outcome = again;
    } else sweep.outcome = outcome;
    log(w, { ev: 'sweep_settled', hash: sweep.hash, outcome: sweep.outcome });
    if (sweep.outcome === 'swept') { w.state = 'swept'; delete w.sweep; w.swept = (w.swept || []).concat([{ hash: sweep.hash, amount: sweep.amount }]); }
    else { w.state = 'failed'; }
    opts.save(journal);
    if (w.state === 'swept' || w.state === 'failed') return;
  }

  let tokens, gas;
  try { tokens = await ports.tokenBalance(w.address); gas = await ports.gasBalance(w.address); }
  catch { w.state = 'unknown'; log(w, { ev: 'balance_read_failed' }); opts.save(journal); return; }

  if (await ports.isContract(w.address)) {
    if (tokens > 0n) { w.state = 'locked_contract'; w.residual = { tokens: tokens.toString(), gas: gas.toString() }; log(w, { ev: 'contract_balance_declared', tokens: tokens.toString() }); }
    else w.state = 'empty';
    opts.save(journal); return;
  }

  if (tokens === 0n) { w.state = 'empty'; opts.save(journal); return; }
  if (tokens <= opts.dust) { w.state = 'dust_accepted'; w.residual = { tokens: tokens.toString() }; log(w, { ev: 'dust_accepted', tokens: tokens.toString() }); opts.save(journal); return; }

  if (!(await ports.controls(w))) { w.state = 'signer_lost'; w.residual = { tokens: tokens.toString(), gas: gas.toString() }; log(w, { ev: 'signer_lost', tokens: tokens.toString() }); opts.save(journal); return; }

  const need = (await ports.gasCostEstimate()) * BigInt(opts.gasReserveMultiple);
  if (gas < need) { w.state = 'needs_gas'; w.residual = { tokens: tokens.toString(), gas: gas.toString(), gasNeeded: need.toString() }; log(w, { ev: 'insufficient_gas', have: gas.toString(), need: need.toString() }); opts.save(journal); return; }

  const nonce = await ports.nonceOf(w.address);
  const prepared = await ports.prepareSweep(w, opts.fundingWallet, tokens, nonce);
  // intent, hash and bytes are durable before the first broadcast
  w.sweep = { hash: prepared.hash, raw: prepared.raw, amount: tokens.toString(), nonce, outcome: 'prepared' };
  log(w, { ev: 'sweep_prepared', hash: prepared.hash, amount: tokens.toString(), nonce });
  opts.save(journal);
  try { await ports.broadcast(prepared.raw); } catch { /* settled by the receipt check below, never by this error */ }
  const outcome = await settleSweep(w, ports, w.sweep);
  if (outcome === 'unknown') {
    // a timeout is not a failure: the same bytes are rebroadcast once, then the wallet stays unknown
    try { await ports.broadcast(prepared.raw); } catch { /* ignore */ }
    const again = await settleSweep(w, ports, w.sweep);
    if (again === 'unknown') { w.sweep.outcome = 'unknown'; w.state = 'unknown'; log(w, { ev: 'sweep_outcome_unknown', hash: prepared.hash }); opts.save(journal); return; }
    w.sweep.outcome = again;
  } else w.sweep.outcome = outcome;
  log(w, { ev: 'sweep_settled', hash: prepared.hash, outcome: w.sweep.outcome });
  if (w.sweep.outcome === 'swept') { w.state = 'swept'; w.swept = (w.swept || []).concat([{ hash: prepared.hash, amount: w.sweep.amount }]); delete w.sweep; }
  else { w.state = 'failed'; }
  opts.save(journal);
}


// Recoverable gas goes back last, after the tokens are settled. A residual below gasDust, or from a wallet
// whose signer is gone, is a declared exception and does not block closure; an UNKNOWN gas-return outcome does.
async function gasOne(w, ports, opts, journal) {
  if (!['swept', 'empty', 'dust_accepted'].includes(w.state)) return;
  if (w.gas && ['returned', 'residual', 'signer_lost'].includes(w.gas.state)) return;
  w.gas = w.gas || { state: 'pending' };
  const g = w.gas;
  if (g.sweep && !['swept', 'failed'].includes(g.sweep.outcome)) {
    let o = await settleSweep(w, ports, g.sweep);
    if (o === 'unknown') { try { await ports.broadcast(g.sweep.raw); } catch { /* ignore */ } o = await settleSweep(w, ports, g.sweep); }
    if (o === 'unknown') { g.state = 'unknown'; log(w, { ev: 'gas_return_outcome_unknown', hash: g.sweep.hash }); opts.save(journal); return; }
    g.sweep.outcome = o;
    log(w, { ev: 'gas_return_settled', hash: g.sweep.hash, outcome: o });
    if (o === 'swept') { g.state = 'returned'; g.returned = g.sweep.amount; delete g.sweep; opts.save(journal); return; }
    g.state = 'failed';
  }
  let have;
  try { have = await ports.gasBalance(w.address); } catch { g.state = 'unknown'; log(w, { ev: 'gas_read_failed' }); opts.save(journal); return; }
  const fee = await ports.gasSweepFee();
  const amount = have - fee;
  if (amount <= opts.gasDust) { g.state = 'residual'; g.residual = have.toString(); log(w, { ev: 'gas_residual_accepted', wei: have.toString() }); opts.save(journal); return; }
  if (!(await ports.controls(w))) { g.state = 'signer_lost'; g.residual = have.toString(); log(w, { ev: 'gas_signer_lost', wei: have.toString() }); opts.save(journal); return; }
  const nonce = await ports.nonceOf(w.address);
  const prepared = await ports.prepareGasSweep(w, opts.fundingWallet, amount, nonce);
  g.sweep = { hash: prepared.hash, raw: prepared.raw, amount: amount.toString(), nonce, outcome: 'prepared' };
  log(w, { ev: 'gas_return_prepared', hash: prepared.hash, amount: amount.toString(), nonce });
  opts.save(journal);
  try { await ports.broadcast(prepared.raw); } catch { /* settled by receipt */ }
  let o = await settleSweep(w, ports, g.sweep);
  if (o === 'unknown') { try { await ports.broadcast(prepared.raw); } catch { /* ignore */ } o = await settleSweep(w, ports, g.sweep); }
  if (o === 'unknown') { g.sweep.outcome = 'unknown'; g.state = 'unknown'; log(w, { ev: 'gas_return_outcome_unknown', hash: prepared.hash }); opts.save(journal); return; }
  g.sweep.outcome = o;
  log(w, { ev: 'gas_return_settled', hash: prepared.hash, outcome: o });
  if (o === 'swept') { g.state = 'returned'; g.returned = g.sweep.amount; delete g.sweep; } else g.state = 'failed';
  opts.save(journal);
}

// Whole run. Safe to call again after any interruption: it reads the journal, settles recorded sweeps first,
// and sweeps only what is still there. It never reports `closed` while any wallet is outside closedStates.
export async function runCleanup(journal, ports, options = {}) {
  const opts = { dust: 0n, gasDust: 0n, gasReserveMultiple: 2, save: () => {}, ...options, fundingWallet: journal.fundingWallet };
  for (const w of Object.values(journal.wallets)) {
    try { await cleanOne(w, journal, ports, opts); }
    catch (e) { w.state = 'unknown'; log(w, { ev: 'cleanup_error', message: String(e && e.message || e).slice(0, 120) }); opts.save(journal); }
  }
  if (!options.skipGas) {
    for (const w of Object.values(journal.wallets)) {
      try { await gasOne(w, ports, opts, journal); }
      catch (e) { w.gas = { state: 'unknown' }; log(w, { ev: 'gas_cleanup_error', message: String(e && e.message || e).slice(0, 120) }); opts.save(journal); }
    }
  }
  return finalize(journal, opts);
}

export function finalize(journal, opts = {}) {
  const ws = Object.values(journal.wallets);
  const gasBlocking = w => w.gas && ['unknown', 'failed', 'pending'].includes(w.gas.state);
  const open = ws.filter(w => !closedStates.has(w.state) || gasBlocking(w));
  const counts = {};
  for (const w of ws) counts[w.state] = (counts[w.state] || 0) + 1;
  journal.status = open.length === 0 ? 'closed' : 'failed_cleanup';
  journal.summary = {
    counts,
    openWallets: open.map(w => ({ id: w.id, address: w.address, state: w.state, gas: w.gas ? w.gas.state : null, residual: w.residual || null })),
    exceptions: ws.filter(w => ['locked_contract', 'dust_accepted'].includes(w.state) || (w.gas && ['residual', 'signer_lost'].includes(w.gas.state))).map(w => ({ id: w.id, state: w.state, gas: w.gas ? w.gas.state : null, residual: w.residual || (w.gas && w.gas.residual) || null })),
  };
  if (opts.save) opts.save(journal);
  return journal;
}

// Reconcile after the sweeps: the funding wallet's gain must equal the sum of settled sweeps. A mismatch
// keeps the run open; it is never explained away.
export function reconcile(journal, fundingBefore, fundingAfter) {
  const swept = Object.values(journal.wallets).flatMap(w => w.swept || []).reduce((a, s) => a + BigInt(s.amount), 0n);
  const gain = BigInt(fundingAfter) - BigInt(fundingBefore);
  journal.reconciliation = { swept: swept.toString(), fundingGain: gain.toString(), matches: gain === swept };
  if (!journal.reconciliation.matches) journal.status = 'failed_cleanup';
  return journal.reconciliation;
}
