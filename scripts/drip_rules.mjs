// Pure rules for the team-wallet test USDC drip (no network, no ethers). Used by drip_test_usdc.mjs and its tests.
// Record and rationale: evidence/circle-faucet-access-20261102/README.md.

export const DAILY_CAP_USDC = 100;        // across all runs in one UTC day
export const FLOOR_USDC = 50;             // the team wallet never goes below this
export const DEFAULT_AMOUNT_USDC = 5;
export const MAX_PER_RUN_ANY = 25;        // the largest per-run cap any allowlist entry may carry

const ADDRESS = /^0x[0-9a-fA-F]{40}$/;
const TITLE = /^Drip (\d+(?:\.\d+)?) test USDC to (0x[0-9a-fA-F]{40})( \(dry run\))?$/;

export function runTitle(amount, recipient, dryRun) {
  return `Drip ${amount} test USDC to ${recipient}${dryRun ? ' (dry run)' : ''}`;
}

export function parseAmount(raw) {
  const s = String(raw ?? '').trim();
  if (!/^\d+(?:\.\d{1,6})?$/.test(s)) return null;
  const n = Number(s);
  return n > 0 ? n : null;
}

// Allowlist: [{address, label, max_per_run, max_balance}]. Returns a map keyed by lower-cased address.
export function loadAllowlist(entries) {
  if (!Array.isArray(entries) || entries.length === 0) throw new Error('allowlist is empty');
  const map = new Map();
  for (const e of entries) {
    if (!ADDRESS.test(e.address)) throw new Error(`allowlist: bad address ${String(e.address)}`);
    const perRun = Number(e.max_per_run), maxBal = Number(e.max_balance);
    if (!(perRun > 0 && perRun <= MAX_PER_RUN_ANY)) throw new Error(`allowlist: max_per_run out of range for ${e.address}`);
    if (!(maxBal > 0)) throw new Error(`allowlist: max_balance must be positive for ${e.address}`);
    map.set(e.address.toLowerCase(), { address: e.address, label: String(e.label || ''), maxPerRun: perRun, maxBalance: maxBal });
  }
  return map;
}

// Runs created at or after `since` (ISO 8601 UTC strings compare lexicographically). The runs API lists newest first.
export function runsSince(runs, since) {
  return runs.filter((r) => typeof r.created_at === 'string' && r.created_at >= since);
}

// Test USDC already committed today by other runs of this workflow. Counts successful runs and runs still
// queued or in progress; skips dry runs and the current run; an unparsable title counts as the largest cap.
export function spentToday(runs, currentRunId) {
  let total = 0;
  for (const r of runs) {
    if (String(r.id) === String(currentRunId)) continue;
    const active = r.status === 'queued' || r.status === 'in_progress' || r.status === 'waiting';
    if (!(active || r.conclusion === 'success')) continue;
    const m = TITLE.exec(r.display_title || r.name || '');
    if (!m) { total += MAX_PER_RUN_ANY; continue; }
    if (m[3]) continue;
    total += Number(m[1]);
  }
  return total;
}

// All amounts in test USDC as numbers. Returns {ok: true} or {ok: false, reason}.
export function decide({ entry, amount, recipientBalance, teamBalance, spent, teamIsRecipient }) {
  if (teamIsRecipient) return { ok: false, reason: 'recipient is the team wallet' };
  if (!entry) return { ok: false, reason: 'recipient is not on the allowlist' };
  if (amount === null) return { ok: false, reason: 'amount is not a positive number' };
  if (amount > entry.maxPerRun) return { ok: false, reason: `amount above this recipient's per-run cap of ${entry.maxPerRun}` };
  if (recipientBalance >= entry.maxBalance) return { ok: false, reason: `recipient already holds its cap of ${entry.maxBalance}` };
  if (teamBalance - amount < FLOOR_USDC) return { ok: false, reason: `team wallet would fall below the floor of ${FLOOR_USDC}` };
  if (spent + amount > DAILY_CAP_USDC) return { ok: false, reason: `daily cap of ${DAILY_CAP_USDC} reached (${spent} already committed today)` };
  return { ok: true };
}
