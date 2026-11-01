// Passkey smart wallet (Coinbase Smart Wallet, EntryPoint v0.6) + sponsor paymaster, shared by scripts and the web app.
import { createPublicClient, http, encodeFunctionData, maxUint256, parseEventLogs, decodeErrorResult } from 'viem';
import { createBundlerClient, toCoinbaseSmartAccount, toWebAuthnAccount, createWebAuthnCredential, entryPoint06Address, entryPoint06Abi } from 'viem/account-abstraction';
import { baseSepolia } from 'viem/chains';
import { ADDR, ABI } from './chain.mjs';

export const CB_FACTORY = '0x0BA5ED0c6AA8c49038F819E587E2633c4A9F428a';

export function clients({ rpc, bundler, paymaster }) {
  const client = createPublicClient({ chain: baseSepolia, transport: http(rpc) });
  const mkBundler = (account) => createBundlerClient({
    account, client, transport: http(bundler),
    paymaster: paymaster ? {
      getPaymasterStubData: async () => ({ paymasterAndData: paymaster }),
      getPaymasterData: async () => ({ paymasterAndData: paymaster }),
    } : undefined,
    userOperation: { estimateFeesPerGas: async () => { const b = await client.getBlock(); const base = b.baseFeePerGas ?? 1000000n; return { maxFeePerGas: base * 2n + 1000000n, maxPriorityFeePerGas: 1000000n }; } },
  });
  return { client, mkBundler };
}

// credential: { id, publicKey } from createWebAuthnCredential; getFn/rpId override for headless use.
export async function openWallet({ client, credential, getFn, rpId }) {
  const owner = toWebAuthnAccount({ credential, getFn, rpId });
  const account = await toCoinbaseSmartAccount({ client, owners: [owner] });
  return account;
}
export const newCredential = ({ name, createFn, rpId }) => createWebAuthnCredential({ name, createFn, rp: rpId ? { id: rpId, name: 'Omnequa test' } : undefined });

export const call = (to, abi, fn, args) => ({ to, data: encodeFunctionData({ abi, functionName: fn, args }) });
export const poolCall = (fn, args) => call(ADDR.pool, ABI.pool, fn, args);
export const usdcCall = (fn, args) => call(ADDR.usdc, ABI.erc20, fn, args);

// Decode revert data from a failed inner call into a short error name (pool custom errors, or a revert string).
export function decodeRevert(data) {
  if (!data || data === '0x') return 'Reverted';
  for (const abi of [ABI.pool]) { try { const d = decodeErrorResult({ abi, data }); if (d.errorName === 'Error') return String(d.args[0]); return d.errorName; } catch {} }
  try { return decodeErrorResult({ abi: [{ type: 'error', name: 'Error', inputs: [{ type: 'string', name: 'message' }] }], data }).args[0]; } catch {}
  return 'Reverted (' + data.slice(0, 10) + ')';
}

// Run calls as one user operation. Returns { success, reason, ... }; success=false means the operation was mined but an inner call reverted.
export async function runOp({ bundlerClient, account, calls }) {
  const hash = await bundlerClient.sendUserOperation({ account, calls });
  const r = await bundlerClient.waitForUserOperationReceipt({ hash, timeout: 120_000 });
  let events = [], reason = null;
  try { events = parseEventLogs({ abi: ABI.pool, logs: r.logs.filter((l) => l.address.toLowerCase() === ADDR.pool.toLowerCase()) }); } catch {}
  if (!r.success) {
    try { const ev = parseEventLogs({ abi: entryPoint06Abi, logs: r.logs.filter((l) => l.address.toLowerCase() === entryPoint06Address.toLowerCase()), eventName: 'UserOperationRevertReason' })[0]; reason = decodeRevert(ev?.args?.revertReason); } catch {}
  }
  return { hash, success: r.success, reason, actualGasCost: r.actualGasCost, txHash: r.receipt.transactionHash, events };
}
