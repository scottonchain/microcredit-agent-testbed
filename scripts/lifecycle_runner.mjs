// Runner adapter for the scenario-wallet lifecycle. DISABLED BY DEFAULT.
//
// This is the only place that decides WHEN the lifecycle component runs around a scenario. It imports no
// network library, holds no key and signs nothing: a caller supplies `ports` (control, balances, prepare,
// broadcast, receipt) that wrap its own signer. With `enabled` not exactly true, `runWithLifecycle` returns
// { status: 'disabled' } without calling a port, touching a file or installing a handler, so a runner that
// routes through it behaves exactly as before until it is turned on.
//
// Order of events when enabled:
//   1. validate the roster (unique ids and addresses) and take a single-owner lock next to the journal;
//   2. if a journal already exists, RESUME: validate it, never fund again, never run the scenario again, and
//      go straight to terminal cleanup from the last durable intent;
//   3. otherwise verify control of EVERY scenario signer before any funds are placed; one missing signer
//      refuses funding (status refused_control) and the inventory is kept;
//   4. record phase 'funding' durably, then fund under supervision (timeout, abort signal); a failure or a
//      crash here is treated as funded; if the funding call has not settled after the quiesce window the
//      outcome is UNCERTAIN: no cleanup, no closure, the lock is kept (status 'unquiesced');
//   5. run the scenario with a timeout and an abort signal (SIGINT/SIGTERM abort it); after a timeout or abort
//      the scenario must actually settle (quiesce) before cleanup starts; if it does not, same as above;
//   6. ALWAYS enter terminal cleanup exactly once: sweep tokens, return gas, re-read every balance, then
//      reconcile the funding wallet's gain against what settled receipts say was swept (every port call is
//      bounded by a timeout; a hung call leaves that wallet unknown, never closed);
//   7. report. Only a closed lifecycle with a successful scenario is success; everything else is non-zero.
//
// The journal holds signed raw transactions. It stays at `journalPath` (mode 0600). Only `publicReport` and
// `checkpoint` may leave the process.

import fs from 'node:fs';
import crypto from 'node:crypto';
import nodePath from 'node:path';
import {
  newJournal, saveJournal, loadJournal, publicView, verifyControl, runCleanup, finalize, reconcile, terminalVerify,
} from './wallet_lifecycle.mjs';

export const ENV_FLAG = 'OMNEQUA_WALLET_LIFECYCLE';

// The ONLY rejection from a prepare port that proves no signature was produced. A port throws it only when it
// can show, independently of any exception text, that signing never began (for example it refused before touching
// the signer). Any other rejection or timeout leaves the durable in-flight marker in place: a generic error does
// not show that signing did not happen (it may have completed before an output or transport failure).
export class PrepareNotStarted extends Error {}
export function lifecycleEnabled(env = process.env) { return env[ENV_FLAG] === '1'; }

const PORTS = ['controls', 'tokenBalance', 'gasBalance', 'gasCostEstimate', 'gasSweepFee', 'nonceOf', 'isContract', 'prepareSweep', 'prepareGasSweep', 'broadcast', 'receipt'];
const CLOSED = new Set(['closed', 'closed_with_exceptions']);

// What may leave the process: no raw bytes, no error text.
export function publicReport(journal) {
  const v = publicView(journal);
  if (v.runner && Array.isArray(v.runner.orphans)) v.runner.orphans = v.runner.orphans.map(o => ({ kind: o.kind, walletId: o.walletId, hash: o.hash, nonce: o.nonce, amount: o.amount }));
  return v;
}

// The narrow interface for a coordinator: unresolved intents and persistence state, nothing secret.
export function checkpoint(journal) {
  const unresolved = [];
  for (const w of Object.values(journal.wallets)) {
    const tokenOpen = !(w.state === 'empty' || w.state === 'swept' || w.state === 'dust_accepted');
    const gasOpen = !(!w.gas || w.gas.state === 'returned' || w.gas.state === 'residual');
    if (tokenOpen || gasOpen || w.sweep || (w.gas && w.gas.sweep)) {
      unresolved.push({
        id: w.id, state: w.state, gas: w.gas ? w.gas.state : null,
        sweepHash: w.sweep ? w.sweep.hash : null, sweepOutcome: w.sweep ? w.sweep.outcome : null,
        gasSweepHash: w.gas && w.gas.sweep ? w.gas.sweep.hash : null, gasSweepOutcome: w.gas && w.gas.sweep ? w.gas.sweep.outcome : null,
      });
    }
  }
  return {
    runId: journal.runId, status: journal.status, gasPhase: journal.gasPhase,
    persistenceFailed: !!(journal.persistence && journal.persistence.failed),
    orphanedIntents: journal.runner && Array.isArray(journal.runner.orphans) ? journal.runner.orphans.length : 0,
    prepareInFlight: !!(journal.runner && journal.runner.prepareInFlight),
    phase: journal.runner ? journal.runner.phase : null,
    scenario: journal.runner ? journal.runner.scenario || null : null,
    reconciliation: journal.reconciliation ? { matches: journal.reconciliation.matches } : null,
    unresolved,
  };
}

