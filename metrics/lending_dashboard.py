#!/usr/bin/env python3
"""Read-only testnet ledger collector. No profiles, keys or transactions.

A successful collection reconciles full event history against pinned contract state
on two providers at a finalized boundary. Failure preserves the last good snapshot.
Ledger activity establishes neither human identity nor incremental human benefit.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.deployment import address, as_int, format_units, load_deployment  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATUS = ("None", "Requested", "Active", "Repaid", "Defaulted", "Cancelled")
DEFAULT_LOGS_RPC = "https://base-sepolia.gateway.tenderly.co"  # sepolia.base.org caps eth_getLogs at 200 blocks
DEPLOYMENT_BLOCK = 0x2D9040C  # deployments/base-sepolia-1812e7d-usdc001 broadcast, first transaction
EAS = "0x4200000000000000000000000000000000000021"  # OP-stack predeploy, present on Base Sepolia
SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"
PROFILE_SCHEMA = ("uint256 loanId,string country,string region,string occupation,string purpose,"
                  "uint8 incomeBand,uint8 consentVersion")
PROFILE_SCHEMA_RESOLVER = "0x0000000000000000000000000000000000000000"
PROFILE_SCHEMA_REVOCABLE = True
INCOME_BANDS = {0: "not stated", 1: "under 2.15 USD a day", 2: "2.15 to 3.65 USD a day",
                3: "3.65 to 6.85 USD a day", 4: "over 6.85 USD a day"}

POOL_EVENTS = (
    "Deposited(address indexed lender,uint256 assets,uint256 shares)",
    "Withdrawn(address indexed lender,address indexed to,uint256 assets,uint256 shares)",
    "LoanRequested(address indexed borrower,uint256 indexed loanId,uint256 amount,uint256 interestRate)",
    "LoanDisbursed(address indexed borrower,uint256 indexed loanId,address to,uint256 amount)",
    "LoanCancelled(address indexed borrower,uint256 indexed loanId)",
    "LoanImpaired(uint256 indexed loanId,uint256 impaired)",
    "LoanDefaulted(address indexed borrower,uint256 indexed loanId,uint256 writtenOff,uint256 recovered)",
    "BackerCharged(address indexed backer,uint256 indexed loanId,uint256 slashed,uint256 charged)",
    "Backed(address indexed backer,address indexed borrower,uint256 secured,uint256 unsecured)",
    "LoanRepaid(address indexed borrower,uint256 indexed loanId,uint256 amount)",
    "MetaLoanRepaid(address indexed borrower,uint256 indexed loanId,uint256 amount)",
    "RepaymentApplied(uint256 indexed loanId,uint256 interest,uint256 principal,uint256 fee)",
    "ReserveFunded(address indexed from,uint256 amount)",
    "ReserveReleased(uint256 amount)",
    "Staked(address indexed account,uint256 amount)",
    "Unstaked(address indexed account,uint256 amount)",
)
EAS_EVENTS = (
    "Attested(address indexed recipient,address indexed attester,bytes32 uid,bytes32 indexed schemaUID)",
    "Revoked(address indexed recipient,address indexed attester,bytes32 uid,bytes32 indexed schemaUID)",
)
POOL_FIELDS = ("totalAssets", "lenderCash", "totalLentOut", "reservedLiquidity", "firstLossReserve",
               "totalImpaired", "totalDuesPaid", "protocolFees", "totalStaked", "lenderCount", "getLoanRate",
               "totalShares")


# ---------------------------------------------------------------- keccak-256 (pure Python)
_RC = (0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B,
       0x0000000080000001, 0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088,
       0x0000000080008009, 0x000000008000000A, 0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
       0x8000000000008003, 0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008)
_ROT = (0, 1, 62, 28, 27, 36, 44, 6, 55, 20, 3, 10, 43, 25, 39, 41, 45, 15, 21, 8, 18, 2, 61, 56, 14)
_MASK = (1 << 64) - 1


def _keccak_f(state):
    for rc in _RC:
        c = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ (((c[(x + 1) % 5] << 1) | (c[(x + 1) % 5] >> 63)) & _MASK) for x in range(5)]
        state = [state[i] ^ d[i % 5] for i in range(25)]
        rotated = [0] * 25
        for x in range(5):
            for y in range(5):
                r = _ROT[x + 5 * y]
                value = state[x + 5 * y]
                rotated[y + 5 * ((2 * x + 3 * y) % 5)] = ((value << r) | (value >> (64 - r))) & _MASK if r else value
        state = [rotated[i] ^ ((~rotated[(i % 5 + 1) % 5 + 5 * (i // 5)]) & rotated[(i % 5 + 2) % 5 + 5 * (i // 5)])
                 for i in range(25)]
        state[0] ^= rc
    return state


def keccak256(data):
    """keccak-256 as used by Ethereum (pad 0x01, not SHA3's 0x06)."""
    rate = 136
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate:
        padded.append(0)
    padded[-1] |= 0x80
    state = [0] * 25
    for offset in range(0, len(padded), rate):
        block = padded[offset:offset + rate]
        for i in range(rate // 8):
            state[i] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        state = _keccak_f(state)
    return b"".join(state[i].to_bytes(8, "little") for i in range(4))


# ---------------------------------------------------------------- minimal ABI
def parse_event(signature):
    name, _, rest = signature.partition("(")
    params = []
    for part in rest.rstrip(")").split(","):
        words = part.split()
        params.append({"type": words[0], "indexed": "indexed" in words, "name": words[-1]})
    canonical = f"{name}({','.join(p['type'] for p in params)})"
    return {"name": name, "params": params, "topic": "0x" + keccak256(canonical.encode()).hex()}


def selector(signature):
    return "0x" + keccak256(signature.encode()).hex()[:8]


def encode_word(kind, value):
    if kind == "address":
        return address(value)[2:].lower().rjust(64, "0")
    if kind.startswith("uint"):
        return format(as_int(value), "064x")
    if kind == "bytes32":
        return value[2:].lower().rjust(64, "0")
    if kind == "bool":
        return format(1 if value else 0, "064x")
    raise ValueError(f"unsupported argument type {kind}")


def decode_word(kind, word):
    if kind == "address":
        return "0x" + word[-40:]
    if kind.startswith("uint"):
        return int(word, 16)
    if kind == "bool":
        return int(word, 16) != 0
    if kind == "bytes32":
        return "0x" + word
    raise ValueError(f"unsupported static type {kind}")


def decode_values(types, data):
    """Decode a flat ABI tuple of static types, strings, bytes and uint256[]/address[]."""
    words = data[2:] if data.startswith("0x") else data
    values = []
    for index, kind in enumerate(types):
        head = words[64 * index:64 * index + 64]
        if kind in ("string", "bytes"):
            offset = int(head, 16) * 2
            length = int(words[offset:offset + 64], 16) * 2
            raw = bytes.fromhex(words[offset + 64:offset + 64 + length])
            values.append(raw.decode("utf-8", "replace") if kind == "string" else "0x" + raw.hex())
        elif kind.endswith("[]"):
            offset = int(head, 16) * 2
            length = int(words[offset:offset + 64], 16)
            values.append([decode_word(kind[:-2], words[offset + 64 + 64 * i:offset + 128 + 64 * i]) for i in range(length)])
        else:
            values.append(decode_word(kind, head))
    return values


def decode_log(events, log):
    event = events.get(log["topics"][0].lower())
    if event is None:
        return None
    args, topics = {}, iter(log["topics"][1:])
    unindexed = [p for p in event["params"] if not p["indexed"]]
    data = decode_values([p["type"] for p in unindexed], log["data"]) if unindexed else []
    for param in event["params"]:
        args[param["name"]] = decode_word(param["type"], next(topics)[2:]) if param["indexed"] else data.pop(0)
    return {"event": event["name"], "args": args, "block": as_int(log["blockNumber"]),
            "logIndex": as_int(log["logIndex"]), "tx": log["transactionHash"], "address": log["address"].lower()}


def schema_uid(schema=PROFILE_SCHEMA, resolver=PROFILE_SCHEMA_RESOLVER, revocable=PROFILE_SCHEMA_REVOCABLE):
    """EAS SchemaRegistry UID: keccak256(abi.encodePacked(schema, resolver, revocable))."""
    packed = schema.encode() + bytes.fromhex(address(resolver)[2:]) + bytes([1 if revocable else 0])
    return "0x" + keccak256(packed).hex()


# ---------------------------------------------------------------- JSON-RPC
class RpcError(RuntimeError):
    pass


class Rpc:
    def __init__(self, url, timeout=15, retries=2):
        self.url, self.timeout, self.retries = url, timeout, retries
        self.calls = 0
        self.deadline = time.monotonic() + 600

    def request(self, method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        last = None
        for attempt in range(self.retries):
            if time.monotonic() >= self.deadline:
                raise RpcError("collection time budget exceeded")
            try:
                # Cloudflare in front of sepolia.base.org rejects the default Python user agent with 403.
                headers = {"content-type": "application/json", "user-agent": "microcredit-lending-dashboard/1"}
                request = urllib.request.Request(self.url, data=body, headers=headers)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                self.calls += 1
                if "error" in payload:
                    raise RpcError("provider rejected request")
                return payload["result"]
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                last = error
                time.sleep(2 ** attempt)
        raise RpcError("provider request failed")

    def block(self, number="latest"):
        tag = number if isinstance(number, str) else hex(number)
        header = self.request("eth_getBlockByNumber", [tag, False])
        if header is None:
            raise RpcError(f"block {tag} not found")
        return header

    def call(self, to, signature, *args, block="latest", types=None):
        kinds = signature[signature.index("(") + 1:signature.index(")")]
        kinds = [k for k in kinds.split(",") if k]
        data = selector(signature) + "".join(encode_word(k, v) for k, v in zip(kinds, args))
        tag = block if isinstance(block, str) else hex(block)
        raw = self.request("eth_call", [{"to": to, "data": data}, tag])
        return decode_values(types, raw) if types else raw

    def logs(self, addresses, from_block, to_block, topics=None, chunk=10_000):
        """eth_getLogs over a range, splitting the range when the node refuses it."""
        found, start = [], from_block
        while start <= to_block:
            end = min(start + chunk - 1, to_block)
            params = {"address": addresses, "fromBlock": hex(start), "toBlock": hex(end)}
            if topics:
                params["topics"] = topics
            try:
                found.extend(self.request("eth_getLogs", [params]))
            except RpcError as error:
                if chunk <= 200:
                    raise
                chunk //= 4
                continue
            start = end + 1
        return found


# ---------------------------------------------------------------- collection
def profile_schema_state(rpc, block):
    uid = schema_uid()
    raw = rpc.call(SCHEMA_REGISTRY, "getSchema(bytes32)", uid, block=block)
    # SchemaRecord(bytes32 uid, address resolver, bool revocable, string schema), returned as one tuple.
    record = decode_values(["bytes32", "address", "bool", "string"], "0x" + raw[2 + 64:]) if len(raw) > 2 + 64 * 4 else None
    registered = bool(record) and record[0].lower() == uid.lower()
    return {"uid": uid, "schema": PROFILE_SCHEMA, "resolver": PROFILE_SCHEMA_RESOLVER,
            "revocable": PROFILE_SCHEMA_REVOCABLE, "registry": SCHEMA_REGISTRY, "eas": EAS, "registered": registered}


def encode_values(types, values):
    """ABI-encode a flat tuple of static types and strings (enough for the profile schema)."""
    head, tail = [], []
    head_size = 32 * len(types)
    for kind, value in zip(types, values):
        if kind == "string":
            raw = value.encode("utf-8")
            head.append(format(head_size + sum(len(t) // 2 for t in tail), "064x"))
            padded = raw.hex().ljust(((len(raw) + 31) // 32) * 64, "0")
            tail.append(format(len(raw), "064x") + padded)
        else:
            head.append(encode_word(kind, value))
    return "0x" + "".join(head) + "".join(tail)


PROFILE_TYPES = ["uint256", "string", "string", "string", "string", "uint8", "uint8"]


def encode_profile(loan_id, country, region, occupation, purpose, income_band, consent_version):
    """Attestation data for the profile schema; the steward passes it to EAS.attest."""
    if income_band not in INCOME_BANDS:
        raise ValueError("income band must be 0 to 4")
    return encode_values(PROFILE_TYPES, [loan_id, country, region, occupation, purpose, income_band, consent_version])


def decode_profile(data):
    loan_id, country, region, occupation, purpose, income_band, consent = decode_values(PROFILE_TYPES, data)
    return {"loanId": loan_id, "country": country, "region": region, "occupation": occupation, "purpose": purpose,
            "incomeBand": income_band, "incomeBandLabel": INCOME_BANDS.get(income_band, "unknown band"),
            "consentVersion": consent}


def read_attestations(rpc, logs_rpc, block, from_block, pool_address, schema):
    # Disabled irrespective of attester, consent claims, expiry or loan linkage.
    # Do not fetch or publish personal attributes, even if supplied by a provider.
    return []


def read_pool_logs(logs_rpc, pool_address, from_block, block):
    events = {parse_event(s)["topic"]: parse_event(s) for s in POOL_EVENTS}
    raw = logs_rpc.logs([pool_address], from_block, block)
    seen, decoded = {}, []
    for log in raw:
        if (log.get("removed") or log["address"].lower() != pool_address.lower()
                or not from_block <= as_int(log["blockNumber"]) <= block):
            raise RpcError("invalid log boundary")
        key = (as_int(log["blockNumber"]), as_int(log["logIndex"]))
        if key in seen:
            if seen[key] != log:
                raise RpcError("conflicting duplicate log")
            continue
        seen[key] = log
        item = decode_log(events, log)
        if item is not None:
            if item["event"] == "MetaLoanRepaid":
                item["event"] = "LoanRepaid"
            item["blockHash"] = log["blockHash"].lower()
            decoded.append(item)
    decoded.sort(key=lambda d: (d["block"], d["logIndex"]))
    return decoded


def block_times(rpc, numbers, cache=None):
    cache = {} if cache is None else cache
    for number in sorted(set(numbers)):
        if number not in cache:
            cache[number] = as_int(rpc.block(number)["timestamp"])
    return cache


def build_loans(events, times, loan_terms):
    loans = {}
    first_seen = {}
    for item in events:
        args = item["args"]
        if "loanId" not in args:
            continue
        loan = loans.setdefault(args["loanId"], {
            "id": args["loanId"], "borrower": None, "principal": 0, "rateBps": None, "status": None,
            "requested": None, "disbursed": None, "closed": None, "repayments": [], "repaid": 0, "interest": 0,
            "principalRepaid": 0, "fee": 0, "writtenOff": 0, "recovered": 0, "backerCharged": 0, "impaired": 0,
            "firstLoan": None, "txs": {}})
        when = {"block": item["block"], "time": times[item["block"]], "tx": item["tx"]}
        name = item["event"]
        if name == "LoanRequested":
            loan.update(borrower=args["borrower"].lower(), principal=args["amount"], rateBps=args["interestRate"],
                        requested=when)
            loan["firstLoan"] = None
            first_seen.setdefault(loan["borrower"], args["loanId"])
        elif name == "LoanDisbursed":
            loan["disbursed"] = when
            loan["disbursedTo"] = args["to"].lower()
        elif name == "LoanRepaid" and args["amount"] > 0:
            loan["repayments"].append({**when, "amount": args["amount"]})
            loan["repaid"] += args["amount"]
        elif name == "RepaymentApplied":
            loan["interest"] += args["interest"]
            loan["principalRepaid"] += args["principal"]
            loan["fee"] += args["fee"]
            loan["impaired"] = max(0, loan["impaired"] - args["principal"])
        elif name == "LoanCancelled":
            loan["closed"] = {**when, "as": "Cancelled"}
        elif name == "LoanDefaulted":
            loan["closed"] = {**when, "as": "Defaulted"}
            loan["writtenOff"] = args["writtenOff"]
            loan["recovered"] = args["recovered"]
        elif name == "BackerCharged":
            loan["backerCharged"] += args["slashed"] + args["charged"]
        elif name == "LoanImpaired":
            loan["impaired"] = args["impaired"]
    for ident, loan in loans.items():
        status, term, requested_at, disbursed_at, due_at = loan_terms[ident]
        loan["status"] = STATUS[status] if 0 <= status < len(STATUS) else f"unknown({status})"
        if loan["status"] in ("Repaid", "Defaulted", "Cancelled"):
            loan["impaired"] = 0
        loan["termDays"] = term // 86400
        loan["dueAt"] = due_at or None
        if loan["status"] == "Repaid" and loan["repayments"]:
            last = loan["repayments"][-1]
            loan["closed"] = {"block": last["block"], "time": last["time"], "tx": last["tx"], "as": "Repaid"}
            loan["onTime"] = bool(due_at) and last["time"] <= due_at
        loan["daysToRepay"] = (round((loan["closed"]["time"] - loan["disbursed"]["time"]) / 86400, 1)
                               if loan.get("closed") and loan.get("disbursed") and loan["closed"]["as"] == "Repaid" else None)
    return [loans[k] for k in sorted(loans)]


def monthly_series(loans, events, times):
    """Cumulative amounts by UTC month: disbursed principal, repaid (principal + interest), interest, lender deposits."""
    buckets = {}

    def month(ts):
        return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m")

    def add(ts, key, amount):
        buckets.setdefault(month(ts), {"disbursed": 0, "repaid": 0, "interest": 0, "deposited": 0, "withdrawn": 0,
                                       "loans": 0})[key] += amount

    for loan in loans:
        if loan["disbursed"]:
            add(loan["disbursed"]["time"], "disbursed", loan["principal"])
            add(loan["disbursed"]["time"], "loans", 1)
        for repayment in loan["repayments"]:
            add(repayment["time"], "repaid", repayment["amount"])
    for item in events:
        if item["event"] == "RepaymentApplied":
            add(times[item["block"]], "interest", item["args"]["interest"])
        elif item["event"] == "Deposited":
            add(times[item["block"]], "deposited", item["args"]["assets"])
        elif item["event"] == "Withdrawn":
            add(times[item["block"]], "withdrawn", item["args"]["assets"])
    series, running = [], {"disbursed": 0, "repaid": 0, "interest": 0, "deposited": 0, "withdrawn": 0, "loans": 0}
    for key in sorted(buckets):
        for name, value in buckets[key].items():
            running[name] += value
        series.append({"month": key, **buckets[key], "cumulative": dict(running)})
    return series


def backing_edges(events):
    current = {}
    for item in events:
        if item["event"] == "Backed":
            key = (item["args"]["backer"].lower(), item["args"]["borrower"].lower())
            total = item["args"]["secured"] + item["args"]["unsecured"]
            if total:
                current[key] = {"backer": key[0], "borrower": key[1], "secured": item["args"]["secured"],
                                "unsecured": item["args"]["unsecured"], "tx": item["tx"], "block": item["block"]}
            else:
                current.pop(key, None)
    return list(current.values())


def stake_by_account(events):
    stake = {}
    for item in events:
        if item["event"] == "Staked":
            stake[item["args"]["account"].lower()] = stake.get(item["args"]["account"].lower(), 0) + item["args"]["amount"]
        elif item["event"] == "BackerCharged":
            a = item["args"]["backer"].lower()
            stake[a] = stake.get(a, 0) - item["args"]["slashed"]
        elif item["event"] == "Unstaked":
            stake[item["args"]["account"].lower()] = stake.get(item["args"]["account"].lower(), 0) - item["args"]["amount"]
    return stake


def human_metrics(loans, profiles, stake):
    """Loan outcomes only. Neither wallets nor profiles establish human counts."""
    repaid = [l for l in loans if l["status"] == "Repaid"]
    closed = [l for l in loans if l["status"] in ("Repaid", "Defaulted")]
    return {"repaymentRate": {"closedLoans": len(closed), "repaid": len(repaid),
             "defaulted": len(closed) - len(repaid),
             "onTime": sum(bool(l.get("onTime")) for l in repaid),
             "rate": len(repaid) / len(closed) if closed else None},
            "humanBorrowers": None, "sponsorExpenditure": None,
            "incrementalHumanBenefit": None, "profileIngestion": "disabled"}


def profile_breakdown(profiles):
    # Do not derive demographic buckets from supplied personal data.
    return {}


PAGE_CALLS = ("totalAssets()", "lenderCash()", "totalLentOut()", "reservedLiquidity()", "firstLossReserve()",
              "totalStaked()", "lenderCount()", "getLoanRate()", "sharePrice()", "getUtilisation()",
              "getLoanTerms(uint256)", "getAttestation(bytes32)", "getSchema(bytes32)")


def abi_for_page():
    """Topics and selectors the page needs to read the chain itself, so it carries no hashing code."""
    events = {ld["topic"]: {"name": ld["name"], "params": ld["params"]} for ld in map(parse_event, POOL_EVENTS + EAS_EVENTS)}
    return {"events": events, "selectors": {sig: selector(sig) for sig in PAGE_CALLS}}


def git_head():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def reconcile(events, loans, records, pool):
    """Contract 1812e7d: lifecycle, cash, shares, stake, reserve and principal.

    Public getLoan/getLoanTerms state is independent of logs. Sub-cent principal forgiveness is a loss,
    not a repayment. Default recovery includes reserve absorption, not only cash.
    """
    def require(ok):
        if not ok:
            raise RpcError("incomplete or inconsistent ledger")
    require({l["id"] for l in loans} == set(records))
    for loan in loans:
        ident = loan["id"]
        principal, repaid, principal_repaid, borrower, rate, term, requested, disbursed, status, impaired = records[ident][:10]
        items = [e for e in events if e["args"].get("loanId") == ident]
        names = [e["event"] for e in items]
        require(names.count("LoanRequested") == 1)
        require(1 <= status <= 5)
        require(names.count("LoanDisbursed") == (1 if disbursed else 0))
        require(names.count("LoanCancelled") == (1 if status == 5 else 0))
        require(names.count("LoanDefaulted") == (1 if status == 4 else 0))
        require((status in (2, 3, 4)) == bool(disbursed))
        require(loan["principal"] == principal and loan["borrower"] == borrower.lower())
        require(repaid is None or loan["repaid"] == repaid)
        require(principal_repaid is None or loan["principalRepaid"] == principal_repaid)
        repaid, principal_repaid = loan["repaid"], loan["principalRepaid"]
        if len(records[ident]) > 10 and status in (1, 2):
            timestamp, outstanding = records[ident][11], records[ident][10]
            elapsed = timestamp - disbursed if disbursed else 0
            interest = (principal * rate // 10000) * elapsed // (365 * 86400) if elapsed >= 86400 else 0
            require(outstanding == max(0, principal + interest - repaid))
        require(loan["interest"] + principal_repaid == repaid and loan["rateBps"] == rate)
        require(loan["requested"]["time"] == requested)
        require(not disbursed or loan["disbursed"]["time"] == disbursed)
        require(not disbursed or requested <= disbursed)
        require(status != 3 or (bool(loan["repayments"]) and principal - principal_repaid < 10_000))
        require(0 <= principal_repaid <= principal)
        if status == 4:
            require(loan["writtenOff"] == principal - principal_repaid)
        # Each applied payment must have its paid event in the same transaction.
        for tx in {e["tx"] for e in items}:
            paid = sum(e["args"]["amount"] for e in items if e["tx"] == tx and e["event"] == "LoanRepaid")
            applied = sum(e["args"]["principal"] + e["args"]["interest"] for e in items
                          if e["tx"] == tx and e["event"] == "RepaymentApplied")
            require(paid == applied)
        for e in items:
            args = e["args"]
            require("borrower" not in args or args["borrower"].lower() == borrower.lower())
            require(e["event"] != "LoanDisbursed" or args["amount"] == principal)
    def total(name, field):
        return sum(e["args"][field] for e in events if e["event"] == name)
    require(pool["totalLentOut"] == sum(l["principal"] - l["principalRepaid"] for l in loans if l["status"] == "Active"))
    require(pool["reservedLiquidity"] == sum(r[0] for r in records.values() if r[8] == 1))
    require(pool["totalImpaired"] == sum(l["impaired"] for l in loans))
    cash = (total("Deposited", "assets") - total("Withdrawn", "assets") + total("ReserveFunded", "amount")
            - total("LoanDisbursed", "amount") + total("LoanRepaid", "amount")
            - total("RepaymentApplied", "fee") + total("BackerCharged", "slashed"))
    require(cash == pool["lenderCash"])
    require(pool["totalShares"] == total("Deposited", "shares") - total("Withdrawn", "shares"))
    require(pool["totalStaked"] == sum(stake_by_account(events).values()))
    forgiven = sum(l["principal"] - l["principalRepaid"] for l in loans if l["status"] == "Repaid")
    # Reserve absorption of forgiven dust is capped by the reserve at that moment;
    # replay cash allocations to preserve that cap rather than assume all dust is covered.
    # If dust exists, exact reserve reconciliation needs allocation events not in this ABI.
    require(forgiven == 0)  # conservative refusal; never publish a guessed reserve flow
    reserve = (total("ReserveFunded", "amount") + pool["totalDuesPaid"] - total("ReserveReleased", "amount")
               - total("LoanDefaulted", "recovered") + total("BackerCharged", "slashed"))
    require(pool["firstLossReserve"] == reserve)
    require(pool["totalAssets"] == max(0, cash + pool["totalLentOut"]
                                       - max(pool["firstLossReserve"], pool["totalImpaired"])))


def collect(deployment, rpc, logs_rpc, block="finalized", from_block=DEPLOYMENT_BLOCK):
    if from_block != DEPLOYMENT_BLOCK:
        raise RpcError("full deployment history required")
    chain = deployment["chain_id"]
    for provider in (rpc, logs_rpc):
        if as_int(provider.request("eth_chainId", [])) != chain:
            raise RpcError("provider chain mismatch")
    finalized = [p.block("finalized") for p in (rpc, logs_rpc)]
    ceiling = min(as_int(h["number"]) for h in finalized)
    number = ceiling if block in ("latest", "finalized") else as_int(block)
    if not from_block <= number <= ceiling:
        raise RpcError("block outside finalized history")
    header = rpc.block(number)
    if as_int(header["number"]) != number:
        raise RpcError("wrong state boundary")
    def match(number, expected):
        for provider in (rpc, logs_rpc):
            h = provider.block(number)
            if (as_int(h["number"]) != number or h["hash"].lower() != expected["hash"].lower()
                    or as_int(h["timestamp"]) != as_int(expected["timestamp"])):
                raise RpcError("provider block mismatch")
    match(number, header)
    start = rpc.block(from_block)
    match(from_block, start)
    pool_address = deployment["pool"]
    if rpc.call(pool_address, "usdc()", block=number, types=["address"])[0].lower() != deployment["token"]["address"].lower():
        raise RpcError("pool token wiring mismatch")
    pool = {name: rpc.call(pool_address, f"{name}()", block=number, types=["uint256"])[0] for name in POOL_FIELDS}
    pool["sharePrice"] = rpc.call(deployment["lens"], "sharePrice()", block=number, types=["uint256"])[0]
    pool["utilisationBps"] = rpc.call(deployment["lens"], "getUtilisation()", block=number, types=["uint256"])[0]
    for key, sig in (("lenders", "getLenders()"), ("borrowers", "getBorrowers()")):
        pool[key] = [a.lower() for a in rpc.call(pool_address, sig, block=number, types=["address[]"])[0]]
    events = read_pool_logs(logs_rpc, pool_address, from_block, number)
    times = {}
    for n in sorted({e["block"] for e in events}):
        h = rpc.block(n)
        match(n, h)
        if any(e["blockHash"] != h["hash"].lower() for e in events if e["block"] == n):
            raise RpcError("log block mismatch")
        times[n] = as_int(h["timestamp"])
    ids = rpc.call(pool_address, "getAllLoanIds()", block=number, types=["uint256[]"])[0]
    if len(ids) != len(set(ids)) or set(ids) != {e["args"]["loanId"] for e in events if "loanId" in e["args"]}:
        raise RpcError("loan inventory mismatch")
    records, terms = {}, {}
    for i in ids:
        principal, outstanding, borrower, rate, active = rpc.call(
            pool_address, "getLoan(uint256)", i, block=number,
            types=["uint256", "uint256", "address", "uint256", "bool"])
        terms[i] = rpc.call(pool_address, "getLoanTerms(uint256)", i, block=number,
                            types=["uint8", "uint256", "uint256", "uint256", "uint256"])
        status, term, requested, disbursed, due = terms[i]
        if active != (status in (1, 2)) or due != (disbursed + term if disbursed else 0):
            raise RpcError("loan state mismatch")
        records[i] = [principal, None, None, borrower, rate, term, requested, disbursed,
                      status, None, outstanding, as_int(header["timestamp"])]
    loans = build_loans(events, times, terms)
    reconcile(events, loans, records, pool)
    match(from_block, start)
    match(number, header)
    deposits = sum(e["args"]["assets"] for e in events if e["event"] == "Deposited")
    withdrawals = sum(e["args"]["assets"] for e in events if e["event"] == "Withdrawn")
    return {
        "snapshot": {"chainId": chain, "network": deployment["network"], "blockNumber": number, "blockHash": header["hash"],
                     "blockTimestamp": as_int(header["timestamp"]),
                     "blockTime": datetime.fromtimestamp(as_int(header["timestamp"]), timezone.utc).isoformat(),
                     "collectedAt": datetime.now(timezone.utc).isoformat(), "verification": "reconciled-finalized-v1",
                     "fromBlock": from_block, "fromBlockHash": start["hash"], "pool": pool_address, "lens": deployment["lens"],
                     "token": deployment["token"], "explorer": deployment["explorer_url"],
                     "collector": "metrics/lending_dashboard.py", "collectorCommit": git_head(), "eventCount": len(events)},
        "abi": abi_for_page(), "pool": pool,
        "flows": {"deposited": deposits, "withdrawn": withdrawals,
                  "disbursed": sum(l["principal"] for l in loans if l["disbursed"]),
                  "repaid": sum(l["repaid"] for l in loans), "interest": sum(l["interest"] for l in loans),
                  "fees": sum(l["fee"] for l in loans), "writtenOff": sum(l["writtenOff"] for l in loans),
                  "reserveFunded": sum(e["args"]["amount"] for e in events if e["event"] == "ReserveFunded"),
                  "reserveReleased": sum(e["args"]["amount"] for e in events if e["event"] == "ReserveReleased")},
        "loans": loans, "loanStatus": {name: sum(l["status"] == name for l in loans) for name in STATUS[1:]},
        "monthly": monthly_series(loans, events, times),
        # Backed events alone do not reflect implicit releases and slashing. Do not present current edges.
        "backing": [], "stake": {k: v for k, v in stake_by_account(events).items() if v},
        "profileSchema": {"uid": schema_uid(), "enabled": False}, "profiles": [], "profileBreakdown": {},
        "humanMetrics": human_metrics(loans, [], {}),
        "caveats": ["Base Sepolia testnet; test USDC has no real monetary value.",
                    "Loan and repayment events do not establish human borrowers or human benefit.",
                    "Sponsor expenditure and incremental human benefit are NOT MEASURED.",
                    "Profile ingestion and publication are disabled. Wallet-linked chain data is pseudonymous and permanent; revocation cannot erase history."],
    }


def atomic_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        name = f.name
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_attempt(out_dir, status):
    atomic_text(out_dir / "refresh-status.json", json.dumps({"attemptedAt": datetime.now(timezone.utc).isoformat(),
                                                          "status": status}) + "\n")


def write_outputs(report, out_dir):
    # Both payloads must be reviewed/published in one Git commit. Browser consumes
    # JSON only on refresh and JS only at boot: it never combines their state.
    if report.get("profiles") or report.get("profileBreakdown"):
        raise ValueError("profile publication disabled")
    text = json.dumps(report, indent=1, sort_keys=True)
    atomic_text(out_dir / "snapshot.json", text + "\n")
    atomic_text(out_dir / "snapshot.js", "window.LENDING_SNAPSHOT = " + text + ";\n")


def print_summary(report):
    s, p, f, h = report["snapshot"], report["pool"], report["flows"], report["humanMetrics"]
    print(f"Pool {s['pool']} on chain {s['chainId']} at block {s['blockNumber']} ({s['blockTime']}), {s['eventCount']} events")
    print(f"  assets {format_units(p['totalAssets'])}  cash {format_units(p['lenderCash'])}  lent {format_units(p['totalLentOut'])}  "
          f"reserve {format_units(p['firstLossReserve'])}  lenders {p['lenderCount']}  share price {format_units(p['sharePrice'], 4)}")
    print(f"  deposited {format_units(f['deposited'])}  withdrawn {format_units(f['withdrawn'])}  disbursed {format_units(f['disbursed'])}  "
          f"repaid {format_units(f['repaid'])}  interest {format_units(f['interest'])}  written off {format_units(f['writtenOff'])}")
    print("  loans: " + ", ".join(f"{k} {v}" for k, v in report["loanStatus"].items() if v))
    r = h["repaymentRate"]
    print(f"  repayment: {r['repaid']} of {r['closedLoans']} closed loans repaid ({r['onTime']} on time), {r['defaulted']} defaulted")
    print("  profiles disabled; human benefit and sponsor expenditure NOT MEASURED")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--block", default="finalized", help="finalized boundary, or an older block")
    parser.add_argument("--from-block", type=int, default=DEPLOYMENT_BLOCK, help="first block to scan for events")
    parser.add_argument("--logs-rpc", default=os.environ.get("LOGS_RPC", DEFAULT_LOGS_RPC),
                        help="RPC for eth_getLogs over wide ranges (the recorded RPC caps ranges at 200 blocks)")
    parser.add_argument("--out", default=str(ROOT / "dashboard" / "data"), help="directory for snapshot.json and snapshot.js")
    parser.add_argument("--no-write", action="store_true", help="print the summary only")
    parser.add_argument("--json", action="store_true", help="print the full report instead of the summary")
    parser.add_argument("--schema-uid", action="store_true", help="print the profile schema and its UID, then exit")
    args = parser.parse_args(argv)
    if args.schema_uid:
        print(json.dumps({"schema": PROFILE_SCHEMA, "resolver": PROFILE_SCHEMA_RESOLVER,
                          "revocable": PROFILE_SCHEMA_REVOCABLE, "uid": schema_uid()}, indent=1))
        return 0
    try:
        deployment = load_deployment()
        block = args.block if args.block in ("latest", "finalized") else as_int(args.block)
        report = collect(deployment, Rpc(deployment["rpc_url"]), Rpc(args.logs_rpc), block, args.from_block)
    except (RpcError, ValueError, OSError, KeyError, IndexError, TypeError) as error:
        if not args.no_write:
            write_attempt(Path(args.out), "failed")
        print("Collection failed; last successful snapshot preserved.", file=sys.stderr)
        return 1
    if not args.no_write:
        write_outputs(report, Path(args.out))
        write_attempt(Path(args.out), "success")
    print(json.dumps(report, indent=1, sort_keys=True)) if args.json else print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
