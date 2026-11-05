// Full candidate pool on a standard-size-limit, in-process Cancun EVM.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const solc=require('solc'),localEVM=require('./local_evm.cjs');
const {createWalletClient,createPublicClient,custom,decodeEventLog}=require('viem');
const {generatePrivateKey,privateKeyToAccount}=require('viem/accounts');
const compiled=JSON.parse(fs.readFileSync(process.env.BUDGET_ARTIFACT,'utf8'));
const unit=1000000n,identity=n=>'0x'+n.toString(16).padStart(64,'0');
const mock=`pragma solidity 0.8.33;
contract Token { bool public failTransfers; function setFailTransfers(bool flag) external {failTransfers=flag;} mapping(address=>uint256) public balanceOf; mapping(address=>mapping(address=>uint256)) public allowance;
event Transfer(address indexed from,address indexed to,uint256 value);
function mint(address to,uint256 v) external {balanceOf[to]+=v;emit Transfer(address(0),to,v);}
function approve(address to,uint256 v) external returns(bool){allowance[msg.sender][to]=v;return true;}
function transfer(address to,uint256 v) external returns(bool){move(msg.sender,to,v);return true;}
function transferFrom(address from,address to,uint256 v) external returns(bool){require(allowance[from][msg.sender]>=v);allowance[from][msg.sender]-=v;move(from,to,v);return true;}
function move(address from,address to,uint256 v) internal {require(!failTransfers);require(balanceOf[from]>=v);balanceOf[from]-=v;balanceOf[to]+=v;emit Transfer(from,to,v);}}
contract CallerWallet { address immutable accepted;constructor(address a){accepted=a;} function isValidSignature(bytes32,bytes calldata) external view returns(bytes4){return msg.sender==accepted?bytes4(0x1626ba7e):bytes4(0xffffffff);} }
`;
const m=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources:{'Mock.sol':{content:mock}},settings:{evmVersion:'shanghai',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}})));
if((m.errors||[]).some(e=>e.severity==='error'))throw Error(JSON.stringify(m.errors));
const fields={DisburseRequest:[['borrower','address'],['loanId','uint256'],['to','address'],['nonce','uint256'],['deadline','uint256']],RepayRequest:[['borrower','address'],['loanId','uint256'],['amount','uint256'],['nonce','uint256'],['deadline','uint256']],LoanRequest:[['borrower','address'],['amount','uint256'],['nonce','uint256'],['deadline','uint256']],BorrowAndDisburse:[['borrower','address'],['amount','uint256'],['to','address'],['repaymentPeriod','uint256'],['maxAprBps','uint256'],['nonce','uint256'],['deadline','uint256']]};
async function setup({baseline=false}={}){
 const p=await localEVM();
 const addresses=await p.request({method:'eth_accounts',params:[]});
 const pub=createPublicClient({transport:custom(p)}),wallet=createWalletClient({transport:custom(p)});
 const borrower=privateKeyToAccount(generatePrivateKey());
 await p.request({method:'evm_setAccountBalance',params:[borrower.address,'0x56bc75e2d63100000']});
 const borrowerWallet=createWalletClient({account:borrower,transport:custom(p)});
 async function deploy(a,args=[]){const h=await wallet.deployContract({account:addresses[0],chain:null,gas:29000000n,abi:a.abi,bytecode:'0x'+a.evm.bytecode.object,args});const r=await pub.waitForTransactionReceipt({hash:h});assert.equal(r.status,'success');return {address:r.contractAddress,abi:a.abi};}
 async function call(c,fn,args=[],who=0,expect='success'){
  const client=who==='borrower'?borrowerWallet:wallet;
  const h=await client.writeContract({address:c.address,abi:c.abi,functionName:fn,args,account:who==='borrower'?borrower:addresses[who],chain:null,gas:6000000n});
  const r=await pub.waitForTransactionReceipt({hash:h});assert.equal(r.status,expect,fn);return r;
 }
 const read=(c,fn,args=[])=>pub.readContract({address:c.address,abi:c.abi,functionName:fn,args});
 const token=await deploy(m.contracts['Mock.sol'].Token);
 const pool=await deploy(compiled[baseline?'CanonicalBaseline.sol':'DecentralizedMicrocredit.sol'].DecentralizedMicrocredit,[0n,0n,100n*unit,token.address,addresses[0]]);
 const budget=await deploy(compiled['ScopedOriginationBudget.sol'].ScopedOriginationBudget,[addresses[0],pool.address,100n*unit,20n*unit,40n*unit]);
 if(!baseline)await call(pool,'setOriginationBudget',[budget.address]);
 await call(token,'mint',[addresses[0],1000n*unit]);await call(token,'approve',[pool.address,1000n*unit]);
 await call(pool,'depositFunds',[500n*unit]);await call(pool,'stake',[100n*unit]);
 const deadline=9999999999n;
 async function grant(address=borrower.address,c=1,g=1){await call(budget,'grant',[address,identity(c),identity(g),20n*unit,deadline]);await call(pool,'back',[address,10n*unit]);}
 const sign=(type,message)=>borrower.signTypedData({domain:{name:'DecentralizedMicrocredit',version:'1',chainId:31337,verifyingContract:pool.address},types:{[type]:fields[type].map(([name,type])=>({name,type}))},primaryType:type,message});
 const request=(amount=5n*unit,nonce=0n)=>({borrower:borrower.address,amount,nonce,deadline});
 const code=await pub.getCode({address:pool.address});assert.ok((code.length-2)/2<=24576);
 return {p,addresses,borrower,pub,wallet,token,pool,budget,call,read,grant,sign,request,deploy,deadline};
}
test('full pool: reusable secured backing cannot replenish cumulative allowance',async()=>{
 const s=await setup();try{await s.grant();
 for(let id=1n;id<=2n;id++){await s.call(s.pool,'requestLoan',[10n*unit],'borrower');await s.call(s.pool,'disburseLoan',[id]);await s.call(s.token,'approve',[s.pool.address,10n*unit],'borrower');await s.call(s.pool,'repayLoan',[id,10n*unit],'borrower');}
 await s.call(s.pool,'requestLoan',[unit],'borrower','reverted');assert.equal(await s.read(s.budget,'totalUsed'),20n*unit);
 assert.equal((await s.read(s.pool,'getBorrowLimit',[s.borrower.address]))[1],10n*unit);
 }finally{await s.p.disconnect();}
});
test('full pool: meta and combined routes, EOA signature replay and expiry',async()=>{
 const s=await setup();try{await s.grant();const req=s.request();const sig=await s.sign('LoanRequest',req);
 await s.call(s.pool,'requestLoanMeta',[req,sig]);await s.call(s.pool,'requestLoanMeta',[req,sig],0,'reverted');
 const expired={...s.request(unit,1n),deadline:1n};await s.call(s.pool,'requestLoanMeta',[expired,await s.sign('LoanRequest',expired)],0,'reverted');
 const combined={...s.request(5n*unit,1n),to:s.borrower.address,repaymentPeriod:604800n,maxAprBps:0n};
 await s.call(s.pool,'borrowAndDisburseMeta',[combined,await s.sign('BorrowAndDisburse',combined)]);
 assert.equal(await s.read(s.budget,'totalUsed'),10n*unit);assert.equal(await s.read(s.token,'balanceOf',[s.borrower.address]),5n*unit);
 }finally{await s.p.disconnect();}
});
test('full pool: failed pool check rolls back consumption and signature nonce',async()=>{
 const s=await setup();try{await s.grant();const req=s.request(11n*unit);await s.call(s.pool,'requestLoanMeta',[req,await s.sign('LoanRequest',req)],0,'reverted');
 assert.equal(await s.read(s.budget,'totalUsed'),0n);assert.equal(await s.read(s.pool,'nonces',[s.borrower.address]),0n);
 await s.call(s.pool,'requestLoan',[11n*unit],'borrower','reverted');assert.equal(await s.read(s.budget,'totalUsed'),0n);
 }finally{await s.p.disconnect();}
});
test('full pool: stop/revoke deny new loans but keep requested disbursement and repayment',async()=>{
 const s=await setup();try{await s.grant();await s.call(s.pool,'requestLoan',[5n*unit],'borrower');await s.call(s.budget,'revoke',[s.borrower.address]);await s.call(s.budget,'stop');
 await s.call(s.pool,'requestLoan',[unit],'borrower','reverted');await s.call(s.pool,'disburseLoan',[1n]);
 await s.call(s.token,'approve',[s.pool.address,5n*unit],'borrower');const repay={borrower:s.borrower.address,loanId:1n,amount:5n*unit,nonce:0n,deadline:s.deadline};await s.call(s.pool,'repayLoanMeta',[repay,await s.sign('RepayRequest',repay),{value:0n,deadline:0n,v:0,r:identity(0),s:identity(0)}]);assert.equal(await s.read(s.budget,'totalUsed'),5n*unit);
 }finally{await s.p.disconnect();}
});
test('full pool: ERC1271 wallet sees pool caller; wrong caller policy rejected',async()=>{
 const s=await setup();try{const correct=await s.deploy(m.contracts['Mock.sol'].CallerWallet,[s.pool.address]);const wrong=await s.deploy(m.contracts['Mock.sol'].CallerWallet,[s.budget.address]);
 await s.grant(correct.address,2,2);await s.grant(wrong.address,3,3);
 await s.call(s.pool,'requestLoanMeta',[{borrower:correct.address,amount:unit,nonce:0n,deadline:s.deadline},'0x']);
 await s.call(s.pool,'requestLoanMeta',[{borrower:wrong.address,amount:unit,nonce:0n,deadline:s.deadline},'0x'],0,'reverted');assert.equal(await s.read(s.budget,'totalUsed'),unit);
 }finally{await s.p.disconnect();}
});

