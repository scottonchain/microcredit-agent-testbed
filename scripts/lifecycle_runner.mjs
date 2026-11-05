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
//   4. record phase 'funding' durably, then fund (a failure or a crash here is treated as funded);
//   5. run the scenario with a timeout and an abort signal (SIGINT/SIGTERM abort it);
//   6. ALWAYS enter terminal cleanup exactly once: sweep tokens, return gas, re-read every balance, then
//      reconcile the funding wallet's gain against what settled receipts say was swept;
//   7. report. Only a closed lifecycle with a successful scenario is success; everything else is non-zero.
//
// The journal holds signed raw transactions. It stays at `journalPath` (mode 0600). Only `publicReport` and
// `checkpoint` may leave the process.

import fs from 'node:fs';
import nodePath from 'node:path';
import {
  newJournal, saveJournal, loadJournal, publicView, verifyControl, runCleanup, finalize, reconcile, terminalVerify,
} from './wallet_lifecycle.mjs';

export const ENV_FLAG = 'OMNEQUA_WALLET_LIFECYCLE';
export function lifecycleEnabled(env = process.env) { return env[ENV_FLAG] === '1'; }

const PORTS = ['controls', 'tokenBalance', 'gasBalance', 'gasCostEstimate', 'gasSweepFee', 'nonceOf', 'isContract', 'prepareSweep', 'prepareGasSweep', 'broadcast', 'receipt'];
const CLOSED = new Set(['closed', 'closed_with_exceptions']);

// What may leave the process: no raw bytes, no error text.
export function publicReport(journal) {
  return publicView(journal);
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

// Single owner per journal. A lock whose process is gone is reclaimed; a live one refuses.
function takeLock(lockPath) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const fd = fs.openSync(lockPath, 'wx', 0o600);
      try { fs.writeSync(fd, JSON.stringify({ pid: process.pid })); } finally { fs.closeSync(fd); }
      return true;
    } catch (e) {
      if (e.code !== 'EEXIST') throw e;
      let pid = null;
      try { pid = JSON.parse(fs.readFileSync(lockPath, 'utf8')).pid; } catch { /* unreadable lock: treat as stale only if no live pid */ }
      if (Number.isInteger(pid) && pidAlive(pid) && pid !== process.pid) return false;
      if (Number.isInteger(pid) && pid === process.pid) return false;
      try { fs.unlinkSync(lockPath); } catch { /* another reclaimer won */ }
    }
  }
  return false;
}
function dropLock(lockPath) { try { fs.unlinkSync(lockPath); } catch { /* already gone */ } }

function checkConfig(cfg) {
  const problems = [];
  if (!cfg.runId) problems.push('runId');
  if (!cfg.fundingWallet) problems.push('fundingWallet');
  if (!Array.isArray(cfg.roster) || cfg.roster.length === 0) problems.push('roster');
  if (!cfg.journalPath || !nodePath.isAbsolute(cfg.journalPath)) problems.push('journalPath must be absolute');
  else if (/(^|[\\/])evidence([\\/]|$)/.test(cfg.journalPath)) problems.push('journalPath must be outside the evidence folder');
  if (typeof cfg.fund !== 'function') problems.push('fund');
  if (typeof cfg.scenario !== 'function') problems.push('scenario');
  if (!cfg.ports || PORTS.some(p => typeof cfg.ports[p] !== 'function')) problems.push('ports');
  return problems;
}

async function readFunding(cfg) {
  try { return BigInt(await cfg.ports.tokenBalance(cfg.fundingWallet)); } catch { return null; }
}

