#!/bin/bash
# build a8a2a57 / runner a8a2a57 (unmodified). Never prints keys.
export PATH=/root/.hermes/tools/node-26.7.0-linux-x64/bin:/root/.foundry/versions/foundry-rs/foundry/v1.8.4:$PATH
cd /root/work/run_bw2/mc
mkdir -p /root/work/run_bw2/ba8
export POOL=0x73872B8fB7F1771C67911f03edc75aBdc9514973 USDC=0x036CbD53842c5426634e7929541eC2318f3dCF7e USDC_IS_MOCK=0
export TESTNET_PRIVATE_KEY=$(tr -d '[:space:]' < /root/.hermes/secrets/usdc001-walkthrough-borrower.key)
export CHROMIUM_PATH=/root/.hermes/tools/chromium-1208/chrome-linux64/chrome CHROMIUM_NO_SANDBOX=1
export LEND_AMOUNT=2 BORROW_AMOUNT=1 SEND_SPACING_MS=8000
B=0x108450c748EEF7AeF23e64739bC508f56E596247; P=0x73872B8fB7F1771C67911f03edc75aBdc9514973
pend() { for id in $(cast call $P "getBorrowerLoanIds(address)(uint256[])" $B -r https://sepolia.base.org | tr -d '[],'); do
  st=$(cast call $P "getLoanTerms(uint256)(uint8,uint256,uint256,uint256,uint256)" $id -r https://sepolia.base.org | head -1 | awk '{print $1}'); [ "$st" = "1" ] && return 0; done; return 1; }
run() { TAG=$1; shift; export OUT=/root/work/run_bw2/ba8/$TAG.json
  echo "== $TAG $* $(date -u +%T)"; node scripts/demo/testnet-walkthrough.mjs "$@" > /root/work/run_bw2/ba8/$TAG.out 2>&1; echo "exit $?"; sleep 8; }
for i in 1 2 3; do
  if pend; then run run-$i-resume --resume-pending --skip-lend --skip-withdraw; fi
  run run-$i-reject-disburse --reject-disburse
done
echo ALLDONE
