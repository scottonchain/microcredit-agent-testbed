// Route R2 (evidence/circle-faucet-access-20261102): from inside a session, log in to Circle's agent wallet with the
// project's agent inbox, draw test USDC from Circle's testnet faucet into that agent wallet, and transfer it to an
// allowlisted address on Base Sepolia. Nothing here touches the team test wallet or any private key.
//
// Modes:  --check      prerequisites only; runs no Circle command that needs the terms, sends nothing
//         --fund-only  login and faucet into the agent wallet; no transfer
//         (default)    login, faucet, transfer to RECIPIENT
// Env:    CIRCLE_AGENT_TERMS_ACCEPTED     the operator's acceptance of Circle's agent Terms of Use and privacy policy
//                                         (https://agents.circle.com/terms-of-use), as a short note such as
//                                         "accepted 2026-11-02 by the operator"; echoed into the result file; without it
//                                         nothing but --check runs ("0", "false" and "no" count as absent)
//         CIRCLE_AGENT_LOGIN_EMAIL        login inbox, default claude-microcredit@agentmail.to (readable through the AgentMail API)
//         RECIPIENT, AMOUNT_USDC          allowlisted address (scripts/drip_allowlist.json) and amount, default 5
//         RPC_URL                         default https://sepolia.base.org;  CIRCLE_CLI_HOME  default ~/.circle-cli
//         CIRCLE_CLI_DIR                  where @circle-fin/cli 1.2.2 is installed, default <tmp>/circle-cli-1.2.2
//         RESULT_PATH                     JSON result, default ./circle-agent-drip-result.json (no code, token or key in it)
// Exit:   0 done (or --check passed), 2 prerequisite or input problem, 3 refused by a rule, 1 Circle or chain failure.
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadAllowlist, parseAmount } from './drip_rules.mjs';
import { USDC_BASE_SEPOLIA, DEFAULT_LOGIN_EMAIL, CLI_PACKAGE, AGENT_WALLET_HOST, extractRequestId, otpFromMessage, pickOtpMessages, parseAgentWallet, parseTransferId, parseCliOutput, idempotencyKey, decodeUsdc, decideAgentDrip } from './circle_agent_rules.mjs';

// Node's fetch ignores HTTPS_PROXY unless NODE_USE_ENV_PROXY is set (Node 22.21+); the container's hosts are only
// reachable through that proxy, so the runner restarts itself with the switch and passes it to the CLI as well.
if (process.env.NODE_USE_ENV_PROXY !== '1') {
  const r = spawnSync(process.execPath, process.argv.slice(1), { stdio: 'inherit', env: { ...process.env, NODE_USE_ENV_PROXY: '1', NODE_NO_WARNINGS: '1' } });
  process.exit(r.status ?? 1);
}

