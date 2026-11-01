// Run the bundler as a standalone process: RPC_URL, BUNDLER_KEY_FILE, PORT (default 4337). Testnet only.
import { readFileSync } from 'node:fs'; import { startBundler } from './bundler.mjs';
const b = await startBundler({ rpc: process.env.RPC_URL, port: Number(process.env.PORT || 4337), key: readFileSync(process.env.BUNDLER_KEY_FILE, 'utf8').trim(), verificationGas: BigInt(process.env.VERIF_GAS || 2500000), log: (...a) => process.env.VERBOSE && console.log(...a) });
console.log('bundler', b.url, 'account', b.address);
