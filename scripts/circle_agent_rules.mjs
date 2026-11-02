// Pure rules and parsers for the Circle agent-wallet drip route (no network). Used by circle_agent_drip.mjs and its tests.
// Record and rationale: evidence/circle-faucet-access-20261102/README.md (route R2).

import { createHash } from 'node:crypto';

const OTP = /\b([A-Za-z0-9]{2,8})-(\d{6})\b/;
const REQUEST_ID = /--request\s+([0-9a-fA-F-]{8,64})/;
const ADDRESS = /^0x[0-9a-fA-F]{40}$/;

export const USDC_BASE_SEPOLIA = '0x036CbD53842c5426634e7929541eC2318f3dCF7e';
export const DEFAULT_LOGIN_EMAIL = 'claude-microcredit@agentmail.to';
export const CLI_PACKAGE = '@circle-fin/cli@1.2.2';
export const AGENT_WALLET_HOST = 'agentic-wallet.circle.com';

// The request id printed by `circle wallet login <email> --init` inside its message text.
export function extractRequestId(text) {
  const m = REQUEST_ID.exec(String(text || ''));
  return m ? m[1] : null;
}

// The one-time password in Circle's email, in the CLI's full form (head, dash, six digits).
export function extractOtp(text) {
  const m = OTP.exec(String(text || ''));
  return m ? `${m[1].toUpperCase()}-${m[2]}` : null;
}

// The CLI prints one pretty-printed object per command: { "data": ... } on success, { "error": { code, message, hint } }
// on failure, sometimes after other text. Returns { data, error }, both null when no JSON object is found.
export function parseCliOutput(stdout) {
  const out = String(stdout || '');
  const brace = out.indexOf('{');
  if (brace < 0) return { data: null, error: null };
  try {
    const parsed = JSON.parse(out.slice(brace));
    return { data: parsed && 'data' in parsed ? parsed.data : null, error: parsed && parsed.error ? parsed.error : null };
  } catch {
    return { data: null, error: null };
  }
}

// A deterministic idempotency key for one transfer: same recipient, amount and UTC day give the same key, so a retry
// after a killed or unclear run cannot send twice. Shaped like a UUID v4, which is what Circle's API expects.
export function idempotencyKey(recipient, amount, day) {
  const h = createHash('sha256').update(`${String(recipient).toLowerCase()}|${amount}|${day}`).digest('hex');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-${(8 + (parseInt(h[16], 16) % 4)).toString(16)}${h.slice(17, 20)}-${h.slice(20, 32)}`;
}

// Candidate OTP messages: not seen before the login request (ids snapshotted by the caller), received at or after the
// request with a small clock allowance, from Circle, newest first. `messages` is the AgentMail list.
export function pickOtpMessages(messages, requestedAtIso, allowanceSeconds = 15, excludeIds = new Set()) {
  const since = new Date(new Date(requestedAtIso).getTime() - allowanceSeconds * 1000).toISOString();
  return (Array.isArray(messages) ? messages : [])
    .filter((m) => m && !excludeIds.has(m.message_id))
    .filter((m) => typeof m.timestamp === 'string' && m.timestamp >= since)
    .filter((m) => /circle/i.test(String(m.from || '')) || /circle/i.test(String(m.subject || '')))
    .sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
}

// The agent wallet for one blockchain from `circle wallet list --type agent --chain <chain> --output json`.
export function parseAgentWallet(json, blockchain) {
  const wallets = json && Array.isArray(json.wallets) ? json.wallets : [];
  const w = wallets.find((x) => x && x.type === 'agent' && x.blockchain === blockchain && ADDRESS.test(String(x.address)));
  return w ? w.address : null;
}

// Whatever identifier the transfer command printed, without guessing its exact field name.
export function parseTransferId(json) {
  if (!json || typeof json !== 'object') return null;
  for (const k of ['transactionId', 'id', 'txHash', 'transactionHash', 'hash']) {
    if (typeof json[k] === 'string' && json[k]) return json[k];
  }
  return null;
}

// Decode a uint256 eth_call result into a USDC amount (6 decimals).
export function decodeUsdc(hex) {
  if (typeof hex !== 'string' || !/^0x[0-9a-fA-F]*$/.test(hex)) return null;
  const v = hex.length > 2 ? BigInt(hex) : 0n;
  return Number(v) / 1e6;
}

// Send from the agent wallet only to an allowlisted address, within its caps, and only what the agent wallet holds.
export function decideAgentDrip({ entry, amount, recipientBalance, agentBalance }) {
  if (!entry) return { ok: false, reason: 'recipient is not on the allowlist' };
  if (!Number.isFinite(recipientBalance) || !Number.isFinite(agentBalance)) return { ok: false, reason: 'a balance could not be read' };
  if (!(amount > 0)) return { ok: false, reason: 'amount is not a positive number' };
  if (amount > entry.maxPerRun) return { ok: false, reason: `amount above this recipient's per-run cap of ${entry.maxPerRun}` };
  if (recipientBalance >= entry.maxBalance) return { ok: false, reason: `recipient already holds its cap of ${entry.maxBalance}` };
  if (agentBalance < amount) return { ok: false, reason: `agent wallet holds ${agentBalance}, less than ${amount}` };
  return { ok: true };
}
