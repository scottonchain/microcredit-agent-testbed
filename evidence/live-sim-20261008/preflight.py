#!/usr/bin/env python3
"""Read-only preflight for HERMES-LIVE-COMMUNITIES-20261008-r1. Prints public facts only, no keys."""
import json, subprocess, sys, hashlib, urllib.request, os
RPC = "https://sepolia.base.org"
CAST = "/root/.foundry/versions/foundry-rs/foundry/v1.8.4/cast"
POOL = "0x73872B8fB7F1771C67911f03edc75aBdc9514973"
USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
PROV = "0x554c6bB61eDF0CAfB90ff31813540369Cb0105e4"
FUNDS = "0x108450c748EEF7AeF23e64739bC508f56E596247"
DEPLOYER = "0x5e4dC7639D2b94006c51aD5373173f5e01c248F9"

def rpc(m, p):
    r = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                               headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
    return json.load(urllib.request.urlopen(r, timeout=30))["result"]

def call(to, sig, *args, block="latest"):
    out = subprocess.run([CAST, "call", to, sig, *map(str, args), "--rpc-url", RPC, "--block", str(block)],
                         capture_output=True, text=True)
    return out.stdout.strip().split(" ")[0] if out.returncode == 0 else "ERR " + out.stderr.strip()[:100]

blk = rpc("eth_getBlockByNumber", ["latest", False])
bn = int(blk["number"], 16)
out = {"chain_id": int(rpc("eth_chainId", []), 16), "block_number": bn, "block_hash": blk["hash"],
       "block_time": int(blk["timestamp"], 16)}
code = {}
for name, a in (("pool", POOL), ("provider", PROV), ("usdc", USDC)):
    c = rpc("eth_getCode", [a, hex(bn)])
    b = bytes.fromhex(c[2:])
    code[name] = {"address": a, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
                  "keccak256": subprocess.run([CAST, "keccak", c], capture_output=True, text=True).stdout.strip()}
out["code"] = code
# manifest comparison (immutables zeroed)
try:
    m = json.load(open("/root/.hermes/cache/scratch/c89/manifest.json"))
    pm = m["contracts"]["DecentralizedMicrocredit"]
    b = bytearray(bytes.fromhex(rpc("eth_getCode", [POOL, hex(bn)])[2:]))
    ranges = pm["immutable_ranges"]
    flat = ranges if isinstance(ranges, list) else list(ranges.values())
    def zero(r):
        s = r.get("start", r.get("offset")); l = r.get("length")
        if s is not None and l is not None:
            b[s:s + l] = bytes(l)
    for r in flat:
        if isinstance(r, dict): zero(r)
        elif isinstance(r, list):
            for x in r:
                if isinstance(x, dict): zero(x)
    out["manifest_template_sha256"] = pm["runtime_template_sha256"]
    out["onchain_with_immutables_zeroed_sha256"] = hashlib.sha256(bytes(b)).hexdigest()
    out["manifest_source_commit"] = m["source_commit"]
except Exception as e:
    out["manifest_compare_error"] = repr(e)[:200]
pf = ["totalAssets()(uint256)", "totalShares()(uint256)", "totalLentOut()(uint256)", "reservedLiquidity()(uint256)",
      "totalStaked()(uint256)", "totalDuesPaid()(uint256)", "firstLossReserve()(uint256)", "lenderCash()(uint256)",
      "totalQueuedShares()(uint256)", "totalImpaired()(uint256)", "totalUnclaimedPayouts()(uint256)", "protocolFees()(uint256)",
      "paused()(bool)", "maxLoanAmount()(uint256)", "reserveBps()(uint256)", "protocolFeeBps()(uint256)",
      "effrRate()(uint256)", "riskPremium()(uint256)", "lendingUtilizationCap()(uint256)", "liquidityBuffer()(uint256)",
      "liquidityThreshold()(uint256)", "relayerWhitelistEnabled()(bool)", "lenderCount()(uint256)"]
out["pool"] = {s.split("(")[0]: call(POOL, s, block=bn) for s in pf}
out["pool"]["usdc_balance"] = call(USDC, "balanceOf(address)(uint256)", POOL, block=bn)
out["provider"] = {s.split("(")[0]: call(PROV, s, block=bn) for s in
                   ["epoch()(uint256)", "totalHeld()(uint256)", "isFresh()(bool)", "lastReportAt()(uint256)", "maxScoreAge()(uint256)"]}
out["lenders"] = {}
for a in subprocess.run([CAST, "call", POOL, "getLenders()(address[])", "--rpc-url", RPC, "--block", str(bn)],
                        capture_output=True, text=True).stdout.strip().strip("[]").split(", "):
    if a:
        out["lenders"][a] = {"sharesOf": call(POOL, "sharesOf(address)(uint256)", a, block=bn),
                             "lenderBalance": call(POOL, "lenderBalance(address)(uint256)", a, block=bn),
                             "queuedShares": call(POOL, "queuedShares(address)(uint256)", a, block=bn),
                             "usdc": call(USDC, "balanceOf(address)(uint256)", a, block=bn)}
out["loan_ids"] = subprocess.run([CAST, "call", POOL, "getAllLoanIds()(uint256[])", "--rpc-url", RPC, "--block", str(bn)],
                                 capture_output=True, text=True).stdout.strip()
wallets = json.load(open("/root/.hermes/cache/scratch/c89/public-wallets.json"))
out["original_13"] = []
for w in wallets:
    a = w["address"]
    out["original_13"].append({"role": w["role"], "address": a,
        "eth_wei": int(rpc("eth_getBalance", [a, hex(bn)]), 16),
        "usdc": call(USDC, "balanceOf(address)(uint256)", a, block=bn),
        "poolShares": call(POOL, "sharesOf(address)(uint256)", a, block=bn),
        "stake": call(POOL, "stakeOf(address)(uint256)", a, block=bn),
        "activeLoans": call(POOL, "activeLoanCount(address)(uint256)", a, block=bn),
        "completedLoans": call(POOL, "completedLoans(address)(uint256)", a, block=bn),
        "nonce": int(rpc("eth_getTransactionCount", [a, hex(bn)]), 16)})
for label, a in (("funds_wallet_0x1084", FUNDS), ("deployer_0x5e4d", DEPLOYER)):
    out[label] = {"address": a, "eth_wei": int(rpc("eth_getBalance", [a, hex(bn)]), 16),
                  "usdc": call(USDC, "balanceOf(address)(uint256)", a, block=bn),
                  "poolShares": call(POOL, "sharesOf(address)(uint256)", a, block=bn),
                  "nonce": int(rpc("eth_getTransactionCount", [a, hex(bn)]), 16)}
out["gas_price_wei"] = int(rpc("eth_gasPrice", []), 16)
json.dump(out, open("/root/work/live-sim-20261008/preflight.json", "w"), indent=1)
print(json.dumps(out, indent=1))
