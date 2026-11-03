// Live-read check: serve the page with an OLDER committed snapshot and let it catch up from the chain,
// then compare what it shows with the collector's full snapshot at a later block.
// Usage: node dashboard/live_check.cjs <old-snapshot-dir> [reference snapshot.json]   (needs network and playwright)
// The reference defaults to dashboard/data/snapshot.json. Totals that cannot change after the reference
// block (counts and flows at or before it) must match exactly; the page may be ahead of the reference.
const { chromium } = require("playwright");
const http = require("node:http");
const { readFileSync, existsSync } = require("node:fs");
const { join, resolve, extname } = require("node:path");

const here = __dirname;
const oldDir = resolve(process.argv[2] || "");
const reference = JSON.parse(readFileSync(resolve(process.argv[3] || join(here, "data", "snapshot.json")), "utf8"));
if (!existsSync(join(oldDir, "snapshot.js"))) { console.error("usage: node dashboard/live_check.cjs <dir with an older snapshot.js>"); process.exit(2); }

const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const path = req.url.split("?")[0];
  const file = path.startsWith("/data/") ? join(oldDir, path.slice(6)) : join(here, path === "/" ? "index.html" : path.slice(1));
  if (!existsSync(file)) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "content-type": types[extname(file)] || "application/octet-stream" }); res.end(readFileSync(file));
});
const canon = (v) => JSON.stringify(v, (k, x) => (x && typeof x === "object" && !Array.isArray(x)) ? Object.fromEntries(Object.keys(x).sort().map((key) => [key, x[key]])) : x);
const failures = [];
const check = (ok, what) => { if (!ok) failures.push(what); console.log(`${ok ? "ok  " : "FAIL"} ${what}`); };

(async () => {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const url = `http://127.0.0.1:${server.address().port}/`;
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(url);
  await page.waitForFunction(() => window.LENDING_LIVE !== undefined || window.LENDING_LIVE_ERROR !== undefined, null, { timeout: 180000 });
  const err = await page.evaluate(() => window.LENDING_LIVE_ERROR);
  check(!err, `live read completed${err ? " (" + err + ")" : ""}`);
  check(errors.length === 0, `no page errors${errors.length ? " (" + errors.join("; ") + ")" : ""}`);
  const live = await page.evaluate(() => window.LENDING_LIVE);
  const old = JSON.parse(readFileSync(join(oldDir, "snapshot.json"), "utf8"));
  console.log(`old snapshot block ${old.snapshot.blockNumber} (${old.loans.length} loans) -> page caught up to block ${live.snapshot.blockNumber} with ${live.snapshot.live.newEvents} new events; reference block ${reference.snapshot.blockNumber}`);
  check(live.snapshot.blockNumber >= reference.snapshot.blockNumber, "page block is at or after the reference block");
  check(live.snapshot.live.newEvents > 0, "events were read live (the old snapshot predates them)");
  const same = (a, b, what) => check(canon(a) === canon(b), `${what}: ${canon(a).length > 120 ? canon(a).slice(0, 117) + "..." : canon(a)} == reference`);
  // Loans that the reference knows must match the page loan for loan (same closing state, amounts and flags).
  const refLoans = new Map(reference.loans.map((l) => [l.id, l]));
  let mismatches = 0;
  for (const l of live.loans) {
    const r = refLoans.get(l.id); if (!r) continue;
    const keys = ["borrower", "principal", "status", "repaid", "interest", "firstLoan", "daysToRepay", "termDays", "dueAt", "writtenOff"];
    for (const k of keys) if (canon(l[k]) !== canon(r[k])) { mismatches++; console.log(`     loan ${l.id} ${k}: page ${JSON.stringify(l[k])} vs reference ${JSON.stringify(r[k])}`); }
    if (canon(l.closed) !== canon(r.closed)) { mismatches++; console.log(`     loan ${l.id} closed differs`); }
  }
  check(mismatches === 0, `every reference loan matches the page loan for loan (${reference.loans.length} loans compared)`);
  const ahead = live.snapshot.blockNumber > reference.snapshot.blockNumber && live.snapshot.eventCount > reference.snapshot.eventCount;
  if (ahead) console.log("     page is ahead of the reference; totals compared with >= instead of ==");
  const ge = (a, b, what) => check(ahead ? a >= b : a === b, `${what}: page ${a} vs reference ${b}`);
  ge(live.loans.length, reference.loans.length, "loan count");
  ge(live.flows.disbursed, reference.flows.disbursed, "disbursed");
  ge(live.flows.repaid, reference.flows.repaid, "repaid");
  ge(live.flows.deposited, reference.flows.deposited, "deposited");
  ge(live.flows.withdrawn, reference.flows.withdrawn, "withdrawn");
  ge(live.flows.interest, reference.flows.interest, "interest");
  ge(live.snapshot.eventCount, reference.snapshot.eventCount, "events read");
  if (!ahead) {
    same(live.loanStatus, reference.loanStatus, "loans by status");
    same(live.humanMetrics, reference.humanMetrics, "human metrics");
    same(live.backing, reference.backing, "backing edges");
    same(live.monthly.map((m) => [m.month, m.cumulative]), reference.monthly.map((m) => [m.month, m.cumulative]), "monthly cumulatives");
    same(live.stake, reference.stake, "stake by account");
    same(live.profileSchema.registered, reference.profileSchema.registered, "profile schema registered flag");
    for (const k of ["totalAssets", "lenderCash", "totalLentOut", "lenderCount", "sharePrice", "totalStaked"]) same(live.pool[k], reference.pool[k], `pool ${k}`);
  }
  check((await page.locator("#live").innerText()).startsWith("Live from the chain"), "badge says the page is live");
  check((await page.locator("#ledger tbody tr").count()) === live.loans.length, "ledger re-rendered with every loan");
  await browser.close(); server.close();
  console.log(failures.length ? `\n${failures.length} check(s) failed` : "\nall live checks passed");
  process.exit(failures.length ? 1 : 0);
})();
