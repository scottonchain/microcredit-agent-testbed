// A small in-memory chain for the B2 integration tests. LOCAL ONLY: generated throwaway keys, no network, no real provider.
// It holds real signed transactions (decoded by the real verifyPrepared), blocks with parent hashes, a mempool, receipts with
// fee components, and an `rpc` object implementing exactly the port the chain gate reads. Everything a "restart" needs is in the
// shared state: a test builds a NEW `rpc()` and a NEW gate over the same state, which is what a fresh process would see.

import { generatePrivateKey, privateKeyToAccount } from 'viem/accounts';
import { keccak256, toHex, encodeFunctionData, parseAbi, encodeAbiParameters, encodeEventTopics, pad } from 'viem';
import { verifyPrepared } from './verify_prepared.mjs';
import { L1_ORACLE } from './chain_state.mjs';

const abi = parseAbi(['function transfer(address,uint256) returns (bool)', 'function balanceOf(address) view returns (uint256)', 'event Transfer(address indexed from, address indexed to, uint256 value)']);
export const CHAIN_ID = 84532;
export const TOKEN = '0x' + 'dd'.repeat(20);
export const TOKEN_CODE = '0x6080aa';
export const FUND = '0x' + 'f1'.repeat(20);
const lc = x => String(x).toLowerCase();
const word = n => toHex(n, { size: 32 });
const bh = (n, salt) => keccak256(toHex(`block-${n}-${salt}`));

export const GAS = { token: 40_000n, native: 21_000n }; // gas actually used
export const GAS_LIMIT = { token: 60_000n, native: 21_000n };
export const FEE_CAP = 1000n; // maxFeePerGas the wallets sign
export const PRICE = 900n; // effectiveGasPrice
export const L1_FEE = 30_000n; // what the receipt reports
export const L1_QUOTE = 30_000n; // what the oracle quotes

