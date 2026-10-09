#!/usr/bin/env bash
# Rerun of the rehearsal tail of scripts/candidate_evidence.sh (unchanged logic) with official cast 1.8.4 + static anvil.
set -euo pipefail
OFF=<FOUNDRY_1.8.4>
mkdir -p <WORK>/bin
ln -sf <WORK>/shim/cast <WORK>/bin/cast
ln -sf $OFF/forge <WORK>/bin/forge
ln -sf <ANVIL_DIR>/anvil <WORK>/bin/anvil
export PATH=<WORK>/bin:$PATH
cd <CHECKOUT>
git checkout -q -- packages scripts docs 2>/dev/null || true
test -z "$(git status --porcelain -- packages/foundry/contracts scripts docs/*.md CLAUDE.md)" || { echo "tree is not clean"; git status --short; exit 1; }
OUT=<WORK>/out-2986e23
RPC=https://sepolia.base.org
ORACLE=0x000000000000000000000000000000000000dEaD
SENDER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
RC="$OUT/logs/rc2.txt"; : > "$RC"
run() { local name=$1 log=$2 rc=0; shift 2; "$@" > "$OUT/logs/$log" 2>&1 || rc=$?; echo "$name $rc" >> "$RC"; }
PORT=8546; FORKDIR=$(mktemp -d); PIDFILE="$FORKDIR/anvil.pid"; FORKLOG="$FORKDIR/anvil.log"
trap 'python3 scripts/candidate_fork.py stop --pidfile "$PIDFILE" --port $PORT || true; rm -rf "$FORKDIR"' EXIT
read -r BLOCK BLOCKHASH < <(python3 scripts/candidate_fork.py block --rpc $RPC)
echo "$BLOCK $BLOCKHASH" > "$OUT/logs/fork-block.txt"
cast --version > "$OUT/logs/cast-rehearsal-version.txt" 2>&1; anvil --version >> "$OUT/logs/cast-rehearsal-version.txt" 2>&1
fresh_fork() {
  python3 scripts/candidate_fork.py stop --pidfile "$PIDFILE" --port $PORT
  python3 scripts/candidate_fork.py start --rpc $RPC --block "$BLOCK" --port $PORT --log "$FORKLOG" --pidfile "$PIDFILE" > /dev/null
  local o line; o=$(cd packages/foundry && BOOTSTRAP_ORACLE=$ORACLE forge script script/DeployBootstrapCandidate.s.sol --rpc-url http://127.0.0.1:$PORT --broadcast --unlocked --sender $SENDER 2>&1) || { echo "$o" >&2; exit 1; }
  rm -rf packages/foundry/broadcast/DeployBootstrapCandidate.s.sol
  line=$(echo "$o" | awk '/candidate pool/{p=$NF} /candidate lens/{l=$NF} /candidate bootstrap order router/{r=$NF} END{print p, l, r}')
  [[ $(wc -w <<<"$line") -eq 3 ]] || { echo "deploy did not print three addresses: $line" >&2; exit 1; }
  read -r P L R <<<"$line"
}
fresh_fork
python3 scripts/verify_candidate_deployment.py --rpc http://127.0.0.1:$PORT --pool "$P" --lens "$L" --router "$R" --json > "$OUT/logs/verifier.json"
run rehearsal-normal rehearsal-normal.txt python3 scripts/candidate_rehearsal.py run --rpc http://127.0.0.1:$PORT --pool "$P" --router "$R"
fresh_fork
run rehearsal-with-default rehearsal-with-default.txt python3 scripts/candidate_rehearsal.py run --rpc http://127.0.0.1:$PORT --pool "$P" --router "$R" --with-default
python3 scripts/candidate_fork.py stop --pidfile "$PIDFILE" --port $PORT
echo "$P $L $R" > "$OUT/logs/fork-addrs-last.txt"
cat "$RC"
