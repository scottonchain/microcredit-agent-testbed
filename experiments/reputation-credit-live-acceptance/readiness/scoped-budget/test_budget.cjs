// In-process EVM only: no listening RPC port, external provider or funded keys.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const ganache=require('ganache');
const {createWalletClient,createPublicClient,custom}=require('viem');
const artifact=JSON.parse(fs.readFileSync(process.env.BUDGET_ARTIFACT,'utf8'))['ScopedOriginationBudget.sol'].ScopedOriginationBudget;
const id=n=>'0x'+n.toString(16).padStart(64,'0');
async function setup(caps=[100n,40n,60n]){
 const provider=ganache.provider({logging:{quiet:true},chain:{chainId:31337,hardfork:'shanghai'},wallet:{totalAccounts:8}});
 const accounts=await provider.request({method:'eth_accounts',params:[]});
 const publicClient=createPublicClient({transport:custom(provider)});
 const wallet=createWalletClient({transport:custom(provider)});
 const hash=await wallet.deployContract({account:accounts[0],chain:null,gas:5000000n,abi:artifact.abi,bytecode:'0x'+artifact.evm.bytecode.object,args:[accounts[0],accounts[1],...caps]});
 const receipt=await publicClient.waitForTransactionReceipt({hash});const address=receipt.contractAddress;
 async function call(fn,args,who=0){
  const {request}=await publicClient.simulateContract({address,abi:artifact.abi,functionName:fn,args,account:accounts[who]});
  const h=await wallet.writeContract({...request,chain:null,gas:5000000n});
  const r=await publicClient.waitForTransactionReceipt({hash:h});assert.equal(r.status,'success');return r;
 }
 const read=(fn,args=[])=>publicClient.readContract({address,abi:artifact.abi,functionName:fn,args});
 const grant=(who,c,g,cap=40n)=>call('grant',[accounts[who],id(c),id(g),cap,9999999999n]);
 return {provider,accounts,call,read,grant};
}
test('borrower allowance consumed cumulatively; cannot renew or change identity',async()=>{
 const s=await setup();try{await s.grant(2,1,1);await s.call('consume',[s.accounts[2],30n],1);await s.call('consume',[s.accounts[2],10n],1);
 await assert.rejects(s.call('consume',[s.accounts[2],1n],1));await assert.rejects(s.grant(2,2,2));assert.equal(await s.read('totalUsed'),40n);
 }finally{await s.provider.disconnect();}
});
test('controller and connected group caps aggregate different borrowers',async()=>{
 const s=await setup();try{await s.grant(2,1,1);await s.grant(3,1,1);await s.grant(4,2,1);
 await s.call('consume',[s.accounts[2],30n],1);await assert.rejects(s.call('consume',[s.accounts[3],11n],1));
 await s.call('consume',[s.accounts[4],30n],1);await assert.rejects(s.call('consume',[s.accounts[3],1n],1));assert.equal(await s.read('totalUsed'),60n);
 }finally{await s.provider.disconnect();}
});
test('portfolio cap across unrelated groups',async()=>{
 const s=await setup([50n,40n,40n]);try{await s.grant(2,1,1);await s.grant(3,2,2);await s.call('consume',[s.accounts[2],40n],1);
 await assert.rejects(s.call('consume',[s.accounts[3],11n],1));await s.call('consume',[s.accounts[3],10n],1);assert.equal(await s.read('totalUsed'),50n);
 }finally{await s.provider.disconnect();}
});
test('only bound pool consumes; owner stop permanent; ungranted and zero denied',async()=>{
 const s=await setup();try{await s.grant(2,1,1);await assert.rejects(s.call('consume',[s.accounts[2],1n],2));
 await assert.rejects(s.call('consume',[s.accounts[3],1n],1));await assert.rejects(s.call('consume',[s.accounts[2],0n],1));
 await assert.rejects(s.call('stop',[],2));await s.call('stop',[]);await assert.rejects(s.call('consume',[s.accounts[2],1n],1));
 assert.equal(await s.read('totalUsed'),0n);
 }finally{await s.provider.disconnect();}
});
test('expiry rejects consumption',async()=>{
 const s=await setup();try{await s.grant(2,1,1);await s.provider.request({method:'evm_setTime',params:[10000000000000]});
 await s.provider.request({method:'evm_mine',params:[]});await assert.rejects(s.call('consume',[s.accounts[2],1n],1));
 }finally{await s.provider.disconnect();}
});

test('individual revocation cannot be undone by regrant',async()=>{
 const s=await setup();try{await s.grant(2,1,1);await assert.rejects(s.call('revoke',[s.accounts[2]],2));
 await s.call('revoke',[s.accounts[2]]);await assert.rejects(s.call('consume',[s.accounts[2],1n],1));await assert.rejects(s.grant(2,2,2));
 assert.equal(await s.read('totalUsed'),0n);
 }finally{await s.provider.disconnect();}
});
