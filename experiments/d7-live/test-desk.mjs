// Headless phone test of the in-app credit desk against a fork. MODE=rules (default) or claude (one real officer run).
import { world, phone, runner, read, usd, toUnits } from './lib/apptest.mjs';
const MODE = process.env.MODE || 'rules';
const PB = Number(process.env.PORT_BASE || 0); const w = await world({ seed: 7 + PB, bundlerPort: 4347 + PB, webPort: 4187 + PB, poolLiquidity: 100, deskFund: 12, daemonMode: MODE });
const p = await phone(w); const R = runner(); const { page } = p;
const shot = (n) => page.screenshot({ path: `results/screens/desk-${n}.png` });
const waitReply = async (n, t = MODE === 'claude' ? 240000 : 40000) => page.waitForFunction((k) => document.querySelectorAll('.bub.desk').length >= k, n, { timeout: t });
try {
  let wallet;
  await R.step('D01 create wallet, home offers the credit desk', async () => { wallet = await p.create(); await p.expectText(/Ask the credit desk/); }, page);
  await R.step('D02 credit screen shows the officer greeting and no backing', async () => { await page.goto('/#credit'); await page.waitForSelector('.bub.desk', { timeout: 20000 }); if ((await page.locator('.bub.desk').count()) !== 1) throw new Error('greeting missing'); if (await page.locator('#toBorrow').isVisible()) throw new Error('Borrow offered before any grant'); await shot('01-greeting'); }, page);
  await R.step('D03 first message (no amount) is answered by the officer with a question or a grant', async () => {
    await page.fill('#msg', 'I want to buy seed for my garden and sell vegetables at the market. I will pay back after the harvest in three weeks.'); await page.locator('#send').click(); await p.tapDone();
    await page.waitForFunction(() => document.querySelectorAll('.bub.me').length === 1); await waitReply(2); await shot('02-first-reply');
    const t = await p.text(); console.log('   officer:', (await page.locator('.bub.desk').last().innerText()).slice(0, 200));
  }, page);
  await R.step('D04 second message with an amount leads to a grant of at most $5 and the Borrow button', async () => {
    const granted = await page.locator('#granted').count();
    if (!granted) { await page.fill('#msg', 'I need 5 dollars.'); await page.locator('#send').click(); await p.tapDone(); await waitReply(3); }
    await page.waitForFunction(() => document.querySelector('#granted'), null, { timeout: MODE === 'claude' ? 240000 : 40000 });
    const b = await read('getBorrowLimit', [wallet]); if (usd(b[0]) < 1 || usd(b[0]) > 5) throw new Error('limit ' + usd(b[0])); if (!(await page.locator('#toBorrow').isVisible())) throw new Error('no Borrow button'); await shot('03-granted');
    console.log('   officer:', (await page.locator('.bub.desk').last().innerText()).slice(0, 200), '| limit', usd(b[0]));
  }, page);
  await R.step('D05 desk stake is committed by the backing (desk is the backer)', async () => { const bk = await read('getBacking', [w.desk.address, wallet]); if (bk[0] + bk[1] === 0n) throw new Error('desk not backing'); }, page);
  await R.step('D06 borrow against the desk line works from the chat', async () => { await page.locator('#toBorrow').click(); await p.expectText(/Available to borrow/); const b = await read('getBorrowLimit', [wallet]); await page.fill('#amt', String(Math.min(5, Math.floor(usd(b[1]))))); await p.expectText(/You receive/); await page.locator('#go').click(); await p.tapDone(); await page.goto('/#home'); await page.reload(); await p.expectText(/You owe/); }, page);
  await R.step('D07 spam guard: a fourth unanswered message is refused before any signature', async () => {
    // stop the officer, write three, the fourth is disabled
    try { w.daemon?.kill('SIGKILL'); } catch {}
    await page.goto('/#credit'); for (let i = 0; i < 3; i++) { await page.fill('#msg', 'hello ' + i); await page.locator('#send').click(); await p.tapDone(); }
    await page.waitForFunction(() => document.querySelector('#send').disabled, null, { timeout: 20000 }); await p.expectText(/wait for the officer/i); await shot('04-wait');
  }, page);
  await R.step('D08 a message over 1000 characters is refused locally', async () => { await page.evaluate(() => { document.querySelector('#send').disabled = false; document.querySelector('#msg').removeAttribute('maxlength'); document.querySelector('#msg').value = 'x'.repeat(1001); }); await page.locator('#send').click(); await p.expectText(/under 1000/); }, page);
  await R.step('D09 maxLine is enforced on chain: officer cannot set a line above it', async () => {
    const { createWalletClient, http } = await import('viem'); const { privateKeyToAccount } = await import('viem/accounts'); const { baseSepolia } = await import('viem/chains');
    const wc = createWalletClient({ account: privateKeyToAccount(w.officerKey), chain: baseSepolia, transport: http(w.RPC) });
    let err = null; try { await wc.writeContract({ address: w.desk.address, abi: w.desk.abi, functionName: 'reply', args: [wallet, 'too much', toUnits(50)] }); } catch (e) { err = String(e.message); }
    if (!/AboveMaxLine/.test(err || '')) throw new Error('expected AboveMaxLine, got ' + (err || 'success').slice(0, 120));
  }, page);
  await R.step('D10 only the officer can reply', async () => { let err = null; try { await w.friend.pool; await w.backer.write?.(); } catch {} const { createWalletClient, http } = await import('viem'); const { privateKeyToAccount } = await import('viem/accounts'); const { baseSepolia } = await import('viem/chains'); const { seededKey } = await import('./lib/sim.mjs'); const wc = createWalletClient({ account: privateKeyToAccount(seededKey(7, 'friend')), chain: baseSepolia, transport: http(w.RPC) }); try { await wc.writeContract({ address: w.desk.address, abi: w.desk.abi, functionName: 'reply', args: [wallet, 'hi', 0n] }); } catch (e) { err = String(e.message); } if (!/NotOfficer/.test(err || '')) throw new Error('expected NotOfficer'); }, page);
  await R.step('D11 no uncaught page errors', async () => { const errs = p.logs.filter((l) => /pageerror/i.test(l)); if (errs.length) throw new Error(errs.slice(0, 2).join(' | ')); }, page);
} finally { await p.browser.close(); await w.close(); }
process.exit(R.finish(`results/test-desk-${MODE}.json`) ? 0 : 1);