const CHAIN = 'BASE-SEPOLIA';
const here = dirname(fileURLToPath(import.meta.url));
const mode = process.argv.includes('--check') ? 'check' : process.argv.includes('--fund-only') ? 'fund-only' : 'full';
const termsValue = String(process.env.CIRCLE_AGENT_TERMS_ACCEPTED || '').trim();
const termsAccepted = termsValue !== '' && !['0', 'false', 'no'].includes(termsValue.toLowerCase());
const loginEmail = process.env.CIRCLE_AGENT_LOGIN_EMAIL || DEFAULT_LOGIN_EMAIL;
const rpc = process.env.RPC_URL || 'https://sepolia.base.org';
const cliHome = process.env.CIRCLE_CLI_HOME || join(homedir(), '.circle-cli');
const cliDir = process.env.CIRCLE_CLI_DIR || join(tmpdir(), 'circle-cli-1.2.2');
const resultPath = process.env.RESULT_PATH || join(process.cwd(), 'circle-agent-drip-result.json');
const result = { mode, startedAt: new Date().toISOString(), chain: CHAIN, loginEmail, termsAcceptance: termsAccepted ? termsValue.slice(0, 80) : null, steps: [] };
const note = (step, data) => { result.steps.push({ step, at: new Date().toISOString(), ...data }); console.error(`[${step}] ${JSON.stringify(data)}`); };
const finish = (code, summary) => { result.finishedAt = new Date().toISOString(); result.summary = summary; writeFileSync(resultPath, JSON.stringify(result, null, 1) + '\n'); console.log(JSON.stringify({ code, summary, resultPath })); process.exit(code); };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function rpcCall(method, params) {
  const res = await fetch(rpc, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method, params }) });
  const body = await res.json();
  if (body.error) throw new Error(`${method}: ${JSON.stringify(body.error).slice(0, 160)}`);
  return body.result;
}
async function usdcBalance(address) {
  const data = '0x70a08231' + address.slice(2).toLowerCase().padStart(64, '0');
  const v = decodeUsdc(await rpcCall('eth_call', [{ to: USDC_BASE_SEPOLIA, data }, 'latest']));
  if (v === null) throw new Error(`unreadable USDC balance for ${address}`);
  return v;
}
async function waitForIncrease(address, before, seconds, label) {
  for (let t = 0; t < seconds; t += 6) {
    await sleep(6000);
    const now = await usdcBalance(address);
    if (now > before) return { received: Number((now - before).toFixed(6)), after: now, seconds: t + 6 };
  }
  note(label, { warning: `no balance increase within ${seconds}s` });
  return null;
}
async function inbox(path) {
  const res = await fetch(`https://api.agentmail.to/v0/inboxes/${encodeURIComponent(loginEmail)}${path}`);
  if (!res.ok) throw new Error(`AgentMail ${res.status} on ${path}`);
  return res.json();
}

function ensureCli() {
  const bin = join(cliDir, 'node_modules', '@circle-fin', 'cli', 'dist', 'index.js');
  if (!existsSync(bin)) {
    const r = spawnSync('npm', ['install', '--prefix', cliDir, '--no-audit', '--no-fund', CLI_PACKAGE], { encoding: 'utf8' });
    if (r.status !== 0) throw new Error(`npm install failed: ${(r.stderr || '').slice(-300)}`);
  }
  return bin;
}
// Runs one CLI command with JSON output. The CLI's terms flag is set only when the operator accepted the terms.
// Transfers get a longer budget than the CLI's own challenge and polling deadlines (60 s plus 120 s).
function circle(bin, args, { needsTerms = true, timeoutMs = 120000 } = {}) {
  const env = { ...process.env, CIRCLE_CLI_HOME: cliHome, CIRCLE_VERSION_CHECK: 'off', NODE_USE_ENV_PROXY: '1', NODE_NO_WARNINGS: '1' };
  delete env.CIRCLE_ACCEPT_TERMS;
  if (needsTerms && termsAccepted) env.CIRCLE_ACCEPT_TERMS = '1';
  const r = spawnSync('node', [bin, ...args, '--output', 'json'], { encoding: 'utf8', env, timeout: timeoutMs });
  const { data, error } = parseCliOutput(r.stdout);
  return { status: r.status, signal: r.signal || null, data, error, stderr: (r.stderr || '').slice(-400) };
}
const errorText = (r) => r.error ? `${r.error.code || 'ERROR'}: ${String(r.error.message || '')}${r.error.hint ? ' (' + r.error.hint + ')' : ''}`.slice(0, 240) : r.signal ? `CLI killed by ${r.signal} at the timeout` : r.stderr.slice(-200);

