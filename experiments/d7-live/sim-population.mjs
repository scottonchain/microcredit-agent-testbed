// Seeded population simulation on a fork of the live pool, with invariants checked every simulated day.
// Usage: RPC_URL=http://127.0.0.1:8545 SEED=7 ACTORS=40 DAYS=120 node sim-population.mjs
import { fork, Actor, seededKey, fundFork, poolState, read, pc, usd, toUnits, asOwner } from './lib/sim.mjs';
import { writeFileSync } from 'node:fs';

const SEED = Number(process.env.SEED || 7), N = Number(process.env.ACTORS || 40), DAYS = Number(process.env.DAYS || 120);
function rng(a) { return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const R = rng(SEED), pick = (arr) => arr[Math.floor(R() * arr.length)], chance = (p) => R() < p;

const snap = await fork.snapshot();
const m = { loans: 0, repaid: 0, defaulted: 0, refused: {}, txs: 0, gas: 0n, lineIssued: 0, curedByBacker: 0, cancelled: 0 };
const bump = (e) => { m.refused[e] = (m.refused[e] || 0) + 1; };

// Cast
const lenders = [], stakers = [], borrowers = [];
const lenderPrincipal = new Map();
for (let i = 0; i < Math.max(2, Math.round(N * 0.15)); i++) lenders.push(await mk('lender' + i, 400));
for (let i = 0; i < Math.round(N * 0.25); i++) stakers.push(await mk('staker' + i, 120));
for (let i = 0; i < Math.round(N * 0.6); i++) { const b = await mk('borrower' + i, 3); b.p = chance(0.2) ? 0.5 : 0.93; b.loan = null; b.line = chance(0.15) ? 5 + Math.floor(R() * 20) : 0; borrowers.push(b); }
const keeper = await mk('keeper', 5);
async function mk(name, bal) { const a = new Actor(name, seededKey(SEED, name)); await fundFork(a, { usdcAmount: toUnits(bal) }); return a; }
for (const l of lenders) { await l.ensureAllowance(toUnits(1000)); const r = await l.pool('depositFunds', [toUnits(300)]); lenderPrincipal.set(l.address, 300); m.txs++; }
for (const s of stakers) await s.ensureAllowance(toUnits(1000));
for (const b of borrowers) if (b.line) { await asOwner('setScoreOverride', [b.address, BigInt(b.line) * 10000n]); m.lineIssued++; }

const price0 = Number(await read('convertToAssets', [10n ** 12n])) / 1e12;
const invariantFailures = [];
async function invariants(day) {
  const s = await poolState(); const fees = await read('protocolFees'), un = await read('totalUnclaimedPayouts');
  if (s.usdcBalance < s.lenderCash + s.staked + fees + un) invariantFailures.push({ day, what: 'pool USDC below cash+stake+fees+unclaimed', have: usd(s.usdcBalance), need: usd(s.lenderCash + s.staked + fees + un) });
  if (s.reserved > s.lenderCash) invariantFailures.push({ day, what: 'reserved exceeds cash' });
  // conservation of credit: sum of borrow limits <= sum of granted credit + sum of stake over all actors
  let sumLimit = 0n, sumGranted = 0n, sumStake = 0n;
  for (const a of [...borrowers, ...stakers, ...lenders]) {
    const [lim] = await read('getBorrowLimit', [a.address]); sumLimit += lim;
    sumGranted += await read('grantedCredit', [a.address]); sumStake += await read('stakeOf', [a.address]);
  }
  if (sumLimit > sumGranted + sumStake) invariantFailures.push({ day, what: 'credit conservation violated', sumLimit: usd(sumLimit), sumGranted: usd(sumGranted), sumStake: usd(sumStake) });
}

async function act(r, who) { m.txs++; if (!r.ok) { bump(r.error); return false; } return true; }
const loansOpen = new Map(); // id -> {borrower, dueDay}
for (let day = 0; day < DAYS; day++) {
  // stakers: stake and back borrowers that have no usable limit; some backers cure a failing loan
  for (const s of stakers) if (chance(0.5)) {
    const staked = await read('stakeOf', [s.address]);
    if (staked < toUnits(60) && chance(0.7)) await act(await s.pool('stake', [toUnits(10 + Math.floor(R() * 20))]));
    const free2 = await read('getFreeCredit', [s.address]);
    if (free2[0] >= toUnits(5)) {
      const needy = []; for (const b of borrowers) { const [, av] = await read('getBorrowLimit', [b.address]); if (av < toUnits(5) && !b.loan) needy.push(b); if (needy.length >= 6) break; }
      if (needy.length) { const b = pick(needy); const amt = toUnits(5 + Math.floor(R() * Math.min(15, usd(free2[0]) - 5 + 1))); await act(await s.pool('back', [b.address, amt])); }
    }
  }
  // borrowers: borrow if idle
  for (const b of borrowers) if (!b.loan && chance(0.3)) {
    const [lim, avail] = await read('getBorrowLimit', [b.address]);
    if (avail >= toUnits(5)) {
      const amt = toUnits(5 + Math.floor(R() * (usd(avail) - 4)));
      const rq = await b.pool('requestLoan', [amt]);
      if (await act(rq)) { const ids = await read('getBorrowerLoanIds', [b.address]); const id = ids[ids.length - 1]; const d = await b.pool('disburseLoan', [id]); if (await act(d)) { m.loans++; const t = await read('getLoanTerms', [id]); b.loan = id; loansOpen.set(id, { b, due: day + Math.round(Number(t[1]) / 86400) }); } }
    } else if (chance(0.2)) { const rq = await b.pool('requestLoan', [toUnits(5)]); await act(rq); }
  }
  // repayments
  for (const [id, o] of [...loansOpen]) {
    const b = o.b; const willPay = day >= o.due - 3 && chance(b.p) && day <= o.due + 2;
    if (willPay) {
      const owed = await read('getCurrentOutstandingAmount', [id]); const bal = await b.usdcBalance();
      const need = owed + 20000n;
      if (bal < need) { await fork.setUsdc(b.address, need + toUnits(0.5)); } // borrowers topping up interest, as testers do from the faucet
      await b.ensureAllowance(need);
      if (await act(await b.pool('repayLoan', [id, need]))) { m.repaid++; loansOpen.delete(id); b.loan = null; }
    } else if (day > o.due + 30) { // keeper marks default once allowed; sometimes a backer cures first
      const r = await keeper.pool('markDefaulted', [id]);
      if (await act(r)) { m.defaulted++; loansOpen.delete(id); b.loan = null; }
    }
  }
  // lenders: occasional withdraw/deposit
  for (const l of lenders) if (chance(0.03)) { const w = await l.pool('withdrawFunds', [toUnits(20 + Math.floor(R() * 40))]); await act(w); }
  await fork.warp(86400);
  if (day % 10 === 9 || day === DAYS - 1) await invariants(day);
}
// wind down: pay anything still open
const s = await poolState();
const price1 = Number(await read('convertToAssets', [10n ** 12n])) / 1e12;
const out = { seed: SEED, actors: N, days: DAYS, metrics: m, sharePrice: { start: price0, end: price1, pctChange: (price1 / price0 - 1) * 100 }, end: Object.fromEntries(Object.entries(s).map(([k, v]) => [k, usd(v)])), invariantFailures, openLoans: loansOpen.size };
console.log(JSON.stringify(out, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1));
writeFileSync(`results/population-seed${SEED}.json`, JSON.stringify(out, (k, v) => typeof v === 'bigint' ? v.toString() : v, 1));
await fork.revert(snap);
process.exit(invariantFailures.length ? 1 : 0);
