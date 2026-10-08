import { createPublicClient, http, parseAbi } from 'viem';
import { base } from 'viem/chains';
import { writeFileSync } from 'node:fs';
const c = createPublicClient({ chain: base, transport: http(process.env.BASE_READ_RPC, { retryCount: 0, timeout: 8000 }) });
const abi = parseAbi(['function harvest(address)']);
const B='0x62C4A163026feedB3eA1045d90bBa96d0C5d4F0B';
const S={'aerodrome-lcap-eusd':'0x87C032C1BCb19Bcf99c2DeA040Ef7fccfbd4C04A','aerodrome-bd-usdc':'0x2014BC461243C9535d65F08EdEcb9700853Cc444'};
const blk=await c.getBlock({blockTag:'latest'}); const gp=await c.getGasPrice();
const out={block:blk.number.toString(),gasPrice:gp.toString(),est:{}};
for (const [k,s] of Object.entries(S)) { try { out.est[k]=(await c.estimateContractGas({address:s,abi,functionName:'harvest',args:[B],account:B,blockNumber:blk.number})).toString(); } catch(e){ out.est[k]='failed '+(e.shortMessage||'').slice(0,100);} }
writeFileSync('est.json',JSON.stringify(out,null,2)); console.log(JSON.stringify(out));
