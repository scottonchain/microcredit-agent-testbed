// Home-screen install behaviour of the web app, headless and without a chain (welcome screen only).
// The browser's own install dialog cannot be driven headlessly, so beforeinstallprompt is dispatched synthetically,
// display-mode is stubbed through matchMedia, and iOS is emulated with an iPhone user agent on the Chromium engine
// (with the Chromium-only install event removed, so the WebKit branch runs). Results: results/test-app-install.json.
// Setup once: npm ci (esbuild, for the bundle check); the preinstalled Playwright provides Chromium.
import { createRequire } from 'node:module'; import http from 'node:http'; import { readFileSync, existsSync, writeFileSync, mkdirSync, readdirSync, unlinkSync } from 'node:fs'; import { extname, join, normalize } from 'node:path'; import { execFileSync } from 'node:child_process'; import { tmpdir } from 'node:os';
const require = createRequire(import.meta.url);
let chromium, devices; try { ({ chromium, devices } = require('playwright')); } catch { console.error('playwright is not resolvable: install it (npm i -D playwright && npx playwright install chromium) or run where it is preinstalled'); process.exit(2); }
const here = new URL('./', import.meta.url).pathname, root = join(here, 'app/'), resultsDir = join(here, 'results/'); mkdirSync(join(resultsDir, 'screens'), { recursive: true });
for (const f of readdirSync(join(resultsDir, 'screens'))) if (/^FAIL-install-/.test(f)) unlinkSync(join(resultsDir, 'screens', f));
// The suite exercises the committed bundle; make sure it was built from the committed source.
const tmpBundle = join(tmpdir(), `d7-install-check-${process.pid}.js`);
execFileSync('npx', ['esbuild', join(here, 'app/src/main.js'), '--bundle', '--minify', '--format=esm', '--target=es2022', '--loader:.json=json', '--define:process.env.NODE_ENV="production"', `--outfile=${tmpBundle}`, '--log-level=error'], { cwd: here, stdio: 'inherit' });
if (!readFileSync(tmpBundle).equals(readFileSync(join(root, 'dist/app.js')))) { console.error('app/dist/app.js is stale: run build-app.sh'); process.exit(2); } unlinkSync(tmpBundle);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };
const web = http.createServer((req, res) => { const u = new URL(req.url, 'http://x'); const p = u.pathname === '/' ? '/index.html' : u.pathname; const f = join(root, normalize(p).replace(/^(\.\.[/\\])+/, ''));
  if (!f.startsWith(root) || !existsSync(f)) { res.writeHead(404); return res.end('not found'); } res.writeHead(200, { 'content-type': types[extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); res.end(readFileSync(f)); });
await new Promise((r) => web.listen(0, '127.0.0.1', r)); const PORT = web.address().port;
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const results = []; let cur = null;
async function step(name, fn) { const t = Date.now(); try { await fn(); results.push({ name, ok: true, ms: Date.now() - t }); console.log('PASS ', name, `(${Date.now() - t} ms)`); }
  catch (e) { results.push({ name, ok: false, error: String(e.message).slice(0, 300) }); console.log('FAIL ', name, '\n      ', String(e.message).split('\n')[0].slice(0, 260)); try { await cur?.page.screenshot({ path: join(resultsDir, 'screens', `FAIL-install-${results.length}.png`) }); } catch {} } finally { try { await cur?.ctx.close(); } catch {} cur = null; } }
const must = (c, m) => { if (!c) throw new Error(m); };
const IPHONE = devices['iPhone 13'], PIXEL = devices['Pixel 7'];
const CRIOS = { ...IPHONE, userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.6312.52 Mobile/15E148 Safari/604.1' };
const IOS_INAPP = { ...IPHONE, userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 320.0.0.0' };
const ANDROID_WV = { ...PIXEL, userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 7 Build/UQ1A.240105.004; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/122.0.6261.64 Mobile Safari/537.36' };
// Synthetic install event: cancelable (so preventDefault is observable), prompt() enforces Chrome's rules (user activation, one call).
const FIRE = `(function (outcome, reject) { const e = new Event('beforeinstallprompt', { cancelable: true }); let used = false;
  e.prompt = () => { window.__prompted = (window.__prompted || 0) + 1; if (reject) return Promise.reject(new DOMException('refused', 'NotAllowedError')); if (used || !(navigator.userActivation && navigator.userActivation.isActive)) return Promise.reject(new DOMException('needs a user gesture, once', 'NotAllowedError')); used = true; return Promise.resolve(); };
  e.userChoice = Promise.resolve({ outcome: outcome, platform: 'web' }); window.__bipEvt = e; window.dispatchEvent(e); })`;
async function open({ device, standalone = false, iosStandalone = false, ipad = false, webkit = false, installedApps = null, colorScheme, path = '/' } = {}) {
  const ctx = await browser.newContext({ ...(device || {}), ...(colorScheme ? { colorScheme } : {}), baseURL: `http://localhost:${PORT}` }); const page = await ctx.newPage(); const errors = []; page.on('pageerror', (e) => errors.push(e.message)); cur = { ctx, page, errors };
  await page.addInitScript(() => { const mm = window.matchMedia.bind(window); const state = { matches: false, listeners: [] }; window.__setStandalone = (m) => { state.matches = m; state.listeners.forEach((fn) => fn({ matches: m, media: '(display-mode: standalone)' })); };
    window.matchMedia = (q) => (q === '(display-mode: standalone)' ? { get matches() { return state.matches; }, media: q, addEventListener(t, fn) { state.listeners.push(fn); }, removeEventListener() {} } : mm(q)); });
  if (standalone) await page.addInitScript(() => window.__setStandalone(true));
  if (iosStandalone) await page.addInitScript(() => Object.defineProperty(navigator, 'standalone', { get: () => true }));
  if (ipad) await page.addInitScript(() => { Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' }); Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 }); });
  if (webkit || (device && /iPhone|iPad/.test(device.userAgent || ''))) await page.addInitScript(() => { delete window.onbeforeinstallprompt; }); // WebKit has no install event
  if (installedApps) await page.addInitScript((apps) => { navigator.getInstalledRelatedApps = () => Promise.resolve(apps); }, installedApps);
  const t0 = Date.now(); await page.goto(path); await page.waitForFunction(() => /Get started/.test(document.body.innerText) && window.__d7 && window.__d7.I); const bootMs = Date.now() - t0;
  const text = () => page.locator('body').innerText(); const sheetText = async () => (await page.locator('#overlay').isVisible()) ? page.locator('#overlay').innerText() : '';
  const waitSheet = (re, t = 6000) => page.waitForFunction((src) => { const o = document.querySelector('#overlay'); return o && !o.hidden && new RegExp(src, 'i').test(o.innerText); }, re.source, { timeout: t });
  const firePrompt = (outcome = 'accepted', reject = false) => page.evaluate(`${FIRE}(${JSON.stringify(outcome)}, ${reject})`);
  const action = (name) => page.locator('#overlayActions button', { hasText: name });
  return Object.assign(cur, { bootMs, text, sheetText, waitSheet, firePrompt, action, card: () => page.locator('[data-install]:not([hidden])'), button: () => page.getByRole('button', { name: 'Add to home screen' }), sheetOpen: () => page.locator('#overlay').isVisible() });
}
const timed = async (fn) => { const t = Date.now(); await fn(); return Date.now() - t; };

await step('I01 browser tab without an install event: the card offers Add to home screen and the menu steps open at once (no dead wait)', async () => {
  const p = await open({ device: PIXEL }); must((await p.card().count()) === 1, 'no install card'); must(!/second passkey|replace/i.test(await p.text()), 'WebKit-only note shown on Android');
  const ms = await timed(async () => { await p.button().click(); await p.waitSheet(/Install app/); }); must(ms < 800, 'sheet took ' + ms + ' ms'); const t = await p.sheetText();
  must(/Add to your home screen/.test(t) && /menu/i.test(t) && /Opened this inside another app/.test(t), 'manual sheet text: ' + t); must(p.errors.length === 0, 'page errors: ' + p.errors.join('; ')); });

await step('I02 Chromium path: after beforeinstallprompt (default prevented) the sheet offers Install, prompt() runs once, Adding it now is shown, appinstalled hides the card', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('accepted'); must(await p.page.evaluate(() => window.__bipEvt.defaultPrevented), 'preventDefault not called'); must(await p.page.evaluate(() => window.__d7.I.canPrompt()), 'event not captured');
  await p.button().click(); await p.waitSheet(/Your browser will ask to install/); await p.action('Install').click(); await p.waitSheet(/Adding it now/);
  must((await p.page.evaluate(() => window.__prompted)) === 1, 'prompt() not called exactly once'); must(!(await p.page.evaluate(() => window.__d7.I.canPrompt())), 'deferred prompt should be spent');
  must((await p.card().count()) === 0, 'card still shown after an accepted dialog'); await p.page.evaluate(() => window.dispatchEvent(new Event('appinstalled')));
  await p.action('OK').click(); must((await p.card().count()) === 0, 'card re-rendered after install'); must(!(await p.page.evaluate(() => window.__d7.I.available())), 'available() after install'); must(p.errors.length === 0, 'page errors: ' + p.errors.join('; ')); });

await step('I03 Chromium path, dismissed: a Not installed sheet, card stays, welcome intact', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('dismissed'); await p.button().click(); await p.waitSheet(/Your browser will ask/); await p.action('Install').click();
  await p.waitSheet(/Not installed/); must(/browser’s menu|browser's menu/.test(await p.sheetText()), 'menu hint missing'); await p.action('OK').click(); must((await p.card().count()) === 1, 'card should stay'); must(/Get started/.test(await p.text()), 'welcome lost'); });

await step('I04 Not now closes the sheet and keeps the captured prompt for later; focus returns to the card button', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('accepted'); await p.button().click(); await p.waitSheet(/Your browser will ask/);
  must(await p.page.evaluate(() => document.activeElement && document.activeElement.closest('#overlay') !== null), 'focus not inside the sheet'); await p.action('Not now').click();
  must(!(await p.sheetOpen()), 'sheet still open'); must(await p.page.evaluate(() => window.__d7.I.canPrompt()), 'prompt should be kept'); must((await p.page.evaluate(() => window.__prompted || 0)) === 0, 'prompt() must not be called');
  must(await p.page.evaluate(() => document.activeElement && document.activeElement.id === 'install'), 'focus did not return to the card button'); });

await step('I05 link flag ?install=1: the sheet opens at once with menu steps, upgrades in place when the install event arrives later, and the flag leaves the address', async () => {
  const p = await open({ device: PIXEL, path: '/?install=1' }); await p.waitSheet(/Install app/, 1500); must(!(await p.page.evaluate(() => location.search)).includes('install'), 'flag still in URL');
  await p.page.waitForTimeout(400); await p.firePrompt('accepted'); await p.waitSheet(/Your browser will ask to install/, 1500); await p.action('Install').click(); await p.waitSheet(/Adding it now/); must((await p.page.evaluate(() => window.__prompted)) === 1, 'prompt() count'); });

await step('I06 link flag without an install event: menu steps immediately, nothing else changes', async () => {
  const p = await open({ device: PIXEL, path: '/?install=1' }); await p.waitSheet(/Install app/, 1500); must(/menu/i.test(await p.sheetText()), 'expected menu steps'); await p.action('OK').click(); must(/Get started/.test(await p.text()), 'welcome not shown'); });

await step('I07 iPhone Safari: Share, Add to Home Screen, Add; the wallet note names Safari; the in-app hint is present; no wait', async () => {
  const p = await open({ device: IPHONE }); must(await p.page.evaluate(() => window.__d7.I.isIOS() && !window.__d7.I.supportsPrompt()), 'iOS emulation wrong'); must((await p.card().count()) === 1, 'no card on iPhone');
  const ms = await timed(async () => { await p.button().click(); await p.waitSheet(/Add to Home Screen/); }); must(ms < 800, 'sheet took ' + ms + ' ms'); const t = await p.sheetText();
  must(/Share/.test(t) && /Add to Home Screen/.test(t) && /Tap Add/.test(t), 'ios steps missing: ' + t); must(/created in Safari does not show up/.test(t), 'wallet note missing or wrong browser: ' + t); must(/Opened this inside another app/.test(t) && /Open in Safari/.test(t), 'in-app hint missing'); });

await step('I08 iPhone link flag: the Share steps open at once', async () => {
  const p = await open({ device: IPHONE, path: '/?install=1' }); await p.waitSheet(/Add to Home Screen/, 1500); must(/Share/.test(await p.sheetText()), 'expected Share steps'); });

await step('I09 running from the home screen (display-mode standalone, Android): no card, no WebKit note, link flag ignored', async () => {
  const p = await open({ device: PIXEL, standalone: true, path: '/?install=1' }); must(await p.page.evaluate(() => window.__d7.I.standalone()), 'standalone() false'); must((await p.card().count()) === 0, 'card shown while standalone');
  await p.page.waitForTimeout(600); must(!(await p.sheetOpen()), 'sheet opened while standalone'); must(!/replace that passkey/i.test(await p.text()), 'WebKit note on Android'); must(!(await p.page.evaluate(() => location.search)).includes('install'), 'flag kept'); });

await step('I10 iPhone home-screen app with no wallet: no card; the warning sits above Create my wallet and names the recovery route', async () => {
  const p = await open({ device: IPHONE, iosStandalone: true }); must(await p.page.evaluate(() => window.__d7.I.standalone()), 'standalone() false on iOS'); must((await p.card().count()) === 0, 'card shown in iOS home-screen app');
  const t = await p.text(); must(/Already made a wallet in a browser on this device/.test(t) && /recovery code/i.test(t) && /separate wallet/.test(t), 'warning missing: ' + t.slice(0, 400));
  const order = await p.page.evaluate(() => { const n = document.querySelector('.note.warn'), b = document.querySelector('#create'); return n && b && (n.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0; }); must(order, 'warning is not above the Create button'); });

await step('I11 iPad (Mac user agent, MacIntel platform, five touch points) counts as iOS', async () => {
  const p = await open({ device: { ...IPHONE, userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15', viewport: { width: 820, height: 1180 } }, ipad: true, webkit: true });
  must(await p.page.evaluate(() => window.__d7.I.isIOS()), 'iPad not detected'); });

await step('I12 desktop Chromium without touch: not iOS, the menu line names Install app and Add to Home screen', async () => {
  const p = await open({}); must(!(await p.page.evaluate(() => window.__d7.I.isIOS())), 'desktop detected as iOS'); await p.button().click(); await p.waitSheet(/Install app/); must(/Add to Home screen/i.test(await p.sheetText()), 'menu line missing'); });

await step('I13 beforeinstallprompt fired before the app module loaded is kept by index.html (default prevented) and adopted by the module', async () => {
  const ctx = await browser.newContext({ ...PIXEL, baseURL: `http://localhost:${PORT}` }); const page = await ctx.newPage(); cur = { ctx, page };
  await page.route('**/dist/app.js', async (route) => { await page.waitForFunction(() => document.readyState !== 'loading', null, { polling: 20, timeout: 10000 }); await page.evaluate(`${FIRE}('accepted', false)`); await route.continue(); });
  await page.goto('/'); await page.waitForFunction(() => /Get started/.test(document.body.innerText) && window.__d7 && window.__d7.I);
  must(await page.evaluate(() => !!window.__bip && window.__bipEvt.defaultPrevented), 'index.html did not keep the early event with preventDefault'); must(await page.evaluate(() => window.__d7.I.canPrompt()), 'module did not adopt the early event');
  await page.getByRole('button', { name: 'Add to home screen' }).click(); await page.waitForFunction(() => /Your browser will ask to install/.test(document.querySelector('#overlay').innerText)); });

await step('I14 appinstalled while the pre-prompt sheet is open (install from the browser menu): the sheet says Adding it now, prompt() is never called', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('accepted'); await p.button().click(); await p.waitSheet(/Your browser will ask/); await p.page.evaluate(() => window.dispatchEvent(new Event('appinstalled')));
  await p.waitSheet(/Adding it now/, 1500); must((await p.page.evaluate(() => window.__prompted || 0)) === 0, 'prompt() was called'); must((await p.card().count()) === 0, 'card still shown'); });

await step('I15 prompt() rejected by the browser: Not installed, the event is spent, the card stays', async () => {
  const p = await open({ device: PIXEL }); await p.firePrompt('accepted', true); await p.button().click(); await p.waitSheet(/Your browser will ask/); await p.action('Install').click(); await p.waitSheet(/Not installed/);
  must(!(await p.page.evaluate(() => window.__d7.I.canPrompt())), 'event should be spent'); await p.action('OK').click(); must((await p.card().count()) === 1, 'card gone'); });

await step('I16 display-mode flips to standalone (tab moved into the app window): the card hides without appinstalled; an accepted dialog there says Installed', async () => {
  const p = await open({ device: PIXEL }); must((await p.card().count()) === 1, 'no card'); await p.page.evaluate(() => window.__setStandalone(true)); await p.page.waitForFunction(() => !document.querySelector('[data-install]:not([hidden])'));
  must(!(await p.page.evaluate(() => window.__d7.I.available())), 'available() in standalone');
  const q = await open({ device: PIXEL }); await q.firePrompt('accepted'); await q.button().click(); await q.waitSheet(/Your browser will ask/); await q.page.evaluate(() => window.__setStandalone(true)); await q.action('Install').click(); await q.waitSheet(/Installed/);
  must(/You are now in the app/.test(await q.sheetText()), 'desktop wording missing'); await p.ctx.close(); });

await step('I17 Chrome on iPhone takes the iOS branch and the note names Chrome, not Safari', async () => {
  const p = await open({ device: CRIOS }); must(await p.page.evaluate(() => window.__d7.I.isIOS() && window.__d7.I.browserName() === 'Chrome'), 'browser name'); await p.button().click(); await p.waitSheet(/Add to Home Screen/);
  const t = await p.sheetText(); must(/created in Chrome does not show up/.test(t) && !/created in Safari/.test(t), 'note names the wrong browser: ' + t); });

await step('I18 Android WebView (in-app browser): the open-in-Chrome line comes first in the menu sheet', async () => {
  const p = await open({ device: ANDROID_WV }); must(await p.page.evaluate(() => window.__d7.I.inAppView()), 'WebView not detected'); await p.button().click(); await p.waitSheet(/Open in Chrome/);
  const t = await p.sheetText(); must(t.indexOf('Opened this inside another app') < t.indexOf('In your browser'), 'in-app line not first: ' + t); });

await step('I19 iOS in-app web view (no Safari token, not standalone): the open-in-Safari line comes first in the iOS sheet', async () => {
  const p = await open({ device: IOS_INAPP }); must(await p.page.evaluate(() => window.__d7.I.inAppView() && !window.__d7.I.standalone()), 'iOS web view not detected'); await p.button().click(); await p.waitSheet(/Open in Safari/);
  const t = await p.sheetText(); must(t.indexOf('Opened this inside another app') < t.indexOf('Share'), 'in-app line not first: ' + t); });

await step('I20 iPhone in dark mode: the iOS sheet renders (screenshot kept in results/screens/install-ios-dark.png)', async () => {
  const p = await open({ device: IPHONE, colorScheme: 'dark' }); await p.button().click(); await p.waitSheet(/Add to Home Screen/); await p.page.screenshot({ path: join(resultsDir, 'screens', 'install-ios-dark.png') });
  const c = await p.page.evaluate(() => getComputedStyle(document.querySelector('.sheet')).backgroundColor); must(c !== 'rgb(255, 255, 255)', 'sheet not dark: ' + c); });

await step('I21 browser reports the app already installed (getInstalledRelatedApps): no card from the start', async () => {
  const p = await open({ device: PIXEL, installedApps: [{ platform: 'webapp', url: 'https://scottonchain.github.io/microcredit-agent-testbed/manifest.webmanifest' }] });
  await p.page.waitForFunction(() => window.__d7.I.isInstalled()); must((await p.page.evaluate(() => document.querySelectorAll('[data-install]:not([hidden])').length)) === 0, 'card shown for an installed app'); });

await step('I22 Cancel on the asking-now sheet closes it, and the late dialog result is ignored', async () => {
  const p = await open({ device: PIXEL }); await p.page.evaluate(() => { const e = new Event('beforeinstallprompt', { cancelable: true }); e.prompt = () => new Promise(() => {}); e.userChoice = new Promise(() => {}); window.dispatchEvent(e); });
  await p.button().click(); await p.waitSheet(/Your browser will ask/); await p.action('Install').click(); await p.waitSheet(/asking now/); await p.action('Cancel').click(); must(!(await p.sheetOpen()), 'sheet still open'); await p.page.waitForTimeout(300); must(!(await p.sheetOpen()), 'sheet reopened'); });

await step('I23 Help-screen wording for a person who has a wallet: Copy your recovery code first (iOS sheet with S.cred set)', async () => {
  const p = await open({ device: IPHONE }); await p.page.evaluate(() => { window.__d7.S.cred = { id: 'x', publicKey: '0x01' }; }); await p.button().click(); await p.waitSheet(/Add to Home Screen/);
  must(/Copy your recovery code first/.test(await p.sheetText()), 'has-wallet note missing'); });

await step('I24 no uncaught page errors across the welcome and the sheets', async () => {
  const p = await open({ device: PIXEL }); await p.button().click(); await p.waitSheet(/Install app/); await p.action('OK').click(); must(p.errors.length === 0, 'errors: ' + p.errors.join('; ')); });

await browser.close(); web.close();
writeFileSync(join(resultsDir, 'test-app-install.json'), JSON.stringify(results, null, 1)); const ok = results.filter((r) => r.ok).length; console.log(`\n${ok}/${results.length} cases pass`); process.exit(ok === results.length ? 0 : 1);
