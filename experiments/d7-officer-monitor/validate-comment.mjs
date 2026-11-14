#!/usr/bin/env node
// Sender-side gate: node validate-comment.mjs <comment.md>. Exit 0 only if the file is exactly the fixed-shape status comment.
import { readFileSync } from 'node:fs';
import { validateBoardComment } from './adapter.mjs';
export function main(argv, read = (p) => readFileSync(p, 'utf8')) { try { return validateBoardComment(read(argv[2])).ok ? 0 : 1; } catch { return 1; } }
if (import.meta.url === `file://${process.argv[1]}`) process.exit(main(process.argv));
