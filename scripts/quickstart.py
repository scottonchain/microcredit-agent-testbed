#!/usr/bin/env python3
"""Small, explicit command-line client for the recorded Base Sepolia pool."""
import argparse
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.deployment import Cast, CastError, UINT256_MAX, address, as_int, format_units, load_deployment, token_units

ERRORS = (
    "NoCredit", "BorrowLimitExceeded", "InsufficientCredit", "BorrowerInDefault", "UtilisationCapExceeded",
    "InsufficientLiquidity", "InsufficientBalance", "SelfBacking", "TooManyBackers", "BackingTooSmall",
    "BackingInUse", "StakeCommitted", "InsufficientStake", "LendingPaused", "ZeroAmount", "InvalidTerm", "NothingToRepay",
)


def parser():
    p = argparse.ArgumentParser(description=__doc__, epilog=(
        "Amounts are USDC with up to 6 decimal places. ACCOUNT or --account permits read-only commands without a key. "
        "Writes require PRIVATE_KEY for a throwaway testnet account. RPC, POOL, LENS, SCORES and USDC override deployments/current.json."
    ))
    p.add_argument("--account", type=address, help="account for status or try-borrow (or set ACCOUNT)")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("status", help="balances, credit and pool state")
    for command in ("lend", "stake", "borrow", "try-borrow", "mint"):
        command_parser = sub.add_parser(command, help="test USDC faucet only" if command == "mint" else None)
        command_parser.add_argument("amount", type=token_units)
    withdraw = sub.add_parser("withdraw")
    withdraw.add_argument("amount", type=lambda value: UINT256_MAX if value == "all" else token_units(value))
    back = sub.add_parser("back")
    back.add_argument("borrower", type=address)
    back.add_argument("amount", type=lambda value: token_units(value, allow_zero=True))
    repay = sub.add_parser("repay")
    repay.add_argument("loan_id", type=loan_id)
    return p


def loan_id(value):
    if not re.fullmatch(r"[0-9]+", value) or not 0 < int(value) <= UINT256_MAX:
        raise argparse.ArgumentTypeError("loan id must be a positive uint256")
    return int(value)


def requested_loan(receipt, pool, borrower, event_topic):
    """Use this receipt's event, never another concurrent loan's array position."""
    ids = []
    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if (log.get("address", "").lower() == pool.lower() and len(topics) == 3
                and topics[0].lower() == event_topic.lower()
                and topics[1][-40:].lower() == borrower[2:].lower()):
            ids.append(as_int(topics[2]))
    if len(ids) != 1:
        raise CastError("request was mined but its LoanRequested event is ambiguous; inspect its receipt before disbursing")
    return ids[0]


def status(client, d, account):
    block = client.block()
    number = as_int(block["number"])
    def call(contract, signature, *args):
        return client.call(contract, signature, *args, block=number)
    def num(contract, signature, *args):
        return as_int(call(contract, signature, *args)[0])
    pool, lens, token = d["pool"], d["lens"], d["token"]["address"]
    limit, available = call(pool, "getBorrowLimit(address)(uint256,uint256)", account)
    credit, stake = call(pool, "getFreeCredit(address)(uint256,uint256)", account)
    print(f"account          {account}\nblock            {number} ({block['hash']})")
    print(f"USDC balance     {format_units(num(token, 'balanceOf(address)(uint256)', account))}")
    print(f"issued+earned    {format_units(num(pool, 'grantedCredit(address)(uint256)', account))}")
    print(f"stake            {format_units(num(pool, 'stakeOf(address)(uint256)', account))}")
    print(f"free to back     {format_units(credit)} credit + {format_units(stake)} stake")
    print(f"borrow limit     {format_units(limit)}, available {format_units(available)}")
    print(f"lender balance   {format_units(num(pool, 'lenderBalance(address)(uint256)', account))}, "
          f"withdrawable now {format_units(num(lens, 'maxWithdrawable(address)(uint256)', account))}")
    print(f"loans            {call(pool, 'getBorrowerLoanIds(address)(uint256[])', account)[0]}")
    print(f"pool             assets {format_units(num(pool, 'totalAssets()(uint256)'))}, "
          f"utilisation {num(lens, 'getUtilisation()(uint256)')} bps, "
          f"share price {format_units(num(lens, 'sharePrice()(uint256)'), 4)}, "
          f"APR {num(pool, 'getLoanRate()(uint256)')} bps")
    if client.block(number)["hash"].lower() != block["hash"].lower():
        raise CastError("block changed during status collection; discard this report and read again")


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    command = args.command or "status"
    try:
        d = load_deployment()
        client = Cast(d)
        readonly = command in ("status", "try-borrow")
        account = args.account or os.environ.get("ACCOUNT")
        private_key = os.environ.get("PRIVATE_KEY")
        if not readonly and not private_key:
            p.error("writes require PRIVATE_KEY for a throwaway testnet account")
        if not account or not readonly:
            if not private_key:
                p.error("set ACCOUNT or --account for a read-only command, or PRIVATE_KEY for a throwaway testnet account")
            signer = address(client.run("wallet", "address", "--private-key", private_key))
            if account and address(account).lower() != signer.lower():
                p.error("ACCOUNT does not match the signing key")
            account = signer
        account = address(account)
        if command == "mint" and os.environ.get("ALLOW_MINT") != "1":
            p.error("Circle test USDC comes from https://faucet.circle.com; ALLOW_MINT=1 is only for an explicitly configured mock token")
        client.check_chain()
        client.check_wiring()
        pool, lens, token = d["pool"], d["lens"], d["token"]["address"]
        if command == "status":
            status(client, d, account)
        elif command == "try-borrow":
            try:
                result = client.call(pool, "requestLoan(uint256)(uint256)", args.amount, account=account)
                print(f"would succeed (loan id {result[0]})")
            except CastError as error:
                message = str(error)
                for name in ERRORS:
                    if client.run("sig", f"{name}()").lower() in message.lower():
                        print(f"reverts with {name}")
                        return 1
                raise
        else:
            def send(contract, signature, *values):
                return client.send(private_key, contract, signature, *values)
            if command in ("lend", "stake"):
                send(token, "approve(address,uint256)", pool, args.amount)
                send(pool, "depositFunds(uint256)" if command == "lend" else "stake(uint256)", args.amount)
            elif command == "withdraw":
                send(pool, "withdrawFunds(uint256)", args.amount)
            elif command == "back":
                send(pool, "back(address,uint256)", args.borrower, args.amount)
            elif command == "mint":
                send(token, "mint(address,uint256)", account, args.amount)
            elif command == "borrow":
                topic = client.run("keccak", "LoanRequested(address,uint256,uint256,uint256)")
                receipt = send(pool, "requestLoan(uint256)", args.amount)
                ident = requested_loan(receipt, pool, account, topic)
                send(pool, "disburseLoan(uint256)", ident)
                print(f"loan id {ident}")
            elif command == "repay":
                owed = client.num(lens, "getOutstandingRoundedToCent(uint256)(uint256)", args.loan_id)
                if owed == 0:
                    raise CastError("loan has no outstanding amount")
                send(token, "approve(address,uint256)", pool, owed)
                send(pool, "repayLoan(uint256,uint256)", args.loan_id, owed)
                print(f"repaid {format_units(owed)}")
        return 0
    except (CastError, ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
