#!/usr/bin/env bash
# Clean evidence rerun of PR28 frozen head 3efdb6f (Hermes fallback per Codex tb#15 6075306717). Local forks only, no public-chain tx.
set -uo pipefail
OFF=<FOUNDRY_1.8.4>
B=<WORK>/bin-clean
mkdir -p $B
ln -sf $OFF/forge $B/forge
ln -sf $OFF/cast $B/cast
ln -sf <ANVIL_DIR>/anvil $B/anvil
export PATH=$B:$PATH
W=<WORK>/clean-3efdb6f-r1
OUT=<WORK>/out-3efdb6f
cd $W
test "$(git rev-parse HEAD)" = 3efdb6f2ed93bfdd19e8fd7f0a379868ca2e81b3 || { echo "wrong head"; exit 2; }
if [ ! -e lib/openzeppelin-contracts/contracts ]; then cp -a <WORK>/ctr2028/lib/openzeppelin-contracts/. lib/openzeppelin-contracts/; fi
date -u +"START %FT%TZ"
forge --version; cast --version; anvil --version
scripts/candidate_evidence.sh $OUT
echo "EXIT $?"
date -u +"END %FT%TZ"
