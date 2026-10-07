export PATH=/root/work/anvil_alpine:$PATH
cd /root/work/run_fork
TB=/root/work/run_fork/tb_1791408601/scenarios/cold-start-three-communities
BN=47820167
anvil --host 127.0.0.1 --port 8550 --chain-id 31337 --fork-url https://sepolia.base.org --fork-block-number $BN --disable-min-priority-fee --silent > anvil4.log 2>&1 &
echo $! > anvil4.pid
sleep 15
F=http://127.0.0.1:8550
echo chain $(cast chain-id --rpc-url $F) block $(cast block-number --rpc-url $F) gasPrice $(cast rpc eth_gasPrice --rpc-url $F)
EV=/root/work/run_fork/evidence4_$(date +%s)
echo $EV > evdir4.txt
python3 $TB/run.py --rpc $F --fork-block $BN --fork-block-hash 0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078 --expected-code-hashes /root/work/run_fork/source-code-hashes.json --output $EV > run4.out 2>&1
echo exit $?
tail -c 4000 run4.out
kill $(cat anvil4.pid)
sleep 1
echo anvil_stopped
ls $EV
