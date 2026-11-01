#!/usr/bin/env bash
# Start a clean local fork of live Base Sepolia on :8545 (kills any previous one started this way).
cd "$(dirname "$0")"
for p in $(ps -eo pid=,args= | grep -E "hardhat( node|.*cli.js node)" | grep -v -E "grep|bash -c|fork-up" | awk '{print $1}'); do kill "$p" 2>/dev/null; done
sleep 2
nohup npx hardhat node --port 8545 > /tmp/claude-0/hh-node.log 2>&1 &
for i in $(seq 1 40); do
  if curl -s -m 2 -X POST -H 'content-type: application/json' --data '{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}' localhost:8545 | grep -q 0x14a34; then echo "fork up"; exit 0; fi
  sleep 1
done
echo "fork failed"; tail -5 /tmp/claude-0/hh-node.log; exit 1
