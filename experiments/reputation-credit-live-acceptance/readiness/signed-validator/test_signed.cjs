const {test}=require('node:test'); const assert=require('node:assert/strict');
const {generatePrivateKey,privateKeyToAccount}=require('viem/accounts');
const {serializeTransaction,parseTransaction}=require('viem');
const {verifySigned}=require('./verify.cjs');
const fixtures=require('../abi-encoding-fixtures.json');
// Ephemeral, unexported, unfunded test key; local chain31337 and fictional desk.
const account=privateKeyToAccount(generatePrivateKey());
const other=privateKeyToAccount(generatePrivateKey());
const base={type:'eip1559',chainId:31337,nonce:3,to:'0x'+'4'.repeat(40),value:0n,data:fixtures.reply,
            gas:200000n,maxFeePerGas:3n,maxPriorityFeePerGas:1n};
const bound={chainId:31337,nonce:3,from:account.address,to:base.to,value:0n,data:base.data};
const limits={expires:2000,gas:250000n,maxFeePerGas:4n,maxTotalFee:1000000n};
const sign=(changes={},a=account)=>a.signTransaction({...base,...changes});
test('recovers signed sender and exact ABI payload but never grants execution',async()=>{
 const r=await verifySigned(await sign(),bound,limits,1000);
 assert.equal(r.sender,account.address.toLowerCase());assert.equal(r.executionAllowed,false);assert.match(r.transactionHash,/^0x[0-9a-f]{64}$/);
});
test('chain sender nonce recipient value calldata tampering rejected',async()=>{
 // Exercise real, valid signatures for each changed field, not malformed stubs.
 for(const change of [{chainId:1},{nonce:4},{to:'0x'+'6'.repeat(40)},{value:1n},{data:base.data+'00'}]) {
  const raw=await sign(change); await assert.rejects(()=>verifySigned(raw,bound,limits,1000));
 }
 const raw=await sign({},other);await assert.rejects(()=>verifySigned(raw,bound,limits,1000));
});
test('fee gas total expiry and access list gates',async()=>{
 for(const change of [{gas:300000n},{maxFeePerGas:5n},{accessList:[{address:base.to,storageKeys:[]}]}]){
  const raw=await sign(change);await assert.rejects(()=>verifySigned(raw,bound,limits,1000));
 }
 await assert.rejects(()=>sign({maxPriorityFeePerGas:4n})); // library refuses invalid tip before signing
 const raw=await sign();await assert.rejects(()=>verifySigned(raw,bound,{...limits,maxTotalFee:1n},1000));
 await assert.rejects(()=>verifySigned(raw,bound,limits,2000));
});
test('unsigned legacy malformed trailing and high-s signatures rejected',async()=>{
 await assert.rejects(()=>verifySigned(serializeTransaction(base),bound,limits,1000));
 const raw=await sign();await assert.rejects(()=>verifySigned(raw+'00',bound,limits,1000));
 const legacy=await account.signTransaction({type:'legacy',chainId:31337,nonce:3,to:base.to,value:0n,data:base.data,gas:200000n,gasPrice:3n});
 await assert.rejects(()=>verifySigned(legacy,bound,limits,1000));
 const t=parseTransaction(raw);const n=0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141n;
 const high=serializeTransaction(t,{r:t.r,s:'0x'+(n-BigInt(t.s)).toString(16).padStart(64,'0'),yParity:1-t.yParity});
 await assert.rejects(()=>verifySigned(high,bound,limits,1000));
});
