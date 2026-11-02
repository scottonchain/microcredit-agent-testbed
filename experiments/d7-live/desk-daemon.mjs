// The credit officer: watches the CreditDesk for unanswered applicants, decides (an AI officer through the
// headless Claude Code CLI, or plain rules for tests) and replies on chain with the officer key.
// env: RPC_URL, DESK, OFFICER_KEY_FILE (or OFFICER_KEY), MODE=claude|rules, POLL (ms), LOG (file),
//      CLAUDE_MODEL (optional), CIRCLE_API_KEY (optional: drip test USDC to a wallet when a line is granted).
import { createPublicClient, createWalletClient, http, formatUnits } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { baseSepolia } from 'viem/chains';
import { spawn } from 'node:child_process';
import { readFileSync, appendFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { ADDR, ABI } from './lib/chain.mjs';

const RPC = process.env.RPC_URL, DESK = process.env.DESK, MODE = process.env.MODE || 'claude', POLL = Number(process.env.POLL || 5000);
const LOG = process.env.LOG || 'results/desk-daemon.log';
const key = process.env.OFFICER_KEY || readFileSync(process.env.OFFICER_KEY_FILE, 'utf8').trim();
if (!process.env.CIRCLE_API_KEY && process.env.CIRCLE_API_KEY_FILE) { try { process.env.CIRCLE_API_KEY = readFileSync(process.env.CIRCLE_API_KEY_FILE, 'utf8').trim(); } catch {} }
if (!RPC || !DESK || !key) { console.error('need RPC_URL, DESK, OFFICER_KEY_FILE'); process.exit(2); }
const deskAbi = JSON.parse(readFileSync(new URL('./build/CreditDesk.json', import.meta.url))).abi;
const officer = privateKeyToAccount(key);
const pc = createPublicClient({ chain: baseSepolia, transport: http(RPC) });
const wc = createWalletClient({ account: officer, chain: baseSepolia, transport: http(RPC) });
const D = (fn, args = []) => pc.readContract({ address: DESK, abi: deskAbi, functionName: fn, args });
const P = (fn, args = []) => pc.readContract({ address: ADDR.pool, abi: ABI.pool, functionName: fn, args });
const log = (o) => { const line = JSON.stringify({ t: new Date().toISOString(), ...o }); console.log(line); try { appendFileSync(LOG, line + '\n'); } catch {} };
const usd = (x) => Number(formatUnits(x, 6));
const inflight = new Set(); const dripped = new Set();

const SYSTEM = (maxLine) => `You are the credit officer at the Omnequa credit desk. You are an AI agent. This is a TEST network: the dollars are test tokens with no value, there is no real loan and no real money, and the applicant has been told so. Your job is a short, warm credit interview, the way a community lender would talk, ending in a decision about a small test credit line that the desk backs with its own stake.
Rules:
- Learn three things: what the money is for, how much they need (whole dollars, 1 to ${maxLine}), and when they will pay it back (every loan runs 30 days; interest is about 9 percent a year, a few cents on these amounts).
- Ask at most two questions in the whole conversation, one at a time. If you already know enough, decide now.
- Grant the amount asked, up to ${maxLine}. If they ask for more than ${maxLine}, grant ${maxLine} and say that is the desk's limit in this test. If they give no amount but a purpose and a repayment intent, grant ${maxLine}.
- Decline (backing 0) only for abuse, threats, or an applicant who says it is not for them. A wallet with a past default is declined.
- Never ask for personal information: no names, ID, phone, address, employer, income documents. If they volunteer any, say that everything written here is public on the test network and do not ask for more.
- Keep each reply under 60 words, plain words, no jargon, no bullet lists. When you grant, say the amount and that they can tap Borrow now. Do not repeat the test-money disclaimer in every message.
Respond with JSON only: {"reply": "<your message to the applicant>", "backing": <whole dollars 0 to ${maxLine}; the TOTAL line you set for this applicant after this message; keep the current backing if you are only asking a question>}`;

function transcript(thread) { return thread.map((m) => (m.from === 0 ? 'APPLICANT: ' : 'OFFICER: ') + m.text).join('\n'); }

async function decideClaude({ thread, facts, maxLine }) {
  const prompt = `Facts about this applicant (from the test network): current line from the desk ${facts.backing}; total credit limit ${facts.limit}; open loans ${facts.open}; loans fully repaid ${facts.repaid}; defaulted ${facts.defaulted ? 'YES' : 'no'}; test USDC in wallet ${facts.usdcBal}.\n\nConversation so far (oldest first):\n${transcript(thread)}\n\nWrite the officer's next message and the backing decision as JSON.`;
  const schema = JSON.stringify({ type: 'object', properties: { reply: { type: 'string' }, backing: { type: 'integer', minimum: 0, maximum: maxLine } }, required: ['reply', 'backing'], additionalProperties: false });
  const cwd = mkdtempSync(join(tmpdir(), 'desk-'));
  const args = ['-p', prompt, '--no-session-persistence', '--output-format', 'json', '--max-turns', '1', '--tools', '', '--system-prompt', SYSTEM(maxLine), '--json-schema', schema, ...(process.env.CLAUDE_MODEL ? ['--model', process.env.CLAUDE_MODEL] : [])];
  const out = await new Promise((resolve, reject) => { const ch = spawn('claude', args, { cwd, env: { ...process.env, CLAUDE_CODE_CHILD_SESSION: '1' }, stdio: ['ignore', 'pipe', 'pipe'] }); let o = '', e = ''; ch.stdout.on('data', (d) => (o += d)); ch.stderr.on('data', (d) => (e += d)); ch.on('error', reject); ch.on('close', (c) => (c === 0 ? resolve(o) : reject(new Error('claude exit ' + c + ': ' + e.slice(0, 300))))); setTimeout(() => { try { ch.kill('SIGKILL'); } catch {} }, 180000); });
  const j = JSON.parse(out); let r = j.structured_output ?? j.result; if (typeof r === 'string') { const m = r.match(/\{[\s\S]*\}/); r = JSON.parse(m ? m[0] : r); }
  const backing = Math.max(0, Math.min(maxLine, Math.round(Number(r.backing) || 0)));
  return { reply: String(r.reply || '').slice(0, 900), backing, cost: j.total_cost_usd };
}

function decideRules({ thread, facts, maxLine }) {
  if (facts.defaulted) return { reply: 'This wallet has a defaulted loan on the test network, so the desk cannot back it.', backing: 0 };
  const mine = thread.filter((m) => m.from === 0).map((m) => m.text).join(' ');
  const m = mine.match(/\$?\s*(\d+(?:\.\d+)?)/); const n = m ? Math.min(maxLine, Math.max(1, Math.round(Number(m[1])))) : 0;
  if (!n) return { reply: `Happy to help. How much do you need, up to $${maxLine}, and what is it for?`, backing: facts.backing };
  return { reply: `Thanks. The desk backs you with $${n} of test credit. Tap Borrow when you are ready; you pay it back within 30 days.`, backing: n };
}

const PREFUND = BigInt(Math.round(Number(process.env.PREFUND_USDC || 0.1) * 1e6)); // test USDC the officer sends a new applicant for the interest, when the faucet drip is refused
async function drip(address) {
  let faucet = null;
  if (process.env.CIRCLE_API_KEY) {
    // curl, not fetch: in this environment outbound HTTPS goes through a proxy that Node's fetch ignores; curl honours it.
    try { const out = await new Promise((resolve, reject) => { const ch = spawn('curl', ['-sS', '-m', '30', '-o', '/dev/null', '-w', '%{http_code}', '-X', 'POST', 'https://api.circle.com/v1/faucet/drips', '-H', 'Authorization: Bearer ' + process.env.CIRCLE_API_KEY, '-H', 'content-type: application/json', '--data', JSON.stringify({ address, blockchain: 'BASE-SEPOLIA', native: false, usdc: true, eurc: false })], { stdio: ['ignore', 'pipe', 'pipe'] }); let o = '', e = ''; ch.stdout.on('data', (d) => (o += d)); ch.stderr.on('data', (d) => (e += d)); ch.on('error', reject); ch.on('close', (c) => (c === 0 ? resolve(o.trim()) : reject(new Error('curl exit ' + c + ' ' + e.slice(0, 100))))); });
      const status = Number(out); faucet = { status }; if (status >= 200 && status < 300) return { faucet }; } catch (e) { faucet = { error: String(e.message).slice(0, 120) }; }
  }
  if (PREFUND === 0n) return { faucet, prefund: 'off' };
  try {
    const mine = await pc.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [officer.address] });
    if (mine < PREFUND) return { faucet, prefund: 'officer has no test USDC left' };
    const hash = await wc.writeContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'transfer', args: [address, PREFUND] }); const rc = await pc.waitForTransactionReceipt({ hash });
    return { faucet, prefund: { amount: usd(PREFUND), tx: hash, ok: rc.status === 'success' } };
  } catch (e) { return { faucet, prefund: { error: String(e.shortMessage || e.message).slice(0, 160) } }; }
}

