// Offline browser regressions. No RPC calls or live-chain evidence.
const { chromium } = require('playwright');
const { readFileSync, mkdirSync } = require('node:fs');
const { createServer } = require('node:http');
const { join, resolve } = require('node:path');
const shots = resolve(process.argv[2] || '/tmp/dashboard-render');
const snapshot = JSON.parse(readFileSync(join(__dirname,'data/snapshot.json'),'utf8'));
let url;
const server=createServer((req,res)=>{
  const paths={'/':'index.html','/data/snapshot.js':'data/snapshot.js','/data/snapshot.json':'data/snapshot.json'};
  const file=paths[req.url];
  if(!file){res.writeHead(404);res.end();return;}
  res.setHeader('Content-Type',file.endsWith('.html')?'text/html':file.endsWith('.js')?'text/javascript':'application/json');
  res.end(readFileSync(join(__dirname,file)));
});
mkdirSync(shots,{recursive:true});
let checks=0; const failures=[];
function check(ok, label) {checks++; if(!ok) failures.push(label); console.log(`${ok?'ok':'FAIL'} ${label}`);}
(async()=>{
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
url=`http://127.0.0.1:${server.address().port}/`;
const browser=await chromium.launch({headless:true, ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {}), args:['--no-sandbox']});
for (const [scheme,width] of [['light',1200],['dark',1200],['light',390]]) {
  const context=await browser.newContext({viewport:{width,height:900},colorScheme:scheme});
  const page=await context.newPage(), errors=[], requests=[];
  await page.route(/^https?:\/\//,r=>{requests.push(r.request().url());return r.request().url().startsWith(url)?r.continue():r.abort();});
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(url); await page.waitForFunction(()=>window.LENDING_REFRESH_DONE);
  const label=`${scheme} ${width}`;
  check(!errors.length,`${label}: no page errors`);
  check((await page.locator('#foot').innerText()).includes('Claude (AI); corrected by Codex (AI)'),`${label}: visible AI disclosure`);
  check((await page.locator('body').innerText()).includes('Balanced omitted deposits and withdrawals can pass'),`${label}: visible event-completeness limit`);
  check((await page.locator('#live').innerText()).includes('Historical snapshot'),`${label}: no false live claim`);
  check((await page.locator('#live').innerText()).includes('stale'),`${label}: unknown verification is stale`);
  check(await page.locator('.tile').count()===6,`${label}: six accounting tiles`);
  check(await page.locator('#ledger tbody tr').count()===snapshot.loans.length,`${label}: preserved ledger`);
  check(await page.locator('#flow-chart svg path').count()===2,`${label}: two series`);
  check((await page.locator('#score-reserve').innerText()).includes('+0.000836'),`${label}: small NAV change visible`);
  check((await page.locator('#score-reserve').innerText()).includes('0.000684'),`${label}: reserve distinct`);
  check((await page.locator('#tiles').innerText()).includes('0.001520'),`${label}: gross interest distinct`);
  check((await page.locator('#score-human').innerText()).includes('NOT MEASURED'),`${label}: no human benefit claim`);
  check(!(await page.locator('#outcome-kv').innerText()).includes('First-time'),`${label}: no first request proxy`);
  check((await page.locator('#refresh-note').innerText()).includes('retained dated snapshot'),`${label}: refresh failure preserves data`);
  check(!requests.some(u=>/sepolia|tenderly/.test(u)),`${label}: no chain requests`);
  for(let i=0;i<4;i++){
    await page.click('#flow-table-btn');
    check(await page.locator('#flow-table').isVisible(),`${label}: table toggle ${i}`);
    await page.click('#flow-table-btn');
    check(await page.locator('#flow-chart').isVisible(),`${label}: chart toggle ${i}`);
    await page.click('#example-btn');
    check(await page.locator('#who .example').count()===1,`${label}: synthetic example toggle ${i}`);
    await page.click('#example-btn');
    check(await page.locator('#who .example').count()===0,`${label}: synthetic example closes ${i}`);
  }
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth),`${label}: no horizontal overflow`);
  await page.screenshot({path:join(shots,`dashboard-${scheme}-${width}.png`),fullPage:true});
  // Simulated published snapshot: fresh verification may change without any ledger changes.
  const verified=structuredClone(snapshot);
  verified.snapshot.verification='reconciled-finalized-v1'; verified.snapshot.collectedAt=new Date().toISOString();
  await page.evaluate(async data=>{
    window.fetch=async path=>({ok:true,json:async()=>String(path).includes('refresh-status')?{status:'success',attemptedAt:data.snapshot.collectedAt}:data});
    window.LENDING_REFRESH_DONE=false; document.getElementById('refresh-btn').click();
  },verified);
  await page.waitForFunction(()=>window.LENDING_REFRESH_DONE);
  check((await page.locator('#live').innerText()).includes('Reconciled committed'),`${label}: unchanged ledger fresh verification`);
  check(!(await page.locator('#live').innerText()).includes('Live from'),`${label}: verification still not live`);
  verified.snapshot.collectedAt=new Date(Date.now()-31*3600000).toISOString();
  await page.evaluate(data=>{window.LENDING_SNAPSHOT=data;},verified);
  // A malicious refresh with personal attributes is rejected, as is a reorged saved boundary.
  for(const mutation of ['profiles','hash','failure']){
    await page.evaluate(async({data,mutation})=>{
      if(mutation==='profiles')data.profiles=[{country:'PRIVATE_SENTINEL',loanId:1,consentVersion:1}];
      if(mutation==='hash')data.snapshot.blockHash='0x'+'ee'.repeat(32);
      window.fetch=async()=>{if(mutation==='failure')throw Error('PRIVATE_PROVIDER_ERROR');return {ok:true,json:async()=>data};};
      window.LENDING_REFRESH_DONE=false; document.getElementById('refresh-btn').click();
    },{data:verified,mutation});
    await page.waitForFunction(()=>window.LENDING_REFRESH_DONE);
    check((await page.locator('#refresh-note').innerText()).includes('retained dated snapshot'),`${label}: ${mutation} rejected`);
    check(!(await page.locator('body').innerText()).includes('PRIVATE_'),`${label}: ${mutation} no private error/profile display`);
    check(await page.locator('#ledger tbody tr').count()===snapshot.loans.length,`${label}: ${mutation} keeps last good ledger`);
  }
  await context.close();
}
// Boot-time invalid/missing data and old verified data.
for(const mode of ['missing','profile','old']){
  const page=await browser.newPage();
  await page.route(/^https?:\/\//,r=>r.request().url().startsWith(url)?r.continue():r.abort());
  await page.route('**/snapshot.js',r=>{
    const s=structuredClone(snapshot);
    if(mode==='profile')s.profiles=[{country:'PRIVATE_SENTINEL'}];
    if(mode==='old'){s.snapshot.verification='reconciled-finalized-v1';s.snapshot.collectedAt='2026-01-01T00:00:00Z';}
    return r.fulfill({contentType:'text/javascript',body:`window.LENDING_SNAPSHOT=${JSON.stringify(mode==='missing'?null:s)};`});
  });
  await page.goto(url);
  if(mode==='old')check((await page.locator('#live').innerText()).includes('Stale'), 'old verified snapshot stale');
  else {check((await page.locator('#sub').innerText()).includes('No usable snapshot'),`${mode}: unavailable, not zero`);check(await page.locator('.tile').count()===0,`${mode}: no asserted totals`);}
  await page.close();
}
await browser.close(); server.close();
console.log(`${checks-failures.length}/${checks} render checks passed`);
if(failures.length)throw Error(failures.join('\n'));
})().catch(e=>{console.error(e);server.close();process.exit(1);});
