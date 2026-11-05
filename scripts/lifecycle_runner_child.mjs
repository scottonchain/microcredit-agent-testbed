// Disposable child for the runner tests. Local fixtures only: a file-backed in-process chain and generated,
// unfunded identities. It exists so a test can send SIGINT/SIGTERM or SIGKILL to a real process at a named
// durable boundary and then start a second process against the same journal and chain file.
// Environment: WORK_DIR, N (wallets), SCENARIO (ok|throw|hang|wait), PAUSE_AT (in_scenario|after_prepare|
// before_broadcast|after_broadcast), LOST, ENABLED (default 1). Prints the checkpoint as one JSON line.

import fs from 'node:fs';
import path from 'node:path';
import { runWithLifecycle, exitCodeFor } from './lifecycle_runner.mjs';
import { makeChain, roster, addr, FUND, TOKEN, CHAIN_ID } from './lifecycle_fixtures.mjs';

const E = process.env;
const dir = E.WORK_DIR; const n = Number(E.N || 2);
const pauseAt = E.PAUSE_AT || '';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const resumeFile = path.join(dir, 'resume');

async function pause(name) {
  if (name !== pauseAt) return;
  fs.writeFileSync(path.join(dir, 'paused.' + name), String(process.pid));
  for (let i = 0; i < 600 && !fs.existsSync(resumeFile); i++) await sleep(50);
}

const chain = makeChain({
  file: path.join(dir, 'chain.json'), fund: 1000n, lost: E.LOST ? E.LOST.split(',') : [],
  hooks: { after_prepare: () => pause('after_prepare'), before_broadcast: () => pause('before_broadcast'), after_broadcast: () => pause('after_broadcast') },
});

const result = await runWithLifecycle({
  enabled: E.ENABLED !== '0', runId: 'child-run', fundingWallet: FUND, roster: roster(n), ports: chain.ports,
  journalPath: path.join(dir, 'private', 'journal.json'), token: TOKEN, chainId: CHAIN_ID, timeoutMs: 20000, settleGraceMs: 200,
  fund: async () => {
    const tokens = {}; const gas = {};
    for (let i = 1; i <= n; i++) { tokens[addr(i)] = BigInt(10 * i); gas[addr(i)] = 1000n; }
    await chain.placeFunds({ tokens, gas });
  },
  scenario: async ({ signal }) => {
    if (E.SCENARIO === 'throw') throw new Error('secret-token-abc');
    if (E.SCENARIO === 'hang' || E.SCENARIO === 'wait' || pauseAt === 'in_scenario') {
      fs.writeFileSync(path.join(dir, 'paused.in_scenario'), String(process.pid));
      await new Promise(res => { signal.addEventListener('abort', res, { once: true }); });
      return;
    }
  },
});
process.stdout.write(JSON.stringify({ status: result.status, ok: result.ok, scenario: result.scenario, resumed: result.resumed, interrupted: result.interrupted, checkpoint: result.checkpoint }) + '\n');
process.exitCode = exitCodeFor(result);
