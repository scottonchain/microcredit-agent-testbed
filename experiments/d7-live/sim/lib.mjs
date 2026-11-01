// Shared helpers for the persona simulation: state file, agent wallets, public world view.
import { readFileSync, writeFileSync, existsSync, appendFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path'; import { fileURLToPath } from 'node:url';
import { maxUint256, getAddress, isAddress } from 'viem';
import { clients, openWallet, newCredential, poolCall, usdcCall, runOp } from '../lib/wallet.mjs';
import { SoftAuthenticator } from '../lib/softpasskey.mjs';
import { ADDR, ABI, usd, toUnits } from '../lib/chain.mjs';
import { friendly } from '../app/src/errors.js';

export const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'sim-state');
export const STATE = join(DIR, 'state.json');
export const load = () => JSON.parse(readFileSync(STATE, 'utf8'));
export const save = (s) => { mkdirSync(DIR, { recursive: true }); writeFileSync(STATE, JSON.stringify(s, null, 1)); };
export const logEvent = (e) => appendFileSync(join(DIR, 'events.jsonl'), JSON.stringify({ t: Date.now(), ...e }) + '\n');

export async function wallet(name, st = load()) {
  const a = st.agents[name]; if (!a) throw new Error('unknown agent ' + name + '. known: ' + Object.keys(st.agents).join(', '));
  const auth = SoftAuthenticator.fromJSON(a.auth);
  const { client, mkBundler } = clients({ rpc: st.rpc, bundler: st.bundler, paymaster: st.paymaster });
  const account = await openWallet({ client, credential: a.credential, getFn: auth.getFn, rpId: 'localhost' });
  return { name, client, account, auth, bc: mkBundler(account), address: await account.getAddress(), st };
}
export async function createAgent(name, st) {
  const auth = new SoftAuthenticator({ rpId: 'localhost', origin: 'http://localhost' });
  const credential = await newCredential({ name, createFn: auth.createFn, rpId: 'localhost' });
  const { client } = clients({ rpc: st.rpc, bundler: st.bundler, paymaster: st.paymaster });
  const account = await openWallet({ client, credential, getFn: auth.getFn, rpId: 'localhost' });
  st.agents[name] = { credential: { id: credential.id, publicKey: credential.publicKey }, auth: auth.toJSON(), address: await account.getAddress() };
  return st.agents[name].address;
}
export const resolve = (st, who) => { if (isAddress(who)) return getAddress(who); const a = st.agents[who]; if (a) return a.address; throw new Error('unknown person ' + who); };
export const nameOf = (st, addr) => Object.entries(st.agents).find(([, a]) => a.address.toLowerCase() === addr.toLowerCase())?.[0] || addr.slice(0, 8);

export const P = (client, fn, args = []) => client.readContract({ address: ADDR.pool, abi: ABI.pool, functionName: fn, args });
export async function view(w) {
  const { client, address } = w;
  const [bal, limit, free, stake, ids, rate, cash, reserved, assets, lent, defaults, completed, dues, shares, lendBal] = await Promise.all([
    client.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [address] }),
    P(client, 'getBorrowLimit', [address]), P(client, 'getFreeCredit', [address]), P(client, 'stakeOf', [address]), P(client, 'getBorrowerLoanIds', [address]), P(client, 'getLoanRate'),
    P(client, 'lenderCash'), P(client, 'reservedLiquidity'), P(client, 'totalAssets'), P(client, 'totalLentOut'), P(client, 'defaultedLoans', [address]), P(client, 'completedLoans', [address]), P(client, 'duesPaid', [address]), P(client, 'sharesOf', [address]), P(client, 'lenderBalance', [address]),
  ]);
  const now = Number((await client.getBlock()).timestamp);
  const loans = [];
  for (const id of ids) { const t = await P(client, 'getLoanTerms', [id]); const st = Number(t[0]); if (st === 1 || st === 2) { const owed = await P(client, 'getCurrentOutstandingAmount', [id]); const l = await P(client, 'getLoan', [id]); loans.push({ id: Number(id), state: st === 1 ? 'requested' : 'active', principal: usd(l[0]), owedNow: Math.ceil(usd(owed) * 100) / 100, owedExact: usd(owed), dueInDays: Math.round((Number(t[4]) - now) / 86400 * 10) / 10 }); } }
  const backings = await P(client, 'getBackings', [address]); const backedAll = await P(client, 'getBackedBorrowers');
  const youBack = []; for (const b of backedAll) { const bk = await client.readContract({ address: ADDR.pool, abi: ABI.pool, functionName: 'getBacking', args: [address, b] }); if (bk[0] + bk[1] > 0n) youBack.push({ borrower: b, amount: usd(bk[0] + bk[1]) }); }
  return { wallet: address, backedBy: backings.map((x) => ({ backer: x.backer, amount: usd(x.secured + x.unsecured) })), youBack, usdc: usd(bal), borrowLimit: usd(limit[0]), canBorrowNow: usd(limit[1]), freeCredit: usd(free[0]), freeStake: usd(free[1]), totalStake: usd(stake), openLoans: loans, loansRepaid: Number(completed), loansDefaulted: Number(defaults), duesPaid: usd(dues), lenderBalance: usd(lendBal), pool: { aprPercent: Number(rate) / 100, totalAssets: usd(assets), freeCash: usd(cash - reserved), lentOut: usd(lent) } };
}
export async function act(w, label, calls, { preflightFn, preflightArgs, retry } = {}) {
  if (preflightFn) { try { await w.client.simulateContract({ address: ADDR.pool, abi: ABI.pool, functionName: preflightFn, args: preflightArgs, account: w.address }); } catch (e) { let n = null; try { e.walk?.((x) => { if (x?.data?.errorName) n = x.data.errorName; }); } catch {} const out = { ok: false, error: n || 'Unknown', message: friendly({ reason: n || '' }) }; logEvent({ who: w.name, label, ...out }); return out; } }
  try {
    const r = await runOp({ bundlerClient: w.bc, account: w.account, calls });
    const out = r.success ? { ok: true, tx: r.txHash } : { ok: false, error: r.reason, message: friendly({ reason: r.reason }) };
    logEvent({ who: w.name, label, ...out }); return out;
  } catch (e) { const out = { ok: false, error: String(e.shortMessage || e.message).slice(0, 160), message: friendly(e) }; logEvent({ who: w.name, label, ...out }); return out; }
}
export { poolCall, usdcCall, toUnits, usd, maxUint256, ADDR, ABI };
