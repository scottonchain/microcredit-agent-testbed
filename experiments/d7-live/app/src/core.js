import { createPublicClient, http, fallback, encodeFunctionData, maxUint256, parseEventLogs, decodeErrorResult, isAddress, getAddress, formatUnits, parseUnits } from 'viem';
import { createBundlerClient, toCoinbaseSmartAccount, toWebAuthnAccount, createWebAuthnCredential, entryPoint06Address, entryPoint06Abi } from 'viem/account-abstraction';
import { baseSepolia } from 'viem/chains';
import poolAbi from '../../abi/DecentralizedMicrocredit.json';

export const erc20Abi = [
  { type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ name: 'a', type: 'address' }], outputs: [{ type: 'uint256' }] },
  { type: 'function', name: 'allowance', stateMutability: 'view', inputs: [{ name: 'o', type: 'address' }, { name: 's', type: 'address' }], outputs: [{ type: 'uint256' }] },
  { type: 'function', name: 'approve', stateMutability: 'nonpayable', inputs: [{ name: 's', type: 'address' }, { name: 'v', type: 'uint256' }], outputs: [{ type: 'bool' }] },
  { type: 'function', name: 'transfer', stateMutability: 'nonpayable', inputs: [{ name: 'to', type: 'address' }, { name: 'v', type: 'uint256' }], outputs: [{ type: 'bool' }] },
];
export const ST = { None: 0, Requested: 1, Active: 2, Repaid: 3, Defaulted: 4, Cancelled: 5 };
export const CENT = 10000n;
export const usd = (x) => Number(formatUnits(x, 6));
export const money = (x) => '$' + usd(x).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const parseUsd = (s) => { const t = String(s).trim().replace(/^\$/, ''); if (!/^\d+(\.\d{1,6})?$/.test(t)) return null; return parseUnits(t, 6); };
export const ceilCent = (x) => ((x + CENT - 1n) / CENT) * CENT;

export let cfg;
export async function loadConfig() { cfg = await (await fetch('config.json', { cache: 'no-store' })).json(); return cfg; }
export function makeClient() {
  const urls = cfg.rpcs; const transport = urls.length > 1 ? fallback(urls.map((u) => http(u, { retryCount: 2 }))) : http(urls[0], { retryCount: 2 });
  return createPublicClient({ chain: baseSepolia, transport, batch: { multicall: true } });
}

const KEY = 'd7.cred';
export const loadCred = () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } };
export const saveCred = (c) => localStorage.setItem(KEY, JSON.stringify({ id: c.id, publicKey: c.publicKey }));
export const forget = () => localStorage.removeItem(KEY);
export const recoveryCode = (c) => btoa(JSON.stringify({ id: c.id, publicKey: c.publicKey }));
export const parseRecovery = (s) => { const o = JSON.parse(atob(s.trim())); if (!o.id || !o.publicKey) throw new Error('bad code'); return o; };

export async function createPasskey(label) { return createWebAuthnCredential({ name: label || 'Omnequa test wallet' }); }
export async function openAccount(client, cred) {
  const owner = toWebAuthnAccount({ credential: cred });
  return toCoinbaseSmartAccount({ client, owners: [owner] });
}
export function bundlerFor(client, account) {
  return createBundlerClient({
    account, client, transport: http(cfg.bundler),
    paymaster: cfg.paymaster ? { getPaymasterStubData: async () => ({ paymasterAndData: cfg.paymaster }), getPaymasterData: async () => ({ paymasterAndData: cfg.paymaster }) } : undefined,
    userOperation: { estimateFeesPerGas: async () => { const b = await client.getBlock(); const base = b.baseFeePerGas ?? 1000000n; return { maxFeePerGas: base * 2n + 1000000n, maxPriorityFeePerGas: 1000000n }; } },
  });
}
export const callOf = (to, abi, fn, args) => ({ to, data: encodeFunctionData({ abi, functionName: fn, args }) });
export const poolCall = (fn, args) => callOf(cfg.pool, poolAbi, fn, args);
export const usdcCall = (fn, args) => callOf(cfg.usdc, erc20Abi, fn, args);

