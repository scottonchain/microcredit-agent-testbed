// Shared harness for headless phone tests of the web app against a fork.
import { createRequire } from 'node:module'; import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs'; import { extname, join, normalize } from 'node:path'; import http from 'node:http'; import { parseEther } from 'viem';
import { startBundler } from '../bundler.mjs'; import { deployPaymaster } from '../deploy-paymaster.mjs'; import { Actor, seededKey, fundFork, fork, read, usd, toUnits, ADDR, pc, asOwner } from './sim.mjs';
const require = createRequire(import.meta.url); const { chromium, devices } = require('playwright');
export { devices, fork, read, usd, toUnits, ADDR, pc, asOwner, Actor, seededKey, fundFork, parseEther };

export async function world({ seed = 2, bundlerPort = 4337, webPort = 4173, poolLiquidity = 300, cap } = {}) {
  const RPC = process.env.RPC_URL; mkdirSync('results/screens', { recursive: true });
  await fundFork(new Actor('d', seededKey(seed, 'deployer')), { eth: parseEther('5') }); await fundFork(new Actor('b', seededKey(seed, 'bundler')), { eth: parseEther('5') });
  const pm = await deployPaymaster({ rpc: RPC, key: seededKey(seed, 'deployer'), ...(cap ? { cap } : {}) });
  const bundler = await startBundler({ rpc: RPC, port: bundlerPort, key: seededKey(seed, 'bundler') });
  const cfgPath = `results/test-config-${webPort}.json`;
  writeFileSync(cfgPath, JSON.stringify({ chainId: 84532, rpcs: [RPC], bundler: bundler.url, paymaster: pm.address, pool: ADDR.pool, usdc: ADDR.usdc, explorer: 'https://sepolia.basescan.org', faucet: 'https://faucet.circle.com', creditRequestIssue: 'https://github.com/scottonchain/microcredit-contract/issues/7', headroomSeconds: 600 }));
  const root = new URL('../app/', import.meta.url).pathname; const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };
  const web = http.createServer((req, res) => { const u = new URL(req.url, 'http://x'); const p = u.pathname === '/' ? '/index.html' : u.pathname;
    if (p === '/config.json') { res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' }); return res.end(readFileSync(cfgPath)); }
    const f = join(root, normalize(p)); if (!f.startsWith(root) || !existsSync(f)) { res.writeHead(404); return res.end('nf'); }
    res.writeHead(200, { 'content-type': types[extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); res.end(readFileSync(f)); });
  await new Promise((r) => web.listen(webPort, '127.0.0.1', r));
  let lender = null;
  if (poolLiquidity > 0) { lender = new Actor('lender', seededKey(seed, 'lender')); await fundFork(lender, { usdcAmount: toUnits(poolLiquidity + 100) }); await lender.ensureAllowance(toUnits(poolLiquidity + 100)); await lender.pool('depositFunds', [toUnits(poolLiquidity)]); }
  const backer = new Actor('backer', seededKey(seed, 'backer')); await fundFork(backer, { usdcAmount: toUnits(200) }); await backer.ensureAllowance(toUnits(200)); await backer.pool('stake', [toUnits(150)]);
  const friend = new Actor('friend', seededKey(seed, 'friend')); await fundFork(friend, {});
  return { RPC, pm, bundler, web, lender, backer, friend, webPort, bundlerPort, close: async () => { web.close(); bundler.close(); } };
}

export async function phone(w, { device = 'iPhone 13', colorScheme } = {}) {
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ ...devices[device], baseURL: `http://localhost:${w.webPort}`, ...(colorScheme ? { colorScheme } : {}) });
  const page = await ctx.newPage(); const logs = []; page.on('console', (m) => logs.push(m.type() + ': ' + m.text())); page.on('pageerror', (e) => logs.push('pageerror: ' + e.message));
  const cdp = await ctx.newCDPSession(page); await cdp.send('WebAuthn.enable');
  const va = await cdp.send('WebAuthn.addVirtualAuthenticator', { options: { protocol: 'ctap2', transport: 'internal', hasResidentKey: true, hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true } });
  const text = () => page.locator('body').innerText();
  const expectText = (re, t = 20000) => page.waitForFunction((src) => new RegExp(src, 'i').test(document.body.innerText), re.source, { timeout: t });
  const addr = () => page.evaluate(() => window.__d7.S.addr);
  const tapDone = async () => { await expectText(/Done/, 60000); await page.locator('#overlayActions button', { hasText: 'OK' }).click(); };
  const closeSheet = async () => { if (await page.locator('#overlay').isVisible()) await page.locator('#overlayActions button').first().click(); };
  const create = async () => { await page.goto('/'); await page.getByRole('button', { name: 'Create my wallet' }).click(); await expectText(/Your wallet/); await expectText(/\$\d/); return addr(); };
  return { browser, ctx, page, cdp, authId: va.authenticatorId, logs, text, expectText, addr, tapDone, closeSheet, create };
}

export function runner() {
  const results = [];
  return { results, async step(name, fn, page) { const t = Date.now(); try { await fn(); results.push({ name, ok: true, ms: Date.now() - t }); console.log('PASS ', name, `(${Date.now() - t} ms)`); } catch (e) { results.push({ name, ok: false, error: String(e.message).slice(0, 300) }); console.log('FAIL ', name, '\n      ', String(e.message).split('\n')[0].slice(0, 260)); try { await page?.screenshot({ path: `results/screens/FAIL-edge-${results.length}.png` }); } catch {} } },
    finish(file) { writeFileSync(file, JSON.stringify(results, null, 1)); const ok = results.filter((r) => r.ok).length; console.log(`\n${ok}/${results.length} cases pass`); return ok === results.length; } };
}
