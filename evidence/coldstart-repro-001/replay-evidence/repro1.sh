export PATH=/root/work/anvil_alpine:$PATH
cd /root/work/run_fork
TB=/root/work/run_fork/tb_1791408601/scenarios/cold-start-three-communities
BN=47820167
date -u +start_%FT%TZ
git -C /root/work/run_fork/tb_1791408601 rev-parse HEAD
git -C /root/work/run_fork/tb_1791408601 show a5a4d951df7e18056dd870db16fd642331f0e8e8:scenarios/cold-start-three-communities/run.py | sha256sum
sha256sum $TB/run.py
anvil --host 127.0.0.1 --port 8561 --chain-id 31337 --fork-url https://sepolia.base.org --fork-block-number $BN --disable-min-priority-fee --silent > repro1_anvil.log 2>&1 &
echo $! > repro1_anvil.pid
sleep 15
F=http://127.0.0.1:8561
echo chain $(cast chain-id --rpc-url $F) block $(cast block-number --rpc-url $F) gasPrice $(cast rpc eth_gasPrice --rpc-url $F)
EV=/root/work/run_fork/repro1_evidence
rm -rf $EV
python3 $TB/run.py --rpc $F --fork-block $BN --fork-block-hash 0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078 --expected-code-hashes /root/work/run_fork/source-code-hashes.json --output $EV > repro1.out 2>&1
echo exit $?
tail -c 1500 repro1.out
kill $(cat repro1_anvil.pid)
sleep 1
date -u +stop_%FT%TZ
echo anvil_stopped
ls $EV
