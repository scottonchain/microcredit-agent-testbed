// Offline compiler. Arguments: canonical1812 pool source, interfaces directory, output.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {execFileSync}=require('node:child_process'),{createHash}=require('node:crypto'),solc=require('solc');
const [source,interfaces,outputFile]=process.argv.slice(2);
if(!source||!interfaces||!outputFile)throw Error('source, interfaces directory and output path required');
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'source.json'),'utf8'));
const hash=s=>createHash('sha256').update(s).digest('hex');
const original=fs.readFileSync(source);if(hash(original)!==manifest.source_sha256)throw Error('source hash mismatch');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'credit-budget-compile-'));
try{
 fs.writeFileSync(path.join(temp,'DecentralizedMicrocredit.sol'),original);
 execFileSync('patch',['-p1','--batch','--forward'],{cwd:temp,input:fs.readFileSync(path.join(__dirname,'canonical-origination.patch'))});
 const candidate=fs.readFileSync(path.join(temp,'DecentralizedMicrocredit.sol'),'utf8');
 if(hash(candidate)!==manifest.candidate_sha256)throw Error('candidate hash mismatch');
 const budget=fs.readFileSync(path.join(__dirname,'ScopedOriginationBudget.sol'),'utf8');
 const settings={optimizer:{enabled:true,runs:1},viaIR:true,evmVersion:'cancun',outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}};
 function compile(sources,config,imports){
  const out=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources,settings:config}),imports));
  for(const e of out.errors||[])console.log(e.severity+': '+e.formattedMessage);
  if((out.errors||[]).some(e=>e.severity==='error'))throw Error('compilation failed');return out.contracts;
 }
 const imports={import:p=>{
  try{return {contents:fs.readFileSync(p.startsWith('@')?require.resolve(p):path.join(interfaces,path.basename(p)),'utf8')}}catch(e){return {error:'missing import '+p}}
 }};
 const pool=compile({'DecentralizedMicrocredit.sol':{content:candidate}},settings,imports);
 const budgetOut=compile({'ScopedOriginationBudget.sol':{content:budget}},{...settings,viaIR:false,evmVersion:'shanghai'},imports);
 const poolBytes=pool['DecentralizedMicrocredit.sol'].DecentralizedMicrocredit.evm.deployedBytecode.object.length/2;
 fs.writeFileSync(outputFile,JSON.stringify(budgetOut));
 console.log(JSON.stringify({compiler:solc.version(),poolEVM:'cancun',budgetTestEVM:'shanghai',poolRuntimeBytes:poolBytes,poolWithinEIP170:poolBytes<=24576,installed:false}));
 if(poolBytes>24576)throw Error('candidate exceeds EIP170; deployment prohibited');
}finally{fs.rmSync(temp,{recursive:true,force:true});}
