// Pinned, in-process Cancun test provider. No listening socket or fork URL.
const {createHardhatNetworkProvider}=require('hardhat/internal/hardhat-network/provider/provider');
const {generatePrivateKey}=require('viem/accounts');
module.exports=async function localEVM(){
 const provider=await createHardhatNetworkProvider({
  hardfork:'cancun',chainId:31337,networkId:31337,blockGasLimit:30000000,minGasPrice:0n,
  automine:true,intervalMining:0,mempoolOrder:'fifo',chains:new Map(),
  genesisAccounts:Array.from({length:5},()=>({privateKey:generatePrivateKey(),balance:'100000000000000000000'})),
  allowUnlimitedContractSize:false,throwOnTransactionFailures:false,throwOnCallFailures:true,
  allowBlocksWithSameTimestamp:true,enableTransientStorage:true,enableRip7212:false,
  initialDate:new Date('2026-01-01T00:00:00Z')
 },{enabled:false});
 return {
  request:({method,params})=>provider.request({method:method==='evm_setAccountBalance'?'hardhat_setBalance':method,params}),
  disconnect:()=>provider.request({method:'hardhat_reset',params:[]})
 };
};
