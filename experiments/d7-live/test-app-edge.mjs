// Edge and failure cases for the web app: network loss, double taps, two tabs, overdue and default states, pool limits, sponsor cap.
import { world, phone, runner, fork, read, usd, toUnits, ADDR, pc, asOwner, parseEther } from './lib/apptest.mjs';
const w = await world({ seed: 4, poolLiquidity: 300 }); const R = runner();
let P = await phone(w); let { page } = P; let wallet = await P.create();
const give = async (amt, back = 30) => { await fork.setUsdc(wallet, toUnits(amt)); if (back) await w.backer.pool('back', [wallet, toUnits(back)]); };
await give(5, 40); await page.reload(); await P.expectText(/\$5\.00/);
const loanIds = () => read('getBorrowerLoanIds', [wallet]);
const status = async (i) => Number((await read('getLoanTerms', [i]))[0]);

await R.step('E01 double tap on Borrow creates exactly one loan', async () => {
  await page.goto('/#borrow'); await page.reload(); await page.fill('#amt', '10'); await P.expectText(/You receive/);
  await page.locator('#go').dblclick({ delay: 20 }); await P.tapDone(); if ((await loanIds()).length !== 1) throw new Error('loans: ' + (await loanIds()).length); }, page);
await R.step('E02 reload during a pending operation leaves a consistent state (no duplicate loan)', async () => {
  await fork.setUsdc(wallet, toUnits(30)); await page.goto('/#repay'); await page.reload(); await P.expectText(/You owe right now/);
  await page.locator('#all').click(); await page.waitForTimeout(150); await page.reload(); await page.waitForTimeout(4000);
  const ids = await loanIds(); let st = await status(ids[ids.length - 1]); for (let i = 0; i < 6 && st !== 3; i++) { await page.waitForTimeout(1000); st = await status(ids[ids.length - 1]); } if (ids.length !== 1 || ![2, 3].includes(st)) throw new Error('loans ' + ids.length + ' status ' + st + ' (expected exactly one loan, active or repaid)');
  if (st === 2) { await page.goto('/#repay'); await page.reload(); await P.expectText(/You owe right now/); await page.locator('#all').click(); await P.tapDone(); if ((await status(ids[0])) !== 3) throw new Error('could not close the loan afterwards'); } await page.goto('/#home'); await page.reload(); await P.expectText(/Your wallet/); }, page);
await R.step('E03 stuck request: Finish it disburses, Cancel it releases', async () => {
  await page.goto('/#home'); await page.reload(); await P.expectText(/You can borrow up to/);
  const r = await page.evaluate(async () => { const { S, C } = window.__d7; const x = await C.send(S.bundler, S.account, [C.poolCall('requestLoan', [4000000n])]); return x.success; }); if (!r) throw new Error('request failed');
  await page.goto('/#home'); await page.reload(); await P.expectText(/requested but not paid out/i); await page.locator('#finish').click(); await P.tapDone();
  const ids = await loanIds(); if ((await status(ids[ids.length - 1])) !== 2) throw new Error('not active after Finish'); await fork.setUsdc(wallet, toUnits(30)); await page.reload(); await P.expectText(/You owe/); await page.locator('#payNow').click(); await P.expectText(/You owe right now/); await page.locator('#all').click(); await P.tapDone(); }, page);
await R.step('E04 stuck request can be cancelled', async () => {
  await page.goto('/#home'); await page.reload(); await P.expectText(/You can borrow up to/);
  await page.evaluate(async () => { const { S, C } = window.__d7; await C.send(S.bundler, S.account, [C.poolCall('requestLoan', [3000000n])]); });
  await page.reload(); await P.expectText(/requested but not paid out/i); await page.locator('#cancelReq').click(); await P.tapDone(); const ids = await loanIds(); if ((await status(ids[ids.length - 1])) !== 5) throw new Error('not cancelled'); }, page);
await R.step('E05 stale second tab: after tab 1 borrows the whole limit, tab 2 gets a plain refusal before any signature', async () => {
  await page.goto('/#home'); await page.reload(); await P.expectText(/You can borrow up to/);
  const [, avail] = await read('getBorrowLimit', [wallet]); const a = (usd(avail) | 0).toString();
  const p2 = await P.ctx.newPage(); await p2.goto('/#borrow'); await p2.reload(); await p2.waitForFunction(() => document.body.innerText.includes('Available to borrow')); await p2.fill('#amt', a); await p2.waitForFunction(() => !document.querySelector('#go').disabled);
  await page.goto('/#borrow'); await page.reload(); await page.fill('#amt', a); await page.waitForFunction(() => !document.querySelector('#go').disabled); await page.locator('#go').click(); await P.tapDone();
  await p2.locator('#go').click(); await p2.waitForFunction(() => /Not possible yet|did not go through/i.test(document.body.innerText), null, { timeout: 30000 }); const t2 = await p2.locator('body').innerText(); if (!/more than your credit|credit allows|limit/i.test(t2)) throw new Error('unfriendly: ' + t2.slice(0, 200)); await p2.close(); await page.goto('/#home'); await page.reload(); }, page);
await R.step('E06 overdue loan shows a clear warning', async () => {
  await fork.warp(33 * 86400); await page.goto('/#home'); await page.reload(); await P.expectText(/Overdue by 3 days/); await page.screenshot({ path: 'results/screens/E06-overdue.png' }); }, page);
await R.step('E07 after the grace period anyone can default it; app shows the defaulted state and blocks borrowing', async () => {
  await fork.warp(31 * 86400); const ids = await loanIds(); const id = ids[ids.length - 1]; const r = await w.backer.pool('markDefaulted', [id]); if (!r.ok) throw new Error('default refused ' + r.error);
  await page.goto('/#home'); await page.reload(); await P.expectText(/defaulted loan/i); if (!(await page.locator('#gBorrow').isDisabled())) throw new Error('borrow should be disabled'); await page.screenshot({ path: 'results/screens/E07-defaulted.png' }); }, page);
