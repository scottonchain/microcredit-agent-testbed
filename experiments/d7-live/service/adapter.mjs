// Chain adapter for the officer service worker (worker.mjs). Clients are injected, so tests use a fake public client and a
// throwaway key; the live service would pass viem's real public client and the officer account. Not wired into the daemon.
// Interface: { pending(), prepare(applicant, token), receipt(txHash), applied(applicant) }.
import { encodeFunctionData, keccak256 } from 'viem';

const same = (a, b) => String(a).toLowerCase() === String(b).toLowerCase();

export function createChainAdapter({ publicClient, account, desk, deskAbi, chainId, decide }) {
  const pendingList = () => publicClient.readContract({ address: desk, abi: deskAbi, functionName: 'pending' });
  return {
    pending: () => pendingList(),
    // "Applied" means the applicant is no longer waiting. An RPC error is thrown, never turned into false:
    // the caller (reconcile) maps a throw to unknown, which holds instead of replaying.
    async applied(applicant) { return !(await pendingList()).some((a) => same(a, applicant)); },
    // Decide (the model call or rules), then build and SIGN the reply. Returns the hash now and a broadcast closure.
    // The raw signed bytes stay in this closure's memory: they are never returned, logged or written anywhere.
    // A crash before the caller journals the hash leaves no transaction in existence, so a restart may decide again.
    async prepare(applicant, token) {
      const { text, backing } = await decide(applicant, token);
      const data = encodeFunctionData({ abi: deskAbi, functionName: 'reply', args: [applicant, text, backing] });
      const nonce = await publicClient.getTransactionCount({ address: account.address, blockTag: 'pending' });
      const gas = await publicClient.estimateGas({ account: account.address, to: desk, data });
      const fees = await publicClient.estimateFeesPerGas();
      const serialized = await account.signTransaction({ type: 'eip1559', chainId, to: desk, data, nonce, gas, maxFeePerGas: fees.maxFeePerGas, maxPriorityFeePerGas: fees.maxPriorityFeePerGas, value: 0n });
      return { txHash: keccak256(serialized), nonce, broadcast: async () => { await publicClient.sendRawTransaction({ serializedTransaction: serialized }); } };
    },
    async receipt(txHash) {
      try { const r = await publicClient.getTransactionReceipt({ hash: txHash }); return r ? { status: r.status } : null; }
      catch (e) { if (e && (e.name === 'TransactionReceiptNotFoundError' || /not found/i.test(String(e.shortMessage || e.message)))) return null; throw e; }
    },
  };
}
