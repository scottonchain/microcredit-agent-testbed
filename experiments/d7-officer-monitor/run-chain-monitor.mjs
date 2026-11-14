#!/usr/bin/env node
// CLI for one chain-only check: node run-chain-monitor.mjs <config.json>. Prints the validated board comment to stdout, nothing else, and posts
// nothing. Exit 0 = OK, 2 = ALERT, 3 = config or message invalid. Read-only; no key; not run by anything in this repository.
import { readFileSync } from 'node:fs';
import { runOnce } from './adapter.mjs';
export async function main(argv, io = {}) {
  const read = io.readFile ?? ((p) => readFileSync(p, 'utf8'));
  let config; try { config = JSON.parse(read(argv[2])); } catch { config = undefined; }
  const r = await runOnce({ config, now: io.now ?? (() => Date.now()), fetchImpl: io.fetchImpl ?? globalThis.fetch, sleep: io.sleep ?? ((ms) => new Promise((res) => setTimeout(res, ms))) });
  (io.write ?? ((s) => process.stdout.write(s)))(r.body ?? '');
  return r.exitCode;
}
if (import.meta.url === `file://${process.argv[1]}`) main(process.argv).then((c) => process.exit(c));