test('full pool: combined transfer failure atomically restores budget loan and nonce',async()=>{
 const s=await setup();try{await s.grant();const req={...s.request(),to:s.borrower.address,repaymentPeriod:604800n,maxAprBps:0n};const sig=await s.sign('BorrowAndDisburse',req);
 await s.call(s.token,'setFailTransfers',[true]);await s.call(s.pool,'borrowAndDisburseMeta',[req,sig],0,'reverted');
 assert.equal(await s.read(s.budget,'totalUsed'),0n);assert.equal(await s.read(s.pool,'nonces',[s.borrower.address]),0n);assert.equal((await s.read(s.pool,'getAllLoanIds')).length,0);
 await s.call(s.token,'setFailTransfers',[false]);await s.call(s.pool,'borrowAndDisburseMeta',[req,sig]);assert.equal(await s.read(s.budget,'totalUsed'),5n*unit);assert.equal((await s.read(s.pool,'getAllLoanIds')).length,1);
 }finally{await s.p.disconnect();}
});
test('full pool: invalid EOA signature and rebinding cannot bypass authority',async()=>{
 const s=await setup();try{await s.grant();await s.call(s.pool,'requestLoanMeta',[s.request(),'0x'],0,'reverted');
 await s.call(s.pool,'setOriginationBudget',[s.budget.address],0,'reverted');await s.call(s.pool,'setOriginationBudget',[s.budget.address],1,'reverted');
 assert.equal(await s.read(s.budget,'totalUsed'),0n);assert.equal(await s.read(s.pool,'nonces',[s.borrower.address]),0n);
 }finally{await s.p.disconnect();}
});
test('lifecycle: request, signed disbursement, partial direct and final signed repayment',async()=>{
 const s=await setup();try{await s.grant();await s.call(s.pool,'requestLoan',[5n*unit],'borrower');
 const d={borrower:s.borrower.address,loanId:1n,to:s.borrower.address,nonce:0n,deadline:s.deadline};const signature=await s.sign('DisburseRequest',d);
 await s.call(s.pool,'disburseLoanMeta',[d,signature]);await s.call(s.pool,'disburseLoanMeta',[d,signature],0,'reverted');
 await s.call(s.token,'approve',[s.pool.address,5n*unit],'borrower');await s.call(s.pool,'repayLoan',[1n,2n*unit],'borrower');
 assert.equal(await s.read(s.pool,'totalLentOut'),3n*unit);
 const r={borrower:s.borrower.address,loanId:1n,amount:0n,nonce:1n,deadline:s.deadline};
 await s.call(s.pool,'repayLoanMeta',[r,await s.sign('RepayRequest',r),{value:0n,deadline:0n,v:0,r:identity(0),s:identity(0)}]);
 assert.equal((await s.read(s.pool,'getLoanTerms',[1n]))[0],3);assert.equal(await s.read(s.pool,'totalLentOut'),0n);assert.equal(await s.read(s.pool,'nonces',[s.borrower.address]),2n);assert.equal(await s.read(s.budget,'totalUsed'),5n*unit);
 }finally{await s.p.disconnect();}
});
test('lifecycle: cancellation frees pool liquidity but never cumulative allowance',async()=>{
 const s=await setup();try{await s.grant();await s.call(s.pool,'requestLoan',[10n*unit],'borrower');await s.call(s.pool,'cancelLoan',[1n],'borrower');
 assert.equal(await s.read(s.pool,'reservedLiquidity'),0n);assert.equal((await s.read(s.pool,'getLoanTerms',[1n]))[0],5);await s.call(s.pool,'disburseLoan',[1n],0,'reverted');
 await s.call(s.pool,'requestLoan',[10n*unit],'borrower');await s.call(s.pool,'cancelLoan',[2n],'borrower');await s.call(s.pool,'requestLoan',[unit],'borrower','reverted');assert.equal(await s.read(s.budget,'totalUsed'),20n*unit);
 }finally{await s.p.disconnect();}
});
test('lifecycle: interest and fee cash allocation survive partial and full repayment',async()=>{
 const s=await setup();try{await s.grant();await s.call(s.pool,'setRiskPremium',[10000n]);await s.call(s.pool,'setProtocolFeeBps',[1000n]);
 await s.call(s.pool,'requestLoan',[10n*unit],'borrower');await s.call(s.pool,'disburseLoan',[1n]);await s.p.request({method:'evm_increaseTime',params:[259200]});await s.p.request({method:'evm_mine',params:[]});
 await s.call(s.token,'approve',[s.pool.address,20n*unit],'borrower');
 const cash=await s.read(s.token,'balanceOf',[s.pool.address]),lenderCash=await s.read(s.pool,'lenderCash'),lent=await s.read(s.pool,'totalLentOut');
 const before=await s.read(s.pool,'getLoan',[1n]),terms=await s.read(s.pool,'getLoanTerms',[1n]);
 const receipt=await s.call(s.pool,'repayLoan',[1n,unit],'borrower');const block=await s.pub.getBlock({blockNumber:receipt.blockNumber});
 const interest=((before[0]*before[3])/10000n)*(block.timestamp-terms[3])/(365n*86400n);
 const principal=unit-interest,fee=interest/10n;
 assert.ok(interest>0n&&interest<unit);
 const applied=receipt.logs.filter(l=>l.address.toLowerCase()===s.pool.address.toLowerCase()).map(l=>decodeEventLog({abi:s.pool.abi,data:l.data,topics:l.topics})).find(e=>e.eventName==='RepaymentApplied');
 assert.ok(applied);assert.deepEqual(Object.values(applied.args),[1n,interest,principal,fee]);
 assert.equal(await s.read(s.pool,'totalLentOut'),lent-principal);assert.equal(await s.read(s.pool,'lenderCash'),lenderCash+unit-fee);
 assert.equal(await s.read(s.token,'balanceOf',[s.pool.address]),cash+unit);assert.equal(await s.read(s.pool,'protocolFees'),fee);
 await s.call(s.token,'mint',[s.borrower.address,unit]);const r={borrower:s.borrower.address,loanId:1n,amount:0n,nonce:0n,deadline:s.deadline};await s.call(s.pool,'repayLoanMeta',[r,await s.sign('RepayRequest',r),{value:0n,deadline:0n,v:0,r:identity(0),s:identity(0)}]);
 assert.equal((await s.read(s.pool,'getLoanTerms',[1n]))[0],3);assert.equal(await s.read(s.pool,'totalLentOut'),0n);assert.equal(await s.read(s.budget,'totalUsed'),10n*unit);
 }finally{await s.p.disconnect();}
});
test('lifecycle: secured default consumes sponsor stake without recreating allowance',async()=>{
 const s=await setup();try{await s.grant();await s.call(s.pool,'requestLoan',[5n*unit],'borrower');await s.call(s.pool,'disburseLoan',[1n]);
 await s.call(s.pool,'markDefaulted',[1n],0,'reverted');await s.p.request({method:'evm_increaseTime',params:[61*86400]});await s.p.request({method:'evm_mine',params:[]});
 const assets=await s.read(s.pool,'totalAssets'),cash=await s.read(s.token,'balanceOf',[s.pool.address]);await s.call(s.pool,'markDefaulted',[1n]);
 assert.equal(await s.read(s.pool,'stakeOf',[s.addresses[0]]),95n*unit);assert.equal(await s.read(s.pool,'totalAssets'),assets);assert.equal(await s.read(s.token,'balanceOf',[s.pool.address]),cash);
 assert.equal((await s.read(s.pool,'getLoanTerms',[1n]))[0],4);await s.call(s.pool,'requestLoan',[unit],'borrower','reverted');await s.call(s.pool,'repayLoan',[1n,unit],'borrower','reverted');assert.equal(await s.read(s.budget,'totalUsed'),5n*unit);
 }finally{await s.p.disconnect();}
});
test('lifecycle: credit-only backing burns reputation capacity but leaves lender cash loss',async()=>{
 const s=await setup();try{await s.call(s.budget,'grant',[s.borrower.address,identity(1),identity(1),20n*unit,s.deadline]);await s.call(s.pool,'setScoreOverride',[s.addresses[1],unit]);await s.call(s.pool,'back',[s.borrower.address,10n*unit],1);
 await s.call(s.pool,'requestLoan',[5n*unit],'borrower');await s.call(s.pool,'disburseLoan',[1n]);await s.p.request({method:'evm_increaseTime',params:[61*86400]});await s.p.request({method:'evm_mine',params:[]});
 const assets=await s.read(s.pool,'totalAssets'),cash=await s.read(s.token,'balanceOf',[s.pool.address]);await s.call(s.pool,'markDefaulted',[1n]);
 assert.equal(await s.read(s.pool,'creditLoss',[s.addresses[1]]),5n*unit);assert.equal(await s.read(s.pool,'totalAssets'),assets-5n*unit);assert.equal(await s.read(s.token,'balanceOf',[s.pool.address]),cash);assert.equal(await s.read(s.budget,'totalUsed'),5n*unit);
 }finally{await s.p.disconnect();}
});
test('parity: below-cap lifecycle accounting matches unmodified canonical optimizer build',async()=>{
 async function scenario(baseline){const s=await setup({baseline});try{await s.grant();await s.call(s.pool,'requestLoan',[5n*unit],'borrower');
 const d={borrower:s.borrower.address,loanId:1n,to:s.borrower.address,nonce:0n,deadline:s.deadline};await s.call(s.pool,'disburseLoanMeta',[d,await s.sign('DisburseRequest',d)]);
 await s.call(s.token,'approve',[s.pool.address,5n*unit],'borrower');await s.call(s.pool,'repayLoan',[1n,2n*unit],'borrower');
 const r={borrower:s.borrower.address,loanId:1n,amount:0n,nonce:1n,deadline:s.deadline};await s.call(s.pool,'repayLoanMeta',[r,await s.sign('RepayRequest',r),{value:0n,deadline:0n,v:0,r:identity(0),s:identity(0)}]);
 await s.call(s.pool,'requestLoan',[3n*unit],'borrower');await s.call(s.pool,'cancelLoan',[2n],'borrower');await s.call(s.pool,'withdrawFunds',[100n*unit]);
 return {assets:await s.read(s.pool,'totalAssets'),cash:await s.read(s.pool,'lenderCash'),lent:await s.read(s.pool,'totalLentOut'),reserved:await s.read(s.pool,'reservedLiquidity'),stake:await s.read(s.pool,'stakeOf',[s.addresses[0]]),nonce:await s.read(s.pool,'nonces',[s.borrower.address]),balance:await s.read(s.token,'balanceOf',[s.borrower.address]),status1:(await s.read(s.pool,'getLoanTerms',[1n]))[0],status2:(await s.read(s.pool,'getLoanTerms',[2n]))[0]};
 }finally{await s.p.disconnect();}}
 assert.deepEqual(await scenario(false),await scenario(true));
});
