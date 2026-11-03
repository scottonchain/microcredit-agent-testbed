// Scripted scenario suite against a fork of the live pool. Each scenario starts from a snapshot and reverts after.
import { fork, Actor, seededKey, fundFork, poolState, read, pc, usd, toUnits, asOwner, ADDR, ABI } from './lib/sim.mjs';
import { writeFileSync } from 'node:fs';

const SEED = Number(process.env.SEED || 1);
const ST = { None: 0, Requested: 1, Active: 2, Repaid: 3, Defaulted: 4, Cancelled: 5 };
const results = [];
let cur;
const eq = (name, got, want) => { const ok = got === want; cur.checks.push({ name, ok, got: String(got), want: String(want) }); };
const near = (name, got, want, tol) => { const ok = Math.abs(Number(got) - Number(want)) <= tol; cur.checks.push({ name, ok, got: String(got), want: `${want}±${tol}` }); };
const yes = (name, cond, note = '') => cur.checks.push({ name, ok: !!cond, got: String(!!cond), want: 'true', note });
const refused = (name, r, err) => cur.checks.push({ name, ok: r.ok === false && r.error === err, got: r.ok ? 'SUCCEEDED' : r.error, want: err });

async function person(name, usdcAmount = 0) {
  const a = new Actor(name, seededKey(SEED, name));
  await fundFork(a, { usdcAmount: toUnits(usdcAmount) });
  return a;
}
async function seedPool(amount = 500) {
  const l = await person('lender-' + Math.random().toString(36).slice(2, 6), amount);
  await l.ensureAllowance(toUnits(amount)); await l.pool('depositFunds', [toUnits(amount)]); return l;
}
async function borrowFull(b, amount) {
  const r = await b.pool('requestLoan', [toUnits(amount)]); if (!r.ok) return { ...r, id: null };
  const ids = await read('getBorrowerLoanIds', [b.address]); const id = ids[ids.length - 1];
  const d = await b.pool('disburseLoan', [id]); return { ...d, id };
}
async function payoff(payer, id, headroomUnits = 20000n) {
  const owed = await read('getCurrentOutstandingAmount', [id]);
  await payer.ensureAllowance(owed + headroomUnits);
  return payer.pool('repayLoan', [id, owed + headroomUnits]);
}
async function invariants(label) {
  const s = await poolState(); const protocolFees = await read('protocolFees');
  const unclaimed = await read('totalUnclaimedPayouts');
  const need = s.lenderCash + s.staked + protocolFees + unclaimed;
  yes(`${label}: pool USDC (${usd(s.usdcBalance)}) covers cash+stake+fees (${usd(need)})`, s.usdcBalance >= need);
  yes(`${label}: reserved liquidity within cash`, s.reserved <= s.lenderCash);
}

async function scenario(name, fn) {
  const snap = await fork.snapshot(); cur = { name, checks: [], started: Date.now() };
  try { await fn(); } catch (e) { cur.checks.push({ name: 'UNCAUGHT ' + (e.shortMessage || e.message).slice(0, 160), ok: false, got: 'exception', want: 'none' }); }
  cur.ms = Date.now() - cur.started; cur.pass = cur.checks.every((c) => c.ok); results.push(cur);
  console.log(`${cur.pass ? 'PASS' : 'FAIL'}  ${name}  (${cur.checks.filter(c => c.ok).length}/${cur.checks.length}, ${cur.ms} ms)`);
  for (const c of cur.checks.filter((c) => !c.ok)) console.log('      x', c.name, '| got', c.got, 'want', c.want);
  await fork.revert(snap);
}

await scenario('S1 stake-led cold start: stake, back, borrow, repay after 15 days', async () => {
  await seedPool(500);
  const staker = await person('staker', 30), b = await person('borrower', 5);
  await staker.ensureAllowance(toUnits(30));
  eq('stake 20 ok', (await staker.pool('stake', [toUnits(20)])).ok, true);
  eq('back 20 ok', (await staker.pool('back', [b.address, toUnits(20)])).ok, true);
  const [limit] = await read('getBorrowLimit', [b.address]);
  eq('borrower limit is 20', usd(limit), 20);
  const t0 = (await pc.getBlock()).timestamp;
  const l = await borrowFull(b, 20); eq('borrow 20 ok', l.ok, true);
  eq('borrower holds 25', usd(await b.usdcBalance()), 25);
  await fork.warp(15 * 86400);
  const owed = await read('getCurrentOutstandingAmount', [l.id]);
  near('interest ~ 20*9.33%*15/365 = 0.0767', usd(owed) - 20, 0.0767, 0.006);
  const r = await payoff(b, l.id); eq('payoff ok', r.ok, true);
  const t = await read('getLoanTerms', [l.id]); eq('loan status Repaid', Number(t[0]), ST.Repaid);
  yes('borrower earned dues', (await read('duesPaid', [b.address])) > 0n);
  eq('staker stake intact', usd(await read('stakeOf', [staker.address])), 20);
  yes('share price rose (assets > deposits)', (await read('totalAssets')) > toUnits(515));
  await invariants('S1');
});

