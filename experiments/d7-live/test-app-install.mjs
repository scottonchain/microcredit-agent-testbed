// Home-screen install behaviour of the web app, headless and without a chain (welcome screen only).
// The browser's own install dialog cannot be driven headlessly, so beforeinstallprompt is dispatched synthetically,
// display-mode is stubbed through matchMedia, and iOS is emulated with an iPhone user agent (Chromium engine).
import { createRequire } from 'node:module'; import http from 'node:http'; import { readFileSync, existsSync, writeFileSync, mkdirSync } from 'node:fs'; import { extname, join, normalize } from 'node:path';
const require = createRequire(import.meta.url); const { chromium, devices } = require('playwright');
const root = new URL('./app/', import.meta.url).pathname; const PORT = Number(process.env.PORT || 4190);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };
const web = http.createServer((req, res) => { const u = new URL(req.url, 'http://x'); const p = u.pathname === '/' ? '/index.html' : u.pathname; const f = join(root, normalize(p).replace(/^(\.\.[/\\])+/, ''));
  if (!f.startsWith(root) || !existsSync(f)) { res.writeHead(404); return res.end('not found'); } res.writeHead(200, { 'content-type': types[extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); res.end(readFileSync(f)); });
await new Promise((r) => web.listen(PORT, '127.0.0.1', r)); mkdirSync('results/screens', { recursive: true });
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const results = []; let cur = null;
async function step(name, fn) { const t = Date.now(); try { await fn(); results.push({ name, ok: true, ms: Date.now() - t }); console.log('PASS ', name, `(${Date.now() - t} ms)`); }
  catch (e) { results.push({ name, ok: false, error: String(e.message).slice(0, 300) }); console.log('FAIL ', name, '\n      ', String(e.message).split('\n')[0].slice(0, 260)); try { await cur?.page.screenshot({ path: `results/screens/FAIL-install-${results.length}.png` }); } catch {} } finally { try { await cur?.ctx.close(); } catch {} cur = null; } }
const must = (c, m) => { if (!c) throw new Error(m); };
const IPHONE = devices['iPhone 13'], PIXEL = devices['Pixel 7'];
async function open({ device, standalone = false, iosStandalone = false, ipad = false, path = '/' } = {}) {
  const ctx = await browser.newContext({ ...(device || {}), baseURL: `http://localhost:${PORT}` }); const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(e.message));
  if (standalone) await page.addInitScript(() => { const mm = window.matchMedia.bind(window); window.matchMedia = (q) => (q === '(display-mode: standalone)' ? { matches: true, media: q, addEventListener() {}, removeEventListener() {} } : mm(q)); });
  if (iosStandalone) await page.addInitScript(() => Object.defineProperty(navigator, 'standalone', { get: () => true }));
  if (ipad) await page.addInitScript(() => { Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' }); Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 }); });
  await page.goto(path); await page.waitForFunction(() => /Create my wallet/.test(document.body.innerText) && window.__d7 && window.__d7.I);
  const text = () => page.locator('body').innerText(); const sheetText = async () => (await page.locator('#overlay').isVisible()) ? page.locator('#overlay').innerText() : '';
  const waitSheet = (re, t = 6000) => page.waitForFunction((src) => { const o = document.querySelector('#overlay'); return o && !o.hidden && new RegExp(src, 'i').test(o.innerText); }, re.source, { timeout: t });
  // A synthetic beforeinstallprompt whose prompt() records the call and resolves userChoice with the given outcome.
  const firePrompt = (outcome = 'accepted') => page.evaluate((o) => { const e = new Event('beforeinstallprompt'); e.prompt = () => { window.__prompted = (window.__prompted || 0) + 1; return Promise.resolve(); }; e.userChoice = Promise.resolve({ outcome: o, platform: 'web' }); window.dispatchEvent(e); }, outcome);
  return (cur = { ctx, page, errors, text, sheetText, waitSheet, firePrompt, card: () => page.locator('[data-install]:not([hidden])'), button: () => page.getByRole('button', { name: 'Add to home screen' }) });
}

await step('I01 browser tab without an install event: the welcome screen offers Add to home screen and the sheet gives menu steps', async () => {
  const p = await open({ device: PIXEL }); must((await p.card().count()) === 1, 'no install card'); must(!/own storage/i.test(await p.text()), 'storage note should not show in a browser tab');
  await p.button().click(); await p.waitSheet(/Install app|Add to Home screen/); const t = await p.sheetText(); must(/Add to your home screen/.test(t) && /menu/i.test(t), 'manual sheet text: ' + t); must(p.errors.length === 0, 'page errors: ' + p.errors.join('; ')); });

await step('I02 Chromium path: after beforeinstallprompt the sheet offers Install, prompt() is called once and Added is shown; appinstalled hides the card', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('accepted'); must(await p.page.evaluate(() => window.__d7.I.canPrompt()), 'event not captured');
  await p.button().click(); await p.waitSheet(/Your browser will ask to install/); await p.page.locator('#overlayActions button', { hasText: 'Install' }).click(); await p.waitSheet(/Added/);
  must((await p.page.evaluate(() => window.__prompted)) === 1, 'prompt() not called exactly once'); must(!(await p.page.evaluate(() => window.__d7.I.canPrompt())), 'deferred prompt should be spent');
  await p.page.evaluate(() => window.dispatchEvent(new Event('appinstalled'))); await p.page.waitForFunction(() => !document.querySelector('[data-install]:not([hidden])')); must(!(await p.page.evaluate(() => window.__d7.I.available())), 'available() after install');
  await p.page.locator('#overlayActions button', { hasText: 'OK' }).click(); must((await p.card().count()) === 0, 'card re-rendered after install'); must(p.errors.length === 0, 'page errors: ' + p.errors.join('; ')); });

await step('I03 Chromium path, dismissed: a Not installed sheet, nothing else changes', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('dismissed'); await p.button().click(); await p.waitSheet(/Your browser will ask/); await p.page.locator('#overlayActions button', { hasText: 'Install' }).click();
  await p.waitSheet(/Not installed/); await p.page.locator('#overlayActions button', { hasText: 'OK' }).click(); must((await p.card().count()) === 1, 'card should stay'); must(/Create my wallet/.test(await p.text()), 'welcome lost'); });

await step('I04 Not now closes the sheet and keeps the captured prompt for later', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('accepted'); await p.button().click(); await p.waitSheet(/Your browser will ask/); await p.page.locator('#overlayActions button', { hasText: 'Not now' }).click();
  must(!(await p.page.locator('#overlay').isVisible()), 'sheet still open'); must(await p.page.evaluate(() => window.__d7.I.canPrompt()), 'prompt should be kept'); must((await p.page.evaluate(() => window.__prompted || 0)) === 0, 'prompt() must not be called'); });

