// Simulation toolkit for the Base Sepolia pool. Fork mode uses hardhat cheat RPCs; live mode uses only normal RPCs.
import { privateKeyToAccount } from 'viem/accounts';
import { keccak256, encodeAbiParameters, toHex, pad, maxUint256 } from 'viem';
import { publicClient, walletClient, ADDR, ABI, usd, toUnits, RPC } from './chain.mjs';

export const OWNER = '0x5e4dC7639D2b94006c51aD5373173f5e01c248F9'; // Hermes: owner/reporter/guardian on the live pool
export const pc = publicClient();
export const IS_FORK = RPC.includes('127.0.0.1') || RPC.includes('localhost');

const raw = (method, params = []) => pc.request({ method, params });
export const fork = {
  setEth: (a, wei = 10n ** 20n) => raw('hardhat_setBalance', [a, toHex(wei)]),
  impersonate: (a) => raw('hardhat_impersonateAccount', [a]),
  stopImpersonating: (a) => raw('hardhat_stopImpersonatingAccount', [a]),
  warp: async (seconds) => { await raw('evm_increaseTime', [Number(seconds)]); await raw('evm_mine'); },
  async setUsdc(a, amount) {
    const slot = keccak256(encodeAbiParameters([{ type: 'address' }, { type: 'uint256' }], [a, 9n]));
    await raw('hardhat_setStorageAt', [ADDR.usdc, slot, pad(toHex(amount), { size: 32 })]);
  },
  snapshot: () => raw('evm_snapshot'),
  revert: (id) => raw('evm_revert', [id]),
};

export const errName = (e) => {
  let n = null;
  try { e.walk?.((x) => { if (x?.data?.errorName) n = x.data.errorName; if (!n && x?.name === 'ContractFunctionRevertedError' && x.reason) n = x.reason; }); } catch {}
  return n || (e.shortMessage || e.message || String(e)).slice(0, 140);
};

export function seededKey(seed, name) {
  return keccak256(toHex(`d7-sim:${seed}:${name}`));
}

export class Actor {
  constructor(name, key) {
    this.name = name; this.account = privateKeyToAccount(key); this.address = this.account.address;
    this.wc = walletClient(this.account); this.log = []; this.gas = 0n;
  }
  async call(address, abi, fn, args = [], { expectRevert = null } = {}) {
    try {
      await pc.simulateContract({ address, abi, functionName: fn, args, account: this.account });
    } catch (e) {
      const n = errName(e); this.log.push({ fn, ok: false, error: n });
      return { ok: false, error: n, expected: expectRevert ? n === expectRevert : undefined };
    }
    const hash = await this.wc.writeContract({ address, abi, functionName: fn, args });
    const rc = await pc.waitForTransactionReceipt({ hash });
    this.gas += rc.gasUsed; this.log.push({ fn, ok: rc.status === 'success', hash });
    return { ok: rc.status === 'success', hash, rc };
  }
  pool(fn, args = [], o) { return this.call(ADDR.pool, ABI.pool, fn, args, o); }
  token(fn, args = [], o) { return this.call(ADDR.usdc, ABI.erc20, fn, args, o); }
  usdcBalance() { return pc.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [this.address] }); }
  async ensureAllowance(amount) {
    const a = await pc.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'allowance', args: [this.address, ADDR.pool] });
    if (a < amount) return this.token('approve', [ADDR.pool, maxUint256]);
    return { ok: true };
  }
}

export const read = (fn, args = []) => pc.readContract({ address: ADDR.pool, abi: ABI.pool, functionName: fn, args });

export async function poolState() {
  const [totalAssets, lenderCash, totalLentOut, reserved, reserve, impaired, staked, shares] = await Promise.all(
    ['totalAssets', 'lenderCash', 'totalLentOut', 'reservedLiquidity', 'firstLossReserve', 'totalImpaired', 'totalStaked', 'totalShares'].map((f) => read(f)));
  const bal = await pc.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [ADDR.pool] });
  return { totalAssets, lenderCash, totalLentOut, reserved, reserve, impaired, staked, shares, usdcBalance: bal };
}

// Fork helpers: give an actor ETH and USDC.
export async function fundFork(actor, { eth = 10n ** 18n, usdcAmount = 0n } = {}) {
  await fork.setEth(actor.address, eth);
  if (usdcAmount > 0n) await fork.setUsdc(actor.address, usdcAmount);
}

// Owner-only helpers on a fork (impersonation). Live mode never calls these.
export async function asOwner(fn, args) {
  await fork.impersonate(OWNER); await fork.setEth(OWNER);
  const wc = walletClient(OWNER);
  const hash = await wc.writeContract({ address: ADDR.pool, abi: ABI.pool, functionName: fn, args, account: OWNER });
  await pc.waitForTransactionReceipt({ hash });
  await fork.stopImpersonating(OWNER);
}
export { usd, toUnits, ADDR, ABI };
