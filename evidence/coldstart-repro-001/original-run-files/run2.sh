export PATH=/root/work/anvil_alpine:$PATH
cd /root/work/run_fork
TB=/root/work/run_fork/tb_1791408601/scenarios/cold-start-three-communities
BN=47820167
rm -f anvil.log
anvil --host 127.0.0.1 --port 8547 --chain-id 31337 --fork-url https://sepolia.base.org --fork-block-number $BN --silent > anvil.log 2>&1 &
echo $! > anvil.pid
sleep 15
echo chain $(cast chain-id --rpc-url http://127.0.0.1:8547) block $(cast block-number --rpc-url http://127.0.0.1:8547)
EV=/root/work/run_fork/evidence_$(date +%s)
echo $EV > evdir.txt
python3 $TB/run.py --rpc http://127.0.0.1:8547 --fork-block $BN --fork-block-hash 0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078 --expected-code-hashes /root/work/run_fork/source-code-hashes.json --output $EV > run.out 2>&1
echo exit $?
tail -c 3000 run.out
kill $(cat anvil.pid)
sleep 1
echo anvil_stopped
