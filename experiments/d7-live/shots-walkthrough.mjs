// Walkthrough screenshots on a fork: the exact steps a first tester takes. Output results/walk/*.png
import { world, phone, toUnits, fork } from './lib/apptest.mjs';
const w = await world({ seed: 5, bundlerPort: 4345, webPort: 4181, poolLiquidity: 300, deskFund: 20, daemonMode: process.env.MODE || 'claude' });
const p = await phone(w);
const shot = (n) => p.page.screenshot({ path: `results/walk/${n}.png` });
const settle = () => p.page.waitForTimeout(400);
try {
  await p.page.goto('/'); await p.expectText(/Create my wallet/); await settle(); await shot('01-welcome');
  await p.page.getByRole('button', { name: 'Create my wallet' }).click(); await p.expectText(/Your wallet/); await p.expectText(/\$0\.00/); await settle(); await shot('02-home-new');
  const wallet = await p.addr();
  await p.page.goto('/#receive'); await p.expectText(/Get test dollars/); await settle(); await shot('03-receive-faucet');
  await fork.setUsdc(wallet, toUnits(20)); await p.page.goto('/#home'); await p.page.reload(); await p.expectText(/\$20\.00/); await settle(); await shot('04-home-funded');
  await p.page.goto('/#credit'); await p.page.waitForSelector('.bub.desk'); await settle(); await shot('05-credit-desk');
  await p.page.fill('#msg', 'I would like to borrow 5 dollars to buy phone credit so I can take tailoring orders. I will pay it back in two weeks when the orders are paid.'); await p.page.locator('#send').click(); await p.tapDone();
  await p.page.waitForFunction(() => document.querySelector('#granted'), null, { timeout: 240000 }); await settle(); await p.page.screenshot({ path: 'results/walk/05b-credit-granted.png', fullPage: true });
  await p.page.goto('/#home'); await p.page.reload(); await p.expectText(/You can borrow up to/); await p.page.waitForFunction(() => /\$[1-5]\.00/.test(document.body.innerText)); await settle(); await shot('05c-home-backed');
  await p.page.goto('/#borrow'); await p.expectText(/Available to borrow/); await p.page.fill('#amt', '5'); await p.expectText(/You receive/); await settle(); await shot('06-borrow-terms');
  await p.page.locator('#go').click(); await p.expectText(/Done/, 60000); await settle(); await shot('07-borrow-done');
  await p.page.locator('#overlayActions button', { hasText: 'OK' }).click(); await p.page.goto('/#home'); await p.page.reload(); await p.expectText(/\$25\.00/); await settle(); await shot('08-home-loan');
  await p.page.goto('/#repay'); await p.page.reload(); await p.expectText(/You owe right now/); await settle(); await shot('09-repay');
  await p.page.locator('#all').click(); await p.expectText(/Done/, 60000); await settle(); await shot('10-repay-done');
  await p.page.locator('#overlayActions button', { hasText: 'OK' }).click(); await p.page.goto('/#home'); await p.page.reload(); await p.expectText(/Your wallet/); await settle(); await shot('11-home-repaid');
  await p.page.goto('/#help'); await p.expectText(/recovery code/i); await settle(); await shot('12-help-recovery');
  console.log('ok', wallet);
} catch (e) { console.log('FAIL', e.message); await shot('FAIL'); } finally { await p.browser.close(); await w.close(); }
