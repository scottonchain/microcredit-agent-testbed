#!/usr/bin/env python3
"""Read-only canonical identity snapshot; never a new-mechanism acceptance pass.

Only the descriptor's public Base Sepolia endpoint is supported. No environment
address overrides, signing, transaction submission, local forks or admin changes.
Code SHA256 identifies observed bytes; it is not an Ethereum Keccak code hash.
Compare with an independently verified release before any acceptance campaign.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}\Z")
HEX = re.compile(r"0x(?:[0-9a-fA-F]{2})*\Z")
READ_METHODS = frozenset(("eth_chainId", "eth_getBlockByNumber", "eth_getCode", "web3_clientVersion"))


class GateError(RuntimeError):
    pass


def descriptor():
    data = json.loads((ROOT / "deployments/current.json").read_text())
    if (data.get("schema_version") != 1 or data.get("chain_id") != 84532
            or data.get("rpc_url") != "https://sepolia.base.org"
            or data.get("token", {}).get("decimals") != 6):
        raise GateError("UNSUPPORTED_CANONICAL_DESCRIPTOR: review changed configuration")
    for addr in (data.get("pool"), data.get("scores"), data.get("lens"), data["token"].get("address")):
        if not isinstance(addr, str) or not ADDRESS.fullmatch(addr):
            raise GateError("INVALID_CANONICAL_ADDRESS")
    return data


class RPC:
    def __init__(self, url):
        self.url = url

    def call(self, method, params):
        if method not in READ_METHODS:
            raise GateError("NON_READ_METHOD_FORBIDDEN")
        request = urllib.request.Request(self.url, data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": method, "params": params,
        }).encode(), headers={"Content-Type": "application/json"})
        # Preserve inherited proxy and CA policy. No redirects to another RPC.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=15) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise GateError("RPC_RESPONSE_TOO_LARGE")
            result = json.loads(raw)
        except urllib.error.HTTPError as error:
            raise GateError(f"RPC_HTTP_{error.code}: no live observation") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise GateError("RPC_ACCESS_UNAVAILABLE: no live observation") from None
        except (ValueError, UnicodeError):
            raise GateError("RPC_MALFORMED_RESPONSE") from None
        if not isinstance(result, dict) or result.get("id") != 1 or "error" in result or "result" not in result:
            raise GateError("RPC_INVALID_OR_ERROR_RESPONSE")
        return result["result"]


def snapshot(data, rpc):
    if rpc.call("eth_chainId", []) != hex(84532):
        raise GateError("WRONG_CHAIN")
    version = rpc.call("web3_clientVersion", [])
    if not isinstance(version, str) or any(x in version.lower() for x in ("anvil", "hardhat", "ganache")):
        raise GateError("LOCAL_TEST_NODE_FORBIDDEN")
    header = rpc.call("eth_getBlockByNumber", ["latest", False])
    if not isinstance(header, dict) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", str(header.get("hash", ""))):
        raise GateError("INVALID_BLOCK_HEADER")
    try:
        number, timestamp = int(header["number"], 16), int(header["timestamp"], 16)
    except (ValueError, TypeError, KeyError):
        raise GateError("INVALID_BLOCK_HEADER") from None
    age = datetime.now(timezone.utc).timestamp() - timestamp
    if not -120 <= age <= 900:
        raise GateError("STALE_OR_FUTURE_BLOCK")
    tag = hex(number)
    observed = {}
    targets = {k: data[k] for k in ("pool", "lens", "scores")}
    targets["token"] = data["token"]["address"]
    for role, addr in targets.items():
        code = rpc.call("eth_getCode", [addr, tag])
        if not isinstance(code, str) or not HEX.fullmatch(code) or code in ("0x", "0x00"):
            raise GateError(f"NO_VALID_CODE_{role.upper()}")
        raw = bytes.fromhex(code[2:])
        observed[role] = {"address": addr, "runtime_byte_length": len(raw), "runtime_sha256": hashlib.sha256(raw).hexdigest()}
    final = rpc.call("eth_getBlockByNumber", [tag, False])
    if not isinstance(final, dict) or final.get("hash") != header["hash"]:
        raise GateError("BLOCK_CHANGED_DISCARD_SNAPSHOT")
    return {"chain_id": 84532, "block_number": number, "block_hash": header["hash"],
            "block_timestamp": timestamp, "contracts": observed,
            "scope": "identity observation only; wiring, release bytecode, proxy implementation and mechanism unverified"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new receipt path, never overwrite")
    args = parser.parse_args()
    report = {"schema_version": 1, "kind": "LIVE_READ_ONLY_PREFLIGHT", "transactions_sent": 0,
              "observed_at": datetime.now(timezone.utc).isoformat(), "new_scoring_acceptance": "NOT_RUN"}
    try:
        data = descriptor()
        report["snapshot"] = snapshot(data, RPC(data["rpc_url"]))
        report["verdict"] = "OBSERVED_NOT_RELEASE_VERIFIED"
        code = 0
    except (GateError, OSError, ValueError, KeyError) as error:
        # Error text never includes proxy URL, endpoint credentials or applicant data.
        report["verdict"] = "BLOCKED"
        report["reason"] = str(error) if isinstance(error, GateError) else "INVALID_OR_UNREADABLE_DESCRIPTOR"
        code = 2
    with args.output.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
