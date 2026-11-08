// Private stdin/stdout protocol only; no network, key loading or execution.
const {verifySigned}=require('./verify.cjs');
let data='';process.stdin.setEncoding('utf8');
process.stdin.on('data',chunk=>{data+=chunk;if(data.length>100000)process.exit(2);});
process.stdin.on('end',async()=>{try{
 const p=JSON.parse(data);const bound={...p.transaction,chainId:Number(BigInt(p.transaction.chainId)),nonce:Number(BigInt(p.transaction.nonce)),value:BigInt(p.transaction.value)};
 const limits={...p.limits,gas:BigInt(p.limits.gas),maxFeePerGas:BigInt(p.limits.maxFeePerGas),maxTotalFee:BigInt(p.limits.maxTotalFee)};
 process.stdout.write(JSON.stringify(await verifySigned(p.serialized,bound,limits,p.now)));
}catch{process.stdout.write(JSON.stringify({signatureValid:false}));process.exitCode=1;}});