export function decodeRevert(data) {
  if (!data || data === '0x') return 'Reverted';
  try { const d = decodeErrorResult({ abi: poolAbi, data }); return d.errorName === 'Error' ? String(d.args[0]) : d.errorName; } catch {}
  return 'Reverted ' + data.slice(0, 10);
}
export async function send(bundlerClient, account, calls, onStage) {
  onStage?.('sign');
  const hash = await bundlerClient.sendUserOperation({ account, calls });
  onStage?.('submit');
  const r = await bundlerClient.waitForUserOperationReceipt({ hash, timeout: 120000 });
  let reason = null, events = [];
  try { events = parseEventLogs({ abi: poolAbi, logs: r.logs.filter((l) => l.address.toLowerCase() === cfg.pool.toLowerCase()) }); } catch {}
  if (!r.success) { try { const ev = parseEventLogs({ abi: entryPoint06Abi, logs: r.logs.filter((l) => l.address.toLowerCase() === entryPoint06Address.toLowerCase()), eventName: 'UserOperationRevertReason' })[0]; reason = decodeRevert(ev?.args?.revertReason); } catch {} }
  return { hash, success: r.success, reason, txHash: r.receipt.transactionHash, events };
}

// Everything the home screen needs, in few round trips.
export async function snapshot(client, addr) {
  const P = (functionName, args = []) => client.readContract({ address: cfg.pool, abi: poolAbi, functionName, args });
  const [usdcBal, limit, free, stake, loanIds, rate, lenderCash, reserved, totalAssets, defaults] = await Promise.all([
    client.readContract({ address: cfg.usdc, abi: erc20Abi, functionName: 'balanceOf', args: [addr] }),
    P('getBorrowLimit', [addr]), P('getFreeCredit', [addr]), P('stakeOf', [addr]), P('getBorrowerLoanIds', [addr]), P('getLoanRate'),
    P('lenderCash'), P('reservedLiquidity'), P('totalAssets'), P('defaultedLoans', [addr]),
  ]);
  const loans = await Promise.all(loanIds.map(async (id) => {
    const [terms, loan, owed] = await Promise.all([P('getLoanTerms', [id]), P('getLoan', [id]), P('getCurrentOutstandingAmount', [id])]);
    return { id, status: Number(terms[0]), term: Number(terms[1]), dueAt: Number(terms[4]), disbursedAt: Number(terms[3]), principal: loan[0], owed, rateBps: loan[3] };
  }));
  const backings = await P('getBackings', [addr]); const backedAll = await P('getBackedBorrowers');
  const backedBy = backings.map((b) => ({ who: b.backer, amount: b.secured + b.unsecured })).filter((b) => b.amount > 0n);
  const youBack = (await Promise.all(backedAll.map(async (b) => { const bk = await client.readContract({ address: cfg.pool, abi: poolAbi, functionName: 'getBacking', args: [addr, b] }); return { who: b, amount: bk[0] + bk[1] }; }))).filter((b) => b.amount > 0n);
  const code = await client.getCode({ address: addr });
  return { backedBy, youBack, usdcBal, limit: limit[0], available: limit[1], freeCredit: free[0], stake, loans, rate, lenderCash, reserved, totalAssets, defaulted: Number(defaults), deployed: !!code && code !== '0x' };
}
export const openLoans = (s) => s.loans.filter((l) => l.status === ST.Active || l.status === ST.Requested);

// Preflight: ask the pool, as the wallet, whether it would accept this request. Returns an error name or null.
export async function preflight(client, addr, fn, args) {
  try { await client.simulateContract({ address: cfg.pool, abi: poolAbi, functionName: fn, args, account: addr }); return null; }
  catch (e) { let n = null; try { e.walk?.((x) => { if (x?.data?.errorName) n = x.data.errorName; }); } catch {} return n || 'Unknown'; }
}
export const nextLoanId = async (client) => { const ids = await client.readContract({ address: cfg.pool, abi: poolAbi, functionName: 'getAllLoanIds' }); return (ids.length ? ids[ids.length - 1] : 0n) + 1n; };
export { isAddress, getAddress, maxUint256, poolAbi };
// Headroom over a payoff quote: one cent at least, plus interest for the signing delay at the 100% APR ceiling.
export const headroom = (principal) => { const a = (principal * 10000n * BigInt(cfg.headroomSeconds)) / (10000n * 31536000n); const b = ceilCent(a + 1n); return b > CENT ? b : CENT; };