await scenario('S2 refusal matrix', async () => {
  await seedPool(500);
  const staker = await person('staker', 50), b = await person('b', 5), c = await person('c', 5), stranger = await person('stranger', 5);
  await staker.ensureAllowance(toUnits(50)); await staker.pool('stake', [toUnits(20)]);
  refused('fresh borrower, no credit', await stranger.pool('requestLoan', [toUnits(5)]), 'NoCredit');
  refused('self-backing', await staker.pool('back', [staker.address, toUnits(5)]), 'SelfBacking');
  refused('backing below minimum', await staker.pool('back', [b.address, 100000n]), 'BackingTooSmall');
  refused('backer without credit', await stranger.pool('back', [b.address, toUnits(5)]), 'InsufficientCredit');
  refused('over-backing own stake', await staker.pool('back', [b.address, toUnits(25)]), 'InsufficientCredit');
  eq('back 10 ok', (await staker.pool('back', [b.address, toUnits(10)])).ok, true);
  refused('borrow above limit', await b.pool('requestLoan', [toUnits(11)]), 'BorrowLimitExceeded');
  refused('pass received backing on', await b.pool('back', [c.address, toUnits(5)]), 'InsufficientCredit');
  refused('unstake committed stake', await staker.pool('unstake', [toUnits(15)]), 'StakeCommitted');
  eq('unstake free 10 ok', (await staker.pool('unstake', [toUnits(10)])).ok, true);
  const l = await borrowFull(b, 10); eq('borrow 10 ok', l.ok, true);
  refused('disburse by stranger', await stranger.pool('disburseLoan', [l.id]), 'LoanNotRequested');
  refused('markDefaulted before due', await stranger.pool('markDefaulted', [l.id]), 'NotYetDefaultable');
  refused('lower backing below use', await staker.pool('back', [b.address, toUnits(5)]), 'BackingInUse');
  refused('zero repayment', await b.pool('repayLoan', [l.id, 0n]), 'ZeroAmount');
  await invariants('S2');
});

await scenario('S3 default: stake slashed, lenders whole, borrower blocked', async () => {
  await seedPool(500);
  const staker = await person('staker', 30), b = await person('b', 0), r = await person('rescuer', 5);
  await staker.ensureAllowance(toUnits(30)); await staker.pool('stake', [toUnits(10)]); await staker.pool('back', [b.address, toUnits(10)]);
  const before = await read('totalAssets');
  const l = await borrowFull(b, 10); eq('borrow 10 ok', l.ok, true);
  await fork.warp(31 * 86400);
  refused('too early (past due, within late period)', await r.pool('markDefaulted', [l.id]), 'NotYetDefaultable');
  await fork.warp(31 * 86400);
  const d = await r.pool('markDefaulted', [l.id]); eq('default ok after due+late', d.ok, true);
  eq('staker stake slashed to 0', usd(await read('stakeOf', [staker.address])), 0);
  eq('loan status Defaulted', Number((await read('getLoanTerms', [l.id]))[0]), ST.Defaulted);
  yes('lenders not worse off (totalAssets >= before)', (await read('totalAssets')) >= before - 1n);
  eq('borrower default count', Number(await read('defaultedLoans', [b.address])), 1);
  refused('defaulted borrower cannot borrow', await b.pool('requestLoan', [toUnits(1)]), 'BorrowerInDefault');
  await invariants('S3');
});

await scenario('S4 third-party cure (CI-28) and partial repayment', async () => {
  await seedPool(500);
  const staker = await person('staker', 40), b = await person('b', 0);
  await staker.ensureAllowance(toUnits(40)); await staker.pool('stake', [toUnits(20)]); await staker.pool('back', [b.address, toUnits(20)]);
  const l = await borrowFull(b, 20);
  await fork.warp(10 * 86400);
  await b.ensureAllowance(toUnits(5)); const p = await b.pool('repayLoan', [l.id, toUnits(5)]); eq('partial 5 ok', p.ok, true);
  eq('loan still active', Number((await read('getLoanTerms', [l.id]))[0]), ST.Active);
  const c = await payoff(staker, l.id); eq('backer pays off the rest', c.ok, true);
  eq('loan Repaid', Number((await read('getLoanTerms', [l.id]))[0]), ST.Repaid);
  await invariants('S4');
});

await scenario('S5 ring of ten fresh accounts: no credit appears', async () => {
  await seedPool(500);
  const ring = []; for (let i = 0; i < 10; i++) ring.push(await person('ring' + i, 5));
  let refusals = 0, loanRefusals = 0;
  for (let i = 0; i < 10; i++) { const r = await ring[i].pool('back', [ring[(i + 1) % 10].address, toUnits(100)]); if (!r.ok && r.error === 'InsufficientCredit') refusals++; }
  for (const m of ring) { const r = await m.pool('requestLoan', [toUnits(5)]); if (!r.ok && r.error === 'NoCredit') loanRefusals++; }
  eq('10 backings refused', refusals, 10); eq('10 loans refused', loanRefusals, 10);
});

