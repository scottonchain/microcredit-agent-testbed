#!/usr/bin/env node
// A person's wallet in the simulation. Usage: node sim/agent.mjs <name> <command> [args]. Output is JSON.
import { load, save, wallet, view, act, resolve, nameOf, P, poolCall, usdcCall, toUnits, usd, maxUint256, createAgent, logEvent, DIR, ADDR, ABI } from './lib.mjs';
import { readFileSync, appendFileSync, existsSync } from 'node:fs'; import { join } from 'node:path';
import { fork } from '../lib/sim.mjs';

const [name, cmd, ...a] = process.argv.slice(2);
const out = (o) => { console.log(JSON.stringify(o, (k, v) => (typeof v === 'bigint' ? v.toString() : v), 1)); process.exit(0); };
const num = (s) => { const v = Number(s); if (!isFinite(v) || v <= 0) throw new Error('amount must be a positive number'); return toUnits(v); };
if (!name || !cmd) out({ usage: 'node sim/agent.mjs <name> status|world|borrow|repay|send|back|stake|unstake|deposit|withdraw|faucet|post|board|default|cure|newwallet ...' });
const st = load(); const w = await wallet(name, st);
const day = st.day;

try {
  switch (cmd) {
    case 'status': { const v = await view(w); const nm = (x) => nameOf(st, x); out({ day, ...v, backedBy: v.backedBy.map((b) => ({ backer: nm(b.backer), amount: b.amount })), youBack: v.youBack.map((b) => ({ borrower: nm(b.borrower), amount: b.amount })) }); }
    case 'world': {
      const ids = await P(w.client, 'getAllLoanIds'); const now = Number((await w.client.getBlock()).timestamp); const rows = [];
      for (const id of ids) { const t = await P(w.client, 'getLoanTerms', [id]); if (Number(t[0]) === 2) { const l = await P(w.client, 'getLoan', [id]); const bks = (await P(w.client, 'getBackings', [l[2]])).map((x) => ({ backer: nameOf(st, x.backer), amount: usd(x.secured + x.unsecured) })).filter((x) => x.amount > 0); rows.push({ loanId: Number(id), borrower: nameOf(st, l[2]), backedBy: bks, principal: usd(l[0]), owedNow: usd(await P(w.client, 'getCurrentOutstandingAmount', [id])), dueInDays: Math.round((Number(t[4]) - now) / 86400 * 10) / 10, overdueDays: Math.max(0, Math.round((now - Number(t[4])) / 86400)) }); } }
      const me = await view(w); const board = existsSync(join(DIR, 'board.jsonl')) ? readFileSync(join(DIR, 'board.jsonl'), 'utf8').trim().split('\n').filter(Boolean).slice(-15).map((l) => JSON.parse(l)) : [];
      out({ day, pool: me.pool, activeLoans: rows, people: Object.keys(st.agents), recentBoardPosts: board });
    }
    case 'borrow': { const v = num(a[0]); const ids = await P(w.client, 'getAllLoanIds'); const build = async () => { const cur = await P(w.client, 'getAllLoanIds'); return [poolCall('requestLoan', [v]), poolCall('disburseLoan', [(cur.length ? cur[cur.length - 1] : 0n) + 1n])]; };
      let r = await act(w, 'borrow ' + a[0], await build(), { preflightFn: 'requestLoan', preflightArgs: [v] }); if (!r.ok && /LoanNotRequested|WrongBorrower/.test(r.error || '')) r = await act(w, 'borrow retry', await build()); if (r.ok) { const v1 = await view(w); const l = v1.openLoans.find((x) => x.state === 'active'); out({ ...r, loan: l, youNowHave: v1.usdc }); } out(r); }
    case 'repay': { const v0 = await view(w); const loan = v0.openLoans.find((l) => l.state === 'active'); if (!loan) out({ ok: false, error: 'NoActiveLoan', message: 'You have no active loan.' });
      const owed = await P(w.client, 'getCurrentOutstandingAmount', [BigInt(loan.id)]); const head = 20000n; const want = a[0] && a[0] !== 'all' ? num(a[0]) : owed + head;
      const calls = []; const allow = await w.client.readContract({ address: ADDR.usdc, abi: (await import('../lib/chain.mjs')).ABI.erc20, functionName: 'allowance', args: [w.address, ADDR.pool] });
      if (allow < want) calls.push(usdcCall('approve', [ADDR.pool, want])); calls.push(poolCall('repayLoan', [BigInt(loan.id), want]));
      const r = await act(w, 'repay ' + (a[0] || 'all'), calls); const v1 = await view(w); out({ ...r, loanId: loan.id, owedBefore: usd(owed), usdcAfter: v1.usdc, stillOwes: v1.openLoans.map((l) => l.owedNow) }); }
    case 'send': out(await act(w, `send ${a[1]} to ${a[0]}`, [usdcCall('transfer', [resolve(st, a[0]), num(a[1])])]));
    case 'back': { const to = resolve(st, a[0]); const v = Number(a[1]) === 0 ? 0n : num(a[1]); const fr = await P(w.client, 'getFreeCredit', [w.address]); const have = fr[0] + fr[1]; const cb = await w.client.readContract({ address: ADDR.pool, abi: ABI.pool, functionName: 'getBacking', args: [w.address, to] }); const cur = cb[0] + cb[1]; const extra = v > cur ? v - cur : 0n; const need = extra > have ? extra - have : 0n; const calls = [];
      if (need > 0n) { calls.push(usdcCall('approve', [ADDR.pool, need])); calls.push(poolCall('stake', [need])); } calls.push(poolCall('back', [to, v])); const before = await view(w); const r = await act(w, `back ${a[0]} ${a[1]}`, calls); const after = await view(w); out({ ...r, ...(r.ok ? { newStakeLocked: usd(need), yourBorrowLimitBefore: before.borrowLimit, yourBorrowLimitAfter: after.borrowLimit, note: 'Backing uses your own credit first, so your own borrowing limit can drop by what you back.' } : { note: 'Nothing was changed: if the action failed, no stake was locked.' }) }); }
    case 'stake': out(await act(w, 'stake ' + a[0], [usdcCall('approve', [ADDR.pool, num(a[0])]), poolCall('stake', [num(a[0])])]));
    case 'unstake': out(await act(w, 'unstake ' + a[0], [poolCall('unstake', [num(a[0])])]));
    case 'deposit': out(await act(w, 'deposit ' + a[0], [usdcCall('approve', [ADDR.pool, num(a[0])]), poolCall('depositFunds', [num(a[0])])]));
    case 'withdraw': out(await act(w, 'withdraw ' + a[0], [poolCall('withdrawFunds', [a[0] === 'all' ? maxUint256 : num(a[0])])]));
    case 'default': out(await act(w, 'markDefaulted ' + a[0], [poolCall('markDefaulted', [BigInt(a[0])])], { preflightFn: 'markDefaulted', preflightArgs: [BigInt(a[0])] }));
    case 'cure': { const id = BigInt(a[0]); const owed = await P(w.client, 'getCurrentOutstandingAmount', [id]); const want = owed + 20000n; out(await act(w, 'cure ' + a[0], [usdcCall('approve', [ADDR.pool, want]), poolCall('repayLoan', [id, want])])); }
    case 'faucet': { // stands in for the Circle faucet: a small drop, limited per person per two sim days
      const last = st.agents[name].lastFaucetDay ?? -99; if (day - last < 2) out({ ok: false, message: `The faucet already gave you test USDC on day ${last}. Try again in ${2 - (day - last)} day(s).` });
      const bal = await (await import('../lib/chain.mjs')).publicClient().readContract({ address: ADDR.usdc, abi: (await import('../lib/chain.mjs')).ABI.erc20, functionName: 'balanceOf', args: [w.address] }); const { fork: f } = await import('../lib/sim.mjs'); await f.setUsdc(w.address, bal + toUnits(20));
      const s2 = load(); s2.agents[name].lastFaucetDay = day; save(s2); logEvent({ who: name, label: 'faucet', ok: true }); out({ ok: true, message: 'The faucet sent you 20 test USDC.' }); }
    case 'post': appendFileSync(join(DIR, 'board.jsonl'), JSON.stringify({ day, from: name, text: a.join(' ').slice(0, 300) }) + '\n'); out({ ok: true });
    case 'board': out(existsSync(join(DIR, 'board.jsonl')) ? readFileSync(join(DIR, 'board.jsonl'), 'utf8').trim().split('\n').filter(Boolean).slice(-30).map((l) => JSON.parse(l)) : []);
    case 'newwallet': { if (name !== 'Dev') out({ ok: false, message: 'Only the tester Dev may create extra wallets (adversarial test).' }); const s2 = load(); const nn = a[0]; if (s2.agents[nn]) out({ ok: false, message: 'exists' }); const ad = await createAgent(nn, s2); save(s2); out({ ok: true, name: nn, address: ad }); }
    case 'diary': { const { mkdirSync, appendFileSync: ap } = await import('node:fs'); mkdirSync(join(DIR, 'diary'), { recursive: true }); ap(join(DIR, 'diary', name + '.md'), `\n## Day ${day}\n${a.join(' ')}\n`); out({ ok: true }); }
    case 'audit': { if (name !== 'Reg') out({ ok: false, message: 'Only the auditor Reg can run audit.' }); const rows = {}; let sumLimit = 0, sumStake = 0, sumGranted = 0;
      for (const n of Object.keys(st.agents)) { const wn = await wallet(n, st); const v = await view(wn); const gr = usd(await P(w.client, 'grantedCredit', [wn.address])); rows[n] = { usdc: v.usdc, limit: v.borrowLimit, stake: v.totalStake, granted: gr, open: v.openLoans.length, defaulted: v.loansDefaulted }; sumLimit += v.borrowLimit; sumStake += v.totalStake; sumGranted += gr; }
      const me = await view(w); const bal = await w.client.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [ADDR.pool] }); const cash = await P(w.client, 'lenderCash'); const staked = await P(w.client, 'totalStaked'); const fees = await P(w.client, 'protocolFees'); const un = await P(w.client, 'totalUnclaimedPayouts');
      out({ day, rows, conservation: { sumBorrowLimits: sumLimit, sumGrantedPlusStake: sumGranted + sumStake, holds: sumLimit <= sumGranted + sumStake + 1e-6 }, poolSolvency: { poolUsdcBalance: usd(bal), cashPlusStakePlusFeesPlusUnclaimed: usd(cash + staked + fees + un), holds: bal >= cash + staked + fees + un }, pool: me.pool }); }
    default: out({ ok: false, message: 'unknown command ' + cmd });
  }
} catch (e) { out({ ok: false, error: String(e.shortMessage || e.message).slice(0, 200), message: 'The command failed: ' + String(e.message).slice(0, 120) }); }
