// Persistent local world for persona runs: a fork of the live Base Sepolia pool with the credit desk, an AI officer,
// a bundler and the app served on :4173, plus a control API on :4180 (health, fund, warp, state, and a stand-in faucet page).
import http from 'node:http'; import { readFileSync, writeFileSync } from 'node:fs'; import { join } from 'node:path';
const D = process.env.D7_DIR; process.chdir(D);
const { world, fork, read, ADDR, pc, toUnits, usd } = await import(join(D, 'lib/apptest.mjs'));
const CTRL = Number(process.env.CTRL_PORT || 4180), WEB = Number(process.env.WEB_PORT || 4173), BUN = Number(process.env.BUNDLER_PORT || 4337);
const w = await world({ seed: 7, bundlerPort: BUN, webPort: WEB, poolLiquidity: 300, deskFund: 50, daemonMode: process.env.DAEMON_MODE || 'claude' });
const cfgPath = join(D, `results/test-config-${WEB}.json`); const cfg = JSON.parse(readFileSync(cfgPath, 'utf8'));
cfg.faucet = `http://127.0.0.1:${CTRL}/faucet`; writeFileSync(cfgPath, JSON.stringify(cfg));
const erc = [{ type: 'function', name: 'balanceOf', stateMutability: 'view', inputs: [{ type: 'address' }], outputs: [{ type: 'uint256' }] }];
const bal = (a) => pc.readContract({ address: ADDR.usdc, abi: erc, functionName: 'balanceOf', args: [a] });
async function fund(addr, amount) { const b = await bal(addr); await fork.setUsdc(addr, b + toUnits(amount)); return usd(await bal(addr)); }
const page = (title, body) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><style>body{font:16px system-ui;max-width:420px;margin:24px auto;padding:0 16px;color:#222}label{display:block;margin:14px 0 4px;font-weight:600}input,select{width:100%;padding:10px;font-size:16px;border:1px solid #bbb;border-radius:8px}button{margin-top:18px;padding:12px 18px;font-size:16px;border:0;border-radius:8px;background:#1c64f2;color:#fff}.ok{background:#e6f7ea;padding:12px;border-radius:8px;margin-top:16px}small{color:#666}</style></head><body>${body}</body></html>`;
const faucetForm = (msg = '') => page('Circle Faucet (stand-in)', `<h1>Testnet Faucet</h1><p><small>Get testnet tokens for development. Limit: one request per address every couple of hours.</small></p>${msg}<form method="post" action="/faucet"><label>Network</label><select name="network"><option>Ethereum Sepolia</option><option>Base Sepolia</option><option>Arbitrum Sepolia</option><option>Polygon Amoy</option></select><label>Token</label><select name="token"><option>USDC</option><option>EURC</option></select><label>Wallet address</label><input name="address" placeholder="0x..." autocomplete="off"><button type="submit">Get tokens</button></form>`);
const api = http.createServer(async (req, res) => {
  const u = new URL(req.url, 'http://x'); const send = (code, obj, type = 'application/json') => { res.writeHead(code, { 'content-type': type }); res.end(type === 'application/json' ? JSON.stringify(obj) : obj); };
  try {
    if (u.pathname === '/health') return send(200, { ok: true, web: WEB, bundler: BUN, desk: w.desk.address, pm: w.pm.address });
    if (u.pathname === '/warp') { const s = Number(u.searchParams.get('seconds') || 0); await fork.warp(s); const b = await pc.getBlock(); return send(200, { ok: true, seconds: s, chainTime: Number(b.timestamp) }); }
    if (u.pathname === '/fund') { const a = u.searchParams.get('addr'); const n = Number(u.searchParams.get('usdc') || 20); return send(200, { ok: true, balance: await fund(a, n) }); }
    if (u.pathname === '/state') { const a = u.searchParams.get('addr'); const ids = await read('getBorrowerLoanIds', [a]); const loans = []; for (const id of ids) { const t = await read('getLoanTerms', [id]); const owed = await read('getCurrentOutstandingAmount', [id]); loans.push({ id: String(id), status: Number(t[0]), dueAt: Number(t[4]), owed: usd(owed) }); } const lim = await read('getBorrowLimit', [a]); return send(200, { usdc: usd(await bal(a)), limit: usd(lim[0]), available: usd(lim[1]), loans }); }
    if (u.pathname === '/faucet' && req.method === 'GET') return send(200, faucetForm(), 'text/html');
    if (u.pathname === '/faucet' && req.method === 'POST') { let body = ''; for await (const c of req) body += c; const f = new URLSearchParams(body); const addr = (f.get('address') || '').trim(); const net = f.get('network'), tok = f.get('token');
      if (!/^0x[0-9a-fA-F]{40}$/.test(addr)) return send(200, faucetForm('<div class="ok" style="background:#fdecea">Please enter a valid wallet address (it starts with 0x and has 42 characters).</div>'), 'text/html');
      if (net !== 'Base Sepolia' || tok !== 'USDC') return send(200, page('Circle Faucet (stand-in)', `<h1>Testnet Faucet</h1><div class="ok">Sent 20 ${tok} on ${net} to ${addr}.</div><p><small>Tokens arrive in about a minute.</small></p><p><a href="/faucet">Request more</a></p>`), 'text/html');
      const after = await fund(addr, 20); return send(200, page('Circle Faucet (stand-in)', `<h1>Testnet Faucet</h1><div class="ok">Sent 20 USDC on Base Sepolia to ${addr}.</div><p><small>Tokens arrive in about a minute. Balance now: ${after} USDC.</small></p><p><a href="/faucet">Request more</a></p>`), 'text/html'); }
    send(404, { error: 'not found' });
  } catch (e) { send(500, { error: e.message }); }
});
api.listen(CTRL, '127.0.0.1', () => console.log(JSON.stringify({ ready: true, ctrl: CTRL, web: WEB, bundler: BUN, desk: w.desk.address, paymaster: w.pm.address, daemon: !!w.daemon })));
process.on('SIGTERM', async () => { await w.close(); process.exit(0); });
