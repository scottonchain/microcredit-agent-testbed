// Back an outside tester's wallet with test credit from the sponsor backer wallet (a persistent passkey smart wallet).
// Usage: node live/back.mjs <address> <totalAmountUSDC>   (DRYRUN=1 with RPC_URL=fork to rehearse). Testnet only.
import { readFileSync, existsSync } from 'node:fs'; import { getAddress, isAddress } from 'viem';
import { RPC, KEYS, key, pc, eoa, usdcOf, P, transferUsdc, smartWallet, ADDR, usd, toUnits, parseEther, poolCall, usdcCall, startBundler, deployPaymaster } from './common.mjs';
const [to, amtS] = process.argv.slice(2); if (!isAddress(to || '')) { console.log('usage: node live/back.mjs <address> <totalAmount>'); process.exit(2); }
const target = getAddress(to); const total = toUnits(Number(amtS || 5)); const DRY = process.env.DRYRUN === '1'; const treasury = eoa('sim-treasury');
let cfg; if (DRY) { const { fork } = await import('../lib/sim.mjs'); await fork.setEth(treasury.address, parseEther('1')); await fork.setUsdc(treasury.address, toUnits(20)); await fork.setEth(eoa('sim-bundler').address, parseEther('1')); const pm = await deployPaymaster({ rpc: RPC, key: key('sim-treasury'), cap: parseEther('0.02'), deposit: parseEther('0.1'), stake: parseEther('0.01') }); cfg = { paymaster: pm.address }; }
else cfg = JSON.parse(readFileSync(KEYS + 'live-config.json', 'utf8'));
const bundler = await startBundler({ rpc: RPC, port: 4340, key: key('sim-bundler'), verificationGas: BigInt(process.env.VERIF_GAS || (DRY ? 2500000 : 1500000)) }); cfg.bundler = bundler.url;
const B = await smartWallet('sponsor-backer', cfg); console.log('sponsor backer wallet', B.address);
const cur = (await pc.readContract({ address: ADDR.pool, abi: (await import('../lib/chain.mjs')).ABI.pool, functionName: 'getBacking', args: [B.address, target] })); const have = cur[0] + cur[1];
const free = await P('getFreeCredit', [B.address]); const extra = total > have ? total - have : 0n; const need = extra > free[0] + free[1] ? extra - (free[0] + free[1]) : 0n;
console.log('currently backing', usd(have), '| target total', usd(total), '| free', usd(free[0] + free[1]), '| new stake needed', usd(need));
if (need > 0n) { const bal = await usdcOf(B.address); if (bal < need) { const top = need - bal; const tb = await usdcOf(treasury.address); if (tb < top) { console.log('treasury short: has', usd(tb), 'needs', usd(top)); process.exit(3); } console.log('treasury -> backer', usd(top), await transferUsdc(treasury, B.address, top)); }
  const r = await B.op('approve+stake ' + usd(need), [usdcCall('approve', [ADDR.pool, need]), poolCall('stake', [need])]); console.log('stake', r.ok, r.tx || r.reason); if (!r.ok) process.exit(1); }
if (total !== have) { const r = await B.op('back ' + target + ' ' + usd(total), [poolCall('back', [target, total])]); console.log('back', r.ok, r.tx || r.reason); if (!r.ok) process.exit(1); }
const [lim, avail] = await P('getBorrowLimit', [target]); console.log('target limit', usd(lim), 'available', usd(avail)); bundler.close(); process.exit(0);
