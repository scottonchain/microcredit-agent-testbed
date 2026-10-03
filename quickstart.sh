#!/usr/bin/env bash
# Quickstart for the microcredit pool on Base Sepolia, using Foundry's `cast`
# (install: https://book.getfoundry.sh/getting-started/installation).
#
#   export PRIVATE_KEY=0x...        # a throwaway testnet key with a little Base Sepolia ETH
#   ./quickstart.sh status          # your balances, credit and the pool's state
#   ./quickstart.sh mint 1000       # mint test USDC (amounts are whole USDC)
#   ./quickstart.sh lend 500        # deposit into the pool
#   ./quickstart.sh withdraw all    # withdraw (an amount, or "all")
#   ./quickstart.sh stake 25        # lock test USDC as your own credit
#   ./quickstart.sh back 0xBorrower 10   # commit 10 of your credit to a borrower (0 removes it)
#   ./quickstart.sh try-borrow 5    # simulate a loan without sending: shows why it would fail
#   ./quickstart.sh borrow 5        # request and disburse a 30-day loan
#   ./quickstart.sh repay <loanId>  # repay a loan in full
#
# Override the deployment with RPC, POOL, LENS, USDC. Testnet only: never use a key that holds real funds.
set -euo pipefail

RPC=${RPC:-https://sepolia.base.org}
POOL=${POOL:-0xe3264D64cEF7C7675a548524D883b597e7894169}
LENS=${LENS:-0x01C0586B3Cef50b427411c1278Be25605e8329Dc}
USDC=${USDC:-0xff9503E3aEc502765C6CfC75fF3D75Db7e863640}

: "${PRIVATE_KEY:?set PRIVATE_KEY to a throwaway testnet key}"
ME=$(cast wallet address --private-key "$PRIVATE_KEY")

usdc() { echo $(($1 * 1000000)); }
fmt() { awk -v v="$1" 'BEGIN { printf "%.2f", v / 1e6 }'; }
call() { cast call --rpc-url "$RPC" "$@" | awk '{ print $1 }'; }
send() { cast send --rpc-url "$RPC" --private-key "$PRIVATE_KEY" "$@" | grep -E '^(status|transactionHash) '; }

# Custom errors the pool reverts with, by selector (see contractErrors.ts in the contract repo).
ERRORS="NoCredit() BorrowLimitExceeded() InsufficientCredit() BorrowerInDefault() UtilisationCapExceeded()
InsufficientLiquidity() InsufficientBalance() SelfBacking() TooManyBackers() BackingTooSmall() BackingInUse()
StakeCommitted() InsufficientStake() LendingPaused() ZeroAmount() InvalidTerm() NothingToRepay()"
explain() {
  local data="$1"
  for e in $ERRORS; do
    if [[ "$data" == *"$(cast sig "$e" | cut -c3-)"* ]]; then echo "reverts with ${e%()}"; return; fi
  done
  echo "reverts: $data"
}

case "${1:-status}" in
  status)
    mapfile -t lim < <(call "$POOL" "getBorrowLimit(address)(uint256,uint256)" "$ME")
    mapfile -t free < <(call "$POOL" "getFreeCredit(address)(uint256,uint256)" "$ME")
    echo "account          $ME"
    echo "USDC balance     $(fmt "$(call "$USDC" "balanceOf(address)(uint256)" "$ME")")"
    echo "issued+earned    $(fmt "$(call "$POOL" "grantedCredit(address)(uint256)" "$ME")")   (grantedCredit: issued line + dues - losses)"
    echo "stake            $(fmt "$(call "$POOL" "stakeOf(address)(uint256)" "$ME")")"
    echo "free to back     $(fmt "${free[0]}") credit + $(fmt "${free[1]}") stake"
    echo "borrow limit     $(fmt "${lim[0]}"), available $(fmt "${lim[1]}")"
    echo "lender balance   $(fmt "$(call "$POOL" "lenderBalance(address)(uint256)" "$ME")"), withdrawable now $(fmt "$(call "$LENS" "maxWithdrawable(address)(uint256)" "$ME")")"
    echo "loans            $(cast call --rpc-url "$RPC" "$POOL" "getBorrowerLoanIds(address)(uint256[])" "$ME")"
    echo "pool             assets $(fmt "$(call "$POOL" "totalAssets()(uint256)")"), utilisation $(call "$LENS" "getUtilisation()(uint256)") bps, share price $(fmt "$(call "$LENS" "sharePrice()(uint256)")"), APR $(call "$POOL" "getLoanRate()(uint256)") bps"
    ;;
  mint)
    send "$USDC" "mint(address,uint256)" "$ME" "$(usdc "$2")" ;;
  lend)
    send "$USDC" "approve(address,uint256)" "$POOL" "$(usdc "$2")"
    send "$POOL" "depositFunds(uint256)" "$(usdc "$2")" ;;
  withdraw)
    amount=$([[ "$2" == all ]] && echo 115792089237316195423570985008687907853269984665640564039457584007913129639935 || usdc "$2")
    send "$POOL" "withdrawFunds(uint256)" "$amount" ;;
  stake)
    send "$USDC" "approve(address,uint256)" "$POOL" "$(usdc "$2")"
    send "$POOL" "stake(uint256)" "$(usdc "$2")" ;;
  back)
    send "$POOL" "back(address,uint256)" "$2" "$(usdc "$3")" ;;
  try-borrow)
    if out=$(cast call --rpc-url "$RPC" --from "$ME" "$POOL" "requestLoan(uint256)(uint256)" "$(usdc "$2")" 2>&1); then
      echo "would succeed (loan id $out)"
    else
      explain "$(echo "$out" | grep -oE '0x[0-9a-fA-F]{8,}' | head -1)"
    fi ;;
  borrow)
    send "$POOL" "requestLoan(uint256)" "$(usdc "$2")"
    id=$(cast call --rpc-url "$RPC" "$POOL" "getBorrowerLoanIds(address)(uint256[])" "$ME" | tr -d '[] ' | tr ',' '\n' | tail -1)
    send "$POOL" "disburseLoan(uint256)" "$id"
    echo "loan id $id" ;;
  repay)
    owed=$(call "$LENS" "getOutstandingRoundedToCent(uint256)(uint256)" "$2")
    send "$USDC" "approve(address,uint256)" "$POOL" "$owed"
    send "$POOL" "repayLoan(uint256,uint256)" "$2" "$owed"
    echo "repaid $(fmt "$owed")" ;;
  *)
    sed -n '2,17p' "$0"; exit 1 ;;
esac
