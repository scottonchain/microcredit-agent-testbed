// Headless phone test of the web app against a fork: virtual passkey authenticator, iPhone viewport, many cases.
import { createRequire } from 'node:module'; import { mkdirSync, writeFileSync } from 'node:fs'; import { parseEther, maxUint256 } from 'viem';
const require = createRequire(import.meta.url); const { chromium, devices } = require('playwright');
import { startBundler } from './bundler.mjs'; import { deployPaymaster } from './deploy-paymaster.mjs'; import { server } from './serve-app.mjs';
import { Actor, seededKey, fundFork, fork, read, usd, toUnits, ADDR, ABI, pc } from './lib/sim.mjs';

const RPC = process.env.RPC_URL, SHOTS = 'results/screens'; mkdirSync(SHOTS, { recursive: true });
const dep = new Actor('deployer', seededKey(2, 'deployer')), bun = new Actor('bundler', seededKey(2, 'bundler'));
await fundFork(dep, { eth: parseEther('5') }); await fundFork(bun, { eth: parseEther('5') });
const pm = await deployPaymaster({ rpc: RPC, key: seededKey(2, 'deployer') });
const bundler = await startBundler({ rpc: RPC, port: 4337, key: seededKey(2, 'bundler') });
writeFileSync('results/test-config.json', JSON.stringify({ chainId: 84532, rpcs: [RPC], bundler: bundler.url, paymaster: pm.address, pool: ADDR.pool, usdc: ADDR.usdc, explorer: 'https://sepolia.basescan.org', faucet: 'https://faucet.circle.com', creditRequestIssue: 'https://github.com/scottonchain/microcredit-contract/issues/7', headroomSeconds: 600 }));
process.argv[3] = 'results/test-config.json'; // serve-app reads argv at import; set via env below instead
const http = await import('node:http'); const appServer = http.createServer(); // replaced below
const { default: _x } = {}; 

