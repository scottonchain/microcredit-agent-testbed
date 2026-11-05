// Runs the decoder tests when its pinned dependency is installed (`npm ci` in this folder); otherwise says so
// plainly and exits 0, because the repository's checks run without network installs. A SKIPPED line is not a pass:
// the decoder is reviewed only where these tests have run.
import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
if (!existsSync(path.join(here, 'node_modules', 'viem'))) {
  console.log('SKIPPED: viem is not installed (run `npm ci` in scripts/lifecycle_verifier); the cryptographic decoder tests did not run');
  process.exit(0);
}
const r = spawnSync(process.execPath, ['--test', path.join(here, 'test_verify_prepared.mjs')], { stdio: 'inherit' });
process.exit(r.status ?? 1);
