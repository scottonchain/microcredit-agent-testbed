import { world, phone, fork, read, usd, toUnits } from './lib/apptest.mjs';
const w = await world({ seed: 5, poolLiquidity: 300 }); const P = await phone(w); const { page } = P; const wallet = await P.create();
await fork.setUsdc(wallet, toUnits(5)); await w.backer.pool('back', [wallet, toUnits(40)]); await page.reload(); await P.expectText(/\$5\.00/);
const p2 = await P.ctx.newPage(); p2.on('console', (m) => console.log('p2', m.type(), m.text().slice(0, 150))); page.on('console', (m) => console.log('p1', m.type(), m.text().slice(0, 150)));
for (const pg of [page, p2]) { await pg.goto('/#borrow'); await pg.reload(); await pg.waitForFunction(() => document.body.innerText.includes('Available to borrow')); await pg.fill('#amt', '40'); await pg.waitForFunction(() => !document.querySelector('#go').disabled); }
await Promise.all([page.locator('#go').click(), p2.locator('#go').click()]);
await page.waitForTimeout(25000);
console.log('--- p1\n', (await page.locator('body').innerText()).slice(0, 500)); console.log('--- p2\n', (await p2.locator('body').innerText()).slice(0, 500));
console.log('loans', (await read('getBorrowerLoanIds', [wallet])).length); await P.browser.close(); await w.close(); process.exit(0);
