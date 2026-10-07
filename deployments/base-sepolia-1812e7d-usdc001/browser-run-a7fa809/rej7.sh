#!/bin/bash
export PATH=/root/.hermes/tools/node-26.7.0-linux-x64/bin:/root/.foundry/versions/foundry-rs/foundry/v1.8.4:$PATH
cd /root/work/run_bw2/mc
export POOL=0x73872B8fB7F1771C67911f03edc75aBdc9514973 USDC=0x036CbD53842c5426634e7929541eC2318f3dCF7e USDC_IS_MOCK=0
export TESTNET_PRIVATE_KEY=$(tr -d '[:space:]' < /root/.hermes/secrets/usdc001-walkthrough-borrower.key)
export CHROMIUM_PATH=/root/.hermes/tools/chromium-1208/chrome-linux64/chrome CHROMIUM_NO_SANDBOX=1
export LEND_AMOUNT=2 BORROW_AMOUNT=1 SEND_SPACING_MS=8000
export OUT=/root/work/run_bw2/ba7/run-6-reject-disburse.json
node scripts/demo/testnet-walkthrough.mjs --reject-disburse > /root/work/run_bw2/ba7/run-6-reject-disburse.out 2>&1
echo exit $?
