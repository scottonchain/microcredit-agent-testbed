// Shared chain helpers: ABIs, addresses, clients. Testnet only.
import { createPublicClient, createWalletClient, http, parseAbi } from 'viem';
import { baseSepolia } from 'viem/chains';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const abi = (n) => JSON.parse(readFileSync(join(here, '..', 'abi', n + '.json'), 'utf8'));

export const ADDR = {
  pool: '0x73872B8fB7F1771C67911f03edc75aBdc9514973',
  lens: '0xe47BAea70DC68D6bDeFE08FD8021F84F69FdF8F4',
  scores: '0x554c6bB61eDF0CAfB90ff31813540369Cb0105e4',
  usdc: '0x036CbD53842c5426634e7929541eC2318f3dCF7e',
};
export const ABI = {
  pool: abi('DecentralizedMicrocredit'),
  lens: abi('MicrocreditLens'),
  scores: abi('OracleScoreProvider'),
  erc20: parseAbi([
    'function balanceOf(address) view returns (uint256)',
    'function allowance(address,address) view returns (uint256)',
    'function approve(address,uint256) returns (bool)',
    'function transfer(address,uint256) returns (bool)',
    'function decimals() view returns (uint8)',
    'function nonces(address) view returns (uint256)',
  ]),
};
export const RPC = process.env.RPC_URL || 'https://sepolia.base.org';
export const chain = baseSepolia;
export const publicClient = () => createPublicClient({ chain, transport: http(RPC) });
export const walletClient = (account) => createWalletClient({ account, chain, transport: http(RPC) });
export const usd = (x) => Number(x) / 1e6;
export const toUnits = (x) => BigInt(Math.round(Number(x) * 1e6));
