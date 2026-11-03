// The core suite with real transactions, small amounts. Live (RPC_URL unset) or on a fork (DRYRUN=1, funds the treasury with cheats).
// Passkey smart wallets, sponsored gas, own bundler in-process. Prints every tx hash.
import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'node:fs';
import { RPC, KEYS, key, pc, eoa, sleep, usdcOf, P, transferUsdc, sendEth, smartWallet, ADDR, ABI, usd, toUnits, parseEther, poolCall, usdcCall, startBundler, deployPaymaster, friendly } from './common.mjs';
import { maxUint256 } from 'viem';

const DRY = process.env.DRYRUN === '1'; const treasury = eoa('sim-treasury'); const results = []; const hashes = [];
if (DRY) { const { fork, Actor } = await import('../lib/sim.mjs'); await fork.setEth(treasury.address, parseEther('1')); await fork.setUsdc(treasury.address, toUnits(20)); await fork.setEth(eoa('sim-bundler').address, parseEther('1')); }
let cfg; const cfgFile = KEYS + 'live-config.json';
if (DRY) { const pm = await deployPaymaster({ rpc: RPC, key: key('sim-treasury'), cap: parseEther('0.02'), deposit: parseEther('0.1'), stake: parseEther('0.01') }); cfg = { paymaster: pm.address }; }
else { if (!existsSync(cfgFile)) { console.log('No live-config.json: run live/setup.mjs after the treasury is funded.'); process.exit(2); } cfg = JSON.parse(readFileSync(cfgFile, 'utf8')); }
const bundler = await startBundler({ rpc: RPC, port: 4339, key: key('sim-bundler'), verificationGas: BigInt(process.env.VERIF_GAS || (DRY ? 2500000 : 1200000)) });
cfg.bundler = bundler.url;

const tb = await usdcOf(treasury.address); console.log('RPC', RPC.includes('127.0.0.1') ? 'fork' : RPC, '| treasury USDC', usd(tb), '| pool assets', usd(await P('totalAssets')), '| free cash', usd((await P('lenderCash')) - (await P('reservedLiquidity'))));
if (tb < toUnits(12)) { console.log('Treasury needs at least 12 test USDC.'); process.exit(2); }
const stamp = Date.now().toString(36); const B = await smartWallet('backer-' + stamp, cfg), W = await smartWallet('borrower-' + stamp, cfg);
console.log('backer', B.address, '\nborrower', W.address);

