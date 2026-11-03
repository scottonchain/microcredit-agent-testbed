// A person's-eye browser for one persona: a phone-sized headless Chromium with a virtual passkey, driven by simple
// commands over HTTP (look, tap, type, press, back, reload, home, wait, days, tabs, switch, closetab, scroll, shot, done).
// Everything the persona can know comes from what is visible on the screen: text, screenshot, and the things to tap.
import { createRequire } from 'node:module'; import http from 'node:http'; import { mkdirSync } from 'node:fs'; import { join } from 'node:path';
const require = createRequire(import.meta.url); const { chromium, devices } = require('playwright');
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const PORT = Number(arg('port', 4201)), DEVICE = arg('device', 'iPhone 13'), ID = arg('id', 'p000'), BASE = arg('base', 'http://localhost:4173'), WORLD = arg('world', 'http://127.0.0.1:4180'), OUT = arg('out', join(process.cwd(), 'results', ID));
const SCHEME = arg('scheme', 'light'); const FONT = Number(arg('fontscale', 1));
mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const dev = devices[DEVICE] || devices['iPhone 13'];
const ctx = await browser.newContext({ ...dev, baseURL: BASE, colorScheme: SCHEME, locale: 'en-US', timezoneId: 'America/New_York' });
const pages = []; const logs = [];
const track = async (pg) => { if (pages.includes(pg)) return; pages.push(pg); pg.on('console', (m) => logs.push(`${new Date().toISOString()} ${m.type()}: ${m.text()}`)); pg.on('pageerror', (e) => logs.push(`${new Date().toISOString()} pageerror: ${e.message}`)); pg.on('close', () => { const i = pages.indexOf(pg); if (i >= 0) pages.splice(i, 1); }); };
ctx.on('page', track);
const first = await ctx.newPage(); await track(first); // the context's page event may also report it: track() ignores repeats
const cdp = await ctx.newCDPSession(first); await cdp.send('WebAuthn.enable');
await cdp.send('WebAuthn.addVirtualAuthenticator', { options: { protocol: 'ctap2', transport: 'internal', hasResidentKey: true, hasUserVerification: true, isUserVerified: true, automaticPresenceSimulation: true } });
if (FONT !== 1) await first.addInitScript((f) => { document.addEventListener('DOMContentLoaded', () => { document.documentElement.style.fontSize = (16 * f) + 'px'; }); }, FONT);
let cur = 0; let shotN = 0;
// The person opens the link: the phone starts on the app, not on a blank page.
try { await first.goto(BASE + '/', { timeout: 30000 }); } catch (e) { logs.push('first load failed: ' + e.message); }
const page = () => pages[Math.min(cur, pages.length - 1)];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const COLLECT = `(() => {
  const vis = (el) => { if (!el) return false; const r = el.getBoundingClientRect(); const st = getComputedStyle(el); if (el.tagName !== 'SUMMARY' && el.closest('details:not([open])')) return false; return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none' && !el.closest('[hidden]'); };
  const overlay = document.querySelector('#overlay'); const dialogOpen = overlay && !overlay.hidden && vis(overlay);
  const nameOf = (el) => { const t = el.tagName.toLowerCase(); if (t === 'input' || t === 'textarea' || t === 'select') { const lab = el.id && document.querySelector('label[for="' + el.id + '"]'); return (el.getAttribute('aria-label') || (lab && lab.innerText) || el.placeholder || el.name || t).trim(); } return (el.getAttribute('aria-label') || el.innerText || el.title || el.value || '').replace(/\\s+/g, ' ').trim(); };
  const els = Array.from(document.querySelectorAll('button, a[href], input, textarea, select, summary, [role=button]')).filter(vis);
  const list = []; els.forEach((el, i) => { el.setAttribute('data-pidx', String(i)); const t = el.tagName.toLowerCase(); const inDialog = !!el.closest('#overlay');
    if (dialogOpen && !inDialog) return; // when a dialog is on top, only its controls can be used
    const kind = t === 'a' ? 'link' : t === 'summary' ? 'expander' : t === 'input' || t === 'textarea' || t === 'select' ? 'field' : 'button';
    const item = { i, kind, name: nameOf(el), tag: t + (el.id ? '#' + el.id : '') }; if (el.disabled) item.disabled = true; if (kind === 'field') { item.value = el.value || ''; if (el.type === 'checkbox') item.checked = el.checked; }
    if (t === 'summary') item.open = el.parentElement.open; if (t === 'a' && el.target === '_blank') item.opensNewTab = true; list.push(item); });
  const text = dialogOpen ? null : document.body.innerText; const dialog = dialogOpen ? overlay.innerText : null;
  const main = document.querySelector('#app'); const screen = (main ? main.innerText : document.body.innerText);
  const banner = document.querySelector('#banner'); const today = (window.__d7 && window.__d7.now) ? new Date(window.__d7.now() * 1000).toDateString() : new Date().toDateString(); return { today, title: document.title, url: location.href, dialog, screen, banner: banner ? banner.innerText : '', controls: list, scrollY: window.scrollY, pageHeight: document.documentElement.scrollHeight, viewportHeight: innerHeight };
})()`;

