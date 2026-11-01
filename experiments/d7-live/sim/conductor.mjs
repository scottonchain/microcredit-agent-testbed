#!/usr/bin/env node
// Runs the shared clock and the world for the persona simulation on a fork. Commands: init | advance DAYS | report | stop
import { spawn } from 'node:child_process'; import { readFileSync, writeFileSync, rmSync, existsSync } from 'node:fs'; import { join } from 'node:path';
import { parseEther } from 'viem';
import { load, save, DIR, createAgent, view, wallet, P, nameOf } from './lib.mjs';
import { Actor, seededKey, fundFork, fork, read, poolState, usd, toUnits, asOwner, pc } from '../lib/sim.mjs';
import { deployPaymaster } from '../deploy-paymaster.mjs';
import { ADDR } from '../lib/chain.mjs';

const RPC = process.env.RPC_URL || 'http://127.0.0.1:8546';
const PEOPLE = { Amara: 5, Kofi: 200, Lina: 80, Dev: 30, Maya: 3, Omar: 5, Sam: 5, Reg: 0 };
const [cmd, arg] = process.argv.slice(2);

if (cmd === 'init') {
  rmSync(DIR, { recursive: true, force: true });
  const deployerKey = seededKey(3, 'deployer'), bundlerKey = seededKey(3, 'bundler');
  await fundFork(new Actor('d', deployerKey), { eth: parseEther('5') }); await fundFork(new Actor('b', bundlerKey), { eth: parseEther('5') });
  const pm = await deployPaymaster({ rpc: RPC, key: deployerKey, cap: parseEther('0.05') });
  writeFileSync('/tmp/claude-0/sim-bundler.key', bundlerKey, { mode: 0o600 });
  const child = spawn('node', ['bundler-server.mjs'], { env: { ...process.env, RPC_URL: RPC, BUNDLER_KEY_FILE: '/tmp/claude-0/sim-bundler.key', PORT: '4338' }, detached: true, stdio: ['ignore', 'ignore', 'ignore'] }); child.unref();
  await new Promise((r) => setTimeout(r, 2500));
  const st = { rpc: RPC, bundler: 'http://127.0.0.1:4338', paymaster: pm.address, day: 0, agents: {}, bundlerPid: child.pid };
  for (const n of Object.keys(PEOPLE)) { const a = await createAgent(n, st); await fork.setUsdc(a, toUnits(PEOPLE[n])); }
  save(st);
  await asOwner('setScoreOverride', [st.agents.Omar.address, 300000n]); // Omar was granted a 30 USDC test line by the test operator
  console.log(JSON.stringify({ ok: true, paymaster: pm.address, bundlerPid: child.pid, people: Object.fromEntries(Object.entries(st.agents).map(([k, v]) => [k, v.address])) }, null, 1));
} else if (cmd === 'advance') {
  const st = load(); const d = Number(arg || 1); await fork.warp(d * 86400); st.day += d; save(st); console.log(JSON.stringify({ day: st.day }));
} else if (cmd === 'report') {
  const st = load(); const s = await poolState(); const price = Number(await read('convertToAssets', [10n ** 12n])) / 1e12;
  const rows = {}; for (const n of Object.keys(st.agents)) { const w = await wallet(n, st); const v = await view(w); rows[n] = { usdc: v.usdc, stake: v.totalStake, lenderBalance: v.lenderBalance, open: v.openLoans.map((l) => `#${l.id} owes ${l.owedNow} due in ${l.dueInDays}d`), repaid: v.loansRepaid, defaulted: v.loansDefaulted, dues: v.duesPaid }; }
  const ev = existsSync(join(DIR, 'events.jsonl')) ? readFileSync(join(DIR, 'events.jsonl'), 'utf8').trim().split('\n').map((l) => JSON.parse(l)) : [];
  const refused = {}; let ok = 0, fail = 0; for (const e of ev) { if (e.label === 'faucet') continue; if (e.ok) ok++; else { fail++; refused[e.error] = (refused[e.error] || 0) + 1; } }
  console.log(JSON.stringify({ day: st.day, pool: Object.fromEntries(Object.entries(s).map(([k, v]) => [k, usd(v)])), sharePriceVs1: price, actions: { ok, fail }, refusals: refused, people: rows }, null, 1));
} else if (cmd === 'stop') { try { process.kill(load().bundlerPid); } catch {} console.log('stopped');
} else console.log('usage: conductor.mjs init|advance DAYS|report|stop');
process.exit(0);