export function makeSim({ wallets = ['w1'], tokens = 8n, native = 10n ** 16n } = {}) {
  const accounts = Object.fromEntries(wallets.map(id => [id, privateKeyToAccount(generatePrivateKey())]));
  const st = {
    chainId: CHAIN_ID, providerId: 'provider-a', salt: 0,
    blocks: [], byHash: new Map(), // every block hash ever seen, so a historical read of a reorged-out block still answers (an archive node)
    native: {}, tokens: {}, nonces: {}, pool: new Map(), mined: new Map(),
    code: { [lc(TOKEN)]: TOKEN_CODE }, l1Quote: L1_QUOTE, l1Fail: false, operatorFee: 0n, broadcasts: [], signs: 0, offline: false, receiptTweak: null, readFail: new Set(), autoMine: 0,
  };
  const addr = id => lc(accounts[id].address);
  for (const id of wallets) { st.native[addr(id)] = native; st.tokens[addr(id)] = tokens; }
  st.native[lc(FUND)] = 0n; st.tokens[lc(FUND)] = 0n;
  const push = (n, parent, ts) => { const b = { number: n, hash: bh(n, st.salt), parentHash: parent, timestamp: ts }; st.blocks.push(b); st.byHash.set(b.hash, b); return b; };
  const head = () => st.blocks[st.blocks.length - 1];
  push(99, bh(98, 0), 1_799_999_998); push(100, head().hash, 1_800_000_000);
  const pendingCount = a => [...st.pool.values()].filter(t => t.from === a).length;
  const known = at => { if (at === undefined || at === null) return; if (!st.byHash.has(at)) throw new Error('missing trie node (non-archive provider)'); };

  function mineBlock() {
    const parent = head(); const b = push(parent.number + 1, parent.hash, parent.timestamp + 2); b.txs = []; b.pre = { native: { ...st.native }, tokens: { ...st.tokens }, nonces: { ...st.nonces } };
    for (const [hash, tx] of [...st.pool.entries()]) {
      if (tx.from && tx.nonce !== (st.nonces[tx.from] ?? 0)) continue; // not yet valid
      const used = tx.kind === 'erc20' ? GAS.token : GAS.native; const fee = used * PRICE + L1_FEE + (st.operatorFee ?? 0n);
      if (st.native[tx.from] < fee + (tx.kind === 'native' ? tx.amount : 0n)) { st.pool.delete(hash); continue; }
      if (tx.kind === 'erc20') { if (st.tokens[tx.from] < tx.amount) { st.pool.delete(hash); continue; } st.tokens[tx.from] -= tx.amount; st.tokens[tx.recipient] = (st.tokens[tx.recipient] ?? 0n) + tx.amount; }
      else { st.native[tx.from] -= tx.amount; st.native[tx.recipient] = (st.native[tx.recipient] ?? 0n) + tx.amount; }
      st.native[tx.from] -= fee; st.nonces[tx.from] = tx.nonce + 1;
      const logs = tx.kind === 'erc20' ? [{ address: TOKEN, topics: encodeEventTopics({ abi, eventName: 'Transfer', args: { from: tx.from, to: tx.recipient } }), data: encodeAbiParameters([{ type: 'uint256' }], [tx.amount]) }] : [];
      const receipt = { status: 1, transactionHash: hash, from: tx.from, to: tx.kind === 'erc20' ? lc(TOKEN) : tx.recipient, blockHash: b.hash, blockNumber: b.number, gasUsed: used, effectiveGasPrice: PRICE, l1Fee: L1_FEE, ...(st.operatorFee === undefined ? {} : { operatorFee: st.operatorFee }), logs };
      st.mined.set(hash, { tx, receipt, block: b.number }); b.txs.push(hash); st.pool.delete(hash);
    }
    return b;
  }
  const mine = (n = 1) => { let b; for (let i = 0; i < n; i++) b = mineBlock(); return b; };
  // replace the last `depth` blocks with an alternative branch of the same length. Balances and nonces roll back to before the
  // first removed block; their transactions return to the pool (keepTxs) or are dropped
  const reorg = (depth, { keepTxs = true } = {}) => {
    st.salt += 1; const removed = st.blocks.splice(st.blocks.length - depth, depth);
    const first = removed[0];
    if (first && first.pre) { st.native = { ...first.pre.native }; st.tokens = { ...first.pre.tokens }; st.nonces = { ...first.pre.nonces }; }
    for (const b of removed) for (const h of b.txs || []) { const m = st.mined.get(h); st.mined.delete(h); if (m && keepTxs) st.pool.set(h, m.tx); }
    let parent = head();
    for (const old of removed) { const b = push(old.number, parent.hash, parent.timestamp + 2); b.txs = []; parent = b; }
  };

  const rpc = () => ({
    async providerId() { if (st.readFail.has('providerId')) throw new Error('down'); return st.providerId; },
    async chainId() { if (st.readFail.has('chainId')) throw new Error('down'); return st.chainId; },
    async getBlock(x) { if (st.readFail.has('getBlock')) throw new Error('down'); if (x === 'latest') return { ...head() }; const b = st.blocks.find(k => k.number === x); return b ? { ...b } : undefined; },
    async getCode(a, at) { known(at); return st.code[lc(a)] ?? '0x'; },
    async getStorageAt(a, slot, at) { known(at); return '0x' + '00'.repeat(32); },
    async getTransactionCount(a, tag, at) { if (st.readFail.has('nonce')) throw new Error('down'); known(at); const n = st.nonces[lc(a)] ?? 0; return tag === 'pending' ? n + pendingCount(lc(a)) : n; },
    async getBalance(a, at) { known(at); return st.native[lc(a)] ?? 0n; },
    async call(tx, at) {
      known(at);
      if (lc(tx.to) === lc(TOKEN)) return word(st.tokens[lc('0x' + tx.data.slice(34, 74))] ?? 0n);
      if (lc(tx.to) === L1_ORACLE) { if (st.l1Fail) throw new Error('oracle down'); return word(st.l1Quote); }
      throw new Error('unexpected call');
    },
    async getTransaction(hash) {
      const m = st.mined.get(hash); if (m) return { hash, from: m.tx.from, to: m.tx.kind === 'erc20' ? lc(TOKEN) : m.tx.recipient, nonce: m.tx.nonce, value: m.tx.kind === 'native' ? m.tx.amount : 0n, input: m.tx.input, blockHash: m.receipt.blockHash };
      const p = st.pool.get(hash); if (p) return { hash, from: p.from, to: p.kind === 'erc20' ? lc(TOKEN) : p.recipient, nonce: p.nonce, value: p.kind === 'native' ? p.amount : 0n, input: p.input, blockHash: null };
      return null;
    },
  });

  // the component's ports: every call is counted; signing uses the wallet's real key
  const ports = () => ({
    async controls(w) { return !!accounts[w.id]; },
    async tokenBalance(a) { return st.tokens[lc(a)] ?? 0n; },
    async gasBalance(a) { return st.native[lc(a)] ?? 0n; },
    async gasCostEstimate() { return 100_000n; },
    async gasSweepFee() { return 21_100_000n; }, // at least the all-in envelope of the native transfer (21,000,000 + margined L1 + operator bound)
    async nonceOf(a) { return st.nonces[lc(a)] ?? 0; },
    async isContract() { return false; },
    async prepareSweep(w, to, amount, nonce) {
      st.signs++;
      const input = encodeFunctionData({ abi, functionName: 'transfer', args: [to, amount] });
      const raw = (await accounts[w.id].signTransaction({ type: 'eip1559', chainId: st.chainId, nonce, to: TOKEN, value: 0n, gas: GAS_LIMIT.token, maxFeePerGas: FEE_CAP, maxPriorityFeePerGas: 10n, data: input })).toLowerCase();
      return { hash: keccak256(raw), raw };
    },
    async prepareGasSweep(w, to, amount, nonce) {
      st.signs++;
      const raw = (await accounts[w.id].signTransaction({ type: 'eip1559', chainId: st.chainId, nonce, to, value: amount, gas: GAS_LIMIT.native, maxFeePerGas: FEE_CAP, maxPriorityFeePerGas: 10n, data: '0x' })).toLowerCase();
      return { hash: keccak256(raw), raw };
    },
    async broadcast(raw) {
      st.broadcasts.push(raw);
      if (st.offline) throw new Error('provider unreachable');
      const d = await verifyPrepared(raw);
      const fresh = !st.pool.has(d.hash) && !st.mined.has(d.hash);
      if (fresh) st.pool.set(d.hash, { from: d.from, nonce: d.nonce, kind: d.kind, recipient: d.recipient, amount: d.amount, input: d.kind === 'erc20' ? encodeFunctionData({ abi, functionName: 'transfer', args: [d.recipient, d.amount] }) : '0x' });
      if (st.autoMine > 0) mine(st.autoMine);
    },
    verifyPrepared,
    async receipt(hash) {
      const m = st.mined.get(hash); if (!m) return null;
      let rpcReceipt = { ...m.receipt };
      if (st.receiptTweak) rpcReceipt = st.receiptTweak(rpcReceipt);
      return { status: rpcReceipt.status, from: m.receipt.from, to: m.tx.recipient, amount: m.tx.amount, nonce: m.tx.nonce, chainId: st.chainId, token: m.tx.kind === 'erc20' ? lc(TOKEN) : undefined, rpc: rpcReceipt };
    },
  });
  return { st, accounts, addr, ports, rpc, mine, reorg, head, now: () => head().timestamp + 1 };
}
