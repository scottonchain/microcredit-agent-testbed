// Live Base Sepolia: deploy the CreditDesk (owner = sim treasury, officer = new throwaway key), stake test USDC in it,
// deploy a new SponsorPaymaster that allows desk.say(), fund it from the old paymaster's deposit, give the officer gas.
// DRYRUN=1 runs the same steps on a fork. Keys live only in the scratchpad keys folder.
import { createPublicClient, createWalletClient, http, parseEther, formatEther, formatUnits } from 'viem';
import { privateKeyToAccount, generatePrivateKey } from 'viem/accounts';
import { baseSepolia } from 'viem/chains';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { KEYS, key, eoa } from './common.mjs';
import { deployDesk } from '../deploy-desk.mjs';
import { deployPaymaster } from '../deploy-paymaster.mjs';
import { ADDR } from '../lib/chain.mjs';
const DRY = process.env.DRYRUN === '1'; const RPC = DRY ? 'http://127.0.0.1:8545' : (process.env.RPC_URL || 'https://sepolia.base.org');
const pc = createPublicClient({ chain: baseSepolia, transport: http(RPC) });
const treasury = eoa('sim-treasury'); const wc = createWalletClient({ account: treasury.account, chain: baseSepolia, transport: http(RPC) });
const cfgPath = `${KEYS}/live-config.json`; const live = existsSync(cfgPath) ? JSON.parse(readFileSync(cfgPath, 'utf8')) : {};
const officerPath = `${KEYS}/desk-officer.key`; if (!existsSync(officerPath)) writeFileSync(officerPath, generatePrivateKey(), { mode: 0o600 });
const officer = privateKeyToAccount(readFileSync(officerPath, 'utf8').trim());
const FUND = BigInt(Math.round(Number(process.env.DESK_FUND || 10) * 1e6));
if (DRY) { const { fork } = await import('../lib/sim.mjs'); await fork.setEth(treasury.address, parseEther('1')); await fork.setUsdc(treasury.address, FUND); }
const out = { rpc: RPC, when: new Date().toISOString(), treasury: treasury.address, officer: officer.address, hashes: {} };
console.log('treasury', treasury.address, 'eth', formatEther(await pc.getBalance({ address: treasury.address })), 'officer', officer.address);
// 1. desk
const desk = await deployDesk({ rpc: RPC, key: key('sim-treasury'), officer: officer.address, maxLine: 5_000_000n, fund: FUND });
out.desk = desk.address; Object.assign(out.hashes, { deskDeploy: desk.hashes.deploy, deskApprove: desk.hashes.approve, deskFund: desk.hashes.fund }); console.log('desk', desk.address, 'funded', formatUnits(FUND, 6));
// 2. recover the old paymaster's deposit (owner = treasury)
if (live.paymaster && !DRY) {
  const pmAbi = JSON.parse(readFileSync(new URL('../build/SponsorPaymaster.json', import.meta.url))).abi;
  const epAbi = [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }];
  const dep = await pc.readContract({ address: '0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789', abi: epAbi, functionName: 'balanceOf', args: [live.paymaster] });
  if (dep > 0n) { const h = await wc.writeContract({ address: live.paymaster, abi: pmAbi, functionName: 'withdrawDeposit', args: [treasury.address, dep] }); await pc.waitForTransactionReceipt({ hash: h }); out.hashes.oldPaymasterWithdraw = h; console.log('recovered', formatEther(dep), 'from old paymaster'); }
}
// 3. new paymaster with the desk allowed
const bal = await pc.getBalance({ address: treasury.address }); const deposit = DRY ? parseEther('0.1') : bal - parseEther('0.0012'); // keep gas for the officer and a reserve
const pm = await deployPaymaster({ rpc: RPC, key: key('sim-treasury'), desk: desk.address, cap: parseEther('0.005'), deposit, stake: parseEther(DRY ? '0.01' : '0.0002') });
out.paymaster = pm.address; console.log('paymaster', pm.address, 'deposit', formatEther(deposit));
// 4. officer gas
const g = await wc.sendTransaction({ to: officer.address, value: parseEther(DRY ? '0.1' : '0.0006') }); await pc.waitForTransactionReceipt({ hash: g }); out.hashes.officerGas = g;
if (!DRY) { writeFileSync(cfgPath, JSON.stringify({ ...live, desk: desk.address, paymaster: pm.address, oldPaymaster: live.paymaster, officer: officer.address, deskSetup: out }, null, 1)); }
writeFileSync(`results/desk-setup-${DRY ? 'fork' : 'live'}-${Date.now().toString(36)}.json`, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
