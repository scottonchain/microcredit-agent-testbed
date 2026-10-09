"""Recorded deployment, exact token amounts and one-shot Foundry calls.

The descriptor records evidence; a live command checks the RPC's chain separately.
No command is run, account inspected or key read when this module is imported.
"""
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
UINT256_MAX = 2**256 - 1
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}\Z")


def address(value):
    if not isinstance(value, str) or not ADDRESS.fullmatch(value):
        raise ValueError("expected a 20-byte 0x address")
    return value


def load_deployment(environ=None):
    env = os.environ if environ is None else environ
    data = json.loads((ROOT / "deployments/current.json").read_text(encoding="utf-8"))
    if data["schema_version"] != 1 or data["chain_id"] != 84532 or data["token"]["decimals"] != 6:
        raise ValueError("unsupported deployment: these tools require Base Sepolia USDC")
    for key, variable in (("pool", "POOL"), ("lens", "LENS"), ("scores", "SCORES")):
        data[key] = address(env.get(variable, data[key]))
    data["token"]["address"] = address(env.get("USDC", data["token"]["address"]))
    data["rpc_url"] = env.get("RPC", data["rpc_url"])
    return data


def token_units(value, *, allow_zero=False):
    """Parse plain USDC decimals exactly, without floats or shell arithmetic."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,6})?", value):
        raise ValueError("amount must be a nonnegative decimal with at most 6 decimal places")
    whole, _, fraction = value.partition(".")
    amount = int(whole) * 1_000_000 + int(fraction.ljust(6, "0") or "0")
    if amount > UINT256_MAX or (amount == 0 and not allow_zero):
        raise ValueError("amount must be positive and fit in uint256" if not allow_zero else "amount exceeds uint256")
    return amount


def as_int(value):
    if type(value) is int:
        return value
    return int(value, 16) if isinstance(value, str) and value.startswith("0x") else int(value)


def format_units(value, places=2):
    # Integer arithmetic avoids rounding large uint256 balances through float.
    amount = as_int(value)
    sign = "-" if amount < 0 else ""
    whole, fractional = divmod(abs(amount), 1_000_000)
    return f"{sign}{whole:,}.{fractional:06d}"[: -(6 - places)] if places < 6 else f"{sign}{whole:,}.{fractional:06d}"


class CastError(RuntimeError):
    pass


class Cast:
    def __init__(self, deployment):
        self.deployment = deployment
        self.rpc = deployment["rpc_url"]

    def run(self, *args, timeout=60):
        argv = ["cast", *map(str, args)]
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise CastError("cast timed out; if this was a send, reconcile its outcome before retrying") from None
        except FileNotFoundError:
            raise CastError("Foundry's cast is required on PATH") from None
        if result.returncode:
            detail = (result.stderr or result.stdout).strip()
            for flag in ("--private-key",):
                if flag in argv:
                    detail = detail.replace(argv[argv.index(flag) + 1], "<redacted>")
            suffix = "; send outcome unconfirmed: reconcile before retrying" if args[0] == "send" else ""
            raise CastError(f"cast {args[0]} failed: {detail[:800]}{suffix}")
        return result.stdout.strip()

    def check_chain(self):
        actual = as_int(self.run("chain-id", "--rpc-url", self.rpc))
        if actual != self.deployment["chain_id"]:
            raise CastError(f"RPC chain is {actual}; expected Base Sepolia ({self.deployment['chain_id']})")

    def check_wiring(self, block=None):
        d = self.deployment
        for contract, signature, expected in (
            (d["pool"], "usdc()(address)", d["token"]["address"]),
            (d["pool"], "scoreProvider()(address)", d["scores"]),
            (d["lens"], "credit()(address)", d["pool"]),
        ):
            actual = self.call(contract, signature, block=block)[0]
            if address(actual).lower() != expected.lower():
                raise CastError(f"deployment wiring mismatch at {signature}; check deployment overrides")
        if self.num(d["token"]["address"], "decimals()(uint8)", block=block) != d["token"]["decimals"]:
            raise CastError("token decimals do not match the deployment descriptor")

    def call(self, to, signature, *args, block=None, account=None):
        flags = []
        if block is not None:
            flags += ["--block", str(block)]
        if account is not None:
            flags += ["--from", address(account)]
        return json.loads(self.run("call", "--json", "--rpc-url", self.rpc, *flags, to, signature, *args))

    def num(self, to, signature, *args, **kwargs):
        return as_int(self.call(to, signature, *args, **kwargs)[0])

    def block(self, number="latest"):
        return json.loads(self.run("block", "--json", "--rpc-url", self.rpc, str(number)))

    def send(self, private_key, to, signature, *args):
        """Send once. Never rebuild a transaction after an unknown outcome."""
        raw = self.run("send", "--json", "--rpc-url", self.rpc,
                       "--private-key", private_key, to, signature, *args, timeout=180)
        try:
            receipt = json.loads(raw)
        except ValueError:
            raise CastError("malformed send response; reconcile its outcome before retrying") from None
        if not isinstance(receipt, dict):
            raise CastError("send response is not a receipt; reconcile before retrying")
        tx = receipt.get("transactionHash")
        if not isinstance(tx, str) or not re.fullmatch(r"0x[0-9a-fA-F]{64}", tx):
            raise CastError("send returned no transaction hash; reconcile before retrying")
        if as_int(receipt.get("status", 0)) != 1:
            raise CastError(f"transaction {tx} reverted; dependent steps were not sent")
        print(f"transactionHash {tx}\nstatus 1")
        return receipt