export async function runWithLifecycle(cfg) {
  if (!cfg || cfg.enabled !== true) return { status: 'disabled', ok: true, ran: false };
  const bad = checkConfig(cfg);
  if (bad.length) return { status: 'refused_config', ok: false, problems: bad };

  const lockPath = cfg.journalPath + '.lock';
  fs.mkdirSync(nodePath.dirname(cfg.journalPath), { recursive: true, mode: 0o700 });
  if (!takeLock(lockPath)) return { status: 'refused_concurrent', ok: false };

  const sig = cfg.signals || process;
  const abort = new AbortController();
  let interrupted = null; let extraSignals = 0;
  const onSignal = name => { if (interrupted) { extraSignals++; return; } interrupted = name; abort.abort(); };
  const handlers = { SIGINT: () => onSignal('SIGINT'), SIGTERM: () => onSignal('SIGTERM') };
  for (const [n, h] of Object.entries(handlers)) sig.on(n, h);

  try {
    const save = j => saveJournal(cfg.journalPath, j);
    const base = {
      save, token: cfg.token || null, chainId: cfg.chainId, dust: cfg.dust ?? 0n, gasDust: cfg.gasDust ?? 0n,
      approvedContracts: cfg.approvedContracts || [], gasReserveMultiple: cfg.gasReserveMultiple ?? 2,
    };
    const setPhase = (j, phase, extra = {}) => { j.runner = { ...(j.runner || {}), phase, ...extra }; save(j); };

    let journal; let resumed = false;
    if (fs.existsSync(cfg.journalPath)) {
      try { journal = loadJournal(cfg.journalPath); }
      catch { return { status: 'refused_invalid_journal', ok: false }; }
      if (journal.runId !== cfg.runId || journal.fundingWallet.toLowerCase() !== String(cfg.fundingWallet).toLowerCase()) return { status: 'refused_journal_mismatch', ok: false };
      if (CLOSED.has(journal.status)) return { status: 'refused_already_closed', ok: false, report: publicReport(journal) };
      resumed = true;
    } else {
      try { journal = newJournal(cfg.runId, cfg.fundingWallet, cfg.roster, (cfg.now || (() => new Date().toISOString()))()); }
      catch { return { status: 'refused_inventory', ok: false }; }
      journal.runner = { phase: 'new' };
      try { save(journal); } catch { return { status: 'refused_not_persistent', ok: false }; }
      const ctl = await verifyControl(journal, cfg.ports, base);
      if (!ctl.ok) {
        // refuse BEFORE any funds are placed; the unique inventory stays in the private journal
        journal.runner.phase = 'refused_control';
        journal.status = 'failed_cleanup';
        try { save(journal); } catch { journal.persistence = { failed: true }; }
        return { status: 'refused_control', ok: false, missing: ctl.missing, funded: false, checkpoint: checkpoint(journal), report: publicReport(journal) };
      }
      try { setPhase(journal, 'controls_ok'); } catch { return { status: 'refused_not_persistent', ok: false }; }
    }

    let scenario = resumed ? 'resumed' : null;
    if (!resumed) {
      // from here on funds may exist: a crash, error or signal below always ends in terminal cleanup
      try { setPhase(journal, 'funding'); } catch { return { status: 'refused_not_persistent', ok: false }; }
      let fundOk = true;
      if (!interrupted) {
        try { await cfg.fund(); } catch { fundOk = false; }
      }
      if (!fundOk) scenario = 'fund_failed';
      else if (interrupted) scenario = 'cancelled';
      else {
        try { setPhase(journal, 'funded'); } catch { journal.persistence = { failed: true }; }
        let timer; let outcome;
        const running = Promise.resolve().then(() => cfg.scenario({ signal: abort.signal, journal: checkpoint(journal) })).then(() => 'success', () => 'failed');
        const timeout = new Promise(r => { timer = setTimeout(() => r('timeout'), cfg.timeoutMs ?? 60000); });
        const cancelled = new Promise(r => abort.signal.addEventListener('abort', () => r('cancelled'), { once: true }));
        outcome = await Promise.race([running, timeout, cancelled]);
        clearTimeout(timer);
        if (outcome === 'timeout' || outcome === 'cancelled') {
          abort.abort(); // make sure a timed-out scenario is told to stop
          const grace = new Promise(r => setTimeout(() => r('not_settled'), cfg.settleGraceMs ?? 2000));
          const settled = await Promise.race([running.then(() => 'settled'), grace]);
          if (settled === 'not_settled') journal.runner.scenarioNotSettled = true;
        }
        scenario = outcome;
      }
      journal.runner.scenario = scenario;
      try { setPhase(journal, 'scenario_done', { scenario }); } catch { journal.persistence = { failed: true }; }
    }

    // ---- terminal cleanup: entered exactly once per process, whatever happened above ----
    try { setPhase(journal, 'cleanup'); } catch { journal.persistence = { failed: true }; }
    if (journal.runner.fundingBefore === undefined) {
      const fb = await readFunding(cfg);
      journal.runner.fundingBefore = fb === null ? null : fb.toString();
      try { save(journal); } catch { journal.persistence = { failed: true }; }
    }
    await runCleanup(journal, cfg.ports, base);
    let found = await terminalVerify(journal, cfg.ports, base);
    if (found.length) { await runCleanup(journal, cfg.ports, base); found = await terminalVerify(journal, cfg.ports, base); }
    const after = await readFunding(cfg);
    const before = journal.runner.fundingBefore;
    if (before !== null && before !== undefined && after !== null) reconcile(journal, BigInt(before), after, base);
    else finalize(journal, base);

    const closed = CLOSED.has(journal.status);
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
    dropLock(lockPath);
  }
}