async function check() {
  const report = { termsAccepted, loginEmail };
  try { report.rpcChainId = await rpcCall('eth_chainId', []); report.rpcOk = report.rpcChainId === '0x14a34'; } catch (e) { report.rpcOk = false; report.rpcError = String(e.message).slice(0, 120); }
  try { const r = await fetch(`https://${AGENT_WALLET_HOST}/v1/cli/version`, { signal: AbortSignal.timeout(15000) }); report.hostStatus = r.status; report.hostReachable = r.ok; const body = await r.json().catch(() => null); if (body?.data) report.hostPolicy = { latestVersion: body.data.latestVersion, minimumVersion: body.data.minimumVersion }; } catch (e) { report.hostReachable = false; report.hostError = String(e.cause?.message || e.message).slice(0, 120); }
  try { const l = await inbox('/messages?limit=1'); report.inboxReadable = Array.isArray(l.messages); } catch (e) { report.inboxReadable = false; report.inboxError = String(e.message).slice(0, 120); }
  try { const list = loadAllowlist(JSON.parse(readFileSync(join(here, 'drip_allowlist.json'), 'utf8'))); report.allowlist = [...list.values()].map((e) => `${e.address} (${e.maxPerRun} per run, balance cap ${e.maxBalance})`); } catch (e) { report.allowlistError = String(e.message); }
  try { const bin = ensureCli(); const v = spawnSync('node', [bin, '--version'], { encoding: 'utf8', env: { ...process.env, CIRCLE_CLI_HOME: cliHome, CIRCLE_VERSION_CHECK: 'off', CIRCLE_ACCEPT_TERMS: '' }, timeout: 60000 }); report.cliVersion = ((v.stdout || '') + (v.stderr || '')).trim().split('\n')[0].slice(0, 80); report.cliInstalled = v.status === 0 && /^\d+\.\d+\.\d+/.test(report.cliVersion); report.cliPinned = report.cliVersion === CLI_PACKAGE.split('@').pop(); } catch (e) { report.cliInstalled = false; report.cliError = String(e.message).slice(0, 160); }
  note('check', report);
  const ok = report.termsAccepted && report.rpcOk && report.hostReachable && report.inboxReadable && report.cliInstalled && !report.allowlistError;
  finish(ok ? 0 : 2, ok ? 'all prerequisites present' : 'missing: ' + [!report.termsAccepted && 'CIRCLE_AGENT_TERMS_ACCEPTED (operator decision)', !report.rpcOk && 'Base Sepolia RPC', !report.hostReachable && `network access to ${AGENT_WALLET_HOST} (operator: environment network settings)`, !report.inboxReadable && 'AgentMail inbox read', !report.cliInstalled && 'Circle CLI install'].filter(Boolean).join('; '));
}

async function loggedIn(bin) {
  const r = circle(bin, ['wallet', 'status', '--type', 'agent']);
  const testnet = r.data?.testnet || null;
  return Boolean(testnet && testnet.tokenStatus === 'VALID');
}
async function login(bin) {
  const deadline = Date.now() + 180000;
  const seen = new Set();
  let requestId = null, requestedAt = null, reinitDone = false;
  const init = async () => {
    // Snapshot the inbox first so an older Circle mail (a previous run, another session) can never be taken for this one.
    try { for (const m of (await inbox('/messages?limit=20')).messages || []) seen.add(m.message_id); } catch (e) { note('login-inbox', { warning: String(e.message).slice(0, 120) }); }
    requestedAt = new Date().toISOString();
    const r = circle(bin, ['wallet', 'login', loginEmail, '--type', 'agent', '--testnet', '--init']);
    requestId = extractRequestId(r.data?.message);
    if (r.status !== 0 || !requestId) { note('login-init', { failed: errorText(r) }); return false; }
    note('login-init', { ok: true, codeSentTo: loginEmail });
    return true;
  };
  if (!(await init())) return false;
  while (Date.now() < deadline) {
    await sleep(5000);
    let candidates = [];
    try { candidates = pickOtpMessages((await inbox('/messages?limit=20')).messages, requestedAt, 15, seen); } catch (e) { note('login-inbox', { warning: String(e.message).slice(0, 120) }); continue; }
    for (const m of candidates) {
      seen.add(m.message_id);
      const d = await inbox(`/messages/${encodeURIComponent(m.message_id)}`);
      const otp = otpFromMessage(d);
      if (!otp) continue;
      const done = circle(bin, ['wallet', 'login', '--request', requestId, '--otp', otp, '--type', 'agent', '--testnet']);
      if (done.status === 0 && /logged in/i.test(String(done.data?.message || ''))) { note('login', { ok: true }); return true; }
      note('login', { rejected: errorText(done) });
      // The CLI discards a login request after one attempt: start one more, once, inside the same budget.
      if (reinitDone) return false;
      reinitDone = true;
      if (!(await init())) return false;
      break;
    }
  }
  note('login', { failed: 'no usable one-time password from Circle within 180s' });
  return false;
}

