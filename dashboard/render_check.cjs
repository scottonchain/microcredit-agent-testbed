// Headless render check for dashboard/index.html against the committed snapshot.
// Usage: node dashboard/render_check.cjs [screenshot-dir]   (needs playwright with its chromium)
// Asserts the page renders every section from the snapshot with no console errors and
// no horizontal overflow at phone width, then writes light/dark screenshots.
const { chromium } = require("playwright");
const { readFileSync, mkdirSync } = require("node:fs");
const { pathToFileURL } = require("node:url");
const { join, resolve } = require("node:path");

const here = __dirname;
const shots = resolve(process.argv[2] || join(here, "..", "evidence", "lending-dashboard-20261103"));
const snapshot = JSON.parse(readFileSync(join(here, "data", "snapshot.json"), "utf8"));
const url = pathToFileURL(join(here, "index.html")).href;

mkdirSync(shots, { recursive: true });
const failures = [];
const check = (ok, what) => { if (!ok) failures.push(what); console.log(`${ok ? "ok  " : "FAIL"} ${what}`); };

(async () => {
const browser = await chromium.launch();
for (const [scheme, width] of [["light", 1200], ["dark", 1200], ["light", 390]]) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, colorScheme: scheme, deviceScaleFactor: 2 });
  const page = await context.newPage();
  await page.route(/^https?:\/\//, (route) => route.abort());  // offline path: the committed snapshot must stand on its own
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error" && !m.text().includes("net::ERR_FAILED")) errors.push(m.text()); });  // aborted network loads are expected offline
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(url);
  await page.waitForLoadState("networkidle").catch(() => {});
  const label = `${scheme} ${width}px`;
  check(errors.length === 0, `${label}: no console or page errors${errors.length ? " (" + errors.join("; ") + ")" : ""}`);
  await page.waitForFunction(() => window.LENDING_LIVE_ERROR !== undefined);
  check((await page.locator("#live").innerText()).includes("live read unavailable"), `${label}: offline badge names the committed snapshot`);
  check(await page.locator(".tile").count() === 6, `${label}: six headline tiles`);
  check(await page.locator("#ledger tbody tr").count() === snapshot.loans.length, `${label}: ledger has ${snapshot.loans.length} loan rows`);
  check(await page.locator("#flow-chart svg path").count() === 2, `${label}: two cumulative series drawn`);
  check((await page.locator("#sub").innerText()).includes(snapshot.snapshot.blockNumber.toLocaleString("en-US")), `${label}: header names block ${snapshot.snapshot.blockNumber}`);
  const who = await page.locator("#who").innerText();
  check(who.includes(`${snapshot.humanMetrics.attestedLoans.withProfile} of ${snapshot.loans.length} loans`), `${label}: profile section states ${snapshot.humanMetrics.attestedLoans.withProfile} of ${snapshot.loans.length} loans`);
  check(who.includes(snapshot.profileSchema.uid), `${label}: profile section shows the schema UID`);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  check(overflow <= 0, `${label}: no horizontal page overflow (${overflow}px)`);
  if (width === 1200) {
    await page.click("#flow-table-btn");
    check(await page.locator("#flow-table table tbody tr").count() === snapshot.monthly.length, `${label}: table view lists ${snapshot.monthly.length} months`);
    await page.click("#flow-table-btn");
    if (snapshot.profiles.length === 0) {
      await page.click("#example-btn");
      check(await page.locator("#who .example").count() === 1, `${label}: example profiles render behind the labelled toggle`);
      await page.screenshot({ path: join(shots, `dashboard-${scheme}-${width}-example.png`), fullPage: true });
      await page.click("#example-btn");
    }
  }
  await page.locator("#hit").hover({ position: { x: 300, y: 100 } }).catch(() => {});
  await page.screenshot({ path: join(shots, `dashboard-${scheme}-${width}.png`), fullPage: true });
  await context.close();
}
await browser.close();
console.log(failures.length ? `\n${failures.length} check(s) failed` : "\nall render checks passed");
process.exit(failures.length ? 1 : 0);
})();