export function exitCodeFor(result) {
  if (result.status === 'disabled') return 0;
  if (result.interrupted) return result.interrupted === 'SIGINT' ? 130 : 143;
  if (result.ok) return 0;
  return result.acceptedWithExceptions ? 3 : 2; // 3: closed, but only with named, approved residuals
}

function pidAlive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; }
}

// Single owner per journal. The lock is PUBLISHED COMPLETE: its content (pid and a random token) is written
// and fsynced to a private temp file and then hard-linked into place, which is atomic and fails if a lock
// exists, so no other entrant ever sees a half-written lock. An unreadable or malformed lock fails closed.
// A lock whose recorded pid is gone is reclaimed under a short-lived guard, and only if it is still the very
// lock that was read. Release removes the lock only if it still carries our token.
function readLock(lockPath) {
  try { const o = JSON.parse(fs.readFileSync(lockPath, 'utf8')); return Number.isInteger(o.pid) && typeof o.token === 'string' ? o : { bad: true }; }
  catch (e) { return e.code === 'ENOENT' ? null : { bad: true }; }
}
function publishLock(lockPath, token) {
  const tmp = `${lockPath}.${token}.tmp`;
  const fd = fs.openSync(tmp, 'wx', 0o600);
  try { fs.writeSync(fd, JSON.stringify({ pid: process.pid, token })); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
  try { fs.linkSync(tmp, lockPath); return true; }
  catch (e) { if (e.code === 'EEXIST') return false; throw e; }
  finally { try { fs.unlinkSync(tmp); } catch { /* gone */ } }
}
function takeLock(lockPath, token) {
  if (publishLock(lockPath, token)) return true;
  const cur = readLock(lockPath);
  if (cur === null) return publishLock(lockPath, token);      // vanished between the two calls: one more try
  if (cur.bad) return false;                                    // malformed or partial: fail closed
  if (pidAlive(cur.pid)) return false;                          // live owner (including this process)
  // the recorded owner is gone: reclaim, serialized by a guard that only one entrant can create
  const guard = lockPath + '.reclaim';
  let gfd;
  try { gfd = fs.openSync(guard, 'wx', 0o600); }
  catch (e) {
    if (e.code !== 'EEXIST') throw e;
    const g = readLock(guard);                                   // a guard left by a dead process may be cleared; anything else fails closed
    if (g && !g.bad && !pidAlive(g.pid)) { try { fs.unlinkSync(guard); } catch { /* raced */ } }
    return false;
  }
  try {
    fs.writeSync(gfd, JSON.stringify({ pid: process.pid, token }));
    const again = readLock(lockPath);
    if (!again || again.bad || again.token !== cur.token) return false; // replaced meanwhile: not ours to remove
    fs.unlinkSync(lockPath);
    return publishLock(lockPath, token);
  } finally {
    try { fs.closeSync(gfd); } catch { /* closed */ }
    try { fs.unlinkSync(guard); } catch { /* gone */ }
  }
}
function dropLock(lockPath, token) {
  const cur = readLock(lockPath);
  if (cur && !cur.bad && cur.token === token) { try { fs.unlinkSync(lockPath); } catch { /* gone */ } }
}

const addrRe = /^0x[0-9a-fA-F]{40}$/;
function checkConfig(cfg) {
  const problems = [];
  if (!cfg.runId) problems.push('runId');
  if (!addrRe.test(cfg.fundingWallet || '')) problems.push('fundingWallet');
  if (!Array.isArray(cfg.roster) || cfg.roster.length === 0) problems.push('roster');
  if (!Number.isInteger(cfg.chainId)) problems.push('chainId');
  if (!addrRe.test(cfg.token || '')) problems.push('token');
  if (!cfg.journalPath || !nodePath.isAbsolute(cfg.journalPath)) problems.push('journalPath must be absolute');
  else if (/(^|[\\/])evidence([\\/]|$)/.test(cfg.journalPath)) problems.push('journalPath must be outside the evidence folder');
  if (typeof cfg.fund !== 'function') problems.push('fund');
  if (typeof cfg.scenario !== 'function') problems.push('scenario');
  if (!cfg.ports || PORTS.some(p => typeof cfg.ports[p] !== 'function')) problems.push('ports');
  return problems;
}

// Everything a resumed run must agree with before it may touch a port: the exact roster, the funding wallet,
// the chain and token, and the recovery policy that decides what counts as done.
function identityOf(cfg) {
  const low = a => String(a).toLowerCase();
  return JSON.stringify({
    v: 1,
    roster: cfg.roster.map(w => [String(w.id), low(w.address)]).sort((a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0)),
    funding: low(cfg.fundingWallet), chainId: cfg.chainId, token: low(cfg.token),
    policy: { dust: String(cfg.dust ?? 0n), gasDust: String(cfg.gasDust ?? 0n), gasReserveMultiple: cfg.gasReserveMultiple ?? 2, approved: [...(cfg.approvedContracts || [])].map(low).sort() },
  });
}

// Every port call is bounded, and every EFFECT call (prepare, broadcast) is also TRACKED. A timeout rejects the
// caller's wrapper; it does not stop the underlying call. So after an effect times out: no further effect is
// launched (they fail at once), the underlying call is followed until it really settles, and a signed
// transaction that comes back late from a prepare that already "failed" is kept as an orphaned intent (private
// bytes) that blocks closure. Reads may simply time out into 'unknown'.
const EFFECT_PORTS = new Set(['prepareSweep', 'prepareGasSweep', 'broadcast']);
// A prepare result counts only if it carries a complete signed-intent record: a non-empty hash and non-empty raw
// signed bytes. Anything else (undefined, null, {}, a hash without bytes, wrong types) is NOT proof that nothing
// was signed, so it can never clear the in-flight marker.
function validPrepared(v) {
  if (!v || typeof v !== 'object') return false;
  if (typeof v.hash !== 'string' || v.hash.length === 0 || v.hash.length > 200) return false;
  const rawOk = (typeof v.raw === 'string' && v.raw.length > 0) || ((v.raw instanceof Uint8Array) && v.raw.length > 0);
  return rawOk;
}
function boundedPorts(ports, ms, hooks) {
  const t = { outstanding: new Set(), halted: false, effectTimedOut: false, orphans: [], lateRejected: false, prepareUncertain: false };
  const out = {};
  for (const name of PORTS) {
    const isEffect = EFFECT_PORTS.has(name);
    out[name] = (...a) => {
      if (isEffect && t.halted) return Promise.reject(new Error('effects_halted'));
      const isPrepare = name.startsWith('prepare');
      // a signature may exist from the moment a prepare starts: the marker is durable BEFORE the signer is called
      if (isPrepare) { try { hooks.prepareStart({ kind: name, walletId: a[0] && a[0].id, amount: String(a[2]), nonce: a[3] }); } catch { return Promise.reject(new Error('marker_not_durable')); } }
      const underlying = Promise.resolve().then(() => ports[name](...a));
      let timedOut = false;
      if (isEffect) {
        const done = underlying.then(v => {
          if (timedOut && isPrepare) {
            if (validPrepared(v)) t.orphans.push({ kind: name, walletId: a[0] && a[0].id, hash: v.hash, raw: typeof v.raw === 'string' ? v.raw : Buffer.from(v.raw).toString('hex'), amount: String(a[2]), nonce: a[3] });
            else { t.prepareUncertain = true; t.halted = true; } // a late malformed result: still not proof of anything
          }
        }, e => { if (timedOut && isPrepare) { if (e instanceof PrepareNotStarted) t.lateRejected = true; else { t.prepareUncertain = true; t.halted = true; } } }).then(() => { t.outstanding.delete(done); });
        t.outstanding.add(done);
      }
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => { timedOut = true; if (isEffect) { t.halted = true; t.effectTimedOut = true; } reject(new Error('port_timeout')); }, ms);
        // in time: the marker is cleared in memory so the component's very next durable write (the intent) carries the clear
        underlying.then(v => {
          clearTimeout(timer);
          if (isPrepare && !timedOut) {
            if (!validPrepared(v)) { t.prepareUncertain = true; t.halted = true; reject(new Error('prepare_output_invalid')); return; } // marker stays
            hooks.prepareEnd();                                                // complete intent in hand: the next durable write carries it and the clear
          }
          resolve(v);
        }, e => {
          clearTimeout(timer);
          if (isPrepare && !timedOut) {
            if (e instanceof PrepareNotStarted) hooks.prepareEnd();          // typed proof that nothing was signed
            else { t.prepareUncertain = true; t.halted = true; }             // unknown: keep the marker, launch nothing more
          }
          reject(e);
        });
      });
    };
  }
  out._t = t;
  return out;
}
// Wait until every outstanding effect call has actually settled, or give up after `ms`.
async function drainEffects(t, ms) {
  let timer;
  const deadline = new Promise(r => { timer = setTimeout(() => r(false), ms); });
  const all = (async () => { while (t.outstanding.size) await Promise.all([...t.outstanding]); return true; })();
  const ok = await Promise.race([all, deadline]);
  clearTimeout(timer);
  return ok;
}

