// Reproduce one historical claim, not a marketplace demand scan. No signer or ABI assumptions.
import { readFileSync, writeFileSync } from 'node:fs';
import { JsonRpcProvider, Interface, Contract, zeroPadValue, toBeHex } from 'ethers';
const hash = '0xc767da642b7647c7b3b8324f404cf5270532a43bcc084c355077ef1c8ab0d880';
const target = '0x238E541BfefD82238730D00a2208E5497F1832E0';
const token = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';
const erc20 = new Interface(['event Transfer(address indexed from,address indexed to,uint256 value)']);
// Data-only subset pinned to Virtual-Protocol/acp-node-v2@392dcc6eb17a6884c214c21aff31afa1b99f45ae.
const abi = JSON.parse(readFileSync(new URL('./acp-trace-abi.json', import.meta.url), 'utf8'));
const acp = new Interface(abi);
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
    let job, creation;
    try {
      const j = await new Contract(target, abi, p).getJob(13868, { blockTag: r.blockNumber });
      job = { client: j.client, status: j.status.toString(), provider: j.provider, evaluator: j.evaluator, budgetRaw: j.budget.toString(), description: j.description };
    } catch { job = { error: 'Pinned SDK getJob layout not decoded at historical block; no buyer inferred' }; }
    try {
      const logs = await p.getLogs({ address: target, fromBlock: r.blockNumber - 2000, toBlock: r.blockNumber,
        topics: [acp.getEvent('JobCreated').topicHash, zeroPadValue(toBeHex(13868), 32)] });
      creation = logs.map(l => { const e = acp.parseLog(l); return { block: l.blockNumber, hash: l.transactionHash, client: e.args.client, provider: e.args.provider, evaluator: e.args.evaluator }; });
    } catch { creation = { error: 'Bounded creation-log query failed; no absence inferred' }; }
    results.push({ rpc, chainId: 8453, checkedBlock, job, creation, receipt: { hash: r.hash, block: r.blockNumber, status: r.status,
      from: r.from, to: r.to, selector: tx?.data?.slice(0, 10), usdcTransfers: transfers,
      targetCodeAtReceipt: await p.getCode(target, r.blockNumber),
      targetLogs: r.logs.filter(x => x.address.toLowerCase() === target.toLowerCase()).map(x => ({ topics: x.topics, data: x.data, index: x.index })) } });
  } catch { results.push({ rpc, error: 'Read failed; no absence or outage inferred' }); }
  finally { p.destroy(); }
}
const output = { checkedAt: new Date().toISOString(), hash, target, readOnly: true, keyLoaded: false, results,
  limitations: ['SDK subset is version-pinned; failed historical getJob decoding does not identify a buyer.', 'Creation scan covers only the 2,000 blocks before settlement.', 'A bundle sender is not the original service buyer.', 'A receipt does not establish beneficial ownership, useful output, costs or a financing gap.', 'Null receipts are source-reproduction results, not proof of no market demand.'] };
writeFileSync('acp-trace-readonly.json', JSON.stringify(output, null, 2) + '\n');
console.log('ACP_TRACE_READONLY=' + JSON.stringify(output));
if (results.every(x => x.error)) process.exitCode = 1;