await scenario('S6 issuer line: unsecured borrow, repay, default burns granted credit', async () => {
  await seedPool(500);
  const b = await person('b', 5);
  await asOwner('setScoreOverride', [b.address, 250000n]); // 0.25 * 100 USDC line
  const [limit] = await read('getBorrowLimit', [b.address]); eq('limit 25', usd(limit), 25);
  const l1 = await borrowFull(b, 25); eq('borrow 25 unsecured ok', l1.ok, true);
  await fork.warp(20 * 86400); const r = await payoff(b, l1.id); eq('repay ok', r.ok, true);
  const l2 = await borrowFull(b, 25); eq('second loan ok', l2.ok, true);
  await fork.warp(70 * 86400); const before = await read('totalAssets');
  const d = await (await person('anyone', 1)).pool('markDefaulted', [l2.id]); eq('default ok', d.ok, true);
  yes('lenders lose at most the unpaid 25', before - (await read('totalAssets')) <= toUnits(25) + 1n);
  eq('borrower blocked after default', (await b.pool('requestLoan', [toUnits(1)])).error, 'BorrowerInDefault');
  await invariants('S6');
});

await scenario('S7 payoff arithmetic: principal alone does not close; headroom does', async () => {
  await seedPool(500);
  const staker = await person('staker', 50), b = await person('b', 5);
  await staker.ensureAllowance(toUnits(50)); await staker.pool('stake', [toUnits(10)]); await staker.pool('back', [b.address, toUnits(10)]);
  const l = await borrowFull(b, 10); await fork.warp(30 * 86400);
  await b.ensureAllowance(toUnits(10)); await b.pool('repayLoan', [l.id, toUnits(10)]);
  eq('principal-only leaves loan active', Number((await read('getLoanTerms', [l.id]))[0]), ST.Active);
  const owed = await read('getCurrentOutstandingAmount', [l.id]); yes('owes interest sliver', owed > 0n && owed < toUnits(0.2));
  const r = await b.pool('repayLoan', [l.id, owed + 5000n]); eq('final repay ok', r.ok, true);
  eq('loan Repaid', Number((await read('getLoanTerms', [l.id]))[0]), ST.Repaid);
  await invariants('S7');
});

await scenario('S8 liquidity: utilisation cap stops lending at 90% of assets', async () => {
  await seedPool(500);
  const assets = usd(await read('totalAssets')); const cap = assets * 0.9;
  let ok = 0, capHit = 0, others = [];
  const nb = Math.ceil(cap / 100) + 3;
  for (let i = 0; i < nb; i++) {
    const b = await person('bb' + i, 0); await asOwner('setScoreOverride', [b.address, 1000000n]);
    const r = await b.pool('requestLoan', [toUnits(100)]);
    if (r.ok) ok++; else if (r.error === 'UtilisationCapExceeded' || r.error === 'InsufficientLiquidity') capHit++; else others.push(r.error);
  }
  const lent = usd((await poolState()).reserved);
  yes(`cap enforced: reserved ${lent} <= ${cap.toFixed(1)} (ok=${ok}, capped=${capHit}, other=${others.join(',')})`, lent <= cap + 0.001 && capHit >= 1 && others.length === 0);
  await invariants('S8');
});

await scenario('S9 request then cancel releases reservation; stale reservation can be cancelled by anyone', async () => {
  await seedPool(500);
  const staker = await person('staker', 30), b = await person('b', 0), x = await person('x', 0);
  await staker.ensureAllowance(toUnits(30)); await staker.pool('stake', [toUnits(10)]); await staker.pool('back', [b.address, toUnits(10)]);
  const r = await b.pool('requestLoan', [toUnits(10)]); eq('request ok', r.ok, true);
  const ids = await read('getBorrowerLoanIds', [b.address]); const id = ids[ids.length - 1];
  eq('status Requested', Number((await read('getLoanTerms', [id]))[0]), ST.Requested);
  yes('reservation held', (await read('reservedLiquidity')) >= toUnits(10));
  refused('stranger cannot cancel early', await x.pool('cancelLoan', [id]), 'NotCancellableYet');
  await fork.warp(8 * 86400);
  eq('anyone cancels after TTL', (await x.pool('cancelLoan', [id])).ok, true);
  eq('status Cancelled', Number((await read('getLoanTerms', [id]))[0]), ST.Cancelled);
  eq('reservation released', usd(await read('reservedLiquidity')), 0);
  await invariants('S9');
});

writeFileSync(`results/suite-core-seed${SEED}-${IS_FORK_LABEL()}.json`, JSON.stringify(results, null, 1));
const total = results.reduce((n, r) => n + r.checks.length, 0), ok = results.reduce((n, r) => n + r.checks.filter(c => c.ok).length, 0);
console.log(`\n${results.filter(r => r.pass).length}/${results.length} scenarios pass, ${ok}/${total} checks`);
function IS_FORK_LABEL() { return 'fork'; }
process.exit(results.every((r) => r.pass) ? 0 : 1);
