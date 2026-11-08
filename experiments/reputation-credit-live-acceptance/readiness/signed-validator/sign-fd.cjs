// Existing runtime holder supplies an inherited sealed key FD, never argv/env/key file.
// Not invoked by default. No network client, broadcasting, or credential creation.
const fs=require('node:fs');
const {privateKeyToAccount}=require('viem/accounts');
let input='';process.stdin.setEncoding('utf8');process.stdin.on('data',c=>{input+=c;if(input.length>100000)process.exit(2);});
process.stdin.on('end',async()=>{try{
 const fd=Number(process.argv[2]);if(!Number.isSafeInteger(fd)||fd<3)throw Error();
 // buffer.fill(0) clears only the Buffer. The key was already copied into the immutable JS string `key`, which cannot be wiped and
 // lives until this short-lived process exits (see RUNTIME-HANDOFF.md: Node strings are not claimed to be securely zeroized).
 const buffer=Buffer.alloc(128);const size=fs.readSync(fd,buffer,0,128,0);const key=buffer.subarray(0,size).toString('utf8').trim();buffer.fill(0);
 if(!/^0x[0-9a-fA-F]{64}$/.test(key))throw Error();
 const {transaction:t,limits:l}=JSON.parse(input);
 const account=privateKeyToAccount(key);
 if(account.address.toLowerCase()!==t.from.toLowerCase())throw Error();
 const serialized=await account.signTransaction({type:'eip1559',chainId:Number(BigInt(t.chainId)),nonce:Number(BigInt(t.nonce)),
  to:t.to,value:BigInt(t.value),data:t.data,gas:BigInt(l.gas),maxFeePerGas:BigInt(l.maxFeePerGas),maxPriorityFeePerGas:BigInt(l.maxPriorityFeePerGas)});
 process.stdout.write(JSON.stringify({serialized}));
}catch{process.stdout.write('{"error":"SIGNING_REJECTED"}');process.exitCode=1;}});
