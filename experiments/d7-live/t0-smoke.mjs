import { fork, Actor, seededKey, fundFork, poolState, read, pc, usd, toUnits, ADDR, ABI } from './lib/sim.mjs';
const lender = new Actor('lender', seededKey(1, 'lender'));
await fundFork(lender, { usdcAmount: toUnits(1000) });
console.log('usdc after cheat', usd(await lender.usdcBalance()));
console.log('state before', Object.fromEntries(Object.entries(await poolState()).map(([k, v]) => [k, usd(v)])));
await lender.ensureAllowance(toUnits(1000));
const r = await lender.pool('depositFunds', [toUnits(500)]);
console.log('deposit', r.ok, r.hash?.slice(0, 12), r.error);
console.log('state after', Object.fromEntries(Object.entries(await poolState()).map(([k, v]) => [k, usd(v)])));
