// Static server for app/ with a runtime config override (no cache). Usage: node serve-app.mjs PORT CONFIG_JSON_PATH
import http from 'node:http'; import { readFileSync, existsSync } from 'node:fs'; import { extname, join, normalize } from 'node:path';
const root = new URL('./app/', import.meta.url).pathname; const port = Number(process.argv[2] || 4173); const cfgPath = process.argv[3];
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.webmanifest': 'application/manifest+json' };
export const server = http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x'); let p = u.pathname === '/' ? '/index.html' : u.pathname;
  if (p === '/config.json' && cfgPath) { res.writeHead(200, { 'content-type': 'application/json', 'cache-control': 'no-store' }); return res.end(readFileSync(cfgPath)); }
  const f = join(root, normalize(p).replace(/^(\.\.[/\\])+/, ''));
  if (!f.startsWith(root) || !existsSync(f)) { res.writeHead(404); return res.end('not found'); }
  res.writeHead(200, { 'content-type': types[extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' }); res.end(readFileSync(f));
});
if (import.meta.url === `file://${process.argv[1]}`) server.listen(port, '127.0.0.1', () => console.log('app on http://localhost:' + port));