async function handle(applicant) {
  const maxLine = usd(await D('maxLine'));
  const thread = (await D('thread', [applicant])).map((m) => ({ from: Number(m.from), at: Number(m.at), text: m.text }));
  const [backing, limit, ids, defaulted, usdcBal] = await Promise.all([D('backingOf', [applicant]), P('getBorrowLimit', [applicant]), P('getBorrowerLoanIds', [applicant]), P('defaultedLoans', [applicant]), pc.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [applicant] })]);
  let open = 0, repaid = 0; for (const id of ids) { const t = await P('getLoanTerms', [id]); const st = Number(t[0]); if (st === 1 || st === 2) open++; if (st === 3) repaid++; }
  const facts = { backing: usd(backing), limit: usd(limit[0]), open, repaid, defaulted: Number(defaulted) > 0, usdcBal: usd(usdcBal) };
  const d = MODE === 'rules' ? decideRules({ thread, facts, maxLine }) : await decideClaude({ thread, facts, maxLine });
  let total = BigInt(Math.round(d.backing * 1e6)); if (total > 0n && total < 1_000_000n) total = 1_000_000n;
  const freeStake = await D('freeStake'); const cur = backing;
  if (total > cur && total - cur > freeStake) { total = cur + freeStake; if (total < 1_000_000n) total = cur; d.reply += total === cur ? ' The desk has no free stake left right now; please try again later.' : ` (The desk can only cover $${usd(total)} right now.)`; }
  let hash;
  try { const { request } = await pc.simulateContract({ address: DESK, abi: deskAbi, functionName: 'reply', args: [applicant, d.reply, total], account: officer }); hash = await wc.writeContract(request); }
  catch (e) { const { request } = await pc.simulateContract({ address: DESK, abi: deskAbi, functionName: 'reply', args: [applicant, d.reply, cur], account: officer }); hash = await wc.writeContract(request); total = cur; log({ ev: 'backing-unchanged', applicant, why: String(e.shortMessage || e.message).slice(0, 200) }); }
  const rc = await pc.waitForTransactionReceipt({ hash });
  let drip_ = null; if (total > 0n && facts.usdcBal < usd(PREFUND) && !dripped.has(applicant)) { dripped.add(applicant); drip_ = await drip(applicant); }
  log({ ev: 'replied', applicant, msgs: thread.length + 1, backing: usd(total), reply: d.reply, tx: hash, ok: rc.status === 'success', cost: d.cost, drip: drip_ });
}

log({ ev: 'start', mode: MODE, desk: DESK, officer: officer.address, rpc: RPC });
for (;;) {
  try {
    const pending = await D('pending');
    for (const a of pending) { if (inflight.has(a)) continue; inflight.add(a); handle(a).catch((e) => log({ ev: 'error', applicant: a, err: String(e.shortMessage || e.message).slice(0, 300) })).finally(() => inflight.delete(a)); }
  } catch (e) { log({ ev: 'poll-error', err: String(e.shortMessage || e.message).slice(0, 200) }); }
  await new Promise((r) => setTimeout(r, POLL));
}
