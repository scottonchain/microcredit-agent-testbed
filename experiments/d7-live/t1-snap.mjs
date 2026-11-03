import { fork, Actor, seededKey, fundFork, poolState, read, usd, toUnits } from './lib/sim.mjs';
const show = async (l) => console.log(l, usd((await poolState()).totalAssets));
await show('start');
const s1 = await fork.snapshot(); console.log('snap id', s1);
const l = new Actor('x', seededKey(9, 'x')); await fundFork(l, { usdcAmount: toUnits(100) }); await l.ensureAllowance(toUnits(100)); await l.pool('depositFunds', [toUnits(100)]);
await show('after deposit');
console.log('revert ->', await fork.revert(s1));
await show('after revert');
const s2 = await fork.snapshot(); console.log('snap id', s2);
