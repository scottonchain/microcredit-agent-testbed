#!/usr/bin/env python3
"""Time-advance extension of run.py: failed-job default path (t2). Interest-bearing repayment is NOT implemented.

Local Anvil fork only (same guards as run.py: loopback RPC, chain 31337, pinned block, pinned code
fingerprints). Adds ONLY clock methods to the RPC allowlist: anvil_setNextBlockTimestamp, evm_mine.
No evm_setStorageAt / anvil_setBalance / anvil_setCode, no keys, no upstream calls.
All results are labelled mode=fork, time=synthetic. The final fork state is NOT restored:
discard the node after each scenario and start a fresh fork for the next one.

  python3 run_timewarp.py --self-test
  python3 run_timewarp.py --rpc http://127.0.0.1:8547 --fork-block N --expected-code-hashes f.json \
        --scenario t2 --output NEW_DIR
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("coldstart_base", HERE / "run.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

DAY = 86_400
CLOCK_METHODS = {"anvil_setNextBlockTimestamp", "evm_mine"}
FORBIDDEN = {"anvil_setBalance", "anvil_setStorageAt", "anvil_setCode", "anvil_setNonce",
             "evm_setAccountBalance", "evm_setAccountCode", "evm_setAccountStorageAt", "hardhat_setBalance"}
OUT_SIGS = {"impairLoan(uint256)", "markDefaulted(uint256)", "repayLoan(uint256,uint256)", "stake(uint256)"}


class ClockRPC(base.RPC):
    ALLOWED = set(base.RPC.ALLOWED) | CLOCK_METHODS


class TimeRunner(base.Runner):
    def __init__(self, args, journal):
        super().__init__(args, journal)
        self.rpc = ClockRPC(args.rpc)
        self.clock_log = []

    # ---- clock -------------------------------------------------------------------------
    def warp(self, seconds, label):
        base.require(seconds > 0, "Clock moves forward only")
        before = int(self.rpc.call("eth_getBlockByNumber", ["latest", False])["timestamp"], 16)
        self.rpc.call("anvil_setNextBlockTimestamp", [before + seconds])
        self.rpc.call("evm_mine")
        after = int(self.rpc.call("eth_getBlockByNumber", ["latest", False])["timestamp"], 16)
        base.require(after - before == seconds, "Clock advance mismatch: %d != %d" % (after - before, seconds))
        entry = {"label": label, "seconds": seconds, "before": before, "after": after, "time": "synthetic"}
        self.clock_log.append(entry)
        self.journal.append("synthetic_time_advance", entry)
        return after

    # ---- one pool transaction outside run.py's allowlist (permissionless calls) ----------
    def send(self, sender, signature, values, label):
        base.require(signature in OUT_SIGS and sender in self.impersonated, "send() not permitted: " + signature)
        self.rpc.guard()
        tx = {"from": sender, "to": base.POOL, "value": "0x0", "data": base.calldata(signature, *values)}
        self.rpc.call("eth_call", [tx, "latest"])
        gas = int(self.rpc.call("eth_estimateGas", [tx]), 16) * 120 // 100 + 1
        price = int(self.rpc.call("eth_gasPrice"), 16)
        base.require(0 < price <= 1_000_000_000 and gas <= 1_500_000, "Gas guard")
        tx.update({"gas": hex(gas), "gasPrice": hex(price)})
        self.journal.append("transaction_intent", {"label": label, "transaction": tx})
        h = self.rpc.call("eth_sendTransaction", [tx])
        receipt = self.rpc.call("eth_getTransactionReceipt", [h])
        base.require(receipt is not None and int(receipt["status"], 16) == 1, "Failed/missing receipt: " + label)
        self.journal.append("transaction_receipt", {"label": label, "hash": h, "receipt": receipt})
        self.tx_count += 1
        return receipt

    def pool_state(self, loan_id, funder, borrower):
        u = self.uint
        keys = ["totalAssets", "totalShares", "lenderCash", "totalLentOut", "totalImpaired",
                "firstLossReserve", "protocolFees", "reservedLiquidity"]
        s = {k: u(base.POOL, k + "()") for k in keys}
        s["token_balance"] = u(base.USDC, "balanceOf(address)", base.POOL)
        s["provider_isFresh"] = u(base.PROVIDER, "isFresh()")
        s["funder_lenderBalance"] = u(base.POOL, "lenderBalance(address)", funder)
        s["funder_creditLoss"] = u(base.POOL, "creditLoss(address)", funder)
        s["funder_stakeOf"] = u(base.POOL, "stakeOf(address)", funder)
        s["funder_stakeCommitted"] = u(base.POOL, "stakeCommitted(address)", funder)
        s["funder_creditCommitted"] = u(base.POOL, "creditCommitted(address)", funder)
        s["funder_grantedCredit"] = u(base.POOL, "grantedCredit(address)", funder)
        s["funder_creditScore"] = u(base.POOL, "getCreditScore(address)", funder)
        s["totalStaked"] = u(base.POOL, "totalStaked()")
        s["backing"] = base.decode_words(self.view(base.POOL, "getBacking(address,address)", funder, borrower))
        s["borrower_defaultedLoans"] = u(base.POOL, "defaultedLoans(address)", borrower)
        s["borrower_completedLoans"] = u(base.POOL, "completedLoans(address)", borrower)
        s["outstanding"] = u(base.POOL, "getCurrentOutstandingAmount(uint256)", loan_id)
        s["loan_terms"] = base.decode_words(self.view(base.POOL, "getLoanTerms(uint256)", loan_id))
        s["block_timestamp"] = int(self.block()["timestamp"], 16)
        return s

    # ---- scenarios ---------------------------------------------------------------------
    def setup_staked(self, i, borrower_role):
        """Sponsor path: 5 USDC lender deposit + SEPARATE 1 USDC stake(); NO score published (no granted credit)."""
        funder, borrower = self.roles["s%d-funder" % i], self.roles[borrower_role]
        base.require(self.uint(base.USDC, "balanceOf(address)", funder) == 0, "Unexpected fresh funder balance")
        self.fund(funder, base.DEPOSIT + base.UNIT, "six-USDC sponsor endowment (5 deposit + 1 explicit stake)")
        assets, shares = self.uint(base.POOL, "totalAssets()"), self.uint(base.POOL, "totalShares()")
        quote = base.exact_quote(assets, shares, base.DEPOSIT)
        base.require(quote["exact"] and self.uint(base.POOL, "convertToShares(uint256)", base.DEPOSIT) == quote["shares"],
                     "Five-USDC deposit is not exactly redeemable at this source state")
        self.journal.append("deposit_quote", quote)
        self.execute(funder, base.USDC, "approve(address,uint256)", (base.POOL, base.DEPOSIT), label="exact five-USDC deposit approval")
        self.execute(funder, base.POOL, "depositFunds(uint256)", (base.DEPOSIT,), label="five-USDC existing pool deposit")
        base.require(self.uint(base.POOL, "lenderBalance(address)", funder) == base.DEPOSIT, "Deposit effects differ")
        self.execute(funder, base.USDC, "approve(address,uint256)", (base.POOL, base.UNIT), label="exact one-USDC stake approval")
        self.send(funder, "stake(uint256)", (base.UNIT,), "explicit one-USDC sponsor stake")
        u = self.uint
        base.require(u(base.POOL, "stakeOf(address)", funder) == base.UNIT and u(base.POOL, "totalStaked()") == base.UNIT,
                     "stakeOf/totalStaked != 1 USDC after stake")
        base.require(u(base.POOL, "grantedCredit(address)", funder) == 0 and u(base.POOL, "creditCommitted(address)", funder) == 0
                     and u(base.POOL, "getCreditScore(address)", funder) == 0,
                     "Score/granted credit/creditCommitted must be zero (no score published)")
        self.execute(funder, base.POOL, "back(address,uint256)", (borrower, base.UNIT), label="one-USDC backing from stake")
        base.require(u(base.POOL, "stakeCommitted(address)", funder) == base.UNIT and u(base.POOL, "stakeOf(address)", funder) == base.UNIT,
                     "stakeOf == stakeCommitted == 1 USDC required before borrowing")
        base.require(base.decode_words(self.view(base.POOL, "getBacking(address,address)", funder, borrower)) == [base.UNIT, 0],
                     "Backing must be [secured=1 USDC, unsecured=0] before borrowing")
        base.require(base.decode_words(self.view(base.POOL, "getBorrowLimit(address)", borrower))[0] == base.UNIT,
                     "Borrow limit must be 1 USDC")
        return funder, borrower

    def t2(self):
        """Sponsor-first-loss failed job: stake-backed (secured) line, borrower never repays; impair at term+1, default at term+LATE+1.
        Expectations are declared here BEFORE any fork run and checked, not tuned, afterwards. No score is published or refreshed."""
        funder, borrower = self.setup_staked(2, "s2-borrower-a")
        loan_id = self.request(borrower)
        self.disburse(loan_id, borrower)
        states = {"disbursed": self.pool_state(loan_id, funder, borrower)}
        self.warp(30 * DAY + 1, "term elapsed (30 days + 1 s)")
        states["term_elapsed"] = self.pool_state(loan_id, funder, borrower)
        self.send(self.treasury, "impairLoan(uint256)", (loan_id,), "permissionless impairLoan")
        states["impaired"] = self.pool_state(loan_id, funder, borrower)
        self.warp(30 * DAY + 1, "LATE_PERIOD elapsed (30 days + 1 s)")
        states["late_elapsed"] = self.pool_state(loan_id, funder, borrower)
        # No provider refresh / no score publish. If markDefaulted needs a fresh provider the tx reverts and the run halts (a finding).
        self.send(self.treasury, "markDefaulted(uint256)", (loan_id,), "permissionless markDefaulted")
        states["defaulted"] = self.pool_state(loan_id, funder, borrower)
        d, pre = states["defaulted"], states["late_elapsed"]
        U = base.UNIT
        checks = {
            "sponsor stake fell by exactly 1 USDC": d["funder_stakeOf"] == pre["funder_stakeOf"] - U,
            "totalStaked fell by exactly 1 USDC": d["totalStaked"] == pre["totalStaked"] - U,
            "sponsor stake is zero": d["funder_stakeOf"] == 0,
            "creditLoss == 0": d["funder_creditLoss"] == 0,
            "firstLossReserve unchanged": d["firstLossReserve"] == states["disbursed"]["firstLossReserve"],
            "totalAssets unchanged vs disbursed": d["totalAssets"] == states["disbursed"]["totalAssets"],
            "totalShares unchanged vs disbursed": d["totalShares"] == states["disbursed"]["totalShares"],
            "sponsor lenderBalance unchanged vs disbursed": d["funder_lenderBalance"] == states["disbursed"]["funder_lenderBalance"],
            "backing edge released/consumed (== [0,0])": d["backing"] == [0, 0],
            "borrower defaultedLoans == 1": d["borrower_defaultedLoans"] == 1,
            "loan outstanding == 0": d["outstanding"] == 0,
            "no score ever published for sponsor": d["funder_creditScore"] == 0 and d["funder_grantedCredit"] == 0,
        }
        return {"loan_id": loan_id, "funder": funder, "borrower": borrower, "provider_refresh": "none (by design)",
                "predeclared_checks": checks, "all_predeclared_checks_passed": all(checks.values()), "states": states}

    def run_scenario(self, which):
        version = self.rpc.guard()
        initial = self.block()
        base.require(int(initial["number"], 16) == self.args.fork_block, "Start a fresh fork at the pinned block")
        base.require(initial["hash"].lower() == self.expected_codes["fork_block_hash"].lower(), "Fork block hash mismatch")
        self.code_hashes = self.record_code(initial["number"])
        self.journal.save("runtime-code-hashes.json", self.code_hashes)
        self.baseline = self.snapshot("initial")
        self.invariant(self.baseline, initial=True)
        for account in sorted(self.senders):
            self.rpc.call("anvil_impersonateAccount", [account])
            self.impersonated.append(account)
        self.gas_topup()
        base.require(which == "t2", "Only t2 (failed job: impair + default) is implemented; interest-bearing repayment is not wired")
        body = self.t2()
        out = {"status": "ran", "mode": "fork", "time": "synthetic", "scenario": which, "chain_id": base.CHAIN,
               "client_version": version, "fork_block": self.args.fork_block, "clock": self.clock_log,
               "tx_count": self.tx_count, "result": body,
               "limitations": ["Final fork state is not restored; discard the node.",
                               "All actors controlled by one operator; synthetic time; not live-chain evidence."]}
        self.journal.save("evidence.json", out)
        return out


def self_test():
    assert not (ClockRPC.ALLOWED & FORBIDDEN), "storage/balance/code edits must stay forbidden"
    assert CLOCK_METHODS <= ClockRPC.ALLOWED and not (CLOCK_METHODS & base.RPC.ALLOWED)
    assert "evm_increaseTime" not in ClockRPC.ALLOWED

    class Stub:  # fake clock RPC; no network
        ts, calls = 1_000, []

        def call(self, method, params=None):
            self.calls.append(method)
            if method == "eth_getBlockByNumber":
                return {"timestamp": hex(self.ts)}
            if method == "anvil_setNextBlockTimestamp":
                self.next = params[0]
            if method == "evm_mine":
                self.ts = self.next

    class J:
        def __init__(self): self.rows = []
        def append(self, kind, payload): self.rows.append((kind, payload))

    r = TimeRunner.__new__(TimeRunner)
    r.rpc, r.journal, r.clock_log = Stub(), J(), []
    assert r.warp(30 * DAY + 1, "t") == 1_000 + 30 * DAY + 1
    assert r.journal.rows[0][1]["seconds"] == 30 * DAY + 1 and r.clock_log[0]["time"] == "synthetic"
    try:
        r.warp(0, "zero")
    except base.Halt:
        pass
    else:
        raise AssertionError("zero warp accepted")
    r.impersonated = []
    try:
        r.send("0x" + "11" * 20, "markDefaulted(uint256)", (1,), "x")
    except base.Halt:
        pass
    else:
        raise AssertionError("send() accepted unimpersonated sender")
    try:
        r.send(r.rpc and "0x" + "11" * 20, "withdrawFunds(uint256)", (1,), "x")
    except base.Halt:
        pass
    else:
        raise AssertionError("send() accepted signature outside allowlist")
    assert base.selector("impairLoan(uint256)") and base.selector("markDefaulted(uint256)")
    return {"status": "passed", "mode": "offline_self_test", "network_calls": 0, "scenarios_executed": False,
            "checks": ["clock-only allowlist extension; storage/balance/code methods absent",
                       "warp arithmetic + journal on stub RPC", "zero/backward warp refused",
                       "send() refuses unimpersonated sender and non-allowlisted signature"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rpc")
    p.add_argument("--fork-block", type=int)
    p.add_argument("--expected-code-hashes", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--scenario", choices=("t2",))
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test:
        print(json.dumps(self_test(), indent=2))
        return 0
    base.require(a.rpc and a.fork_block and a.expected_code_hashes and a.output and a.scenario, "missing arguments")
    base.local_url(a.rpc)
    a.fork_block_hash = None
    journal = base.Journal(a.output)
    runner = None
    try:
        runner = TimeRunner(a, journal)
        out = runner.run_scenario(a.scenario)
        print(json.dumps({"status": out["status"], "scenario": a.scenario, "output": str(a.output.resolve())}, indent=2))
        return 0
    except Exception as exc:
        fail = {"status": "stopped", "mode": "fork", "error": str(exc),
                "instruction": "Inspect journal; use a fresh fork for any rerun."}
        journal.append("failure", fail)
        journal.save("failure.json", fail)
        print(json.dumps(fail, indent=2), file=sys.stderr)
        return 1
    finally:
        if runner:
            runner.stop_impersonating()
        journal.handle.close()


if __name__ == "__main__":
    sys.exit(main())
