// Mobile layout audit for the Omnequa theme. Usage:
//   node audit.cjs <baseURL> <outDir> [widths]      e.g. node audit.cjs http://127.0.0.1:8765 ./shots 320,360,390,414,768
//   node audit.cjs https://omnequa.org ./live-shots
// Measures horizontal overflow, elements outside the viewport, nav link size, text under 12px and tap targets under 24px.
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
const base = (process.argv[2] || 'http://127.0.0.1:8765').replace(/\/$/, ''); const out = process.argv[3] || 'shots';
const widths = (process.argv[4] || '320,360,390,414,768').split(',').map(Number);
const pages = ['/', '/about/', '/history/', '/how-we-work/', '/journal/', '/journal/read/', '/newsroom/', '/contact/', '/privacy/', '/partners/', '/mission/'];
const local = /^https?:\/\/(127\.0\.0\.1|localhost)/.test(base);
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch(); const report = [];
  for (const w of widths) {
    const ctx = await browser.newContext({ viewport: { width: w, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
    const page = await ctx.newPage();
    if (local) await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, r => r.abort());
    for (const p of pages) {
      const res = await page.goto(base + p, { waitUntil: 'load' }); await page.waitForTimeout(300);
      const m = await page.evaluate(() => {
        const vw = document.documentElement.clientWidth, sw = document.documentElement.scrollWidth; const offenders = [];
        for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect(); if (r.width && (r.right > vw + 1 || r.left < -1)) offenders.push({ tag: el.tagName.toLowerCase(), cls: String(el.className || '').slice(0, 60), left: Math.round(r.left), right: Math.round(r.right), text: (el.textContent || '').trim().slice(0, 40) }); }
        const nav = document.querySelector('.site-header nav'); let navInfo = null;
        if (nav) navInfo = { overflow: nav.scrollWidth > nav.clientWidth + 1, links: [...nav.querySelectorAll('a')].map(a => { const b = a.getBoundingClientRect(); return { t: a.textContent, l: Math.round(b.left), r: Math.round(b.right), h: Math.round(b.height), fs: getComputedStyle(a).fontSize }; }) };
        const smallText = []; for (const el of document.querySelectorAll('a,p,li,span,button,figcaption,small,label,dt,time')) { const fs = parseFloat(getComputedStyle(el).fontSize); if (!el.children.length && (el.textContent || '').trim() && fs < 12) smallText.push({ tag: el.tagName.toLowerCase(), cls: String(el.className || '').slice(0, 40), fs, text: (el.textContent || '').trim().slice(0, 30) }); }
        const smallTargets = []; for (const el of document.querySelectorAll('a,button,input,textarea,summary')) { const r = el.getBoundingClientRect(); if (r.width && r.height && (r.height < 24 || r.width < 24) && getComputedStyle(el).position !== 'absolute') smallTargets.push({ tag: el.tagName.toLowerCase(), cls: String(el.className || '').slice(0, 40), w: Math.round(r.width), h: Math.round(r.height), text: (el.textContent || '').trim().slice(0, 30) }); }
        const h1 = document.querySelector('h1'); const vp = document.querySelector('meta[name=viewport]');
        return { vw, sw, hOverflow: sw > vw, nOffenders: offenders.length, offenders: offenders.slice(0, 12), navInfo, h1: h1 ? getComputedStyle(h1).fontSize : null, nSmallText: smallText.length, smallText: smallText.slice(0, 10), nSmallTargets: smallTargets.length, smallTargets: smallTargets.slice(0, 10), viewport: vp ? vp.content : null, stylesheet: [...document.styleSheets].map(s => s.href).filter(Boolean) };
      });
      const name = (p.replace(/^\/|\/$/g, '') || 'home').replace(/\//g, '_');
      await page.screenshot({ path: path.join(out, `${name}-${w}.png`) });
      report.push({ page: p, width: w, status: res && res.status(), ...m });
      console.log(`${w}px ${p.padEnd(16)} status=${res && res.status()} scrollW=${m.sw} overflow=${m.hOverflow} offenders=${m.nOffenders} navOverflow=${m.navInfo && m.navInfo.overflow} navFont=${m.navInfo && m.navInfo.links[0] && m.navInfo.links[0].fs} text<12px=${m.nSmallText} targets<24px=${m.nSmallTargets} h1=${m.h1} viewport=${m.viewport}`);
    }
    await ctx.close();
  }
  await browser.close(); fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
})();