// Run `fn` under a timeout and an abort signal. After a timeout or an abort the work must actually SETTLE
// within `quiesceMs`; if it does not, the caller must treat the situation as unresolved.
async function supervise(fn, abort, timeoutMs, quiesceMs) {
  const running = Promise.resolve().then(fn).then(() => 'success', () => 'failed');
  let t1; let t2;
  const timeout = new Promise(r => { t1 = setTimeout(() => r('timeout'), timeoutMs); });
  const cancelled = new Promise(r => { if (abort.signal.aborted) r('cancelled'); else abort.signal.addEventListener('abort', () => r('cancelled'), { once: true }); });
  const first = await Promise.race([running, timeout, cancelled]);
  clearTimeout(t1);
  if (first === 'success' || first === 'failed') return { outcome: first, settled: true, running };
  abort.abort(); // tell it to stop, then wait for it to really stop
  const q = await Promise.race([running.then(() => 'settled'), new Promise(r => { t2 = setTimeout(() => r('pending'), quiesceMs); })]);
  clearTimeout(t2);
  return { outcome: first, settled: q === 'settled', running };
}

async function readFunding(ports, cfg) {
  try { return BigInt(await ports.tokenBalance(cfg.fundingWallet)); } catch { return null; }
}

export async function runWithLifecycle(cfg) {
  if (!cfg || cfg.enabled !== true) return { status: 'disabled', ok: true, ran: false };
  const bad = checkConfig(cfg);
  if (bad.length) return { status: 'refused_config', ok: false, problems: bad };

  const lockPath = cfg.journalPath + '.lock';
  const token = crypto.randomBytes(12).toString('hex');
  fs.mkdirSync(nodePath.dirname(cfg.journalPath), { recursive: true, mode: 0o700 });
  if (!takeLock(lockPath, token)) return { status: 'refused_concurrent', ok: false };

  const sig = cfg.signals || process;
  const abort = new AbortController();
  let interrupted = null; let extraSignals = 0;
  const onSignal = name => { if (interrupted) { extraSignals++; return; } interrupted = name; abort.abort(); };
  const handlers = { SIGINT: () => onSignal('SIGINT'), SIGTERM: () => onSignal('SIGTERM') };
  for (const [n, h] of Object.entries(handlers)) sig.on(n, h);

  let keepOwnership = false; let lateSettle = null;
  try {
    const identity = identityOf(cfg);
    const timeoutMs = cfg.timeoutMs ?? 60000; const quiesceMs = cfg.quiesceMs ?? 30000;
    const save = j => saveJournal(cfg.journalPath, j);
    const cur = { journal: null };
    const ports = boundedPorts(cfg.ports, cfg.portTimeoutMs ?? 15000, {
      prepareStart: info => { const j = cur.journal; const prev = j.runner.prepareInFlight; j.runner.prepareInFlight = { ...info, at: (cfg.now || (() => new Date().toISOString()))() }; try { save(j); } catch (e) { j.runner.prepareInFlight = prev; j.persistence = { failed: true }; throw e; } }, // the signer is not called, so nothing was signed
      prepareEnd: () => { if (cur.journal && cur.journal.runner) cur.journal.runner.prepareInFlight = null; },
    });
    const base = {
      save, token: cfg.token, chainId: cfg.chainId, dust: cfg.dust ?? 0n, gasDust: cfg.gasDust ?? 0n,
      approvedContracts: cfg.approvedContracts || [], gasReserveMultiple: cfg.gasReserveMultiple ?? 2,
    };
    const setPhase = (j, phase, extra = {}) => { j.runner = { ...(j.runner || {}), phase, ...extra }; save(j); };
    // unresolved work: keep ownership (the lock stays while this process lives) and never clean up or close
    const recordOrphans = journal => {
      const t = ports._t;
      if (t.orphans.length) { journal.runner.orphans = (journal.runner.orphans || []).concat(t.orphans.splice(0)); journal.runner.prepareInFlight = null; }
      else if (t.lateRejected && journal.runner.prepareInFlight) { journal.runner.prepareInFlight = null; t.lateRejected = false; } // the signer refused: nothing was signed
    };
    const sleepU = ms => new Promise(r => { const h = setTimeout(r, ms); if (h.unref) h.unref(); });
    // late results are made durable before ownership is given up; if the write keeps failing, the lock stays
    const retrySave = async journal => {
      for (let i = 0; i <= (cfg.lateRetries ?? 50); i++) {
        try { save(journal); return true; } catch { await sleepU(cfg.lateRetryMs ?? 200); }
      }
      return false;
    };
    const unresolved = (journal, what, running) => {
      keepOwnership = true;
      journal.status = 'failed_cleanup';
      try { setPhase(journal, 'unquiesced_' + what); } catch { journal.persistence = { failed: true }; }
      // released only once the work really has settled AND its late result is durable; the next run then resumes
      lateSettle = running.then(async () => {
        recordOrphans(journal); journal.status = 'failed_cleanup';
        if (await retrySave(journal)) dropLock(lockPath, token);
      });
      return { status: 'unquiesced', ok: false, unresolved: what, interrupted, extraSignals, checkpoint: checkpoint(journal), report: publicReport(journal) };
    };

    let journal; let resumed = false;
    if (fs.existsSync(cfg.journalPath)) {
      try { journal = loadJournal(cfg.journalPath); }
      catch { return { status: 'refused_invalid_journal', ok: false }; }
      if (journal.runId !== cfg.runId || journal.fundingWallet.toLowerCase() !== String(cfg.fundingWallet).toLowerCase()) return { status: 'refused_journal_mismatch', ok: false };
      // the exact roster, chain, token and recovery policy must match, before any port is touched
      if (!journal.runner || journal.runner.identity !== identity) return { status: 'refused_identity_mismatch', ok: false };
      if (CLOSED.has(journal.status)) return { status: 'refused_already_closed', ok: false, report: publicReport(journal) };
      // a signed intent that came back after its timeout exists somewhere: nothing more is signed or sent for this
      // run until a reviewed procedure dispositions it
      if ((journal.runner.orphans && journal.runner.orphans.length) || journal.runner.prepareInFlight) return { status: 'orphans_unresolved', ok: false, checkpoint: checkpoint(journal), report: publicReport(journal) };
      resumed = true;
    } else {
      try { journal = newJournal(cfg.runId, cfg.fundingWallet, cfg.roster, (cfg.now || (() => new Date().toISOString()))()); }
      catch { return { status: 'refused_inventory', ok: false }; }
      journal.runner = { phase: 'new', identity };
      try { save(journal); } catch { return { status: 'refused_not_persistent', ok: false }; }
      const ctl = await verifyControl(journal, ports, base);
      if (!ctl.ok) {
        // refuse BEFORE any funds are placed; the unique inventory stays in the private journal
        journal.runner.phase = 'refused_control';
        journal.status = 'failed_cleanup';
        try { save(journal); } catch { journal.persistence = { failed: true }; }
        return { status: 'refused_control', ok: false, missing: ctl.missing, funded: false, checkpoint: checkpoint(journal), report: publicReport(journal) };
      }
      try { setPhase(journal, 'controls_ok'); } catch { return { status: 'refused_not_persistent', ok: false }; }
    }

    cur.journal = journal;
    let scenario = resumed ? 'resumed' : null;
    if (!resumed) {
      // from here on funds may exist: a crash, error or signal below always ends in cleanup or an unresolved state
      try { setPhase(journal, 'funding'); } catch { return { status: 'refused_not_persistent', ok: false }; }
      let fundOk = true;
      if (!interrupted) {
        const f = await supervise(() => cfg.fund({ signal: abort.signal }), abort, cfg.fundTimeoutMs ?? timeoutMs, quiesceMs);
        if (!f.settled) return unresolved(journal, 'funding', f.running); // a transfer may still land: do not race it
        // a signal during funding lets it finish (it settled): the funds may be placed, so it is 'cancelled', not failed
        fundOk = f.outcome === 'success' || f.outcome === 'cancelled';
      }
      if (!fundOk) scenario = 'fund_failed';
      else if (interrupted) scenario = 'cancelled';
      else {
        try { setPhase(journal, 'funded'); } catch { journal.persistence = { failed: true }; }
        const sc = await supervise(() => cfg.scenario({ signal: abort.signal, journal: checkpoint(journal) }), abort, timeoutMs, quiesceMs);
        if (!sc.settled) return unresolved(journal, 'scenario', sc.running); // still running: no cleanup, no closure, no release
        scenario = sc.outcome;
      }
      journal.runner.scenario = scenario;
      try { setPhase(journal, 'scenario_done', { scenario }); } catch { journal.persistence = { failed: true }; }
    }

    // ---- terminal cleanup: entered exactly once per process, whatever happened above ----
    try { setPhase(journal, 'cleanup'); } catch { journal.persistence = { failed: true }; }
    if (journal.runner.fundingBefore === undefined) {
      const fb = await readFunding(ports, cfg);
      journal.runner.fundingBefore = fb === null ? null : fb.toString();
      try { save(journal); } catch { journal.persistence = { failed: true }; }
    }
    // Passes are bounded. If an effect call timed out, no further effect is launched in this pass; we wait for the
    // outstanding calls to really settle (or keep ownership if they do not), then reconcile from receipts.
    const tr = ports._t;
    for (let pass = 0; pass < (cfg.maxCleanupPasses ?? 4); pass++) {
      await runCleanup(journal, ports, base);
      let found = await terminalVerify(journal, ports, base);
      if (found.length && !tr.effectTimedOut && !tr.prepareUncertain) { await runCleanup(journal, ports, base); found = await terminalVerify(journal, ports, base); }
      if (tr.prepareUncertain) break;     // a prepare failed in an unknown way: no more signing; the marker stays
      if (!tr.effectTimedOut) break;
      if (!(await drainEffects(tr, quiesceMs))) return unresolved(journal, 'cleanup_effects', (async () => { while (tr.outstanding.size) await Promise.all([...tr.outstanding]); })());
      recordOrphans(journal);
      try { save(journal); } catch { journal.persistence = { failed: true }; }
      if ((journal.runner.orphans && journal.runner.orphans.length) || tr.prepareUncertain) break; // no further signing once an orphan or an unknown prepare failure exists
      tr.halted = false; tr.effectTimedOut = false; // everything has stopped: the next pass reads the receipts
    }
    const after = await readFunding(ports, cfg);
    const before = journal.runner.fundingBefore;
    if (before !== null && before !== undefined && after !== null) reconcile(journal, BigInt(before), after, base);
    else finalize(journal, base);
    // an orphaned signed intent (a prepare that returned after it had timed out) can never be closed over
    if ((journal.runner.orphans && journal.runner.orphans.length) || journal.runner.prepareInFlight) { journal.status = 'failed_cleanup'; try { save(journal); } catch { journal.persistence = { failed: true }; } }

    // a resumed run never reports success: its scenario did not complete in this process
    const persistOk = !(journal.persistence && journal.persistence.failed);
    const ok = journal.status === 'closed' && scenario === 'success' && persistOk;
    const acceptedWithExceptions = journal.status === 'closed_with_exceptions' && scenario === 'success' && persistOk;
    return {
      status: journal.status, ok, acceptedWithExceptions, scenario, resumed, interrupted, extraSignals,
      funded: journal.runner.phase !== 'new', checkpoint: checkpoint(journal), report: publicReport(journal),
    };
  } finally {
    for (const [n, h] of Object.entries(handlers)) sig.off(n, h);
    if (!keepOwnership) dropLock(lockPath, token);
    else void lateSettle;
  }
}