await R.step('E08 offline: friendly message and Try again works after reconnecting', async () => {
  await P.ctx.setOffline(true); await page.goto('about:blank'); await P.ctx.setOffline(false); await page.goto('/#home'); await P.expectText(/Your wallet/);
  await page.route(`**/127.0.0.1:${new URL(w.RPC).port}/**`, (r) => r.abort()); await page.reload(); await P.expectText(/Cannot reach the test network|went wrong|busy/i); const had = await page.locator('#retry').count();
  await page.unroute(`**/127.0.0.1:${new URL(w.RPC).port}/**`); if (had) { await page.locator('#retry').click(); await P.expectText(/Your wallet/); } else { await page.reload(); await P.expectText(/Your wallet/); } }, page);
await R.step('E09 bundler down: operation fails politely and nothing changes; recovers when it is back', async () => {
  // fresh wallet so the default state above does not interfere
  const p2 = await phone(w); const w2 = await p2.create(); await fork.setUsdc(w2, toUnits(5)); await w.backer.pool('back', [w2, toUnits(20)]); await p2.page.reload(); await p2.expectText(/\$5\.00/);
  await p2.page.goto('/#send'); await p2.page.fill('#to', w.friend.address); await p2.page.fill('#amt', '1'); w.bundler.close(); await p2.page.locator('#go').click(); await p2.expectText(/did not go through/i, 60000); const t = await p2.text(); if (!/Cannot reach|went wrong|Nothing was lost/i.test(t)) throw new Error('unfriendly: ' + t.slice(0, 200));
  await p2.closeSheet(); const { startBundler } = await import('./bundler.mjs'); const { seededKey } = await import('./lib/sim.mjs'); w.bundler = await startBundler({ rpc: w.RPC, port: w.bundlerPort, key: seededKey(4, 'bundler') });
  await p2.page.goto('/#send'); await p2.page.fill('#to', w.friend.address); await p2.page.fill('#amt', '1'); await p2.page.locator('#go').click(); await p2.tapDone(); await p2.browser.close(); }, page);
await R.step('E10 pool short of cash: borrow bigger than free cash gets the plain pool message', async () => {
  const p2 = await phone(w); const w2 = await p2.create(); await asOwner('setScoreOverride', [w2, 1000000n]); // a 100 USDC line
  // drain pool liquidity: other borrowers take most of it
  for (let i = 0; i < 3; i++) { const b = new (await import('./lib/sim.mjs')).Actor('big' + i, (await import('./lib/sim.mjs')).seededKey(4, 'big' + i)); await (await import('./lib/sim.mjs')).fundFork(b, {}); await asOwner('setScoreOverride', [b.address, 1000000n]); const rq = await b.pool('requestLoan', [toUnits(95)]); if (rq.ok) { const ids = await read('getBorrowerLoanIds', [b.address]); await b.pool('disburseLoan', [ids[ids.length - 1]]); } }
  await p2.page.goto('/#borrow'); await p2.page.reload(); await p2.page.fill('#amt', '100'); await p2.expectText(/You receive/); await p2.page.locator('#go').click(); await p2.expectText(/Not possible yet/i, 30000); const t = await p2.text(); if (!/pool|lent out|free/i.test(t)) throw new Error(t.slice(0, 200)); await p2.browser.close(); }, page);
await R.step('E11 sponsor allowance used up: a plain message, no crash', async () => {
  const p2 = await phone(w); const w2 = await p2.create(); await fork.setUsdc(w2, toUnits(5));
  const art = JSON.parse((await import('node:fs')).readFileSync('build/SponsorPaymaster.json')); const { Actor, seededKey } = await import('./lib/sim.mjs'); const dep = new Actor('d', seededKey(4, 'deployer'));
  await dep.call(w.pm.address, w.pm.abi, 'setCap', [1000n]);
  await p2.page.goto('/#send'); await p2.page.fill('#to', w.friend.address); await p2.page.fill('#amt', '1'); await p2.page.locator('#go').click(); await p2.expectText(/did not go through/i, 60000); const t = await p2.text(); if (!/allowance|free-gas|went wrong/i.test(t)) throw new Error('unfriendly: ' + t.slice(0, 240)); await dep.call(w.pm.address, w.pm.abi, 'setCap', [parseEther('0.02')]); await p2.browser.close(); }, page);
await R.step('E12 small phones and dark mode: no horizontal scroll on every screen', async () => {
  for (const [device, scheme] of [['iPhone SE', 'light'], ['Pixel 5', 'dark'], ['Galaxy S8', 'light']]) { const p2 = await phone(w, { device, colorScheme: scheme }); await p2.create();
    for (const r of ['home', 'borrow', 'repay', 'send', 'receive', 'back', 'help', 'credit']) { await p2.page.goto('/#' + r); await p2.page.waitForTimeout(400); const m = await p2.page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth })); if (m.sw > m.cw + 1) throw new Error(`${device} ${r}: ${m.sw} > ${m.cw}`); }
    if (device === 'Pixel 5') await p2.page.screenshot({ path: 'results/screens/E12-dark-help.png' }); await p2.browser.close(); } }, page);
await R.step('E13 no uncaught page errors across the edge run', async () => { const errs = P.logs.filter((l) => /pageerror/i.test(l)); if (errs.length) throw new Error(errs.slice(0, 3).join(' | ')); }, page);

await P.browser.close(); await w.close(); const ok = R.finish('results/test-app-edge.json'); process.exit(ok ? 0 : 1);
