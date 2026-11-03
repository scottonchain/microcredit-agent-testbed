// Deploy the CreditDesk and stake test USDC in it. On a fork the deployer is a funded cheat account; on live it is the sim treasury key.
import { readFileSync } from 'node:fs';
import { createPublicClient, createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { baseSepolia } from 'viem/chains';
import { ADDR } from './lib/chain.mjs';
const erc20 = [{ type: 'function', name: 'approve', stateMutability: 'nonpayable', inputs: [{ type: 'address' }, { type: 'uint256' }], outputs: [{ type: 'bool' }] }];
export const deskAbi = JSON.parse(readFileSync(new URL('./build/CreditDesk.json', import.meta.url))).abi;
export async function deployDesk({ rpc, key, officer, maxLine = 5_000_000n, fund = 0n }) {
  const art = JSON.parse(readFileSync(new URL('./build/CreditDesk.json', import.meta.url)));
  const account = privateKeyToAccount(key); const pc = createPublicClient({ chain: baseSepolia, transport: http(rpc) });
  const wc = createWalletClient({ account, chain: baseSepolia, transport: http(rpc) });
  const hash = await wc.deployContract({ abi: art.abi, bytecode: art.bytecode, args: [ADDR.pool, ADDR.usdc, officer, maxLine] });
  const rc = await pc.waitForTransactionReceipt({ hash }); const address = rc.contractAddress;
  const hashes = { deploy: hash };
  if (fund > 0n) {
    const a = await wc.writeContract({ address: ADDR.usdc, abi: erc20, functionName: 'approve', args: [address, fund] }); await pc.waitForTransactionReceipt({ hash: a });
    const f = await wc.writeContract({ address, abi: art.abi, functionName: 'fund', args: [fund] }); await pc.waitForTransactionReceipt({ hash: f });
    hashes.approve = a; hashes.fund = f;
  }
  return { address, abi: art.abi, hashes };
}
