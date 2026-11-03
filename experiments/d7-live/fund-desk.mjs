// Add test stake to the practice world's credit desk from the fork's deployer (free test USDC on the fork).
import { createRequire } from 'node:module'; import { readFileSync } from 'node:fs';
import { Actor, seededKey, fundFork, toUnits, ADDR, pc } from './lib/sim.mjs';
const DESK = process.argv[2], AMT = toUnits(Number(process.argv[3] || 500));
const dep = new Actor('deployer', seededKey(7, 'deployer')); await fundFork(dep, { usdcAmount: AMT });
const abi = JSON.parse(readFileSync('./abi/CreditDesk.json', 'utf8')).abi || JSON.parse(readFileSync('./abi/CreditDesk.json', 'utf8'));
const r1 = await dep.token('approve', [DESK, AMT]); console.log('approve', r1.ok ?? r1);
const r2 = await dep.call(DESK, abi, 'fund', [AMT]).catch((e) => ({ error: e.message })); console.log('fund', r2.ok ?? r2);
const free = await pc.readContract({ address: DESK, abi, functionName: 'freeStake' }); console.log('freeStake now', Number(free) / 1e6);
