#!/usr/bin/env python3
"""Three bounded simulations on an existing Base Sepolia deployment, on local Anvil only.

Python 3 standard library only. No keys, signed transactions, upstream requests,
deployment, token minting, contract storage/code edits, or balance injection.
"""
import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
POOL = "0x73872b8fb7f1771c67911f03edc75abdc9514973"
USDC = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
PROVIDER = "0x554c6bb61edf0cafb90ff31813540369cb0105e4"
HERMES = "0x5e4dc7639d2b94006c51ad5373173f5e01c248f9"
AVERY = "0xc5e42b0fb0c109e55f4a40cccfCf3fed1fc39009".lower()
ZERO = "0x" + "00" * 20
UNIT = 1_000_000
DEPOSIT = 5 * UNIT
UINT_MAX = (1 << 256) - 1
GAS_FLOOR = 10 ** 15
CHAIN = 31337
MASK64 = (1 << 64) - 1
ROUND = [0x0000000000000001, 0x0000000000008082, 0x800000000000808a,
         0x8000000080008000, 0x000000000000808b, 0x0000000080000001,
         0x8000000080008081, 0x8000000000008009, 0x000000000000008a,
         0x0000000000000088, 0x0000000080008009, 0x000000008000000a,
         0x000000008000808b, 0x800000000000008b, 0x8000000000008089,
         0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
         0x000000000000800a, 0x800000008000000a, 0x8000000080008081,
         0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
       [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]


class Halt(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Halt(message)


def keccak256(data):
    """Legacy Keccak-256 (Ethereum), not NIST SHA3-256."""
    def rol(x, n):
        return ((x << n) | (x >> ((64 - n) % 64))) & MASK64

    state = [0] * 25
    padded = bytearray(data) + b"\x01"
    padded.extend(b"\0" * ((135 - len(data)) % 136))
    padded[-1] |= 0x80
    for start in range(0, len(padded), 136):
        for i in range(17):
            state[i] ^= int.from_bytes(padded[start + i * 8:start + i * 8 + 8], "little")
        for rc in ROUND:
            c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
                 for x in range(5)]
            d = [c[(x - 1) % 5] ^ rol(c[(x + 1) % 5], 1) for x in range(5)]
            b = [0] * 25
            for x in range(5):
                for y in range(5):
                    b[y + 5 * ((2 * x + 3 * y) % 5)] = rol(state[x + 5 * y] ^ d[x], ROT[x][y])
            for x in range(5):
                for y in range(5):
                    state[x + 5 * y] = b[x + 5 * y] ^ ((~b[(x + 1) % 5 + 5 * y]) & b[(x + 2) % 5 + 5 * y])
            state[0] ^= rc
    return b"".join(x.to_bytes(8, "little") for x in state)[:32]


def selector(signature):
    return keccak256(signature.encode())[:4].hex()


def addr(value):
    require(isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{40}", value), "Invalid address")
    return value.lower()


def word(value):
    if isinstance(value, str):
        value = int(addr(value), 16)
    require(isinstance(value, int) and 0 <= value <= UINT_MAX, "ABI integer out of range")
    return value.to_bytes(32, "big")


def abi_array(items):
    return word(len(items)) + b"".join(word(x) for x in items)


def encode_report(epoch, users, scores):
    require(0 < epoch < (1 << 64), "Epoch is not uint64")
    require(len(users) == len(scores), "Report array length mismatch")
    u = abi_array(users)
    return word(epoch) + word(96) + word(96 + len(u)) + u + abi_array(scores)


def calldata(signature, *args):
    types = signature.partition("(")[2][:-1].split(",") if "()" not in signature else []
    require(len(types) == len(args), "ABI argument count mismatch")
    head, tail = [], b""
    for typ, arg in zip(types, args):
        if typ in ("bytes", "address[]"):
            body = (word(len(arg)) + arg + b"\0" * ((-len(arg)) % 32)) if typ == "bytes" else abi_array(arg)
            head.append(word(32 * len(args) + len(tail)))
            tail += body
        elif typ == "address" or re.fullmatch(r"uint(?:256|64)?", typ):
            head.append(word(arg))
        else:
            raise Halt("Unsupported ABI type " + typ)
    return "0x" + selector(signature) + (b"".join(head) + tail).hex()


def decode_words(encoded):
    require(isinstance(encoded, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{64})*", encoded), "Malformed ABI return data")
    raw = bytes.fromhex(encoded[2:])
    return [int.from_bytes(raw[x:x + 32], "big") for x in range(0, len(raw), 32)]


def decode_address(value):
    require(value < (1 << 160), "Noncanonical address in ABI response")
    return "0x" + format(value, "040x")


def decode_array(encoded, tuple_size=1, offset_index=0):
    w = decode_words(encoded)
    require(len(w) > offset_index and w[offset_index] % 32 == 0, "Malformed ABI array offset")
    start = w[offset_index] // 32
    require(start < len(w) and w[start] <= 10_000, "Malformed/oversized ABI array")
    count = w[start]
    require(start + 1 + count * tuple_size <= len(w), "Truncated ABI array")
    return [w[start + 1 + i * tuple_size:start + 1 + (i + 1) * tuple_size] for i in range(count)]


def exact_quote(assets, shares, deposit):
    a, s = assets + 1, shares + UNIT
    quantum = a // math.gcd(a, s)
    issued = deposit * s // a
    redeem = issued * (a + deposit) // (s + issued)
    return {"virtual_assets": 1, "virtual_shares": UNIT, "quantum": quantum,
            "deposit": deposit, "shares": issued, "full_redemption": redeem,
            "exact": deposit % quantum == 0 and redeem == deposit}


def local_url(value):
    match = re.fullmatch(r"http://127\.0\.0\.1:([0-9]{1,5})", value or "")
    require(match is not None and 1 <= int(match.group(1)) <= 65535,
            "RPC must be exactly http://127.0.0.1:<port>; public, DNS, proxy, TLS, paths and credentials refused")
    return value


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class Journal:
    """Append-only hash-linked public evidence, with fsync after every write."""
    def __init__(self, directory):
        import os
        self.os = os
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.handle = (self.directory / "journal.jsonl").open("x", encoding="utf-8")
        self.previous = "0" * 64
        self.sequence = 0

    def append(self, kind, payload):
        self.sequence += 1
        record = {"sequence": self.sequence, "kind": kind, "payload": payload,
                  "previous_sha256": self.previous}
        self.previous = hashlib.sha256(canonical(record)).hexdigest()
        record["record_sha256"] = self.previous
        self.handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.handle.flush()
        self.os.fsync(self.handle.fileno())
        return record

    def save(self, filename, value):
        temp = self.directory / (filename + ".tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            self.os.fsync(f.fileno())
        temp.replace(self.directory / filename)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Halt("RPC redirect refused")


class RPCError(Halt):
    def __init__(self, error):
        self.error = error
        super().__init__("Local RPC error: " + json.dumps(error, sort_keys=True))


class RPC:
    ALLOWED = {"web3_clientVersion", "eth_chainId", "anvil_nodeInfo", "eth_blockNumber",
               "eth_getBlockByNumber", "eth_getCode", "eth_getBalance", "eth_call",
               "eth_estimateGas", "eth_gasPrice", "eth_sendTransaction", "eth_getTransactionReceipt",
               "eth_getTransactionByHash", "anvil_impersonateAccount", "anvil_stopImpersonatingAccount"}

    def __init__(self, url):
        self.url = local_url(url)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.serial = 0

    def call(self, method, params=None):
        require(method in self.ALLOWED, "RPC method not permitted: " + method)
        self.serial += 1
        payload = {"jsonrpc": "2.0", "id": self.serial, "method": method, "params": params or []}
        request = urllib.request.Request(self.url, data=canonical(payload), headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(request, timeout=20) as response:
                require(response.status == 200, "RPC HTTP failure")
                raw = response.read(20_000_001)
                require(len(raw) <= 20_000_000, "Oversized RPC response")
                data = json.loads(raw)
        except (urllib.error.URLError, ValueError) as exc:
            raise Halt("Local RPC unavailable/malformed: " + str(exc)) from exc
        require(data.get("id") == self.serial and data.get("jsonrpc") == "2.0", "Mismatched JSON RPC response")
        if "error" in data:
            raise RPCError(data["error"])
        require("result" in data, "Missing JSON RPC result")
        return data["result"]

    def guard(self):
        version = self.call("web3_clientVersion")
        require(isinstance(version, str) and "anvil" in version.lower(), "Client is not Anvil")
        require(int(self.call("eth_chainId"), 16) == CHAIN, "Fork chainId must be 31337")
        return version


POOL_GLOBALS = ["totalAssets", "totalShares", "lenderCash", "totalLentOut", "totalImpaired",
                "reservedLiquidity", "firstLossReserve", "protocolFees", "protocolFeeBps", "reserveBps",
                "totalQueuedShares", "totalQueuedWithdrawals", "totalStaked", "totalDuesPaid",
                "totalUnclaimedPayouts", "lendingUtilizationCap", "liquidityBuffer", "liquidityThreshold",
                "maxLoanAmount", "effrRate", "riskPremium", "paused"]
POSITION = ["sharesOf", "lenderPrincipal", "lenderBalance", "queuedShares", "queuedWithdrawals",
            "stakeOf", "stakeCommitted", "creditCommitted", "creditLoss", "duesPaid", "unclaimedPayouts",
            "activeLoanCount", "completedLoans", "defaultedLoans", "scoreOverrides", "getCreditScore", "grantedCredit"]
PROVIDER_GLOBALS = ["epoch", "lastReportAt", "isFresh", "maxScoreAge", "maxTotalScore",
                    "maxIncreasePerReport", "totalScore", "totalHeld"]
ZERO_GLOBALS = ["totalLentOut", "totalImpaired", "reservedLiquidity", "firstLossReserve", "protocolFees",
                "protocolFeeBps", "totalQueuedShares", "totalQueuedWithdrawals", "totalStaked", "totalDuesPaid",
                "totalUnclaimedPayouts", "paused"]
ROOT_ZERO = [x for x in POSITION if x != "completedLoans"]


class Runner:
    def __init__(self, args, journal):
        self.args, self.journal = args, journal
        self.rpc = RPC(args.rpc)
        self.wallets = json.loads((HERE / "public-wallets.json").read_text())
        require(len(self.wallets) == 13 and len({x["address"].lower() for x in self.wallets}) == 13,
                "Exactly thirteen distinct public root wallets required")
        self.roles = {x["role"]: addr(x["address"]) for x in self.wallets}
        expected_roles = {"treasury"} | {"s%d-%s" % (i, r) for i in (1, 2, 3)
                                       for r in ("funder", "borrower-a", "borrower-b", "sink")}
        require(set(self.roles) == expected_roles, "Wallet role set mismatch")
        self.treasury = self.roles["treasury"]
        require(self.treasury == "0x5225c44c41566d2c8785cfadfc712a21c0b51575", "Treasury identity mismatch")
        self.senders = set(self.roles.values()) | {HERMES}
        self.manifest = json.loads((HERE / "manifest.json").read_text())
        require(self.manifest["source_commit"] == "1812e7d2b67e159e341bbff33d6d604409eebb67", "Manifest source version mismatch")
        for c in self.manifest["contracts"].values():
            for sig, expected in c["selectors"].items():
                require(selector(sig) == expected, "Manifest ABI selector mismatch: " + sig)
        self.impersonated, self.results, self.loans = [], [], []
        self.code_hashes = None
        self.baseline = None
        self.gas_spent = 0
        self.gas_topups = 0
        self.tx_count = 0
        self.expected_codes = json.loads(args.expected_code_hashes.read_text())
        require(self.expected_codes.get("source_chain_id") == 84532 and
                self.expected_codes.get("fork_block_number") == args.fork_block,
                "Code fingerprints must be independently pinned to this source chain/block")
        require(re.fullmatch(r"0x[0-9a-fA-F]{64}", self.expected_codes.get("fork_block_hash", "")) is not None,
                "Code fingerprints must include a pinned source block hash")

    def view(self, target, signature, *values, block="latest"):
        return self.rpc.call("eth_call", [{"to": target, "data": calldata(signature, *values)}, block])

    def uint(self, target, signature, *values, block="latest"):
        w = decode_words(self.view(target, signature, *values, block=block))
        require(len(w) == 1, "Expected single ABI word: " + signature)
        return w[0]

    def address(self, target, signature, block="latest"):
        return decode_address(self.uint(target, signature, block=block))

    def block(self):
        return self.rpc.call("eth_getBlockByNumber", ["latest", False])

    def record_code(self, block="latest"):
        result = {}
        for name, address in (("DecentralizedMicrocredit", POOL), ("OracleScoreProvider", PROVIDER), ("USDC", USDC)):
            encoded = self.rpc.call("eth_getCode", [address, block])
            require(re.fullmatch(r"0x(?:[0-9a-fA-F]{2})+", encoded) is not None, "Empty/malformed deployed code: " + name)
            code = bytes.fromhex(encoded[2:])
            item = {"address": address, "bytes": len(code), "sha256": hashlib.sha256(code).hexdigest(),
                    "keccak256": "0x" + keccak256(code).hex()}
            if name in self.manifest["contracts"]:
                expected = self.manifest["contracts"][name]
                template = bytearray.fromhex(expected["runtime"].removeprefix("0x"))
                observed = bytearray(code)
                same_length = len(observed) == len(template)
                for region in expected["immutable_ranges"]:
                    a, z = region["start"], region["start"] + region["length"]
                    require(z <= len(template), "Invalid immutable region")
                    template[a:z] = b"\0" * (z - a)
                    if same_length:
                        observed[a:z] = b"\0" * (z - a)
                item["artifact_normalized_runtime_matches"] = same_length and template == observed
                item["source_sha256"] = expected["source_sha256"]
                item["immutable_ranges_masked_for_artifact_comparison"] = expected["immutable_ranges"]
                item["normalized_runtime_sha256"] = hashlib.sha256(observed).hexdigest()
            fingerprint = self.expected_codes.get("contracts", {}).get(name)
            require(isinstance(fingerprint, dict) and fingerprint.get("address", "").lower() == address and
                    fingerprint.get("sha256", "").removeprefix("0x").lower() == item["sha256"] and
                    fingerprint.get("keccak256", "").lower() == item["keccak256"],
                    "Fork runtime differs from independently pinned source fingerprint: " + name)
            result[name] = item
        return result

    def snapshot(self, label):
        block = self.block()
        tag = block["number"]
        pool = {x: self.uint(POOL, x + "()", block=tag) for x in POOL_GLOBALS}
        pool["token_balance"] = self.uint(USDC, "balanceOf(address)", POOL, block=tag)
        for name in ("owner", "guardian", "scoreProvider", "usdc"):
            pool[name] = self.address(POOL, name + "()", block=tag)
        provider = {x: self.uint(PROVIDER, x + "()", block=tag) for x in PROVIDER_GLOBALS}
        for name in ("owner", "reporter", "lending", "forwarder"):
            provider[name] = self.address(PROVIDER, name + "()", block=tag)
        scores = self.view(PROVIDER, "getScores()", block=tag)
        users = [decode_address(x[0]) for x in decode_array(scores, offset_index=0)]
        amounts = [x[0] for x in decode_array(scores, offset_index=1)]
        require(len(users) == len(amounts) and len(set(users)) == len(users), "Provider score lists malformed")
        provider["scores"] = {u: {"score": s, "held": self.uint(PROVIDER, "budgetHeld(address)", u, block=tag)}
                              for u, s in zip(users, amounts)}
        lenders = [decode_address(x[0]) for x in decode_array(self.view(POOL, "getLenders()", block=tag))]
        pool["existing_lenders"] = {u: {x: self.uint(POOL, x + "(address)", u, block=tag)
                                      for x in ("sharesOf", "lenderPrincipal", "lenderBalance", "queuedShares")}
                                    for u in lenders if u not in self.roles.values()}
        wallets = {}
        for role, account in self.roles.items():
            pos = {x: self.uint(POOL, x + "(address)", account, block=tag) for x in POSITION}
            pos["borrow_limit"], pos["available_credit"] = decode_words(self.view(POOL, "getBorrowLimit(address)", account, block=tag))
            pos["provider_score"] = self.uint(PROVIDER, "creditScore(address)", account, block=tag)
            pos["budget_held"] = self.uint(PROVIDER, "budgetHeld(address)", account, block=tag)
            pos["backings_received"] = [{"backer": decode_address(x[0]), "secured": x[1], "unsecured": x[2]}
                                        for x in decode_array(self.view(POOL, "getBackings(address)", account, block=tag), 3)]
            wallets[role] = {"address": account, "usdc_units": self.uint(USDC, "balanceOf(address)", account, block=tag),
                             "eth_wei": int(self.rpc.call("eth_getBalance", [account, tag]), 16), "position": pos}
        result = {"label": label, "block_number": int(tag, 16), "block_hash": block["hash"],
                  "timestamp": int(block["timestamp"], 16), "pool": pool, "provider": provider, "wallets": wallets,
                  "root_aggregate_usdc_units": sum(x["usdc_units"] for x in wallets.values()),
                  "tracked_loan_ids": self.loans[:],
                  "loans": {str(x): {"getLoan": decode_words(self.view(POOL, "getLoan(uint256)", x, block=tag)),
                                     "getLoanTerms": decode_words(self.view(POOL, "getLoanTerms(uint256)", x, block=tag))}
                            for x in self.loans}}
        self.journal.append("snapshot", result)
        self.journal.save(label + ".json", result)
        return result

    def invariant(self, snap, initial=False):
        p, v = snap["pool"], snap["provider"]
        for key in ZERO_GLOBALS:
            require(p[key] == 0, "Pool must be empty of obligations/fees at boundary: " + key)
        require(p["owner"] == p["guardian"] == HERMES and p["usdc"] == USDC and p["scoreProvider"] == PROVIDER,
                "Pool ownership/token/provider identity mismatch")
        require(p["maxLoanAmount"] == 100 * UNIT and p["reserveBps"] == 4500, "Unexpected pool loan/reserve configuration")
        require(v["owner"] == v["reporter"] == HERMES and v["lending"] == POOL and v["forwarder"] == ZERO,
                "Provider roles/routing mismatch")
        require(v["maxTotalScore"] == 50_000_000 and v["maxIncreasePerReport"] >= 10_000,
                "Provider issuance budget mismatch")
        require(v["isFresh"] == 1 and v["lastReportAt"] != 0 and
                snap["timestamp"] <= v["lastReportAt"] + v["maxScoreAge"], "Provider stale")
        require(v["totalScore"] == v["totalHeld"] == 920_000, "Existing issuance budget changed")
        if initial:
            require(p["totalAssets"] == p["lenderCash"] == p["token_balance"] and p["totalAssets"] in (15 * UNIT, 20 * UNIT) and
                    p["totalShares"] == p["totalAssets"] * UNIT, "Original fifteen/twenty-USDC source pool baseline differs")
            positives = {u: x for u, x in v["scores"].items() if x["score"] or x["held"]}
            require(positives == {AVERY: {"score": 920_000, "held": 920_000}},
                    "Existing Avery score/budget must be 920000")
            require(snap["root_aggregate_usdc_units"] in (15 * UNIT, 20 * UNIT), "Root baseline must be fifteen or twenty USDC")
            require((snap["root_aggregate_usdc_units"], p["totalAssets"]) in
                    ((20 * UNIT, 15 * UNIT), (15 * UNIT, 20 * UNIT)),
                    "Root and source-pool baselines must reconcile the temporary five-USDC contribution")
            require(snap["wallets"]["treasury"]["usdc_units"] == 15 * UNIT and
                    snap["wallets"]["s1-funder"]["usdc_units"] in (0, DEPOSIT), "Unexpected initial root allocation")
            require(all(x["usdc_units"] == 0 for r, x in snap["wallets"].items() if r not in ("treasury", "s1-funder")),
                    "Fresh actor wallets must initially have no USDC")
        else:
            for key, value in self.baseline["pool"].items():
                require(p[key] == value, "Original pool or unrelated lender state changed: " + key)
            require(snap["root_aggregate_usdc_units"] == self.baseline["root_aggregate_usdc_units"],
                    "Root aggregate USDC is not exactly restored")
            require(all(x["usdc_units"] == 0 for r, x in snap["wallets"].items() if r != "treasury"),
                    "Non-treasury USDC must be swept completely")
            for u, state in self.baseline["provider"]["scores"].items():
                require(v["scores"].get(u) == state, "Original provider score/budget changed: " + u)
            for u, state in v["scores"].items():
                if u not in self.baseline["provider"]["scores"]:
                    require(u in self.roles.values() and state == {"score": 0, "held": 0}, "Unexpected provider entry")
            for key, value in self.baseline["provider"].items():
                if key not in ("epoch", "lastReportAt", "scores"):
                    require(v[key] == value, "Provider configuration/budget changed: " + key)
        for role, wallet in snap["wallets"].items():
            pos = wallet["position"]
            for key in ROOT_ZERO:
                require(pos[key] == 0, "Root position not clear: " + role + "/" + key)
            require(pos["borrow_limit"] == pos["available_credit"] == pos["provider_score"] == pos["budget_held"] == 0,
                    "Root credit/budget remains: " + role)
            require(not pos["backings_received"], "Root backing remains: " + role)
            expected = 0 if initial else sum(r["borrower_role"] == role for r in self.results)
            require(pos["completedLoans"] == expected, "Unexpected completed-loan history: " + role)
        if not initial:
            require(self.record_code(hex(snap["block_number"])) == self.code_hashes, "Runtime code changed during simulation")

    def execute(self, sender, target, signature=None, values=(), value=0, label=""):
        require(sender in self.senders and target in (POOL, USDC, PROVIDER) or
                (sender == self.treasury and target in self.senders and signature is None), "Unapproved transaction routing")
        require(sender in self.impersonated, "Sender is not an explicitly allowed impersonated account")
        if target == POOL:
            require(signature in ("depositFunds(uint256)", "withdrawFunds(uint256)", "back(address,uint256)",
                                  "requestLoan(uint256)", "disburseLoan(uint256)", "repayLoan(uint256,uint256)"),
                    "Pool mutation outside scenario allowlist")
        elif target == USDC:
            require(signature in ("approve(address,uint256)", "transfer(address,uint256)"), "Token mutation outside scenario allowlist")
            if signature.startswith("approve"):
                require(values[0] == POOL and values[1] in (UNIT, DEPOSIT), "Only exact scenario approvals allowed")
            else:
                require(values[0] in self.roles.values(), "USDC destination is not root controlled")
        elif target == PROVIDER:
            require(signature in ("publishScores(bytes)", "releaseBudget(address[])"), "Provider mutation outside scenario allowlist")
            if signature.startswith("publish"):
                require(sender == HERMES, "Only original reporter may publish")
        else:
            require(signature is None and sender == self.treasury and target != sender and 0 < value <= GAS_FLOOR,
                    "Only treasury-funded bounded ETH top-ups allowed")
        self.rpc.guard()
        tx = {"from": sender, "to": target, "value": hex(value)}
        if signature:
            tx["data"] = calldata(signature, *values)
        # A successful call/estimate is a preflight; only a mined receipt counts as execution.
        self.rpc.call("eth_call", [tx, "latest"])
        gas_estimate = int(self.rpc.call("eth_estimateGas", [tx]), 16)
        gas = (gas_estimate * 120 + 99) // 100
        require(gas <= 1_500_000, "Gas estimate outside bounded scenario budget")
        price = int(self.rpc.call("eth_gasPrice"), 16)
        require(0 < price <= 1_000_000_000, "Gas price above one gwei; stop for bounded gas review")
        balance = int(self.rpc.call("eth_getBalance", [sender, "latest"]), 16)
        require(balance >= value + gas * price, "Actor gas exhausted; no injected balances/fallback")
        require(self.gas_spent + gas * price <= 20_000_000_000_000_000, "Total gas upper bound exceeded")
        tx.update({"gas": hex(gas), "gasPrice": hex(price)})
        self.journal.append("transaction_intent", {"label": label, "transaction": tx})
        txhash = self.rpc.call("eth_sendTransaction", [tx])
        require(isinstance(txhash, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", txhash), "Invalid local transaction hash")
        self.journal.append("transaction_submitted", {"label": label, "hash": txhash})
        deadline = time.monotonic() + 30
        receipt = None
        while time.monotonic() < deadline:
            receipt = self.rpc.call("eth_getTransactionReceipt", [txhash])
            if receipt is not None:
                break
            time.sleep(0.2)
        require(receipt is not None, "Mining receipt timeout; stop without retrying transaction")
        self.journal.append("transaction_receipt", {"label": label, "hash": txhash, "receipt": receipt})
        require(receipt.get("transactionHash", "").lower() == txhash.lower() and receipt.get("from", "").lower() == sender and
                receipt.get("to", "").lower() == target and int(receipt.get("status", "0x0"), 16) == 1,
                "Failed/mismatched mined receipt")
        require(not receipt.get("contractAddress"), "Deployment is forbidden")
        mined = self.rpc.call("eth_getTransactionByHash", [txhash])
        require(mined is not None and mined.get("blockHash") == receipt.get("blockHash") and
                mined.get("to", "").lower() == target and mined.get("from", "").lower() == sender and
                int(mined.get("value", "0x0"), 16) == value and
                mined.get("input", "0x").lower() == tx.get("data", "0x").lower(), "Mined transaction differs from intent")
        block = self.rpc.call("eth_getBlockByNumber", [receipt["blockNumber"], False])
        require(block is not None and block["hash"] == receipt["blockHash"], "Receipt block mismatch")
        self.gas_spent += int(receipt["gasUsed"], 16) * int(receipt.get("effectiveGasPrice", hex(price)), 16)
        self.tx_count += 1
        self.journal.append("mined_transaction", {"label": label, "transaction": mined, "block_timestamp": int(block["timestamp"], 16)})
        return receipt

    def reject(self, sender, signature, values, expected, label):
        self.rpc.guard()
        block = self.block()
        tx = {"from": sender, "to": POOL, "data": calldata(signature, *values)}
        try:
            self.rpc.call("eth_call", [tx, block["number"]])
        except RPCError as exc:
            def extract(value):
                if isinstance(value, str) and re.fullmatch(r"0x[0-9a-fA-F]{8,}", value):
                    return value.lower()
                if isinstance(value, dict):
                    for key in ("data", "return", "result", "originalError"):
                        if key in value:
                            found = extract(value[key])
                            if found:
                                return found
                return None
            raw = extract(exc.error.get("data"))
            require(raw is not None and raw[:10] == expected, "Wrong/missing actual revert selector for " + label)
            result = {"label": label, "mode": "read_only_eth_call", "transaction": tx,
                      "block_number": int(block["number"], 16), "block_hash": block["hash"],
                      "expected_selector": expected, "actual_selector": raw[:10], "revert_data": raw,
                      "rpc_error": exc.error}
            self.journal.append("expected_revert", result)
            require(self.block()["hash"] == block["hash"], "Concurrent block change during negative read-only check")
            return result
        raise Halt("Expected rejection succeeded: " + label)

    def gas_topup(self):
        require(int(self.rpc.call("eth_getBalance", [self.treasury, "latest"]), 16) >= 20_000_000_000_000_000,
                "Treasury needs at least 0.02 ETH for bounded gas funding")
        for account in sorted(self.senders - {self.treasury}):
            balance = int(self.rpc.call("eth_getBalance", [account, "latest"]), 16)
            if balance < GAS_FLOOR:
                topup = GAS_FLOOR - balance
                require(self.gas_topups + topup <= 13 * GAS_FLOOR, "Gas top-up aggregate exceeded")
                self.execute(self.treasury, account, value=topup, label="treasury gas top-up")
                self.gas_topups += topup

    def fund(self, receiver, amount, label):
        self.execute(self.treasury, USDC, "transfer(address,uint256)", (receiver, amount), label=label)

    def issue(self, funder, score):
        require(funder in [self.roles["s%d-funder" % i] for i in (1, 2, 3)] and score in (0, 10_000),
                "Only bounded temporary funder scores allowed")
        epoch = self.uint(PROVIDER, "epoch()")
        self.execute(HERMES, PROVIDER, "publishScores(bytes)", (encode_report(epoch + 1, [funder], [score]),),
                     label="temporary funder score " + str(score))
        require(self.uint(PROVIDER, "creditScore(address)", funder) == score, "Score report not applied")

    def setup(self, i, borrower_role):
        funder, borrower = self.roles["s%d-funder" % i], self.roles[borrower_role]
        balance = self.uint(USDC, "balanceOf(address)", funder)
        require(balance in (0, DEPOSIT), "Unexpected fresh funder balance")
        if balance == 0:
            self.fund(funder, DEPOSIT, "five-USDC root funder endowment")
        assets, shares = self.uint(POOL, "totalAssets()"), self.uint(POOL, "totalShares()")
        quote = exact_quote(assets, shares, DEPOSIT)
        require(quote["exact"] and self.uint(POOL, "convertToShares(uint256)", DEPOSIT) == quote["shares"],
                "Five-USDC deposit is not exactly redeemable at this source state")
        self.journal.append("deposit_quote", quote)
        self.execute(funder, USDC, "approve(address,uint256)", (POOL, DEPOSIT), label="exact five-USDC deposit approval")
        self.execute(funder, POOL, "depositFunds(uint256)", (DEPOSIT,), label="five-USDC existing pool deposit")
        require(self.uint(POOL, "sharesOf(address)", funder) == quote["shares"] and
                self.uint(POOL, "lenderBalance(address)", funder) == DEPOSIT and
                self.uint(POOL, "totalAssets()") == assets + DEPOSIT and
                self.uint(POOL, "totalShares()") == shares + quote["shares"] and
                self.uint(USDC, "balanceOf(address)", funder) == 0, "Deposit effects differ from exact quote")
        self.issue(funder, 10_000)
        require(self.uint(POOL, "grantedCredit(address)", funder) == UNIT, "Temporary funder own line is not one USDC")
        self.execute(funder, POOL, "back(address,uint256)", (borrower, UNIT), label="one-USDC existing-provider backing")
        require(decode_words(self.view(POOL, "getBacking(address,address)", funder, borrower)) == [0, UNIT] and
                decode_words(self.view(POOL, "getBorrowLimit(address)", borrower)) == [UNIT, UNIT], "Backing not an exact unsecured one-USDC line")
        return funder, borrower

    def request(self, borrower):
        receipt = self.execute(borrower, POOL, "requestLoan(uint256)", (UNIT,), label="one-USDC loan request")
        topic = "0x" + keccak256(b"LoanRequested(address,uint256,uint256,uint256)").hex()
        events = [x for x in receipt.get("logs", []) if x.get("address", "").lower() == POOL and
                  x.get("topics") and x["topics"][0].lower() == topic]
        require(len(events) == 1, "Request must have exactly one LoanRequested in its own mined receipt")
        event = events[0]
        require(len(event["topics"]) == 3 and decode_address(int(event["topics"][1], 16)) == borrower,
                "LoanRequested borrower mismatch")
        loan_id = int(event["topics"][2], 16)
        require(loan_id > 0 and loan_id not in self.loans, "Invalid/reused receipt-derived loan id")
        payload = decode_words(event["data"])
        require(len(payload) == 2 and payload[0] == UNIT, "LoanRequested principal mismatch")
        loan = decode_words(self.view(POOL, "getLoan(uint256)", loan_id))
        terms = decode_words(self.view(POOL, "getLoanTerms(uint256)", loan_id))
        require(loan[0:2] == [UNIT, UNIT] and decode_address(loan[2]) == borrower and loan[4] == 1 and
                terms[0] == 1 and self.uint(POOL, "reservedLiquidity()") == UNIT,
                "Requested loan/reservation mismatch")
        self.loans.append(loan_id)
        self.journal.append("receipt_derived_loan", {"loan_id": loan_id, "borrower": borrower,
                                                   "transaction_hash": receipt["transactionHash"], "log": event})
        return loan_id

    def disburse(self, loan_id, borrower):
        self.execute(self.treasury, POOL, "disburseLoan(uint256)", (loan_id,), label="permissionless loan disbursement")
        terms = decode_words(self.view(POOL, "getLoanTerms(uint256)", loan_id))
        require(terms[0] == 2 and terms[3] > 0 and self.uint(POOL, "reservedLiquidity()") == 0 and
                self.uint(POOL, "totalLentOut()") == UNIT and self.uint(USDC, "balanceOf(address)", borrower) == UNIT,
                "Disbursement state/cash mismatch")
        return terms[3]

    def repay(self, payer, loan_id, disbursed_at):
        outstanding = self.uint(POOL, "getCurrentOutstandingAmount(uint256)", loan_id)
        now = int(self.block()["timestamp"], 16)
        require(now - disbursed_at < 86_399 and outstanding == UNIT,
                "Stop: full one-USDC repayment must mine strictly before 86400-second interest boundary")
        self.execute(payer, USDC, "approve(address,uint256)", (POOL, outstanding), label="exact full-outstanding repayment approval")
        now = int(self.block()["timestamp"], 16)
        require(now - disbursed_at < 86_399, "Interest boundary approached before repayment")
        receipt = self.execute(payer, POOL, "repayLoan(uint256,uint256)", (loan_id, outstanding), label="full principal repayment")
        block = self.rpc.call("eth_getBlockByNumber", [receipt["blockNumber"], False])
        require(int(block["timestamp"], 16) - disbursed_at < 86_400, "Repayment mined at/after interest boundary")
        terms = decode_words(self.view(POOL, "getLoanTerms(uint256)", loan_id))
        require(terms[0] == 3 and self.uint(POOL, "getCurrentOutstandingAmount(uint256)", loan_id) == 0 and
                self.uint(POOL, "totalLentOut()") == 0, "Loan did not close with zero outstanding principal")

    def close(self, funder, borrower):
        self.execute(funder, POOL, "back(address,uint256)", (borrower, 0), label="remove closed loan backing")
        require(decode_words(self.view(POOL, "getBorrowLimit(address)", borrower)) == [0, 0] and
                self.uint(POOL, "duesPaid(address)", borrower) == 0 and
                self.uint(POOL, "grantedCredit(address)", borrower) == 0 and
                self.uint(POOL, "completedLoans(address)", borrower) == 1,
                "Completion must create history only; no dues/independent credit")
        require(self.uint(POOL, "lenderBalance(address)", funder) == DEPOSIT, "Full withdrawal no longer exact")
        self.execute(funder, POOL, "withdrawFunds(uint256)", (UINT_MAX,), label="withdraw every unqueued funder share")
        require(self.uint(POOL, "sharesOf(address)", funder) == 0 and self.uint(USDC, "balanceOf(address)", funder) == DEPOSIT,
                "Full funder withdrawal did not exactly recover five USDC")
        self.issue(funder, 0)
        self.execute(self.treasury, PROVIDER, "releaseBudget(address[])", ([funder],), label="release temporary provider budget")
        require(self.uint(PROVIDER, "budgetHeld(address)", funder) == 0 and
                self.uint(PROVIDER, "totalHeld()") == self.baseline["provider"]["totalHeld"], "Temporary budget not released")
        for role, wallet in self.roles.items():
            if role == "treasury":
                continue
            balance = self.uint(USDC, "balanceOf(address)", wallet)
            if balance:
                self.execute(wallet, USDC, "transfer(address,uint256)", (self.treasury, balance), label="sweep all " + role + " USDC")

    def scenario(self, i):
        a, b, sink = [self.roles["s%d-%s" % (i, r)] for r in ("borrower-a", "borrower-b", "sink")]
        borrower_role = "s%d-borrower-%s" % (i, "b" if i == 2 else "a")
        funder, borrower = self.setup(i, borrower_role)
        negatives = []
        if i == 2:
            self.fund(a, UNIT, "one-USDC entire voluntary-aid endowment")
            require(self.uint(POOL, "activeLoanCount(address)", a) == 0 and
                    self.uint(POOL, "grantedCredit(address)", a) == 0, "Aid donor must have no own loan/issued credit")
            negatives.append(self.reject(b, "back(address,uint256)", (a, UNIT), "0x8ac4bc73", "received backing cannot fund a second hop"))
        if i == 3:
            negatives.append(self.reject(a, "back(address,uint256)", (b, UNIT), "0x8ac4bc73", "A cannot back B with received backing"))
            negatives.append(self.reject(a, "requestLoan(uint256)", (1_010_000,), "0x5d615d32", "A cannot exceed one-USDC backing limit"))
            negatives.append(self.reject(b, "requestLoan(uint256)", (UNIT,), "0x315b0e14", "B without credit cannot request a loan"))
        loan_id = self.request(borrower)
        if i == 3:
            negatives.append(self.reject(a, "requestLoan(uint256)", (UNIT,), "0x5d615d32", "Reservation consumes available credit"))
            negatives.append(self.reject(funder, "back(address,uint256)", (a, 0), "0x9917947d", "Backing cannot be removed while reservation is open"))
        disbursed_at = self.disburse(loan_id, borrower)
        self.snapshot("scenario%d-active" % i)
        if i == 1:
            self.execute(a, USDC, "transfer(address,uint256)", (sink, UNIT), label="controlled simulated invoice expense")
            self.fund(a, UNIT, "root treasury pays accepted simulated task; internal subsidy")
            self.repay(a, loan_id, disbursed_at)
            meaning = "Accepted simulated worker invoice; treasury payment is internal subsidy, not outside income. Completion count is not independent trust."
        elif i == 2:
            self.execute(b, USDC, "transfer(address,uint256)", (sink, UNIT), label="controlled B simulated expense")
            self.repay(a, loan_id, disbursed_at)
            require(self.uint(USDC, "balanceOf(address)", a) == self.uint(USDC, "balanceOf(address)", b) == 0,
                    "Voluntary aid did not spend entire donor budget/leave borrower cash zero")
            meaning = "Voluntary third-party repayment spends A's entire one-USDC endowment; sustainable credit was declined, bounded aid accepted. No cure needed."
        else:
            self.execute(a, USDC, "transfer(address,uint256)", (b, UNIT), label="controlled collusion A transfers borrowed cash to B")
            negatives.append(self.reject(b, "requestLoan(uint256)", (UNIT,), "0x315b0e14", "Receiving USDC cash does not create borrowing credit"))
            self.journal.append("actor_decision", {"scenario": 3, "A": "refuses voluntary repayment", "classification": "actor refusal, not on-chain default"})
            self.repay(b, loan_id, disbursed_at)
            meaning = "Controlled collusion cannot create credit by backing or transferring cash. B repays A using transferred principal under root cure; no actual default."
        self.close(funder, borrower)
        if i == 2:
            negatives.append(self.reject(b, "requestLoan(uint256)", (UNIT,), "0x315b0e14", "Closed history and removed backing do not create own credit"))
        result = {"scenario": i, "mode": "fork", "borrower_role": borrower_role, "loan_id_from_mined_receipt": loan_id,
                  "meaning": meaning, "negative_checks": negatives, "status": "complete_pending_boundary_check"}
        self.results.append(result)
        after = self.snapshot("scenario%d-after" % i)
        self.invariant(after)
        result["status"] = "passed"
        result["after_block_number"] = after["block_number"]
        result["after_block_hash"] = after["block_hash"]
        self.journal.append("scenario_result", result)
        self.journal.save("scenario%d-result.json" % i, result)

    def run(self):
        version = self.rpc.guard()
        node = self.rpc.call("anvil_nodeInfo")
        fork = node.get("forkConfig") or node.get("fork_config")
        require(isinstance(fork, dict), "Anvil must expose forkConfig; standalone/mocked Anvil refused")
        fork_url = fork.get("forkUrl", fork.get("fork_url"))
        fork_num = fork.get("forkBlockNumber", fork.get("fork_block_number"))
        fork_num = int(fork_num, 0) if isinstance(fork_num, str) else fork_num
        require(fork_url == "https://sepolia.base.org" and fork_num == self.args.fork_block,
                "Anvil forkConfig must target canonical Base Sepolia URL and requested pinned block")
        initial_block = self.block()
        require(int(initial_block["number"], 16) == self.args.fork_block, "Start a fresh fork at the pinned block; existing local mutations refused")
        require(initial_block["hash"].lower() == self.expected_codes["fork_block_hash"].lower(),
                "Fork block hash differs from independently pinned source fingerprint")
        if self.args.fork_block_hash:
            require(initial_block["hash"].lower() == self.args.fork_block_hash.lower(), "Pinned source block hash mismatch")
        require(self.uint(USDC, "decimals()") == 6, "Canonical token must have six decimals")
        self.code_hashes = self.record_code(initial_block["number"])
        self.journal.save("runtime-code-hashes.json", self.code_hashes)
        self.journal.append("fork_guard", {"mode": "fork", "chain_id": CHAIN, "source_chain_id": 84532,
                                            "rpc": self.args.rpc, "client_version": version,
                                            "fork_block_target": self.args.fork_block,
                                            "source_block_hash": initial_block["hash"], "code_hashes": self.code_hashes,
                                            "no_live_fund_moves": True, "no_keys_or_signed_bytes": True})
        self.baseline = self.snapshot("initial")
        self.invariant(self.baseline, initial=True)
        for account in sorted(self.senders):
            require(self.rpc.call("anvil_impersonateAccount", [account]) in (None, True), "Account impersonation rejected")
            self.impersonated.append(account)
            self.journal.append("local_impersonation", {"address": account, "scope": "root-controlled actor" if account != HERMES else "original provider reporter in local fork"})
        self.gas_topup()
        for i in (1, 2, 3):
            self.scenario(i)
        final = self.snapshot("final")
        self.invariant(final)
        output = {"status": "passed", "mode": "fork", "chain_id": CHAIN, "source_chain_id": 84532,
                  "source_commit": self.manifest["source_commit"], "fork_block_target": self.args.fork_block,
                  "fork_block_hash": initial_block["hash"], "no_live_fund_moves": True,
                  "no_keys_signed_bytes_or_balance_storage_code_injection": True,
                  "initial_root_aggregate_usdc_units": self.baseline["root_aggregate_usdc_units"],
                  "final_root_aggregate_usdc_units": final["root_aggregate_usdc_units"],
                  "gas_topups_from_treasury_wei": self.gas_topups, "gas_spent_wei": self.gas_spent,
                  "mined_local_transaction_count": self.tx_count, "scenarios": self.results,
                  "runtime_code_hashes": self.code_hashes,
                  "limitations": ["All actors are controlled by one operator; this is a fork rehearsal, not live testnet execution.",
                                  "Task payment and voluntary aid are internal transfers, not external earnings.",
                                  "No default, cent writeoff, time warp, or interest-boundary branch was executed.",
                                  "Reports/history add zero-score funder and completed-loan records; financial obligations and original issuance budget are restored."]}
        self.journal.append("complete", output)
        output["journal_tip_sha256"] = self.journal.previous
        self.journal.save("evidence.json", output)
        return output

    def stop_impersonating(self):
        for account in reversed(self.impersonated):
            try:
                self.rpc.call("anvil_stopImpersonatingAccount", [account])
                self.journal.append("stop_local_impersonation", {"address": account})
            except Exception as exc:
                self.journal.append("stop_local_impersonation_failed", {"address": account, "error": str(exc)})


def self_test():
    # Real Ethereum golden hashes guard the pure stdlib Keccak implementation.
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert selector("transfer(address,uint256)") == "a9059cbb"
    assert selector("InsufficientCredit()") == "8ac4bc73"
    assert selector("BorrowLimitExceeded()") == "5d615d32"
    assert selector("NoCredit()") == "315b0e14"
    assert selector("BackingInUse()") == "9917947d"
    for good in ("http://127.0.0.1:8547", "http://127.0.0.1:1", "http://127.0.0.1:65535"):
        assert local_url(good) == good
    for bad in ("https://sepolia.base.org", "http://localhost:8547", "http://127.0.0.1:8547/",
                "http://127.0.0.1:0", "http://127.0.0.1:65536", "http://127.0.0.1:8547@evil.test",
                "http://127.0.0.1:8547/path", "http://[::1]:8547", "http://127.0.0.1:8547?x=1"):
        try:
            local_url(bad)
        except Halt:
            pass
        else:
            raise AssertionError("Unsafe URL accepted: " + bad)
    quote = exact_quote(20_000_000, 20_000_000_000_000, DEPOSIT)
    assert quote == {"virtual_assets": 1, "virtual_shares": UNIT, "quantum": 1, "deposit": DEPOSIT,
                     "shares": DEPOSIT * UNIT, "full_redemption": DEPOSIT, "exact": True}
    assert not exact_quote(20_000_001, 20_000_000_000_000, DEPOSIT)["exact"]
    manifest = json.loads((HERE / "manifest.json").read_text())
    for contract in manifest["contracts"].values():
        for signature, expected in contract["selectors"].items():
            assert selector(signature) == expected, signature
    vectors = json.loads((HERE / "abi-vectors.json").read_text())
    for group in vectors["selectors"].values():
        for signature, expected in group.items():
            assert selector(signature) == expected.removeprefix("0x"), signature
    funder = "0xab7a7ee666b83607cb9d11b5d54f49c1085f980c"
    report = encode_report(1, [funder], [10_000])
    assert "0x" + report.hex() == vectors["report1"]["encoded"]
    assert calldata("publishScores(bytes)", report) == vectors["report1"]["publishScoresCalldata"]
    assert calldata("releaseBudget(address[])", [funder]) == vectors["releaseBudget"]["calldata"]
    assert "0x" + keccak256(b"LoanRequested(address,uint256,uint256,uint256)").hex() == vectors["loanRequested"]["topic0"]
    assert decode_array("0x" + (word(32) + abi_array([funder])).hex())[0][0] == int(funder, 16)
    try:
        decode_array("0x" + word(64).hex())
    except Halt:
        pass
    else:
        raise AssertionError("Malformed array accepted")
    with tempfile.TemporaryDirectory() as path:
        journal = Journal(path)
        first = journal.append("intent", {"amount": UNIT})
        second = journal.append("receipt", {"status": 1})
        journal.save("result.json", {"status": "passed"})
        entries = [json.loads(x) for x in (Path(path) / "journal.jsonl").read_text().splitlines()]
        assert entries == [first, second] and second["previous_sha256"] == first["record_sha256"]
        for entry in entries:
            digest = entry.pop("record_sha256")
            assert digest == hashlib.sha256(canonical(entry)).hexdigest()
        assert json.loads((Path(path) / "result.json").read_text()) == {"status": "passed"}
        try:
            Journal(path)
        except FileExistsError:
            pass
        else:
            raise AssertionError("Existing journal overwritten")
    return {"status": "passed", "mode": "offline_self_test", "network_calls": 0,
            "checks": ["Ethereum Keccak/selectors", "viem ABI golden vectors", "strict local URL guards",
                       "exact deposit/withdrawal quote and rounding rejection", "ABI decoding guards",
                       "append-only hash-linked journal and output collision guard"],
            "scenarios_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc", help="Only http://127.0.0.1:<port> is accepted")
    parser.add_argument("--fork-block", type=int, help="Same pinned source block used when starting fresh Anvil")
    parser.add_argument("--fork-block-hash", help="Optional independently observed canonical source block hash")
    parser.add_argument("--output", type=Path, help="New directory for public fork evidence; existing journal refused")
    parser.add_argument("--expected-code-hashes", type=Path, help="Required public fingerprints from independently pinned source reads")
    parser.add_argument("--self-test", action="store_true", help="Offline ABI, guards, journal and exact-share tests; no RPC")
    args = parser.parse_args()
    if args.self_test:
        require(not any((args.rpc, args.fork_block, args.output, args.fork_block_hash, args.expected_code_hashes)), "Self-test accepts no RPC/fork arguments")
        print(json.dumps(self_test(), indent=2))
        return 0
    require(args.rpc and args.fork_block and args.fork_block > 0 and args.output and args.expected_code_hashes,
            "--rpc, --fork-block, --expected-code-hashes and --output are required")
    local_url(args.rpc)
    if args.fork_block_hash:
        require(re.fullmatch(r"0x[0-9a-fA-F]{64}", args.fork_block_hash) is not None, "Invalid fork block hash")
    journal = Journal(args.output)
    runner = None
    try:
        runner = Runner(args, journal)
        result = runner.run()
        print(json.dumps({"status": result["status"], "mode": "fork", "chain_id": CHAIN,
                          "output": str(args.output.resolve()), "scenarios": 3,
                          "no_live_fund_moves": True}, indent=2))
        return 0
    except Exception as exc:
        failure = {"status": "stopped", "mode": "fork", "chain_id": CHAIN, "error": str(exc),
                   "scenarios_passed": len([x for x in runner.results if x["status"] == "passed"]) if runner else 0,
                   "live_fund_moves": False,
                   "instruction": "Stop and inspect journal. Do not claim success or retry against this partially mutated fork. Start a fresh fork for any corrected rerun."}
        journal.append("failure", failure)
        journal.save("failure.json", failure)
        print(json.dumps(failure, indent=2), file=sys.stderr)
        return 1
    finally:
        if runner:
            runner.stop_impersonating()
        journal.handle.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Halt, OSError, AssertionError) as exc:
        print("Stopped: " + str(exc), file=sys.stderr)
        sys.exit(1)
