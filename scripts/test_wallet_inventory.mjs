// Public-address inventory only. No signer, key, transaction submission or recovery.
import { readFileSync, writeFileSync } from 'node:fs';
import { JsonRpcProvider, Contract, formatUnits } from 'ethers';
const root = '0x38e9845A1Df22c59Bfc693bf2CEAa3361158d6d1';
const abi = ['function balanceOf(address) view returns (uint256)'];
const roles = JSON.parse(readFileSync(new URL('../experiments/guarantee-trust-circle-coldstart/evidence/20261013-run1/role-balances.json', import.meta.url), 'utf8'));
const baseAddresses = [
  { id: 'root', address: root },
  { id: 'legacy-guarantee-pool', address: '0x7eD9B2B67E598fd2a1f384CC885c0C860bfD0466' },
  ...roles.map(({ id, address }) => ({ id, address })),
  { id: 'd7-treasury', address: '0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212' },
  { id: 'd7-officer', address: '0xb88DC88d538a754f57cAB344C1E09d02C129fcf2' },
  { id: 'd7-credit-desk', address: '0x28e1d776d9f9f60b90cfb8075ebb9d0f07c82462' },
  { id: 'd7-lending-pool', address: '0x73872B8fB7F1771C67911f03edc75aBdc9514973' },
];
if (roles.length !== 98 || new Set(baseAddresses.map(x => x.address.toLowerCase())).size !== baseAddresses.length) throw Error('Unexpected or duplicate public address set');
async function inventory(chainId, rpc, token, addresses) {
  const p = new JsonRpcProvider(rpc, undefined, { batchMaxCount: 1, cacheTimeout: 0 });
  try {
    if (Number((await p.getNetwork()).chainId) !== chainId) throw Error('Wrong test chain');
    const block = await p.getBlockNumber();
    const c = new Contract(token, abi, p);
    const rows = [];
    for (let i = 0; i < addresses.length; i += 8) {
      rows.push(...await Promise.all(addresses.slice(i, i + 8).map(async x => {
        const balance = await c.balanceOf(x.address, { blockTag: block });
        return { ...x, raw: balance.toString(), testUsdc: formatUnits(balance, 6) };
      })));
    }
    return { chainId, rpc, token, decimals: 6, block, rootEthWei: (await p.getBalance(root, block)).toString(), addresses: rows };
  } finally { p.destroy(); }
}
const results = [];
for (const [chainId, rpc, token, addresses] of [
  [11155111, 'https://ethereum-sepolia-rpc.publicnode.com', '0x1c7d4b196cb0c7b01d743fbc6116a902379c7238', [{ id: 'root', address: root }]],
  [84532, 'https://base-sepolia-rpc.publicnode.com', '0x036CbD53842c5426634e7929541eC2318f3dCF7e', baseAddresses],
]) {
  try { results.push(await inventory(chainId, rpc, token, addresses)); }
  catch { results.push({ chainId, rpc, token, error: 'Inventory failed; no balance inferred' }); }
}
const output = { checkedAt: new Date().toISOString(), readOnly: true, keyLoaded: false, results,
  limitations: ['Blocks are pinned separately on each chain, not simultaneous.', 'Addresses cover the historical cold-start cohort and named D7 roles, not every later recipient.', 'Contract token balances include obligations and are not freely withdrawable treasury.', 'No recovered or spendable amount is inferred from a token balance.'] };
writeFileSync('test-wallet-inventory.json', JSON.stringify(output, null, 2) + '\n');
console.log('TEST_WALLET_INVENTORY=' + JSON.stringify(output));
if (results.some(x => x.error)) process.exitCode = 1;
