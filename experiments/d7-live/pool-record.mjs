#!/usr/bin/env node
// Reads what the chain knows about an applicant, their backer and their practice wallet, and writes the
// pool record the screening policy consumes (experiments/self-service-borrower-app/screening, D17).
//   node pool-record.mjs --borrower 0x.. [--backer 0x..] [--trial 0x..] [--desk 0x..] [--out pool-record.json]
// Read-only. RPC_URL overrides the public endpoint. The practice record is read from the same test network
// here; when the real pool is on mainnet, --trial-rpc points this reader at the test network for that part.
import { writeFileSync, readFileSync } from 'node:fs';
import { createPublicClient, http, getAddress } from 'viem';
import { baseSepolia } from 'viem/chains';
import { ADDR, ABI, RPC, usd } from './lib/chain.mjs';

const arg = (name, fallback = null) => { const i = process.argv.indexOf('--' + name); return i > 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback; };
const borrower = getAddress(arg('borrower') || (() => { throw new Error('--borrower 0x.. is required'); })());
const backer = arg('backer') ? getAddress(arg('backer')) : null;
const trial = arg('trial') ? getAddress(arg('trial')) : null;
const desk = arg('desk') || (() => { try { return JSON.parse(readFileSync(new URL('./app/config.json', import.meta.url), 'utf8')).desk; } catch { return null; } })();
const out = arg('out');
const pc = createPublicClient({ chain: baseSepolia, transport: http(RPC) });
const tc = createPublicClient({ chain: baseSepolia, transport: http(arg('trial-rpc', RPC)) });
const P = (client, fn, args = []) => client.readContract({ address: ADDR.pool, abi: ABI.pool, functionName: fn, args });

// Loan status indices as the pool reports them in getLoanTerms()[0]: 1 requested, 2 active, 3 repaid; defaults are counted by defaultedLoans().
async function loans(client, address) {
  const ids = await P(client, 'getBorrowerLoanIds', [address]);
  let open = 0, repaid = 0;
  for (const id of ids) { const t = await P(client, 'getLoanTerms', [id]); const st = Number(t[0]); if (st === 1 || st === 2) open++; if (st === 3) repaid++; }
  const defaults = Number(await P(client, 'defaultedLoans', [address]));
  return { loans: ids.length, open_loans: open, repaid_on_time: repaid, repaid_late: 0, defaults }; // the pool does not expose days late; repaid counts as on time until the lens reports it
}

const record = { read_at: new Date().toISOString(), chain_id: baseSepolia.id, pool: ADDR.pool, rpc: RPC };
const [rate, assets] = await Promise.all([P(pc, 'getLoanRate'), P(pc, 'totalAssets')]);
record.apr = Number(rate) / 10000; record.reserve_usdc = usd(assets);
record.borrower = { address: borrower, ...(await loans(pc, borrower)) };
if (backer) {
  const [free, backing] = await Promise.all([P(pc, 'getFreeCredit', [backer]), P(pc, 'getBacking', [backer, borrower])]);
  record.backer = { address: backer, free_credit_usdc: usd(free[0]), staked_usdc: usd(free[1]), already_backing_borrower_usdc: usd(backing[0] + backing[1]), ...(await loans(pc, backer)) };
}
if (trial) {
  const t = await loans(tc, trial);
  let deskBacking = null; if (desk) { try { const deskAbi = JSON.parse(readFileSync(new URL('./build/CreditDesk.json', import.meta.url), 'utf8')).abi; deskBacking = usd(await tc.readContract({ address: desk, abi: deskAbi, functionName: 'backingOf', args: [trial] })); } catch {} }
  // linked is false until the applicant signs the intake's challenge with the practice wallet's passkey; the screen gives an unlinked wallet nothing.
  record.trial = { wallet: trial, linked: false, repaid: t.repaid_on_time, defaults: t.defaults, open_loans: t.open_loans, desk_backing_usdc: deskBacking };
}
const text = JSON.stringify(record, (_, v) => (typeof v === 'bigint' ? v.toString() : v), 2);
if (out) writeFileSync(out, text + '\n'); else console.log(text);
