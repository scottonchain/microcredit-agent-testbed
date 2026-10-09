#!/usr/bin/env python3
"""Chain helpers for the live run (Base Sepolia only). Keys are read from the files named by RETRY_FIXTURE_RELAYER_KEY_FILE /
RETRY_FIXTURE_BORROWER_KEY_FILE and passed to `cast`; never printed. Requires foundry's cast on PATH.
Pool and token come from RETRY_FIXTURE_POOL / RETRY_FIXTURE_USDC. Defaults reproduce the historical October 3 MockUSDC
run, not the current public pool. Current public tooling uses deployments/current.json. The first run (EVIDENCE.json) used the pre-redesign pool
0x09d9D1fd4Ed5EC5d9e8ceB9275D864D9c8d99A1f with token 0xa12a5c8C8605945d5e07E4Ea4A95de45d6a9807C."""
import json, os, re, subprocess, time, urllib.request

RPC = os.environ.get("RETRY_FIXTURE_RPC", "https://sepolia.base.org")
CHAIN_ID = 84532
POOL = os.environ.get("RETRY_FIXTURE_POOL", "0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8")
USDC = os.environ.get("RETRY_FIXTURE_USDC", "0x7C46870111257d8A3aaF846BC6D2F7DA7FBb76f1")
DEPLOYER = "0x5e4dC7639D2b94006c51aD5373173f5e01c248F9"
DEPLOYER_KEY_FILE = os.environ.get("RETRY_FIXTURE_RELAYER_KEY_FILE", "relayer.key")
BORROWER_KEY_FILE = os.environ.get("RETRY_FIXTURE_BORROWER_KEY_FILE", "borrower.key")
REPAY_SIG = "repayLoanMeta((address,uint256,uint256,uint256,uint256),bytes,(uint256,uint256,uint8,bytes32,bytes32))"
BORROW_SIG = "borrowAndDisburseMeta((address,uint256,address,uint256,uint256,uint256,uint256),bytes)"
REPAY_TYPE = "RepayRequest(address borrower,uint256 loanId,uint256 amount,uint256 nonce,uint256 deadline)"
BORROW_TYPE = "BorrowAndDisburse(address borrower,uint256 amount,address to,uint256 repaymentPeriod,uint256 maxAprBps,uint256 nonce,uint256 deadline)"
PERMIT_TYPE = "Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"
DOMAIN_TYPE = "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"


def cast(*args, timeout=90):
    argv = ["cast", *map(str, args)]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("cast %s timed out" % args[0]) from None
    if result.returncode:
        detail = (result.stdout + result.stderr).strip()
        if "--private-key" in argv:
            detail = detail.replace(argv[argv.index("--private-key") + 1], "<redacted>")
        raise RuntimeError("cast %s failed: %s" % (args[0], detail[:400]))
    return result.stdout.strip()


def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())


def keccak_text(s):
    return cast("keccak", s)


def keccak_hex(h):
    return cast("keccak", h)


def abi_encode(types, *values):
    return cast("abi-encode", "f(%s)" % types, *values)


def key(path):
    return open(path).read().strip()


def addr_of(path):
    return cast("wallet", "address", "--private-key", key(path))


def call(to, sig, *args, block=None, frm=None):
    extra = []
    if block is not None:
        extra += ["--block", str(block)]
    if frm:
        extra += ["--from", frm]
    for attempt in range(12):   # the public RPC is load-balanced; a node may not yet have the receipt's block
        try:
            return cast("call", to, sig, *args, "--rpc-url", RPC, *extra)
        except RuntimeError as e:
            if "block not found" in str(e) or "missing trie node" in str(e) or "header not found" in str(e):
                time.sleep(3)
                continue
            raise
    raise RuntimeError("block %s not served by the RPC after retries" % block)


JOURNAL = os.environ.get("RETRY_FIXTURE_JOURNAL", os.path.join(os.path.dirname(os.path.abspath(__file__)), "JOURNAL.jsonl"))


