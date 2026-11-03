#!/usr/bin/env python3
"""Lending dashboard collector: one on-chain snapshot of the pool's lending economy.

Reads the recorded Base Sepolia pool (deployments/current.json) with plain JSON-RPC and
no external packages: every loan's events, the pool's balance sheet at one block, and the
anonymized borrower profiles attested on-chain under the Omnequa profile schema (EAS).
Writes dashboard/data/snapshot.json plus snapshot.js for dashboard/index.html.

No transaction is sent and no key is read. Exit 0 means a complete snapshot at one block
hash; the block is re-read at the end and a changed hash discards the snapshot.

Event-based human-benefit metrics (METRICS.md 1 to 4, 8 and 10) are recomputed here from
the public ledger. A testnet repayment is not human benefit; "attested" counts come only
from profile attestations, and there are none until the steward registers the schema.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
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
    def __init__(self, url, timeout=60, retries=4):
        self.url, self.timeout, self.retries = url, timeout, retries
        self.calls = 0

    def request(self, method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        last = None
        for attempt in range(self.retries):
            try:
                # Cloudflare in front of sepolia.base.org rejects the default Python user agent with 403.
                headers = {"content-type": "application/json", "user-agent": "microcredit-lending-dashboard/1"}
                request = urllib.request.Request(self.url, data=body, headers=headers)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.load(response)
                self.calls += 1
                if "error" in payload:
                    raise RpcError(f"{method}: {payload['error'].get('message', payload['error'])}")
                return payload["result"]
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                last = error
                time.sleep(2 ** attempt)
        raise RpcError(f"{method} failed after {self.retries} attempts: {last}")

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

    def logs(self, addresses, from_block, to_block, topics=None, chunk=500_000):
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
    events = {parse_event(s)["topic"]: parse_event(s) for s in EAS_EVENTS}
    raw = logs_rpc.logs([EAS], from_block, block, topics=[[e["topic"] for e in events.values()], None, None, schema["uid"]])
    revoked = set()
    attested = []
    for log in sorted(raw, key=lambda l: (as_int(l["blockNumber"]), as_int(l["logIndex"]))):
        decoded = decode_log(events, log)
        if decoded is None:
            continue
        if decoded["event"] == "Revoked":
            revoked.add(decoded["args"]["uid"])
        else:
            attested.append(decoded)
    profiles = []
    types = ["bytes32", "bytes32", "uint64", "uint64", "uint64", "bytes32", "address", "address", "bool", "bytes"]
    for item in attested:
        uid = item["args"]["uid"]
        raw_attestation = rpc.call(EAS, "getAttestation(bytes32)", uid, block=block)
        fields = decode_values(types, "0x" + raw_attestation[2 + 64:])
        if fields[4] or uid in revoked:
            continue  # revoked: the borrower withdrew consent
        try:
            profile = decode_profile(fields[9])
        except (ValueError, IndexError):
            continue
        profile.update({"uid": uid, "attester": fields[7].lower(), "borrower": fields[6].lower(),
                        "attestedAt": fields[2], "tx": item["tx"], "block": item["block"]})
        profiles.append(profile)
    return profiles


def read_pool_logs(logs_rpc, pool_address, from_block, block):
    events = {parse_event(s)["topic"]: parse_event(s) for s in POOL_EVENTS}
    raw = logs_rpc.logs([pool_address], from_block, block)
    decoded = [decode_log(events, log) for log in raw]
    decoded = [d for d in decoded if d is not None]
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
            loan["firstLoan"] = loan["borrower"] not in first_seen
            first_seen.setdefault(loan["borrower"], args["loanId"])
        elif name == "LoanDisbursed":
            loan["disbursed"] = when
            loan["disbursedTo"] = args["to"].lower()
        elif name == "LoanRepaid":
            loan["repayments"].append({**when, "amount": args["amount"]})
            loan["repaid"] += args["amount"]
        elif name == "RepaymentApplied":
            loan["interest"] += args["interest"]
            loan["principalRepaid"] += args["principal"]
            loan["fee"] += args["fee"]
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
        elif item["event"] == "Unstaked":
            stake[item["args"]["account"].lower()] = stake.get(item["args"]["account"].lower(), 0) - item["args"]["amount"]
    return stake


def human_metrics(loans, profiles, stake):
    """METRICS.md 1 to 4, 8 and 10, split attested (profile on-chain) versus unattested."""
    attested_loans = {p["loanId"] for p in profiles}
    attested_borrowers = {p["borrower"] for p in profiles}
    repaid = [l for l in loans if l["status"] == "Repaid"]
    closed = [l for l in loans if l["status"] in ("Repaid", "Defaulted")]
    disbursed = [l for l in loans if l["disbursed"]]
    unique_repaying = {l["borrower"] for l in repaid}
    first_principal = sum(l["principal"] for l in disbursed if l["firstLoan"])
    total_principal = sum(l["principal"] for l in disbursed)
    no_stake_borrowers = {l["borrower"] for l in disbursed if stake.get(l["borrower"], 0) <= 0}
    interest = sum(l["interest"] for l in loans)
    written_off = sum(l["writtenOff"] for l in loans)
    recovered = sum(l["recovered"] for l in loans)
    return {
        "uniqueRepayingBorrowers": {"attested": len(unique_repaying & attested_borrowers),
                                    "unattested": len(unique_repaying - attested_borrowers)},
        "firstTimeBorrowerShare": (first_principal / total_principal) if total_principal else None,
        "disbursedToBorrowersWithNoOwnStake": {"borrowers": len(no_stake_borrowers), "ofBorrowers": len({l["borrower"] for l in disbursed})},
        "repaymentRate": {"closedLoans": len(closed), "repaid": len(repaid),
                          "defaulted": len([l for l in closed if l["status"] == "Defaulted"]),
                          "onTime": len([l for l in repaid if l.get("onTime")]),
                          "rate": (len(repaid) / len(closed)) if closed else None},
        "attestedLoans": {"withProfile": len([l for l in loans if l["id"] in attested_loans]), "ofLoans": len(loans)},
        "netYield": {"interestCollected": interest, "writtenOff": written_off, "recovered": recovered,
                     "net": interest - written_off + recovered},
    }


def profile_breakdown(profiles):
    def count(key):
        out = {}
        for p in profiles:
            out[p[key] or "not stated"] = out.get(p[key] or "not stated", 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
    return {"byCountry": count("country"), "byOccupation": count("occupation"), "byPurpose": count("purpose"),
            "byIncomeBand": count("incomeBandLabel")}


def git_head():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def collect(deployment, rpc, logs_rpc, block="latest", from_block=DEPLOYMENT_BLOCK):
    chain = as_int(rpc.request("eth_chainId", []))
    if chain != deployment["chain_id"]:
        raise RpcError(f"RPC chain is {chain}; expected {deployment['chain_id']}")
    header = rpc.block(block)
    number = as_int(header["number"])
    pool_address = deployment["pool"]
    wired = rpc.call(pool_address, "usdc()", block=number, types=["address"])[0]
    if wired.lower() != deployment["token"]["address"].lower():
        raise RpcError("pool token wiring does not match the deployment descriptor")

    pool = {name: rpc.call(pool_address, f"{name}()", block=number, types=["uint256"])[0] for name in POOL_FIELDS}
    pool["sharePrice"] = rpc.call(deployment["lens"], "sharePrice()", block=number, types=["uint256"])[0]
    pool["utilisationBps"] = rpc.call(deployment["lens"], "getUtilisation()", block=number, types=["uint256"])[0]
    pool["lenders"] = [a.lower() for a in rpc.call(pool_address, "getLenders()", block=number, types=["address[]"])[0]]
    pool["borrowers"] = [a.lower() for a in rpc.call(pool_address, "getBorrowers()", block=number, types=["address[]"])[0]]

    events = read_pool_logs(logs_rpc, pool_address, from_block, number)
    times = block_times(rpc, [e["block"] for e in events], {number: as_int(header["timestamp"])})
    loan_ids = rpc.call(pool_address, "getAllLoanIds()", block=number, types=["uint256[]"])[0]
    terms = {ident: rpc.call(pool_address, "getLoanTerms(uint256)", ident, block=number,
                             types=["uint8", "uint256", "uint256", "uint256", "uint256"]) for ident in loan_ids}
    for ident in {e["args"]["loanId"] for e in events if "loanId" in e["args"]} - set(terms):
        terms[ident] = rpc.call(pool_address, "getLoanTerms(uint256)", ident, block=number,
                                types=["uint8", "uint256", "uint256", "uint256", "uint256"])
    loans = build_loans(events, times, terms)
    schema = profile_schema_state(rpc, number)
    profiles = read_attestations(rpc, logs_rpc, number, from_block, pool_address, schema) if schema["registered"] else []
    stake = stake_by_account(events)

    if rpc.block(number)["hash"].lower() != header["hash"].lower():
        raise RpcError("block changed during collection; discard this snapshot and read again")
    deposits = sum(e["args"]["assets"] for e in events if e["event"] == "Deposited")
    withdrawals = sum(e["args"]["assets"] for e in events if e["event"] == "Withdrawn")
    return {
        "snapshot": {"chainId": chain, "network": deployment["network"], "blockNumber": number, "blockHash": header["hash"],
                     "blockTimestamp": as_int(header["timestamp"]),
                     "blockTime": datetime.fromtimestamp(as_int(header["timestamp"]), timezone.utc).isoformat(),
                     "fromBlock": from_block, "pool": pool_address, "lens": deployment["lens"],
                     "scores": deployment["scores"], "token": deployment["token"],
                     "explorer": deployment["explorer_url"], "stateRpc": rpc.url, "logsRpc": logs_rpc.url,
                     "collector": "metrics/lending_dashboard.py", "collectorCommit": git_head(),
                     "eventCount": len(events), "rpcCalls": rpc.calls + logs_rpc.calls},
        "pool": pool,
        "flows": {"deposited": deposits, "withdrawn": withdrawals,
                  "disbursed": sum(l["principal"] for l in loans if l["disbursed"]),
                  "repaid": sum(l["repaid"] for l in loans), "interest": sum(l["interest"] for l in loans),
                  "fees": sum(l["fee"] for l in loans), "writtenOff": sum(l["writtenOff"] for l in loans)},
        "loans": loans,
        "loanStatus": {name: len([l for l in loans if l["status"] == name]) for name in STATUS[1:]},
        "monthly": monthly_series(loans, events, times),
        "backing": backing_edges(events),
        "stake": {k: v for k, v in stake.items() if v},
        "profileSchema": schema,
        "profiles": profiles,
        "profileBreakdown": profile_breakdown(profiles),
        "humanMetrics": human_metrics(loans, profiles, stake),
        "caveats": [
            "Base Sepolia testnet: test USDC only, no real funds, no real borrowers.",
            "Every loan so far was taken by an AI agent or a team test account; none is a human outcome.",
            "A repaid testnet loan is plumbing evidence, not human benefit (NORTH_STAR.md).",
            "Borrower profiles appear only after the steward registers the profile schema and attests with consent.",
        ],
    }


def write_outputs(report, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=1, sort_keys=True)
    (out_dir / "snapshot.json").write_text(text + "\n", encoding="utf-8")
    (out_dir / "snapshot.js").write_text("window.LENDING_SNAPSHOT = " + text + ";\n", encoding="utf-8")


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
    print(f"  profiles: {h['attestedLoans']['withProfile']} of {h['attestedLoans']['ofLoans']} loans; schema "
          f"{'registered' if report['profileSchema']['registered'] else 'NOT registered'} ({report['profileSchema']['uid']})")
    print(f"  attested repaying borrowers {h['uniqueRepayingBorrowers']['attested']}, unattested {h['uniqueRepayingBorrowers']['unattested']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--block", default="latest", help="read at a specific block instead of latest")
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
        block = args.block if args.block == "latest" else as_int(args.block)
        report = collect(deployment, Rpc(deployment["rpc_url"]), Rpc(args.logs_rpc, timeout=120), block, args.from_block)
    except (RpcError, ValueError, OSError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not args.no_write:
        write_outputs(report, Path(args.out))
    print(json.dumps(report, indent=1, sort_keys=True)) if args.json else print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
