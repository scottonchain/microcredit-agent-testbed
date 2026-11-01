// End-to-end on a fork: passkey smart wallet borrows from the live pool, sends, and repays, gas sponsored.
import { parseEther, formatEther } from 'viem';
import { generatePrivateKey } from 'viem/accounts';
import { startBundler } from './bundler.mjs';
import { deployPaymaster } from './deploy-paymaster.mjs';
import { SoftAuthenticator } from './lib/softpasskey.mjs';
import { clients, openWallet, newCredential, poolCall, usdcCall, runOp } from './lib/wallet.mjs';
import { fork, Actor, seededKey, fundFork, read, usd, toUnits, ADDR, ABI, pc } from './lib/sim.mjs';
import { maxUint256 } from 'viem';

const RPC = process.env.RPC_URL; if (!RPC) throw new Error('set RPC_URL (fork)');
const deployerKey = seededKey(1, 'deployer'), bundlerKey = seededKey(1, 'bundler');
const dep = new Actor('deployer', deployerKey), bun = new Actor('bundler', bundlerKey);
await fundFork(dep, { eth: parseEther('5') }); await fundFork(bun, { eth: parseEther('5') });
const pm = await deployPaymaster({ rpc: RPC, key: deployerKey });
console.log('paymaster', pm.address);
const b = await startBundler({ rpc: RPC, port: 4337, key: bundlerKey });
const { client, mkBundler } = clients({ rpc: RPC, bundler: b.url, paymaster: pm.address });

// Liquidity + a backer with stake (stand-ins for the lenders and friends of a real borrower).
const lender = new Actor('lender', seededKey(1, 'lender')); await fundFork(lender, { usdcAmount: toUnits(300) });
await lender.ensureAllowance(toUnits(300)); await lender.pool('depositFunds', [toUnits(200)]);
const backer = new Actor('backer', seededKey(1, 'backer')); await fundFork(backer, { usdcAmount: toUnits(50) });
await backer.ensureAllowance(toUnits(50)); await backer.pool('stake', [toUnits(25)]);

// The user: a fresh passkey, no ETH, no USDC beyond the faucet drop.
const auth = new SoftAuthenticator({ rpId: 'localhost', origin: 'http://localhost' });
const credential = await newCredential({ name: 'tester', createFn: auth.createFn, rpId: 'localhost' });
const account = await openWallet({ client, credential, getFn: auth.getFn, rpId: 'localhost' });
const addr = await account.getAddress(); console.log('wallet address (counterfactual)', addr, 'code?', (await client.getCode({ address: addr })) || 'none');
await fork.setUsdc(addr, toUnits(2)); // stand-in for Circle faucet: a little USDC for interest
await backer.pool('back', [addr, toUnits(10)]);
const bc = mkBundler(account);

const t = Date.now();
let [lim] = await read('getBorrowLimit', [addr]); console.log('limit', usd(lim));
// Borrow: request + disburse in one operation (predict the next loan id).
const ids = await read('getAllLoanIds'); const nextId = (ids.length ? ids[ids.length - 1] : 0n) + 1n;
console.log('existing loan ids', ids.map(String).join(','), '-> predicted next', nextId);
const r1 = await runOp({ bundlerClient: bc, account, calls: [poolCall('requestLoan', [toUnits(10)]), poolCall('disburseLoan', [nextId])] });
console.log('borrow op success', r1.success, 'gas cost wei', r1.actualGasCost, 'tx', r1.txHash.slice(0, 12), 'events', r1.events.map(e => e.eventName).join(','));
console.log('wallet code now', (await client.getCode({ address: addr }))?.length > 2 ? 'deployed' : 'none', ' USDC', usd(await pc.readContract({ address: ADDR.usdc, abi: ABI.erc20, functionName: 'balanceOf', args: [addr] })));
// Send 3 USDC to a friend.
const friend = new Actor('friend', seededKey(1, 'friend'));
const r2 = await runOp({ bundlerClient: bc, account, calls: [usdcCall('transfer', [friend.address, toUnits(3)])] });
console.log('send op success', r2.success, 'friend has', usd(await friend.usdcBalance()));
// Repay after 12 days: approve + repay in one operation.
await fork.warp(12 * 86400);
const owed = await read('getCurrentOutstandingAmount', [nextId]); console.log('owed', usd(owed));
const rBad = await runOp({ bundlerClient: bc, account, calls: [usdcCall('approve', [ADDR.pool, maxUint256]), poolCall('repayLoan', [nextId, owed + 20000n])] });
console.log('repay with too little USDC: success', rBad.success, 'reason', rBad.reason);
await fork.setUsdc(addr, toUnits(12)); // back from the faucet
const r3 = await runOp({ bundlerClient: bc, account, calls: [usdcCall('approve', [ADDR.pool, maxUint256]), poolCall('repayLoan', [nextId, owed + 20000n])] });
console.log('repay op success', r3.success, 'status', Number((await read('getLoanTerms', [nextId]))[0]), '(3=Repaid)');
console.log('passkey prompts used', auth.calls, 'elapsed ms', Date.now() - t);
const spent = await pc.readContract({ address: pm.address, abi: pm.abi, functionName: 'spent', args: [addr] }); console.log('sponsored gas for this wallet (ETH)', formatEther(spent));
b.close(); process.exit(0);
