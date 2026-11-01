// A minimal ERC-4337 (EntryPoint v0.6) bundler for tests and for self-hosting a tester relay.
// Methods: eth_chainId, eth_supportedEntryPoints, eth_estimateUserOperationGas, eth_sendUserOperation,
// eth_getUserOperationReceipt, eth_getUserOperationByHash. It submits handleOps from its own EOA.
import http from 'node:http';
import { createPublicClient, createWalletClient, http as vhttp, hexToBigInt, toHex, decodeEventLog, parseEther } from 'viem';
import { entryPoint06Abi, entryPoint06Address } from 'viem/account-abstraction';
import { privateKeyToAccount } from 'viem/accounts';
import { baseSepolia } from 'viem/chains';

const fromRpc = (o) => ({
  sender: o.sender, nonce: hexToBigInt(o.nonce), initCode: o.initCode || '0x', callData: o.callData,
  callGasLimit: hexToBigInt(o.callGasLimit), verificationGasLimit: hexToBigInt(o.verificationGasLimit), preVerificationGas: hexToBigInt(o.preVerificationGas),
  maxFeePerGas: hexToBigInt(o.maxFeePerGas), maxPriorityFeePerGas: hexToBigInt(o.maxPriorityFeePerGas),
  paymasterAndData: o.paymasterAndData || '0x', signature: o.signature,
});

export function startBundler({ rpc, port = 4337, key, verificationGas = 2_500_000n, callGas = 1_500_000n, preVerificationGas = 120_000n, log = () => {} }) {
  const account = privateKeyToAccount(key);
  const pc = createPublicClient({ chain: baseSepolia, transport: vhttp(rpc) });
  const wc = createWalletClient({ account, chain: baseSepolia, transport: vhttp(rpc) });
  const txOf = new Map(); // userOpHash -> tx hash
  const opOf = new Map();
  const EP = entryPoint06Address;

  async function handle(method, params) {
    switch (method) {
      case 'eth_chainId': return toHex(baseSepolia.id);
      case 'eth_supportedEntryPoints': return [EP];
      case 'eth_estimateUserOperationGas':
        return { preVerificationGas: toHex(preVerificationGas), verificationGasLimit: toHex(verificationGas), callGasLimit: toHex(callGas) };
      case 'eth_sendUserOperation': {
        const op = fromRpc(params[0]);
        const hash = await pc.readContract({ address: EP, abi: entryPoint06Abi, functionName: 'getUserOpHash', args: [op] });
        // Pre-flight: simulate the bundle so a doomed operation is refused with a reason instead of wasting gas.
        try { await pc.simulateContract({ address: EP, abi: entryPoint06Abi, functionName: 'handleOps', args: [[op], account.address], account }); }
        catch (e) { const m = (e.shortMessage || e.message || '').slice(0, 300); log('reject', m); throw Object.assign(new Error(m), { code: -32500 }); }
        const tx = await wc.writeContract({ address: EP, abi: entryPoint06Abi, functionName: 'handleOps', args: [[op], account.address] });
        txOf.set(hash, tx); opOf.set(hash, params[0]); log('sent', hash, tx);
        return hash;
      }
      case 'eth_getUserOperationReceipt': {
        const hash = params[0]; const tx = txOf.get(hash); if (!tx) return null;
        const raw = await pc.request({ method: 'eth_getTransactionReceipt', params: [tx] }); if (!raw) return null;
        let ev = null;
        for (const l of raw.logs) { if (l.address.toLowerCase() !== EP.toLowerCase()) continue; try { const d = decodeEventLog({ abi: entryPoint06Abi, data: l.data, topics: l.topics }); if (d.eventName === 'UserOperationEvent' && d.args.userOpHash === hash) ev = d.args; } catch {} }
        if (!ev) return null;
        return { userOpHash: hash, entryPoint: EP, sender: ev.sender, nonce: toHex(ev.nonce), paymaster: ev.paymaster, actualGasCost: toHex(ev.actualGasCost), actualGasUsed: toHex(ev.actualGasUsed), success: ev.success, reason: '', logs: raw.logs, receipt: raw };
      }
      case 'eth_getUserOperationByHash': {
        const hash = params[0]; const op = opOf.get(hash); if (!op) return null; const tx = txOf.get(hash);
        const raw = await pc.request({ method: 'eth_getTransactionByHash', params: [tx] });
        return { userOperation: op, entryPoint: EP, blockNumber: raw?.blockNumber ?? null, blockHash: raw?.blockHash ?? null, transactionHash: tx };
      }
      default: throw Object.assign(new Error('method not found: ' + method), { code: -32601 });
    }
  }
  const server = http.createServer((req, res) => {
    res.setHeader('access-control-allow-origin', '*'); res.setHeader('access-control-allow-headers', 'content-type');
    if (req.method === 'OPTIONS') { res.writeHead(204); return res.end(); }
    let body = ''; req.on('data', (c) => (body += c)); req.on('end', async () => {
      let id = null;
      try { const j = JSON.parse(body); id = j.id; const result = await handle(j.method, j.params || []); res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify({ jsonrpc: '2.0', id, result })); }
      catch (e) { res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify({ jsonrpc: '2.0', id, error: { code: e.code || -32000, message: e.message } })); }
    });
  });
  return new Promise((resolve) => server.listen(port, '127.0.0.1', () => resolve({ url: `http://127.0.0.1:${port}`, address: account.address, close: () => server.close() })));
}
