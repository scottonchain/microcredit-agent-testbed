// Live: a headless smart wallet writes to the credit desk through the public bundler and the sponsor paymaster,
// then waits for the officer's on-chain reply. No funds needed by the wallet. Prints hashes and the conversation.
import { readFileSync } from 'node:fs';
import { encodeFunctionData, formatUnits } from 'viem';
import { smartWallet, pc, P, usd } from './common.mjs';
const cfg = JSON.parse(readFileSync(new URL('../app/config.json', import.meta.url), 'utf8')); if (process.env.BUNDLER) cfg.bundler = process.env.BUNDLER;
const deskAbi = JSON.parse(readFileSync(new URL('../abi/CreditDesk.json', import.meta.url), 'utf8'));
const D = (fn, args = []) => pc.readContract({ address: cfg.desk, abi: deskAbi, functionName: fn, args });
const name = process.env.WALLET || 'desk-smoke-' + Date.now().toString(36);
const W = await smartWallet(name, cfg); console.log('wallet', W.address, 'bundler', cfg.bundler, 'paymaster', cfg.paymaster, 'desk', cfg.desk);
const text = process.env.TEXT || 'Hello. I would like to borrow 3 dollars to buy phone credit so I can take orders for my tailoring. I will pay it back in two weeks when the orders are paid.';
const r = await W.op('say', [{ to: cfg.desk, data: encodeFunctionData({ abi: deskAbi, functionName: 'say', args: [text] }) }]);
console.log('say', r.ok, r.tx, r.ms + ' ms', r.reason || '');
if (!r.ok) process.exit(1);
const n0 = (await D('thread', [W.address])).length; const t0 = Date.now();
for (;;) { const th = await D('thread', [W.address]); if (th.length > n0 && Number(th[th.length - 1].from) === 1) { for (const m of th) console.log(Number(m.from) === 0 ? 'APPLICANT:' : 'OFFICER:  ', m.text); break; } if (Date.now() - t0 > 300000) { console.log('no reply in 300 s'); process.exit(1); } await new Promise((x) => setTimeout(x, 5000)); }
console.log('reply after', Math.round((Date.now() - t0) / 1000), 's; desk backing', formatUnits(await D('backingOf', [W.address]), 6), 'limit', usd((await P('getBorrowLimit', [W.address]))[0]));
