#!/usr/bin/env node
// Sender-side dedup step: node decide-post.mjs <status-comment.md> <comments.json> <count.txt> [dedup-config.json]
// Reads three local files, prints exactly two lines for $GITHUB_OUTPUT (`post=true|false`, `reason=<CLOSED_CODE>`), posts nothing, and holds no token.
// Exit 0 = a decision was made (post or quiet skip). Exit 3 = halt: the job must fail visibly (bad config, bad candidate, unreadable or incomplete
// listing, board near its comment cap). The printed values come from closed lists, so nothing from the board can reach the output file.
import { readFileSync } from 'node:fs';
import { decide, POST_REASONS, SKIP_REASONS, HALT_REASONS } from './dedup.mjs';

export function main(argv, io = {}) {
  const read = io.readFile ?? ((p) => readFileSync(p, 'utf8'));
  const out = io.write ?? ((s) => process.stdout.write(s));
  const nowMs = (io.now ?? (() => Date.now()))();
  const decideFn = io.decide ?? decide; // injectable so the tests can feed this wrapper a hostile or inconsistent decision
  let candidate, listing, config;
  try { candidate = read(argv[2]); } catch { candidate = undefined; }
  try {
    const comments = JSON.parse(read(argv[3])); const count = Number(String(read(argv[4])).trim());
    listing = /^\d{1,7}$/.test(String(read(argv[4])).trim()) ? { count, comments } : null; // Number('') is 0 and Number('0x10') is 16, so the text is checked first
  } catch { listing = null; }
  if (argv[5] !== undefined) { try { config = JSON.parse(read(argv[5])); } catch { config = null; } }
  let d; try { d = decideFn({ candidate, listing, nowMs, config }); } catch { d = null; }
  if (!d || typeof d !== 'object') d = { post: false, halt: true, reason: 'INTERNAL' };
  const known = d.post ? POST_REASONS : d.halt ? HALT_REASONS : SKIP_REASONS;
  const reason = known.includes(d.reason) ? d.reason : 'INTERNAL';
  out(`post=${d.post && !d.halt && reason === d.reason ? 'true' : 'false'}\nreason=${reason}\n`);
  return d.halt || reason !== d.reason ? 3 : 0;
}
if (import.meta.url === `file://${process.argv[1]}`) process.exit(main(process.argv));