let cur; const checks = []; const eq = (n, got, want) => checks.push({ n, ok: String(got) === String(want), got: String(got), want: String(want) }); const yes = (n, c, note = '') => checks.push({ n, ok: !!c, got: String(!!c), want: 'true', note });
async function step(name, fn) { const t = Date.now(); checks.length = 0; try { await fn(); } catch (e) { checks.push({ n: 'EXCEPTION ' + String(e.shortMessage || e.message).slice(0, 160), ok: false, got: 'x', want: 'none' }); }
  const ok = checks.every((c) => c.ok); results.push({ name, ok, ms: Date.now() - t, checks: [...checks] }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name} (${Date.now() - t} ms)`); for (const c of checks.filter((c) => !c.ok)) console.log('      x', c.n, '| got', c.got, 'want', c.want); }
const rec = (r) => { if (r.tx) hashes.push({ label: r.label, tx: r.tx }); return r; };

await step('L0 fund the wallets from the treasury (plain USDC transfers)', async () => {
  rec({ label: 'treasury -> backer 8 USDC', tx: await transferUsdc(treasury, B.address, toUnits(8)) }); rec({ label: 'treasury -> borrower 1 USDC', tx: await transferUsdc(treasury, W.address, toUnits(1)) });
  eq('backer has 8', usd(await usdcOf(B.address)), 8); eq('borrower has 1', usd(await usdcOf(W.address)), 1); });
await step('L1 a fresh passkey wallet with no credit is refused in plain words', async () => {
  eq('preflight says NoCredit', await W.preflight('requestLoan', [toUnits(3)]), 'NoCredit');
  const r = rec(await W.op('borrow without credit (mined, inner revert)', [poolCall('requestLoan', [toUnits(3)]), poolCall('disburseLoan', [(await P('getAllLoanIds')).length + 1])])); eq('operation reports failure', r.ok, false); yes('revert named NoCredit', /NoCredit/.test(r.reason || ''), r.reason); });
await step('L2 backer stakes 6 in one operation (approve + stake)', async () => {
  const r = rec(await B.op('backer approve+stake 6', [usdcCall('approve', [ADDR.pool, toUnits(6)]), poolCall('stake', [toUnits(6)])])); eq('ok', r.ok, true, r.reason); eq('stake is 6', usd(await P('stakeOf', [B.address])), 6); });
await step('L3 backer backs the borrower with 5; the borrower limit becomes 5', async () => {
  const r = rec(await B.op('backer back borrower 5', [poolCall('back', [W.address, toUnits(5)])])); eq('ok', r.ok, true); const [lim] = await P('getBorrowLimit', [W.address]); eq('limit 5', usd(lim), 5); });
await step('L4 refusals with real transactions: committed stake, self-backing, below the minimum', async () => {
  eq('unstake committed (preflight)', await B.preflight('unstake', [toUnits(2)]), 'StakeCommitted'); eq('self-backing (preflight)', await B.preflight('back', [B.address, toUnits(1)]), 'SelfBacking'); eq('below minimum (preflight)', await B.preflight('back', [W.address, 100000n]), 'BackingTooSmall'); });
let loanId;
await step('L5 borrower borrows 4 (request + payout in one operation) and owns the cash', async () => {
  const ids = await P('getAllLoanIds'); loanId = (ids.length ? ids[ids.length - 1] : 0n) + 1n;
  const r = rec(await W.op('borrower borrow 4', [poolCall('requestLoan', [toUnits(4)]), poolCall('disburseLoan', [loanId])])); eq('ok', r.ok, true); if (!r.ok) console.log('   reason:', r.reason);
  eq('borrower holds 5', usd(await usdcOf(W.address)), 5); eq('loan active', Number((await P('getLoanTerms', [loanId]))[0]), 2); });
await step('L6 over the limit is refused before any signature', async () => { eq('borrow 2 more -> BorrowLimitExceeded', await W.preflight('requestLoan', [toUnits(2)]), 'BorrowLimitExceeded'); });
await step('L7 borrower repays everything in one operation (approve + repay)', async () => {
  const owed = await P('getCurrentOutstandingAmount', [loanId]); const want = owed + 20000n; console.log('   owed', usd(owed));
  const r = rec(await W.op('borrower repay all', [usdcCall('approve', [ADDR.pool, want]), poolCall('repayLoan', [loanId, want])])); eq('ok', r.ok, true); if (!r.ok) console.log('   reason:', r.reason);
  eq('loan repaid', Number((await P('getLoanTerms', [loanId]))[0]), 3); yes('history recorded (completed loans = 1)', Number(await P('completedLoans', [W.address])) === 1); });
await step('L8 a second, smaller loan works and is repaid (the cycle repeats)', async () => {
  const ids = await P('getAllLoanIds'); const id2 = ids[ids.length - 1] + 1n;
  const a = rec(await W.op('borrower borrow 2 (second)', [poolCall('requestLoan', [toUnits(2)]), poolCall('disburseLoan', [id2])])); eq('borrow ok', a.ok, true);
  const owed = await P('getCurrentOutstandingAmount', [id2]); const r = rec(await W.op('borrower repay second', [usdcCall('approve', [ADDR.pool, owed + 20000n]), poolCall('repayLoan', [id2, owed + 20000n])])); eq('repay ok', r.ok, true); eq('repaid', Number((await P('getLoanTerms', [id2]))[0]), 3); });
await step('L9 backer lowers the backing to zero and unstakes everything', async () => {
  const a = rec(await B.op('backer lower backing to 0', [poolCall('back', [W.address, 0n])])); eq('lower ok', a.ok, true, a.reason);
  const r = rec(await B.op('backer unstake 6', [poolCall('unstake', [toUnits(6)])])); eq('unstake ok', r.ok, true, r.reason); eq('stake 0', usd(await P('stakeOf', [B.address])), 0); });
await step('L10 recycle: both wallets send their USDC back to the treasury', async () => {
  for (const w of [B, W]) { const bal = await usdcOf(w.address); if (bal > 0n) rec(await w.op('return USDC to treasury', [usdcCall('transfer', [treasury.address, bal])])); }
  const t = await usdcOf(treasury.address); yes('treasury has its USDC back (within interest)', usd(t) >= usd(tb) - 0.001, String(usd(t))); });

const ok = results.filter((r) => r.ok).length; mkdirSync('results', { recursive: true });
const out = { when: new Date().toISOString(), rpc: DRY ? 'fork' : RPC, paymaster: cfg.paymaster, backer: B.address, borrower: W.address, results, hashes };
writeFileSync(`results/live-suite-${DRY ? 'fork' : 'live'}-${stamp}.json`, JSON.stringify(out, null, 1));
console.log(`\n${ok}/${results.length} steps pass; ${hashes.length} transactions`); for (const h of hashes) console.log(' ', h.label, h.tx);
bundler.close(); process.exit(ok === results.length ? 0 : 1);
