import solc from 'solc'; import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
const src = readFileSync('contracts/SponsorPaymaster.sol', 'utf8');
const out = JSON.parse(solc.compile(JSON.stringify({ language: 'Solidity', sources: { 'SponsorPaymaster.sol': { content: src } }, settings: { optimizer: { enabled: true, runs: 200 }, viaIR: true, outputSelection: { '*': { '*': ['abi', 'evm.bytecode.object'] } } } })));
const errs = (out.errors || []).filter((e) => e.severity === 'error'); for (const e of out.errors || []) console.log(e.severity, e.formattedMessage.split('\n')[0]);
if (errs.length) process.exit(1);
const c = out.contracts['SponsorPaymaster.sol'].SponsorPaymaster; mkdirSync('build', { recursive: true });
writeFileSync('build/SponsorPaymaster.json', JSON.stringify({ abi: c.abi, bytecode: '0x' + c.evm.bytecode.object }));
console.log('compiled, bytecode bytes', c.evm.bytecode.object.length / 2);