// Start the static server with the config override.
import { readFileSync, existsSync } from 'node:fs'; import { extname, join, normalize } from 'node:path';
const root = new URL('./app/', import.meta.url).pathname; const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };
const web = http.createServer((req, res) => { const u = new URL(req.url, 'http://x'); const p = u.pathname === '/' ? '/index.html' : u.pathname;
  if (p === '/config.json') { res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' }); return res.end(readFileSync('results/test-config.json')); }
  const f = join(root, normalize(p)); if (!f.startsWith(root) || !existsSync(f)) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200, { 'content-type': types[extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); res.end(readFileSync(f)); });
await new Promise((r) => web.listen(4173, '127.0.0.1', r));

// World: liquidity, a backer with stake, a friend.
const lender = new Actor('lender', seededKey(2, 'lender')); await fundFork(lender, { usdcAmount: toUnits(400) }); await lender.ensureAllowance(toUnits(400)); await lender.pool('depositFunds', [toUnits(300)]);
const backer = new Actor('backer', seededKey(2, 'backer')); await fundFork(backer, { usdcAmount: toUnits(100) }); await backer.ensureAllowance(toUnits(100)); await backer.pool('stake', [toUnits(60)]);
const friend = new Actor('friend', seededKey(2, 'friend')); await fundFork(friend, {});

const results = []; let page, wallet = null, authId;
async function step(name, fn) {
  const t = Date.now();
  try { await fn(); results.push({ name, ok: true, ms: Date.now() - t }); console.log('PASS ', name, `(${Date.now() - t} ms)`); }
  catch (e) { results.push({ name, ok: false, error: String(e.message).slice(0, 300) }); console.log('FAIL ', name, '\n      ', String(e.message).split('\n')[0].slice(0, 240)); try { await page.screenshot({ path: `${SHOTS}/FAIL-${results.length}.png` }); } catch {} }
}
const shot = (n) => page.screenshot({ path: `${SHOTS}/${String(results.length + 1).padStart(2, '0')}-${n}.png` });
const text = () => page.locator('body').innerText();
const expectText = async (re, t = 20000) => { await page.waitForFunction((src) => new RegExp(src, 'i').test(document.body.innerText), re.source, { timeout: t }); };
const addr = () => page.evaluate(() => window.__d7.S.addr);
const closeSheet = async () => { const b = page.locator('#overlayActions button').first(); if (await page.locator('#overlay').isVisible()) await b.click(); };
const tapDone = async () => { await expectText(/Done/, 60000); await page.locator('#overlayActions button', { hasText: 'OK' }).click(); };

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const ctx = await browser.newContext({ ...devices['iPhone 13'], baseURL: 'http://localhost:4173', permissions: [] });
page = await ctx.newPage(); const logs = []; page.on('console', (m) => logs.push(m.type() + ': ' + m.text())); page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
const cdp = await ctx.newCDPSession(page); await cdp.send('WebAuthn.enable');
const va = await cdp.send('WebAuthn.addVirtualAuthenticator', { options: { protocol: 'ctap2', transport: 'internal', hasResidentKey: true, hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true } });
authId = va.authenticatorId;

await step('T01 first visit shows welcome and the test-network banner', async () => { await page.goto('/'); await expectText(/Create my wallet/); const t = await text(); if (!/TEST NETWORK/.test(t)) throw new Error('banner missing'); await shot('welcome'); });
await step('T02 create wallet with a passkey, land on home with $0.00 and no credit', async () => { await page.getByRole('button', { name: 'Create my wallet' }).click(); await expectText(/Your wallet/); await expectText(/\$0\.00/); const t = await text(); if (!/no credit yet/i.test(t)) throw new Error('no-credit hint missing'); wallet = await addr(); if (!/^0x[0-9a-fA-F]{40}$/.test(wallet)) throw new Error('bad address ' + wallet); await shot('home-new'); });
await step('T03 borrow with no credit is refused in plain words', async () => { await page.goto('/#borrow'); await expectText(/Available to borrow/); await page.fill('#amt', '5'); await expectText(/no credit|more than you can borrow/i); await shot('borrow-nocredit'); const dis = await page.locator('#go').isDisabled(); if (!dis) throw new Error('Borrow button should be disabled'); });
await step('T04 receive screen shows address, QR and faucet steps', async () => { await page.goto('/#receive'); await expectText(/Get test dollars/); if (!(await page.locator('.qr svg').count())) throw new Error('no QR'); const a = await page.locator('#addrBox').innerText(); if (a.trim().toLowerCase() !== wallet.toLowerCase()) throw new Error('address mismatch'); await shot('receive'); });
await step('T05 faucet drop of $3 shows on home after reload', async () => { await fork.setUsdc(wallet, toUnits(3)); await page.goto('/#home'); await page.reload(); await expectText(/\$3\.00/); });
await step('T06 a friend backs the wallet with $20, available becomes $20', async () => { await backer.pool('back', [wallet, toUnits(20)]); await page.reload(); await expectText(/You can borrow up to/); await page.waitForFunction(() => document.querySelector('#avail')?.innerText.includes('20.00'), null, { timeout: 15000 }); await shot('home-backed'); });
await step('T07 borrow more than the limit is refused before any signature', async () => { await page.goto('/#borrow'); await page.fill('#amt', '25'); await expectText(/more than you can borrow/i); if (!(await page.locator('#go').isDisabled())) throw new Error('should be disabled'); });
await step('T08 invalid amounts keep Borrow disabled (blank, abc, -5, 0, 1.2345678)', async () => { for (const v of ['', 'abc', '-5', '0', '1.2345678']) { await page.fill('#amt', v); if (!(await page.locator('#go').isDisabled())) throw new Error('enabled for ' + JSON.stringify(v)); } });
await step('T09 borrow $10: one fingerprint prompt, success, owed shown', async () => {
  await page.fill('#amt', '10'); await expectText(/You receive/); await shot('borrow-terms'); await page.locator('#go').click(); await tapDone();
  await page.goto('/#home'); await page.reload(); await expectText(/You owe/); const t = await text(); if (!/\$13\.00/.test(t)) throw new Error('balance should be $13.00: ' + t.slice(0, 200)); await shot('home-loan'); });
await step('T10 borrow while a loan is open is not offered', async () => { await page.goto('/#home'); if (!(await page.locator('#gBorrow').isDisabled())) throw new Error('Borrow should be disabled with an open loan'); });
await step('T11 send $2 to a friend', async () => { await page.goto('/#send'); await page.fill('#to', friend.address); await page.fill('#amt', '2'); await page.locator('#go').click(); await tapDone(); const b = usd(await friend.usdcBalance()); if (b !== 2) throw new Error('friend has ' + b); });
await step('T12 send validation: bad address, own address, zero, too much', async () => {
  await page.goto('/#send');
  const tryIt = async (to, amt, re) => { await page.fill('#to', to); await page.fill('#amt', amt); await page.locator('#go').click(); await expectText(re, 8000); };
  await tryIt('0x123', '1', /not a valid wallet address/i); await tryIt(wallet, '1', /your own address/i); await tryIt(friend.address, '0', /Enter an amount/i); await tryIt(friend.address, '500', /only have/i); });
await step('T13 repay with too little: shortfall note and Pay all disabled', async () => { await fork.warp(15 * 86400); await fork.setUsdc(wallet, toUnits(9)); await page.goto('/#repay'); await page.reload(); await expectText(/short/i); if (!(await page.locator('#all').isDisabled())) throw new Error('Pay all should be disabled'); await shot('repay-short'); });
await step('T14 faucet top-up then pay part ($4) leaves the loan open', async () => { await fork.setUsdc(wallet, toUnits(20)); await page.reload(); await page.locator('summary', { hasText: 'Pay only part' }).click(); await page.fill('#part', '4'); await page.locator('#partGo').click(); await tapDone(); const ids = await read('getBorrowerLoanIds', [wallet]); const st = Number((await read('getLoanTerms', [ids[ids.length - 1]]))[0]); if (st !== 2) throw new Error('loan status ' + st); });
await step('T15 pay back everything closes the loan', async () => { await page.goto('/#repay'); await page.reload(); await expectText(/You owe right now/); await page.locator('#all').click(); await tapDone(); const ids = await read('getBorrowerLoanIds', [wallet]); const st = Number((await read('getLoanTerms', [ids[ids.length - 1]]))[0]); if (st !== 3) throw new Error('loan status ' + st + ' (3 = repaid)'); await page.goto('/#home'); await page.reload(); await expectText(/You can borrow up to/); const t = await text(); if (/You owe/.test(t)) throw new Error('still shows a debt'); await shot('home-repaid'); });
await step('T16 history effect: dues earned and limit available again', async () => { const dues = await read('duesPaid', [wallet]); if (dues === 0n) throw new Error('no dues earned'); const [, avail] = await read('getBorrowLimit', [wallet]); if (usd(avail) < 19.9) throw new Error('available ' + usd(avail)); });
await step('T17 borrow again after repaying works (second loan)', async () => { await page.goto('/#borrow'); await page.reload(); await page.fill('#amt', '5'); await expectText(/You receive/); await page.locator('#go').click(); await tapDone(); });
await step('T18 cancelled fingerprint: friendly message, nothing sent', async () => {
  await cdp.send('WebAuthn.setUserVerified', { authenticatorId: authId, isUserVerified: false }); const before = (await read('getBorrowerLoanIds', [wallet])).length;
  await page.goto('/#send'); await page.fill('#to', friend.address); await page.fill('#amt', '1'); await page.locator('#go').click();
  await expectText(/did not go through|Cancelled/i, 30000); const t = await text(); if (!/Cancelled|fingerprint/i.test(t)) throw new Error('no friendly cancel text: ' + t.slice(0, 300)); await shot('cancelled'); await closeSheet();
  await cdp.send('WebAuthn.setUserVerified', { authenticatorId: authId, isUserVerified: true }); if ((await read('getBorrowerLoanIds', [wallet])).length !== before) throw new Error('state changed'); });
await step('T19 back a friend with new stake from wallet USDC', async () => { await page.goto('/#back'); await page.reload(); await page.fill('#to', friend.address); await page.fill('#amt', '5'); await expectText(/lock/i); await page.locator('#go').click(); await tapDone(); const bk = await read('getBacking', [wallet, friend.address]); if (usd(bk[0]) + usd(bk[1]) !== 5) throw new Error('backing ' + bk); });
await step('T19b raising an existing backing adds only the difference (5 to 8 locks just 3 more stake)', async () => { const st0 = await read('stakeOf', [wallet]); await page.goto('/#back'); await page.reload(); await page.fill('#to', friend.address); await expectText(/currently back this friend with \$5\.00/); await page.fill('#amt', '8'); await expectText(/adds \$3\.00/); await page.locator('#go').click(); await tapDone(); const bk = await read('getBacking', [wallet, friend.address]); if (usd(bk[0]) + usd(bk[1]) !== 8) throw new Error('backing ' + bk); const st1 = await read('stakeOf', [wallet]); if (usd(st1 - st0) !== 3) throw new Error('stake rose by ' + usd(st1 - st0)); });
await step('T19c lowering to $2 and then removing (0) both work from the Change link', async () => { await page.goto('/#home'); await page.reload(); await expectText(/You back/); await page.locator('a', { hasText: 'Change' }).first().click(); await expectText(/currently back this friend with \$8\.00/); await page.fill('#amt', '2'); await expectText(/lowers your backing/); await page.locator('#go').click(); await tapDone(); let bk = await read('getBacking', [wallet, friend.address]); if (usd(bk[0]) + usd(bk[1]) !== 2) throw new Error('lowered to ' + bk); await page.goto('/#back?to=' + friend.address); await page.reload(); await expectText(/currently back this friend with \$2\.00/); await page.fill('#amt', '0'); await expectText(/removes your backing/); await page.locator('#go').click(); await tapDone(); bk = await read('getBacking', [wallet, friend.address]); if (bk[0] + bk[1] !== 0n) throw new Error('not removed ' + bk); });
await step('T20 back validation: self, below $1, bad address', async () => { await page.goto('/#back'); const t1 = async (to, amt, re) => { await page.fill('#to', to); await page.fill('#amt', amt); await page.locator('#go').click(); await expectText(re, 8000); await closeSheet().catch(() => {}); }; await t1('0xabc', '5', /not a valid wallet address/i); await t1(wallet, '5', /cannot back yourself/i); await t1(friend.address, '0.5', /at least 1 USDC/i); });
await step('T21 recovery code round trip restores the same address', async () => {
  await page.goto('/#help'); await expectText(/Your recovery code/); const code = await page.locator('.addr').first().innerText();
  await page.evaluate(() => localStorage.clear()); await page.goto('/'); await page.reload(); await expectText(/Create my wallet/);
  await page.locator('summary', { hasText: 'recovery code' }).click(); await page.fill('#rc', code.trim()); await page.getByRole('button', { name: 'Restore wallet' }).click(); await expectText(/Your wallet/); const a2 = await addr(); if (a2.toLowerCase() !== wallet.toLowerCase()) throw new Error('address changed'); });
await step('T22 bad recovery code is rejected politely', async () => { await page.evaluate(() => localStorage.clear()); await page.goto('/'); await page.reload(); await page.locator('summary', { hasText: 'recovery code' }).click(); await page.fill('#rc', 'not-a-code'); await page.getByRole('button', { name: 'Restore wallet' }).click(); await expectText(/does not work/i); await closeSheet(); });
await step('T23 no horizontal scroll and tap targets at least 44px on home', async () => {
  await page.evaluate(() => { localStorage.clear(); }); // restore wallet again for the layout check
  await page.goto('/'); await page.reload(); await page.getByRole('button', { name: 'Create my wallet' }).click(); await expectText(/Your wallet/); await expectText(/\$0\.00/);
  const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, small: [...document.querySelectorAll('button:not(.link),.btn')].filter((b) => b.offsetParent && b.getBoundingClientRect().height < 44).length }));
  if (m.sw > m.cw) throw new Error('horizontal scroll ' + m.sw + ' > ' + m.cw); if (m.small) throw new Error(m.small + ' small tap targets'); });
await step('T24 sponsor allowance accounted for the wallet and gas stayed tiny', async () => { const spent = await pc.readContract({ address: pm.address, abi: pm.abi, functionName: 'spent', args: [wallet] }); if (spent === 0n || spent > parseEther('0.001')) throw new Error('spent ' + spent); });
const errs = logs.filter((l) => /pageerror|error:/i.test(l) && !/favicon|404|Failed to load resource/i.test(l)); await step('T25 no uncaught page errors in the console', async () => { if (errs.length) throw new Error(errs.slice(0, 3).join(' | ')); });

await browser.close(); web.close(); bundler.close();
writeFileSync('results/test-app.json', JSON.stringify({ results, consoleErrors: errs }, null, 1));
const ok = results.filter((r) => r.ok).length; console.log(`\n${ok}/${results.length} app cases pass`); process.exit(ok === results.length ? 0 : 1);
