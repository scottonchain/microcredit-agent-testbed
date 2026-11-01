// Live (or fork) runner helpers. No cheat RPCs here: everything is a normal transaction. Testnet only.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { createPublicClient, createWalletClient, http, parseEther, formatEther, encodeFunctionData } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { baseSepolia } from 'viem/chains';
import { ADDR, ABI, usd, toUnits } from '../lib/chain.mjs';
import { deployPaymaster } from '../deploy-paymaster.mjs';
import { startBundler } from '../bundler.mjs';
import { SoftAuthenticator } from '../lib/softpasskey.mjs';
import { clients, openWallet, newCredential, poolCall, usdcCall, runOp } from '../lib/wallet.mjs';
import { friendly } from '../app/src/errors.js';

export const RPC = process.env.RPC_URL || 'https://sepolia.base.org';
export const KEYS = process.env.KEYS_DIR || new URL('../../../../keys/', import.meta.url).pathname; // scratchpad/keys, outside the repo
export const key = (n) => readFileSync(KEYS + n + '.key', 'utf8').trim();
export const pc = createPublicClient({ chain: baseSepolia, transport: http(RPC) });
export const eoa = (n) => { const account = privateKeyToAccount(key(n)); return { account, address: account.address, wc: createWalletClient({ account, chain: baseSepolia, transport: http(RPC) }) }; };
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const usdcOf = (a) => pc.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [a] });
export const P = (fn, args = []) => pc.readContract({ address: ADDR.pool, abi: ABI.pool, functionName: fn, args });
export async function sendTx(who, req) { const hash = await who.wc.writeContract(req); const rc = await pc.waitForTransactionReceipt({ hash, timeout: 120000 }); if (rc.status !== 'success') throw new Error('tx failed ' + hash); return hash; }
export async function transferUsdc(who, to, amt) { return sendTx(who, { address: ADDR.usdc, abi: ABI.erc20, functionName: 'transfer', args: [to, amt] }); }
export async function sendEth(who, to, wei) { const hash = await who.wc.sendTransaction({ to, value: wei }); await pc.waitForTransactionReceipt({ hash }); return hash; }

// A passkey wallet driven headlessly: soft authenticator persisted to disk under KEYS_DIR.
export async function smartWallet(name, cfg) {
  const file = KEYS + 'wallet-' + name + '.json'; const { client, mkBundler } = clients({ rpc: RPC, bundler: cfg.bundler, paymaster: cfg.paymaster });
  let auth, credential;
  if (existsSync(file)) { const o = JSON.parse(readFileSync(file, 'utf8')); auth = SoftAuthenticator.fromJSON(o.auth); credential = o.credential; }
  else { auth = new SoftAuthenticator({ rpId: 'localhost', origin: 'http://localhost' }); const c = await newCredential({ name, createFn: auth.createFn, rpId: 'localhost' }); credential = { id: c.id, publicKey: c.publicKey }; writeFileSync(file, JSON.stringify({ credential, auth: auth.toJSON() }), { mode: 0o600 }); }
  const account = await openWallet({ client, credential, getFn: auth.getFn, rpId: 'localhost' });
  const address = await account.getAddress(); const bc = mkBundler(account);
  const save = () => writeFileSync(file, JSON.stringify({ credential, auth: auth.toJSON() }), { mode: 0o600 });
  return { name, address, account, bc, client, auth, save,
    async op(label, calls, { expect = 'ok', expectError } = {}) {
      const t = Date.now(); let r;
      try { r = await runOp({ bundlerClient: bc, account, calls }); } catch (e) { r = { success: false, reason: String(e.shortMessage || e.message).slice(0, 160), thrown: true }; }
      save(); return { label, ok: r.success, reason: r.reason, tx: r.txHash, ms: Date.now() - t, gasCost: r.actualGasCost }; },
    async preflight(fn, args) { try { await pc.simulateContract({ address: ADDR.pool, abi: ABI.pool, functionName: fn, args, account: address }); return null; } catch (e) { let n = null; try { e.walk?.((x) => { if (x?.data?.errorName) n = x.data.errorName; }); } catch {} return n || 'Unknown'; } },
  };
}
export { ADDR, ABI, usd, toUnits, parseEther, formatEther, poolCall, usdcCall, friendly, deployPaymaster, startBundler };