def journal(entry):
    """Append-only intent journal written BEFORE broadcast (the fixture's own rule), then updated with the tx hash."""
    entry = dict(entry, t=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    created = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a") as f:
        f.write(json.dumps(entry) + "\n")
        f.flush()
        os.fsync(f.fileno())
    if created:
        directory = os.open(os.path.dirname(os.path.abspath(JOURNAL)), os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    return entry


def call_data(to, data, frm=None):
    extra = ["--from", frm] if frm else []
    r = subprocess.run(["cast", "call", to, "--data", data, "--rpc-url", RPC, *extra], capture_output=True, text=True, timeout=90)
    return r.returncode, (r.stdout + r.stderr).strip()


def domain_separator(name, version, verifying):
    return keccak_hex(abi_encode("bytes32,bytes32,bytes32,uint256,address", keccak_text(DOMAIN_TYPE), keccak_text(name),
                                 keccak_text(version), CHAIN_ID, verifying))


def sign_struct(key_file, ds, struct_hash):
    digest = keccak_hex("0x1901" + ds[2:] + struct_hash[2:])
    sig = cast("wallet", "sign", "--no-hash", "--private-key", key(key_file), digest)
    assert len(sig) == 132, sig[:10]
    return sig, digest


def sign_repay(key_file, borrower, loan_id, amount, nonce, deadline):
    sh = keccak_hex(abi_encode("bytes32,address,uint256,uint256,uint256,uint256", keccak_text(REPAY_TYPE), borrower, loan_id, amount, nonce, deadline))
    return sign_struct(key_file, domain_separator("DecentralizedMicrocredit", "1", POOL), sh)[0]


def sign_borrow(key_file, borrower, amount, to, period, max_apr, nonce, deadline):
    sh = keccak_hex(abi_encode("bytes32,address,uint256,address,uint256,uint256,uint256,uint256", keccak_text(BORROW_TYPE), borrower, amount, to,
                               period, max_apr, nonce, deadline))
    return sign_struct(key_file, domain_separator("DecentralizedMicrocredit", "1", POOL), sh)[0]


def sign_permit(key_file, owner, spender, value, deadline):
    ds = call(USDC, "DOMAIN_SEPARATOR()(bytes32)")
    nonce = int(call(USDC, "nonces(address)(uint256)", owner).split()[0])
    sh = keccak_hex(abi_encode("bytes32,address,address,uint256,uint256,uint256", keccak_text(PERMIT_TYPE), owner, spender, value, nonce, deadline))
    sig, _ = sign_struct(key_file, ds, sh)
    r, s, v = sig[2:66], sig[66:130], int(sig[130:132], 16)
    return "(%d,%d,%d,0x%s,0x%s)" % (value, deadline, v, r, s)


def no_permit():
    return "(0,0,0,0x%s,0x%s)" % ("0" * 64, "0" * 64)


def repay_calldata(borrower, loan_id, amount, nonce, deadline, sig, permit_tuple):
    req = "(%s,%d,%d,%d,%d)" % (borrower, loan_id, amount, nonce, deadline)
    return cast("calldata", REPAY_SIG, req, sig, permit_tuple)


def borrow_calldata(borrower, amount, to, period, max_apr, nonce, deadline, sig):
    req = "(%s,%d,%s,%d,%d,%d,%d)" % (borrower, amount, to, period, max_apr, nonce, deadline)
    return cast("calldata", BORROW_SIG, req, sig)


def to_int(x):
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        return int(x, 16) if x.startswith("0x") else int(x)
    return x


def wait_receipt(txhash):
    for _ in range(60):
        r = rpc("eth_getTransactionReceipt", [txhash])
        if r.get("result"):
            return r["result"]
        time.sleep(3)
    raise RuntimeError("no receipt for " + txhash)


class BroadcastOutcomeUnknown(RuntimeError):
    """The command may have broadcast. Reconcile the intent before another send."""


def _send_async(args):
    """One broadcast attempt. Never recreate a transaction after a lost response.

    Even `already known`, a timeout, 429 or a gas-estimation diagnostic does not
    authorize another cast send: a fresh invocation could use a fresh nonce.
    The persisted intent is the starting point for explicit reconciliation.
    Error text and TimeoutExpired.cmd may contain a key, so neither is exposed.
    """
    try:
        result = subprocess.run(["cast", args[0], "--async", *args[1:]],
                                capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise BroadcastOutcomeUnknown("broadcast response timed out; reconcile the journal before retrying") from None
    if result.returncode == 0:
        hashes = [value for value in result.stdout.split() if re.fullmatch(r"0x[0-9a-fA-F]{64}", value)]
        if len(hashes) == 1:
            return hashes[0]
    raise BroadcastOutcomeUnknown("broadcast response did not establish one transaction hash; reconcile the journal before retrying")


def broadcast(args, intent):
    journal(dict(intent, state="intent"))
    try:
        tx_hash = _send_async(args)
    except BroadcastOutcomeUnknown:
        journal({"step": intent.get("step"), "state": "broadcast_unknown", "to": intent.get("to")})
        raise
    journal({"step": intent.get("step"), "state": "broadcast", "to": intent.get("to"), "tx": tx_hash})
    return wait_receipt(tx_hash)


def send_data(key_file, to, data, gas_limit=None, value=None, step=None):
    """Sends a raw-calldata tx and returns its receipt (dict, hex fields) even if it reverted on chain.
    Journal: intent row before broadcast, hash row after broadcast, so an interrupted run can be reconciled from the chain."""
    args = ["send", to, data, "--rpc-url", RPC, "--private-key", key(key_file)]
    if gas_limit:
        args += ["--gas-limit", str(gas_limit)]
    if value:
        args += ["--value", str(value)]
    return broadcast(args, {"step": step, "to": to, "data": data, "gas_limit": gas_limit})


def create(key_file, bytecode, step=None):
    args = ["send", "--rpc-url", RPC, "--private-key", key(key_file), "--create", bytecode]
    return broadcast(args, {"step": step, "to": None, "data_sha256": __import__("hashlib").sha256(bytes.fromhex(bytecode[2:])).hexdigest()})


def send_sig(key_file, to, sig, *args, gas_limit=None, step=None):
    data = cast("calldata", sig, *args)
    return send_data(key_file, to, data, gas_limit=gas_limit, step=step)


def nonces(addr, block=None):
    return int(call(POOL, "nonces(address)(uint256)", addr, block=block).split()[0])


def now():
    return int(time.time())