await step('I05 link flag ?install=1 opens the sheet by itself, offers the dialog once the event arrives, and the flag is removed from the address', async () => {
  const p = await open({ device: PIXEL, path: '/?install=1' }); await p.firePrompt('accepted'); await p.waitSheet(/Your browser will ask to install/);
  must(!(await p.page.evaluate(() => location.search)).includes('install'), 'flag still in URL: ' + (await p.page.evaluate(() => location.href))); must((await p.page.evaluate(() => location.hash)) === '', 'hash changed');
  await p.page.locator('#overlayActions button', { hasText: 'Not now' }).click(); must(/Create my wallet/.test(await p.text()), 'welcome not shown'); });

await step('I06 link flag without an install event falls back to menu steps after a short wait', async () => {
  const p = await open({ device: PIXEL, path: '/?install=1' }); await p.waitSheet(/Install app|Add to Home screen/, 6000); must(/menu/i.test(await p.sheetText()), 'expected menu steps'); });

await step('I07 iPhone in Safari: the sheet gives Share, then Add to Home Screen, and the storage note', async () => {
  const p = await open({ device: IPHONE }); must(await p.page.evaluate(() => window.__d7.I.isIOS()), 'isIOS false under iPhone UA'); must((await p.card().count()) === 1, 'no card on iPhone');
  await p.button().click(); await p.waitSheet(/Add to Home Screen/); const t = await p.sheetText(); must(/Share/.test(t) && /Add to Home Screen/.test(t) && /Tap Add/.test(t), 'ios steps missing: ' + t); must(/own storage/i.test(t) && /recovery code/i.test(t), 'storage note missing: ' + t); });

