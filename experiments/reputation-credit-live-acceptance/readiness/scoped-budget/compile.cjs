// Offline compiler. Arguments: canonical1812 pool source, interfaces directory, output, canonical OZ contracts directory.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {execFileSync}=require('node:child_process'),{createHash}=require('node:crypto'),solc=require('solc');
const [source,interfaces,outputFile,openzeppelinRoot]=process.argv.slice(2);
if(!source||!interfaces||!outputFile||!openzeppelinRoot)throw Error('source, interfaces, output and canonical OpenZeppelin contracts directory required');
const dependencyManifest=JSON.parse(fs.readFileSync(path.join(__dirname,'openzeppelin-files.json'),'utf8'));
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'source.json'),'utf8'));
const hash=s=>createHash('sha256').update(s).digest('hex');
if(hash(fs.readFileSync(path.join(__dirname,'openzeppelin-files.json')))!==manifest.openzeppelin_manifest_sha256)throw Error('dependency manifest hash mismatch');
if(hash(fs.readFileSync(path.join(__dirname,'compiler-settings.json')))!==manifest.settings_sha256)throw Error('settings hash mismatch');
if(!solc.version().startsWith('0.8.33+'))throw Error('pinned solc0.8.33 required');

if(hash(fs.readFileSync(path.join(interfaces,'IScoreProvider.sol')))!==manifest.interface_sha256)throw Error('interface hash mismatch');
const original=fs.readFileSync(source);if(hash(original)!==manifest.source_sha256)throw Error('source hash mismatch');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'credit-budget-compile-'));
try{
 fs.writeFileSync(path.join(temp,'DecentralizedMicrocredit.sol'),original);
 execFileSync('patch',['-p1','--batch','--forward'],{cwd:temp,input:fs.readFileSync(path.join(__dirname,'canonical-origination.patch'))});
 const candidate=fs.readFileSync(path.join(temp,'DecentralizedMicrocredit.sol'),'utf8');
 if(hash(candidate)!==manifest.candidate_sha256)throw Error('candidate hash mismatch');
 const budget=fs.readFileSync(path.join(__dirname,'ScopedOriginationBudget.sol'),'utf8');
 const settings={...JSON.parse(fs.readFileSync(path.join(__dirname,'compiler-settings.json'),'utf8')),outputSelection:{'*':{'*':['abi','evm.bytecode.object','evm.deployedBytecode.object']}}};
 function compile(sources,config,imports){
  const out=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources,settings:config}),imports));
  for(const e of out.errors||[])console.log(e.severity+': '+e.formattedMessage);
  if((out.errors||[]).some(e=>e.severity==='error'))throw Error('compilation failed');return out.contracts;
 }
 const imports={import:p=>{
  try{
   if(p.startsWith('@openzeppelin/contracts/')){
    const relative=p.slice('@openzeppelin/contracts/'.length);
    const contents=fs.readFileSync(path.join(openzeppelinRoot,relative),'utf8');
    if(!dependencyManifest.files[relative]||hash(contents)!==dependencyManifest.files[relative])throw Error('dependency hash mismatch '+relative);
    return {contents};
   }
   return {contents:fs.readFileSync(path.join(interfaces,path.basename(p)),'utf8')};
  }catch(e){return {error:e.message}}
 }};
 const pool=compile({'DecentralizedMicrocredit.sol':{content:candidate}},settings,imports);
 const baseline=compile({'DecentralizedMicrocredit.sol':{content:original.toString('utf8')}},{...settings,optimizer:{enabled:true,runs:200}},imports);
 const budgetOut=compile({'ScopedOriginationBudget.sol':{content:budget}},{...settings,viaIR:false,evmVersion:'shanghai'},imports);
 const poolBytes=pool['DecentralizedMicrocredit.sol'].DecentralizedMicrocredit.evm.deployedBytecode.object.length/2;
 fs.writeFileSync(outputFile,JSON.stringify({...pool,...budgetOut,'CanonicalBaseline.sol':baseline['DecentralizedMicrocredit.sol']}));
 console.log(JSON.stringify({compiler:solc.version(),poolEVM:settings.evmVersion,budgetTestEVM:'shanghai',poolRuntimeBytes:poolBytes,baselineRuntimeBytes:baseline['DecentralizedMicrocredit.sol'].DecentralizedMicrocredit.evm.deployedBytecode.object.length/2,poolWithinEIP170:poolBytes<=24576,installed:false}));
 if(poolBytes>24576)throw Error('candidate exceeds EIP170; deployment prohibited');
}finally{fs.rmSync(temp,{recursive:true,force:true});}
