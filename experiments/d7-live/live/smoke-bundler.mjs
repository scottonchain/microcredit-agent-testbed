// Keyless smoke test of the public bundler path used by the phone app: a fresh in-memory passkey wallet sends one
// sponsored user operation (pool.setDisplayName) through BUNDLER (default: the app's public bundler) with the live
// sponsor paymaster from app/config.json. No keys, no funds, nothing persisted. Testnet only.
// Usage: node live/smoke-bundler.mjs            (BUNDLER=... to override; RPC_URL=... to override the chain endpoint)
import { readFileSync } from 'node:fs';
import { createPublicClient, http } from 'viem'; import { baseSepolia } from 'viem/chains';
import { SoftAuthenticator } from '../lib/softpasskey.mjs';
import { clients, openWallet, newCredential, runOp } from '../lib/wallet.mjs';
import { ADDR, ABI } from '../lib/chain.mjs';
import { encodeFunctionData } from 'viem';
const cfg = JSON.parse(readFileSync(new URL('../app/config.json', import.meta.url), 'utf8'));
const RPC = process.env.RPC_URL || cfg.rpcs[0], BUNDLER = process.env.BUNDLER || cfg.bundler;
console.log('rpc', RPC, '\nbundler', BUNDLER, '\npaymaster', cfg.paymaster);
const t0 = Date.now();
try {
  const r0 = await fetch(BUNDLER, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'eth_supportedEntryPoints', params: [] }) });
  console.log('eth_supportedEntryPoints HTTP', r0.status, (await r0.text()).slice(0, 200));
} catch (e) { console.log('bundler unreachable:', e.message); process.exit(2); }
const { client, mkBundler } = clients({ rpc: RPC, bundler: BUNDLER, paymaster: cfg.paymaster });
const auth = new SoftAuthenticator({ rpId: 'localhost', origin: 'http://localhost' });
const credential = await newCredential({ name: 'smoke', createFn: auth.createFn, rpId: 'localhost' });
const account = await openWallet({ client, credential, getFn: auth.getFn, rpId: 'localhost' });
const address = await account.getAddress(); console.log('fresh wallet', address);
const bc = mkBundler(account);
try {
  const r = await runOp({ bundlerClient: bc, account, calls: [{ to: ADDR.pool, data: encodeFunctionData({ abi: ABI.pool, functionName: 'setDisplayName', args: ['smoke ' + new Date().toISOString().slice(11, 19)] }) }] });
  console.log('user operation mined:', r.success ? 'SUCCESS' : 'inner revert ' + r.reason, '\ntx', r.txHash, '\ngas cost wei', String(r.actualGasCost), '\nelapsed ms', Date.now() - t0);
  process.exit(r.success ? 0 : 1);
} catch (e) { console.log('FAILED:', (e.details || e.shortMessage || e.message || String(e)).slice(0, 600)); console.log('elapsed ms', Date.now() - t0); process.exit(1); }