await step('I08 iPhone link flag: the Share steps open at once', async () => {
  const p = await open({ device: IPHONE, path: '/?install=1' }); await p.waitSheet(/Add to Home Screen/, 6000); must(/Share/.test(await p.sheetText()), 'expected Share steps'); });

await step('I09 running from the home screen (display-mode standalone, Android): no install card, no iOS note, link flag ignored', async () => {
  const p = await open({ device: PIXEL, standalone: true, path: '/?install=1' }); must(await p.page.evaluate(() => window.__d7.I.standalone()), 'standalone() false'); must((await p.card().count()) === 0, 'card shown while standalone');
  await p.page.waitForTimeout(1800); must(!(await p.page.locator('#overlay').isVisible()), 'sheet opened while standalone'); must(!/own storage/i.test(await p.text()), 'iOS note on Android'); must(!(await p.page.evaluate(() => location.search)).includes('install'), 'flag kept'); });

await step('I10 iPhone home-screen app (navigator.standalone) with no wallet: no install card, Safari storage note with the recovery route', async () => {
  const p = await open({ device: IPHONE, iosStandalone: true }); must(await p.page.evaluate(() => window.__d7.I.standalone()), 'standalone() false on iOS'); must((await p.card().count()) === 0, 'card shown in iOS home-screen app');
  const t = await p.text(); must(/own storage/i.test(t) && /recovery code/i.test(t) && /Safari/.test(t), 'iOS storage note missing: ' + t.slice(0, 300)); });

await step('I11 iPad (Mac user agent, MacIntel platform, five touch points) counts as iOS', async () => {
  // iPadOS Safari reports a Mac user agent; Chromium emulation cannot set platform or multi-touch, so those two are stubbed.
  const p = await open({ device: { ...IPHONE, userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15', viewport: { width: 820, height: 1180 } }, ipad: true });
  must(await p.page.evaluate(() => window.__d7.I.isIOS()), 'iPad not detected'); });

await step('I12 desktop browser without touch is not iOS and gets menu steps', async () => {
  const p = await open({}); must(!(await p.page.evaluate(() => window.__d7.I.isIOS())), 'desktop detected as iOS'); await p.button().click(); await p.waitSheet(/Add to Dock|Install app/); });

await step('I13 beforeinstallprompt fired before the app module loaded is still usable (captured by index.html)', async () => {
  const ctx = await browser.newContext({ ...PIXEL, baseURL: `http://localhost:${PORT}` }); const page = await ctx.newPage(); cur = { ctx, page };
  await page.route('**/dist/app.js', async (route) => { await page.waitForFunction(() => document.readyState !== 'loading', null, { polling: 20, timeout: 10000 }); await page.evaluate(() => { const e = new Event('beforeinstallprompt'); e.prompt = () => { window.__prompted = (window.__prompted || 0) + 1; return Promise.resolve(); }; e.userChoice = Promise.resolve({ outcome: 'accepted', platform: 'web' }); window.dispatchEvent(e); }); await route.continue(); });
  await page.goto('/'); await page.waitForFunction(() => /Create my wallet/.test(document.body.innerText) && window.__d7 && window.__d7.I);
  must(await page.evaluate(() => !!window.__bip), 'index.html did not keep the early event'); must(await page.evaluate(() => window.__d7.I.canPrompt()), 'module did not adopt the early event');
  await page.getByRole('button', { name: 'Add to home screen' }).click(); await page.waitForFunction(() => /Your browser will ask to install/.test(document.querySelector('#overlay').innerText)); });

await browser.close(); web.close();
writeFileSync('results/install-tests.json', JSON.stringify(results, null, 1)); const ok = results.filter((r) => r.ok).length; console.log(`\n${ok}/${results.length} cases pass`); process.exit(ok === results.length ? 0 : 1);
