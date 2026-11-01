import { Actor, seededKey, fundFork, read, usd, toUnits, asOwner } from './lib/sim.mjs';
const s = new Actor('s', seededKey(5, 's')); await fundFork(s, { usdcAmount: toUnits(60) }); await s.ensureAllowance(toUnits(60));
const show = async (l) => { const f = await read('getFreeCredit', [s.address]); console.log(l.padEnd(28), 'free=[', usd(f[0]), usd(f[1]), '] stakeOf', usd(await read('stakeOf', [s.address])), 'granted', usd(await read('grantedCredit', [s.address]))); };
await show('fresh'); await s.pool('stake', [toUnits(20)]); await show('after stake 20');
const b = new Actor('b', seededKey(5, 'b')); await s.pool('back', [b.address, toUnits(12)]); await show('after back 12');
await asOwner('setScoreOverride', [s.address, 300000n]); await show('after 30 line');
await s.pool('back', [b.address, toUnits(40)]); await show('after back 40 more');
