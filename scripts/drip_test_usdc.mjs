// Send a bounded amount of test USDC from the team test wallet to an allowlisted address on Base Sepolia.
// Runs from .github/workflows/drip-test-usdc.yml; rules in drip_rules.mjs; allowlist in drip_allowlist.json.
// Environment: RECIPIENT (required), AMOUNT_USDC (default 5), DRY_RUN=true (read-only plan),
//   TEST_WALLET_PRIVATE_KEY (live runs only), RPC_URL, ALLOWLIST (path), GITHUB_TOKEN, GITHUB_REPOSITORY,
//   GITHUB_RUN_ID (daily total from today's runs of this workflow), DAILY_SPENT_USDC (dry runs only, when no token).
// Exit codes: 0 sent or dry run, 3 refused by a rule, 2 bad input or missing prerequisite, 1 transaction failed.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { JsonRpcProvider, Wallet, Contract, isAddress, getAddress, parseUnits, formatUnits } from 'ethers';
import { DEFAULT_AMOUNT_USDC, loadAllowlist, parseAmount, runsSince, spentToday, decide } from './drip_rules.mjs';

const USDC = '0x036CbD53842c5426634e7929541eC2318f3dCF7e';
const TEAM = '0x38e9845A1Df22c59Bfc693bf2CEAa3361158d6d1';
const WORKFLOW_FILE = 'drip-test-usdc.yml';
const here = dirname(fileURLToPath(import.meta.url));
const out = (o) => console.log(JSON.stringify(o));
const fail = (code, msg) => { console.error(msg); process.exit(code); };

const dryRun = String(process.env.DRY_RUN || '').toLowerCase() === 'true';
const raw = process.env.RECIPIENT || '';
if (!isAddress(raw)) fail(2, 'RECIPIENT is not a valid address');
const recipient = getAddress(raw);
const amount = parseAmount(process.env.AMOUNT_USDC || String(DEFAULT_AMOUNT_USDC));
const allowlist = loadAllowlist(JSON.parse(readFileSync(process.env.ALLOWLIST || join(here, 'drip_allowlist.json'), 'utf8')));
const entry = allowlist.get(recipient.toLowerCase()) || null;

async function fetchSpentToday() {
  const token = process.env.GITHUB_TOKEN, repo = process.env.GITHUB_REPOSITORY, runId = process.env.GITHUB_RUN_ID || '';
  if (!token || !repo) {
    if (!dryRun) fail(2, 'live run needs GITHUB_TOKEN and GITHUB_REPOSITORY to compute the daily total');
    return { spent: Number(process.env.DAILY_SPENT_USDC || 0), source: 'DAILY_SPENT_USDC (dry run, no token)' };
  }
  // Today's runs are selected here, not by a server-side date filter: the API lists runs newest first, so pages are
  // read until one holds a run older than today. Many runs in one day (for example dry runs) cannot hide live runs.
  const since = `${new Date().toISOString().slice(0, 10)}T00:00:00Z`;
  const headers = { authorization: `Bearer ${token}`, accept: 'application/vnd.github+json', 'x-github-api-version': '2022-11-28' };
  const today = [];
  let page = 1, seen = 0;
  for (; page <= 10; page++) {
    const res = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=100&page=${page}`, { headers });
    if (!res.ok) fail(2, `GitHub API ${res.status} while listing this workflow's runs`);
    const batch = (await res.json()).workflow_runs || [];
    const fresh = runsSince(batch, since);
    seen += batch.length; today.push(...fresh);
    if (batch.length < 100 || fresh.length < batch.length) break;
  }
  if (page > 10) fail(2, 'more than 1,000 runs today; refusing to count');
  return { spent: spentToday(today, runId), source: `${today.length} runs since ${since} (${seen} read)` };
}

const provider = new JsonRpcProvider(process.env.RPC_URL || 'https://base-sepolia-rpc.publicnode.com', undefined, { batchMaxCount: 1 });
const net = await provider.getNetwork();
if (Number(net.chainId) !== 84532) fail(2, `wrong chain ${String(net.chainId)}`);
const usdc = new Contract(USDC, ['function balanceOf(address) view returns (uint256)', 'function transfer(address,uint256) returns (bool)'], provider);
const [recBal, teamBal, block, daily] = await Promise.all([usdc.balanceOf(recipient), usdc.balanceOf(TEAM), provider.getBlockNumber(), fetchSpentToday()]);
const recipientBalance = Number(formatUnits(recBal, 6)), teamBalance = Number(formatUnits(teamBal, 6));
const plan = { block, recipient, label: entry ? entry.label : null, amountUsdc: amount, recipientUsdc: recipientBalance, teamUsdc: teamBalance, spentTodayUsdc: daily.spent, spentSource: daily.source, dryRun };
const verdict = decide({ entry, amount, recipientBalance, teamBalance, spent: daily.spent, teamIsRecipient: recipient.toLowerCase() === TEAM.toLowerCase() });
if (!verdict.ok) { out({ ...plan, refused: verdict.reason }); process.exit(3); }
if (dryRun) { out({ ...plan, wouldSend: true }); process.exit(0); }

const key = process.env.TEST_WALLET_PRIVATE_KEY;
if (!key) fail(2, 'TEST_WALLET_PRIVATE_KEY is not set');
const wallet = new Wallet(key, provider);
if (wallet.address.toLowerCase() !== TEAM.toLowerCase()) fail(2, 'the key does not control the team wallet');
const tx = await usdc.connect(wallet).transfer(recipient, parseUnits(String(amount), 6));
out({ ...plan, hash: tx.hash, submitted: true });
const receipt = await tx.wait(1);
out({ hash: receipt.hash, status: receipt.status, block: receipt.blockNumber });
process.exit(receipt.status === 1 ? 0 : 1);
