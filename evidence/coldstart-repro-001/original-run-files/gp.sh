export PATH=/root/work/anvil_alpine:$PATH
cd /root/work/run_fork
anvil --host 127.0.0.1 --port 8548 --chain-id 31337 --fork-url https://sepolia.base.org --fork-block-number 47820167 --silent > a2.log 2>&1 &
echo $! > a2.pid
sleep 14
F=http://127.0.0.1:8548
echo gasPrice $(cast rpc eth_gasPrice --rpc-url $F)
echo prio $(cast rpc eth_maxPriorityFeePerGas --rpc-url $F)
echo block $(cast block latest --field baseFeePerGas --rpc-url $F)
kill $(cat a2.pid)
anvil --help | grep -i -E "gas-price|base-fee|fork-chain"
