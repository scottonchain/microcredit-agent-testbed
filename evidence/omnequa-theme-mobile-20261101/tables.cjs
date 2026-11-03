const { chromium } = require('playwright'); const S=process.argv[2];
(async()=>{const b=await chromium.launch();
for (const [tag,css] of [['before',null],['after',S+'/style-live-patched.css']]) {
  const ctx=await b.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true}); const p=await ctx.newPage();
  if (css) await p.route(/\/style\.css(\?.*)?$/, r=>r.fulfill({path:css,contentType:'text/css'}));
  for (const [name,url,sel] of [['research','https://omnequa.org/research/agent-operated-businesses/','table'],['analytics','https://omnequa.org/analytics/','.chart-data']]) {
    await p.goto(url,{waitUntil:'load'}); await p.waitForTimeout(300);
    const el=await p.$(sel); if(!el){console.log('no',sel);continue;}
    if (name==='analytics') { await p.$$eval('details.chart-data', ds=>ds.forEach(d=>d.open=true)); await p.waitForTimeout(100); }
    await el.scrollIntoViewIfNeeded(); await p.waitForTimeout(100);
    const info=await p.evaluate(()=>({sw:document.documentElement.scrollWidth, tables:[...document.querySelectorAll('table')].map(t=>{const r=t.getBoundingClientRect();return [Math.round(r.left),Math.round(r.right),t.scrollWidth,t.clientWidth]})}));
    console.log(tag,name,JSON.stringify(info));
    await p.screenshot({path:`${S}/live-shots-patched/${name}-table-390-${tag}.png`});
  }
  await ctx.close(); }
await b.close(); })();
