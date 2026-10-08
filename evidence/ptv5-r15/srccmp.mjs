import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const require = createRequire('/root/work/ptv5_probe_r6/package.json');
const { keccak256 } = await import(pathToFileURL(require.resolve('viem')).href);
for (const a of ['0x13ad51a6664973ebd0749a7c84939d973f247921', '0x4f09bab2f0e15e2a078a227fe1537665f55b8360']) {
  const j = JSON.parse(readFileSync('/root/work/run_r15/sourcify_' + a + '.json'));
  const rb = j.runtimeBytecode || {};
  console.log(a, 'runtimeBytecode keys', Object.keys(rb));
  for (const k of ['onchainBytecode', 'recompiledBytecode']) if (typeof rb[k] === 'string') console.log(' ', k, 'bytes', (rb[k].length - 2) / 2, 'keccak', keccak256(rb[k].startsWith('0x') ? rb[k] : '0x' + rb[k]));
  console.log('  match fields', j.match, j.runtimeMatch, 'deployment', JSON.stringify(j.deployment).slice(0, 300));
  console.log('  sources', Object.keys(j.sources || {}).slice(0, 12).join(', '));
}
