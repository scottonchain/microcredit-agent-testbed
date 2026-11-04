// Reproduce one historical claim, not a marketplace demand scan. No signer or ABI assumptions.
import { writeFileSync } from 'node:fs';
import { JsonRpcProvider, Interface } from 'ethers';
const hash = '0xc767da642b7647c7b3b8324f404cf5270532a43bcc084c355077ef1c8ab0d880';
const target = '0x238E541BfefD82238730D00a2208E5497F1832E0';
const token = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const erc20 = new Interface(['event Transfer(address indexed from,address indexed to,uint256 value)']);
const results = [];
for (const rpc of ['https://mainnet.base.org', 'https://base-rpc.publicnode.com']) {
  const p = new JsonRpcProvider(rpc, undefined, { batchMaxCount: 1, cacheTimeout: 0 });
  try {
    if (Number((await p.getNetwork()).chainId) !== 8453) throw Error('Wrong chain');
    const checkedBlock = await p.getBlockNumber();
    const r = await p.getTransactionReceipt(hash);
    if (!r) { results.push({ rpc, chainId: 8453, checkedBlock, receipt: null }); continue; }
    const tx = await p.getTransaction(hash);
    const transfers = r.logs.filter(x => x.address.toLowerCase() === token.toLowerCase()).flatMap(x => {
      try { const e = erc20.parseLog(x); return [{ from: e.args.from, to: e.args.to, raw: e.args.value.toString() }]; }
      catch { return []; }
    });
    results.push({ rpc, chainId: 8453, checkedBlock, receipt: { hash: r.hash, block: r.blockNumber, status: r.status,
      from: r.from, to: r.to, input: tx?.data, usdcTransfers: transfers,
      targetCodeAtReceipt: await p.getCode(target, r.blockNumber),
      targetLogs: r.logs.filter(x => x.address.toLowerCase() === target.toLowerCase()).map(x => ({ topics: x.topics, data: x.data, index: x.index })) } });
  } catch { results.push({ rpc, error: 'Read failed; no absence or outage inferred' }); }
  finally { p.destroy(); }
}
const output = { checkedAt: new Date().toISOString(), hash, target, readOnly: true, keyLoaded: false, results,
  limitations: ['No unmatched SDK ABI is used to label raw ACP logs.', 'A bundle sender is not the original service buyer.', 'A receipt does not establish beneficial ownership, useful output, costs or a financing gap.', 'Null receipts are source-reproduction results, not proof of no market demand.'] };
writeFileSync('acp-trace-readonly.json', JSON.stringify(output, null, 2) + '\n');
console.log('ACP_TRACE_READONLY=' + JSON.stringify(output));
if (results.every(x => x.error)) process.exitCode = 1;
