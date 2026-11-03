// One-time live setup from the funded sim treasury: deploy and fund the sponsor paymaster, float the bundler account, write live-config.json.
import { writeFileSync } from 'node:fs';
import { RPC, KEYS, key, pc, eoa, sendEth, deployPaymaster, parseEther, formatEther } from './common.mjs';
const treasury = eoa('sim-treasury'); const bundlerAcc = eoa('sim-bundler');
const bal = await pc.getBalance({ address: treasury.address }); console.log('treasury ETH', formatEther(bal), treasury.address);
const need = Number(process.env.MIN_ETH || 0.004); if (Number(formatEther(bal)) < need) { console.log('Not enough ETH to set up (need ' + need + '). Fund the treasury first.'); process.exit(2); }
const deposit = parseEther(process.env.PM_DEPOSIT || '0.003'), float = parseEther(process.env.BUNDLER_FLOAT || '0.001');
const pm = await deployPaymaster({ rpc: RPC, key: key('sim-treasury'), cap: parseEther('0.005'), deposit, stake: parseEther(process.env.PM_STAKE || '0.0005') });
console.log('paymaster', pm.address); const t = await sendEth(treasury, bundlerAcc.address, float); console.log('bundler float tx', t);
writeFileSync(KEYS + 'live-config.json', JSON.stringify({ rpc: RPC, paymaster: pm.address, bundlerAccount: bundlerAcc.address, treasury: treasury.address }, null, 1)); console.log('wrote live-config.json');
