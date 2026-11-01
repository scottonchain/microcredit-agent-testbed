// Deploy and fund the SponsorPaymaster. On a fork it uses a funded cheat account; on live it needs DEPLOYER_KEY (testnet).
import { readFileSync } from 'node:fs';
import { createPublicClient, createWalletClient, http, parseEther } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { baseSepolia } from 'viem/chains';
import { ADDR } from './lib/chain.mjs';
import { CB_FACTORY } from './lib/wallet.mjs';
import { entryPoint06Address } from 'viem/account-abstraction';

export async function deployPaymaster({ rpc, key, cap = parseEther('0.02'), deposit = parseEther('0.5'), stake = parseEther('0.05') }) {
  const art = JSON.parse(readFileSync(new URL('./build/SponsorPaymaster.json', import.meta.url)));
  const account = privateKeyToAccount(key); const pc = createPublicClient({ chain: baseSepolia, transport: http(rpc) });
  const wc = createWalletClient({ account, chain: baseSepolia, transport: http(rpc) });
  const hash = await wc.deployContract({ abi: art.abi, bytecode: art.bytecode, args: [entryPoint06Address, ADDR.pool, ADDR.usdc, CB_FACTORY, cap] });
  const rc = await pc.waitForTransactionReceipt({ hash }); const address = rc.contractAddress;
  const t1 = await wc.sendTransaction({ to: address, value: deposit }); await pc.waitForTransactionReceipt({ hash: t1 });
  const t2 = await wc.writeContract({ address, abi: art.abi, functionName: 'addStake', args: [86400], value: stake }); await pc.waitForTransactionReceipt({ hash: t2 });
  return { address, abi: art.abi };
}