// A person looks when the screen has settled: wait until the text stops changing (and no "Loading" remains), up to 8 s.
async function settle(pg, maxMs = 8000) {
  let last = null; const t0 = Date.now();
  while (Date.now() - t0 < Math.max(maxMs, 45000)) {
    let st; try { st = await pg.evaluate(() => { const o = document.querySelector('#overlay'); const busy = o && !o.hidden && /Setting up|Checking with|Sending to the test network|Approve with your|Loading/.test(o.innerText); return { t: document.body.innerText, busy }; }); } catch { return; }
    const t = st.t; if (!st.busy && t === last && !/Loading…/.test(t)) return; if (!st.busy && t !== last && Date.now() - t0 > maxMs) return; last = t; await sleep(400);
  }
}
async function look(label = 'look') {
  const pg = page(); await pg.waitForLoadState('domcontentloaded').catch(() => {}); await settle(pg); await sleep(150);
  let info; try { info = await pg.evaluate(COLLECT); } catch (e) { info = { title: await pg.title().catch(() => ''), url: pg.url(), screen: '(page not readable: ' + e.message.slice(0, 80) + ')', controls: [] }; }
  const shot = join(OUT, `${String(++shotN).padStart(3, '0')}-${label.replace(/[^a-z0-9]+/gi, '_').slice(0, 30)}.png`);
  try { await pg.screenshot({ path: shot, fullPage: false }); } catch {}
  return { tab: `${cur + 1} of ${pages.length}`, ...info, shot };
}
function findControl(controls, name, kinds) {
  const n = name.trim().toLowerCase(); const pool = kinds ? controls.filter((c) => kinds.includes(c.kind)) : controls;
  return pool.find((c) => c.name.toLowerCase() === n) || pool.find((c) => c.name.toLowerCase().startsWith(n)) || pool.find((c) => c.name.toLowerCase().includes(n)) || null;
}
async function tap(name) {
  const pg = page(); const info = await pg.evaluate(COLLECT); const c = findControl(info.controls, name, ['button', 'link', 'expander']) || findControl(info.controls, name);
  if (!c) return { error: `Nothing on the screen is called "${name}". Look again and use the exact words you see.` };
  if (c.disabled) return { error: `"${c.name}" is greyed out and cannot be tapped right now.` };
  const before = pages.length;
  try { await pg.locator(`[data-pidx="${c.i}"]`).first().click({ timeout: 8000 }); } catch (e) { return { error: 'Could not tap "' + c.name + '": ' + e.message.split('\n')[0].slice(0, 120) }; }
  await sleep(900); if (pages.length > before) { cur = pages.length - 1; await sleep(1200); }
  return look('tap_' + c.name);
}
async function type(label, text) {
  const pg = page(); const info = await pg.evaluate(COLLECT); const c = findControl(info.controls, label, ['field']);
  if (!c) return { error: `There is no box called "${label}" to type in. Look again.` };
  try { const loc = pg.locator(`[data-pidx="${c.i}"]`).first(); await loc.fill(''); await loc.type(String(text), { delay: 20 }); } catch (e) { return { error: 'Could not type: ' + e.message.split('\n')[0].slice(0, 120) }; }
  await sleep(500); return look('type_' + c.name);
}
async function handle(cmd, a) {
  const pg = page();
  switch (cmd) {
    case 'look': return look();
    case 'tap': return tap(a.join(' '));
    case 'type': return type(a[0], a.slice(1).join(' '));
    case 'press': await pg.keyboard.press(a[0] || 'Enter'); await sleep(600); return look('press_' + a[0]);
    case 'back': await pg.goBack({ timeout: 8000 }).catch(() => {}); await sleep(700); return look('back');
    case 'reload': await pg.reload({ timeout: 20000 }).catch(() => {}); await sleep(1200); return look('reload');
    case 'home': await pg.goto(BASE + '/', { timeout: 20000 }).catch(() => {}); await sleep(1200); return look('home');
    case 'wait': { const s = Math.min(Number(a[0] || 5), 120); await sleep(s * 1000); return look('wait_' + s + 's'); }
    case 'scroll': { const dir = (a[0] || 'down'); await pg.mouse.wheel(0, dir === 'up' ? -600 : 600); await sleep(400); return look('scroll_' + dir); }
    case 'days': { const d = Math.max(0, Math.min(Number(a[0] || 1), 400)); const r = await fetch(`${WORLD}/warp?seconds=${Math.round(d * 86400)}`).then((x) => x.json()).catch((e) => ({ error: e.message })); if (r.error) return { error: 'The clock could not move: ' + r.error }; await pg.reload({ timeout: 20000 }).catch(() => {}); await sleep(1500); const l = await look('days_' + d); const when = r.chainTime ? new Date(r.chainTime * 1000).toDateString() : ''; l.note = `${d} day(s) have passed${when ? '; today is ' + when : ''}. You open the app again. (Other testers share this clock, so it may have moved further than your own days.)`; return l; }
    case 'tabs': return { tabs: pages.map((p, i) => ({ n: i + 1, current: i === cur, url: p.url() })) };
    case 'switch': { cur = Math.max(0, Math.min(Number(a[0] || 1) - 1, pages.length - 1)); return look('switch'); }
    case 'closetab': { if (pages.length > 1) { await pg.close(); cur = pages.length - 1; } return look('closetab'); }
    case 'shot': return { shot: (await look(a[0] || 'shot')).shot };
    case 'logs': return { logs: logs.slice(-40) };
    case 'done': setTimeout(async () => { try { await browser.close(); } catch {} process.exit(0); }, 300); return { ok: true, bye: true };
    default: return { error: 'unknown command ' + cmd };
  }
}
const server = http.createServer(async (req, res) => {
  let body = ''; req.on('data', (c) => (body += c)); req.on('end', async () => {
    try { const { cmd, args = [] } = JSON.parse(body || '{}'); const out = await handle(cmd, args); res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify(out)); }
    catch (e) { res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
  });
});
server.listen(PORT, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, port: PORT, id: ID, device: DEVICE, out: OUT })));