async function main() {
  if (mode === 'check') return check();
  if (!termsAccepted) finish(2, 'CIRCLE_AGENT_TERMS_ACCEPTED is not set: accepting Circle\'s agent terms is the operator\'s decision; run --check');
  let entry = null, amount = null, recipient = null;
  if (mode === 'full') {
    const list = loadAllowlist(JSON.parse(readFileSync(join(here, 'drip_allowlist.json'), 'utf8')));
    recipient = String(process.env.RECIPIENT || '');
    entry = list.get(recipient.toLowerCase()) || null;
    amount = parseAmount(process.env.AMOUNT_USDC || '5');
    if (!entry) finish(3, 'recipient is not on the allowlist');
    if (amount === null) finish(2, 'AMOUNT_USDC is not a positive number');
  }
  const bin = ensureCli();
  if (!(await loggedIn(bin)) && !(await login(bin))) finish(1, 'login failed');
  // Login provisions the agent wallets; a missing one is a finding to record, not something to create blindly.
  const list = circle(bin, ['wallet', 'list', '--type', 'agent', '--chain', CHAIN]);
  const agent = parseAgentWallet(list.data, CHAIN);
  if (!agent) { note('wallet-list', { detail: list.status === 0 ? 'no agent wallet listed for ' + CHAIN : errorText(list) }); finish(1, `no agent wallet on ${CHAIN} for this login; check 'circle blockchain list' and the CLI's testnet support`); }
  result.agentWallet = agent;
  const before = await usdcBalance(agent);
  const fund = circle(bin, ['wallet', 'fund', '--address', agent, '--chain', CHAIN, '--token', 'usdc']);
  note('faucet', { status: fund.status, detail: fund.status === 0 ? String(fund.data?.message || 'requested').slice(0, 160) : errorText(fund), agentBalanceBefore: before });
  const got = fund.status === 0 ? await waitForIncrease(agent, before, 180, 'faucet') : null;
  if (got) note('faucet', got);
  const agentBalance = got ? got.after : await usdcBalance(agent);
  if (mode === 'fund-only') finish(fund.status === 0 && got ? 0 : 1, got ? `faucet gave ${got.received} test USDC in ${got.seconds}s` : 'faucet gave nothing');
  const recipientBalance = await usdcBalance(recipient);
  const verdict = decideAgentDrip({ entry, amount, recipientBalance, agentBalance });
  if (!verdict.ok) finish(3, verdict.reason);
  const key = idempotencyKey(recipient, amount, result.startedAt.slice(0, 10));
  const tr = circle(bin, ['wallet', 'transfer', recipient, '--amount', String(amount), '--token', USDC_BASE_SEPOLIA, '--address', agent, '--chain', CHAIN, '--idempotency-key', key], { timeoutMs: 300000 });
  const id = parseTransferId(tr.data);
  const killed = tr.status === null;
  note('transfer', { status: tr.status, id, state: tr.data?.state || null, detail: tr.status === 0 ? null : errorText(tr), recipientBalanceBefore: recipientBalance, idempotencyKey: key });
  if (tr.status !== 0 && !killed) finish(1, 'transfer refused');
  const landed = await waitForIncrease(recipient, recipientBalance, 180, 'transfer');
  if (landed) note('transfer', landed);
  finish(landed ? 0 : 1, landed ? `${landed.received} test USDC reached ${recipient} in ${landed.seconds}s` : killed ? 'CLI killed at its timeout after the transfer attempt; nothing seen on chain within 180s; the same day and amount reuse the idempotency key' : 'transfer not seen on chain within 180s');
}
main().catch((e) => { note('error', { message: String(e.message).slice(0, 200) }); finish(1, 'unexpected error'); });
