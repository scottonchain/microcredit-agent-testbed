#!/usr/bin/env python3
"""HERMES-LIVE-COMMUNITIES-20261008-r1 runner. Base Sepolia (84532) only; existing pool; Circle testUSDC.
Usage: live_sim.py init | live_sim.py case N
Public outputs: results.json, run.log (no keys, no raw tx). Private: /root/.hermes/secrets/live-sim-20261008/ (keys, journal).
Each tx: fresh nonce, eth_call simulation, sign locally, journal intended hash BEFORE publish, publish once, wait receipt, never auto-retry.
"""
import json, os, subprocess, sys, time, urllib.request
RPC = "https://sepolia.base.org"
CAST = "/root/.foundry/versions/foundry-rs/foundry/v1.8.4/cast"
POOL = "0x73872B8fB7F1771C67911f03edc75aBdc9514973"
USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
PROV = "0x554c6bB61eDF0CAfB90ff31813540369Cb0105e4"
DEPLOYER = "0x5e4dC7639D2b94006c51aD5373173f5e01c248F9"
CTRL_KEYFILE = "/root/.hermes/secrets/usdc001-walkthrough-borrower.key"
SEC = "/root/.hermes/secrets/live-sim-20261008"
PUB = "/root/work/live-sim-20261008"
UNIT = 1_000_000
DEP = 5 * UNIT
UINT_MAX = 2**256 - 1
TOPUP_WEI = 50_000_000_000_000  # 0.00005 ETH per scenario wallet
ETH_CAP_WEI = 3_000_000_000_000_000  # 0.003 ETH cap on gas funding
USDC_TOTAL_CAP = 7 * UNIT
HEAD = [0]
LOG = open(PUB + "/run.log", "a")

def log(*a):
    s = time.strftime("%H:%M:%S", time.gmtime()) + "Z " + " ".join(str(x) for x in a)
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()

def rpc_raw(m, p):
    r = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                               headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
    return json.load(urllib.request.urlopen(r, timeout=30))

def rpc(m, p):
    d = rpc_raw(m, p)
    if "error" in d: raise RuntimeError(m + " " + json.dumps(d["error"])[:300])
    return d["result"]

def sh(args, env=None):
    e = dict(os.environ); e.update(env or {})
    o = subprocess.run(args, capture_output=True, text=True, env=e)
    if o.returncode != 0: raise RuntimeError("cast failed: " + o.stderr.strip()[:300])
    return o.stdout.strip()

def call(to, sig, *args):
    for i in range(12):
        try:
            return sh([CAST, "call", to, sig, *map(str, args), "--rpc-url", RPC, "--block", str(HEAD[0])]).split(" ")[0]
        except RuntimeError as e:
            if i == 11: raise
            time.sleep(1.2)

def calln(to, sig, *args): return int(call(to, sig, *args))

def words(to, sig, *args):
    for i in range(12):
        try:
            o = sh([CAST, "call", to, sig, *map(str, args), "--rpc-url", RPC, "--block", str(HEAD[0])])
            return [int(x.split(" ")[0]) for x in o.split("\n") if x.strip()]
        except RuntimeError:
            if i == 11: raise
            time.sleep(1.2)

def keccak(s): return sh([CAST, "keccak", s])

def calldata(sig, *args): return sh([CAST, "calldata", sig, *map(str, args)])

def sim_revert(sender, to, sig, *args):
    """read-only eth_call at HEAD; returns ('ok', ret) or ('revert', data)"""
    d = rpc_raw("eth_call", [{"from": sender, "to": to, "data": calldata(sig, *args)}, "latest"])
    if "error" in d:
        data = d["error"].get("data") or ""
        return ("revert", data if isinstance(data, str) else str(data))
    return ("ok", d["result"])

# ---------------- wallets ----------------
ROLES = [f"s{i}-{r}" for i in (1, 2, 3) for r in ("lender", "sponsor", "borrower", "other")]

def load_keys():
    k = json.load(open(SEC + "/wallets.json"))
    k["controller"] = {"address": sh([CAST, "wallet", "address", "--private-key", open(CTRL_KEYFILE).read().strip()]),
                       "private_key": open(CTRL_KEYFILE).read().strip()}
    return k

def init():
    os.makedirs(SEC, mode=0o700, exist_ok=True)
    p = SEC + "/wallets.json"
    if os.path.exists(p): print("wallets exist"); return
    w = {}
    for r in ROLES:
        j = json.loads(sh([CAST, "wallet", "new", "--json"]))
        if "data" in j: j = j["data"]
        j = j[0] if isinstance(j, list) else j
        w[r] = {"address": j["address"], "private_key": j["private_key"]}
    open(p, "w").write(json.dumps(w)); os.chmod(p, 0o600)
    pub = {r: v["address"] for r, v in w.items()}
    json.dump(pub, open(PUB + "/scenario_wallets_public.json", "w"), indent=1)
    print(json.dumps(pub, indent=1))

# ---------------- tx engine ----------------
RESULTS = json.load(open(PUB + "/results.json")) if os.path.exists(PUB + "/results.json") else {"txs": [], "cases": {}, "gas_wei": {"gas_cost": 0, "eth_funded": 0}}

def save(): json.dump(RESULTS, open(PUB + "/results.json", "w"), indent=1)

TOPIC_LR = None

def tx(label, who, K, to, sig=None, args=(), value=0):
    sender, pk = K[who]["address"], K[who]["private_key"]
    # simulation (read-only) at HEAD
    if sig:
        for attempt in range(4):  # public RPC nodes can lag a block; a persistent revert still aborts
            st, ret = sim_revert(sender, to, sig, *args)
            if st == "ok": break
            time.sleep(2.5)
        if st != "ok": raise RuntimeError(f"simulation reverted for {label}: {ret}")
    nonce = int(rpc("eth_getTransactionCount", [sender, "pending"]), 16)
    base = [CAST, "mktx", to] + ([sig, *map(str, args)] if sig else []) + ["--private-key", pk, "--rpc-url", RPC, "--nonce", str(nonce)] + (["--value", str(value)] if value else [])
    raw = sh(base)
    h = keccak(raw)
    os.makedirs(SEC, exist_ok=True)
    with open(SEC + "/journal.jsonl", "a") as j:
        j.write(json.dumps({"t": time.time(), "label": label, "from": sender, "nonce": nonce, "intended_hash": h, "raw": raw}) + "\n"); j.flush(); os.fsync(j.fileno())
    sent = rpc("eth_sendRawTransaction", [raw])
    if sent.lower() != h.lower(): raise RuntimeError("hash mismatch " + sent + " " + h)
    rc = None
    for i in range(45):
        rc = rpc("eth_getTransactionReceipt", [h])
        if rc: break
        time.sleep(2)
    if not rc: raise RuntimeError(f"NO RECEIPT after 90s for {label} {h} (reconcile before any retry)")
    if rc["status"] != "0x1": raise RuntimeError(f"tx failed on chain {label} {h}")
    HEAD[0] = max(HEAD[0], int(rc["blockNumber"], 16))
    cost = int(rc["gasUsed"], 16) * int(rc["effectiveGasPrice"], 16) + int(rc.get("l1Fee", "0x0"), 16)
    RESULTS["gas_wei"]["gas_cost"] += cost
    RESULTS["txs"].append({"label": label, "from": sender, "to": to, "hash": h, "block": int(rc["blockNumber"], 16),
                           "gasUsed": int(rc["gasUsed"], 16), "cost_wei": cost, "nonce": nonce})
    save()
    log("TX", label, h, "block", int(rc["blockNumber"], 16))
    time.sleep(2.5)
    return rc

def req(c, cond, msg):
    if not cond: raise RuntimeError("REQUIRE FAILED: " + msg)

# ---------------- state ----------------
POOL_KEYS = ["totalAssets", "totalShares", "totalLentOut", "reservedLiquidity", "totalStaked", "totalDuesPaid", "firstLossReserve",
             "lenderCash", "totalQueuedShares", "totalImpaired", "totalUnclaimedPayouts", "protocolFees"]

def pool_state():
    s = {k: calln(POOL, k + "()(uint256)") for k in POOL_KEYS}
    s["deployer_shares"] = calln(POOL, "sharesOf(address)(uint256)", DEPLOYER)
    s["pool_usdc"] = calln(USDC, "balanceOf(address)(uint256)", POOL)
    s["provider_totalHeld"] = calln(PROV, "totalHeld()(uint256)")
    s["paused"] = call(POOL, "paused()(bool)")
    s["block"] = HEAD[0]
    return s

def agg(K):
    per = {r: calln(USDC, "balanceOf(address)(uint256)", v["address"]) for r, v in K.items()}
    return sum(per.values()), per

def init_head():
    HEAD[0] = int(rpc("eth_blockNumber", []), 16)

def expect_rev(case, label, sender, to, sig, args, selector):
    st, data = sim_revert(sender, to, sig, *args)
    ok = st == "revert" and data.startswith(selector)
    rec = {"label": label, "call": sig, "expected_selector": selector, "result": st, "revert_data": data, "block": HEAD[0], "match": ok}
    RESULTS["cases"].setdefault(str(case), {}).setdefault("refusals", []).append(rec); save()
    log("REFUSAL", label, st, data[:10], "match" if ok else "MISMATCH")
    RESULTS["cases"][str(case)]["refusals"][-1]["note"] = "observation recorded; run continues"

def run_case(n):
    init_head()
    K = load_keys()
    ctrl = K["controller"]["address"]
    L, S, B, O = (K[f"s{n}-{r}"]["address"] for r in ("lender", "sponsor", "borrower", "other"))
    R = RESULTS["cases"].setdefault(str(n), {})
    base_agg, base_per = agg(K)
    req(n, base_agg == 25 * UNIT, f"aggregate {base_agg} != 25 USDC at start (previous case not reconciled?)")
    for r, v in K.items():
        if r != "controller": req(n, base_per[r] == 0, "scenario wallet holds USDC at start " + r)
    ps0 = pool_state()
    R["pool_before"] = ps0; R["aggregate_before_micro"] = base_agg; R["per_address_before"] = base_per
    req(n, ps0["totalLentOut"] == 0 and ps0["reservedLiquidity"] == 0 and ps0["totalStaked"] == 0 and ps0["paused"] == "false", "pool not idle")
    # gas funding (cap)
    for who in (f"s{n}-lender", f"s{n}-sponsor", f"s{n}-borrower", f"s{n}-other"):
        if RESULTS["gas_wei"]["eth_funded"] + TOPUP_WEI > ETH_CAP_WEI: raise RuntimeError("ETH cap")
        tx("gas top-up 0.00005 ETH -> " + who, "controller", K, K[who]["address"], value=TOPUP_WEI)
        RESULTS["gas_wei"]["eth_funded"] += TOPUP_WEI
    # funding: lender 5, sponsor 1 (spare 1 stays at controller or goes to peer in case 2)
    tx("fund lender 5 USDC", "controller", K, USDC, "transfer(address,uint256)", (L, DEP))
    tx("fund sponsor 1 USDC", "controller", K, USDC, "transfer(address,uint256)", (S, UNIT))
    if n == 2: tx("fund peer 1 USDC (its own endowment)", "controller", K, USDC, "transfer(address,uint256)", (O, UNIT))
    # lender deposit
    sh0 = calln(POOL, "totalShares()(uint256)"); as0 = calln(POOL, "totalAssets()(uint256)")
    q = calln(POOL, "convertToShares(uint256)(uint256)", DEP)
    tx("lender approve pool 5", f"s{n}-lender", K, USDC, "approve(address,uint256)", (POOL, DEP))
    tx("lender depositFunds 5", f"s{n}-lender", K, POOL, "depositFunds(uint256)", (DEP,))
    req(n, calln(POOL, "lenderBalance(address)(uint256)", L) == DEP and calln(POOL, "totalAssets()(uint256)") == as0 + DEP, "deposit effects")
    # sponsor stake + back (no officer grant)
    tx("sponsor approve pool 1", f"s{n}-sponsor", K, USDC, "approve(address,uint256)", (POOL, UNIT))
    tx("sponsor stake 1", f"s{n}-sponsor", K, POOL, "stake(uint256)", (UNIT,))
    tx("sponsor back borrower 1", f"s{n}-sponsor", K, POOL, "back(address,uint256)", (B, UNIT))
    req(n, words(POOL, "getBacking(address,address)(uint256,uint256)", S, B) == [UNIT, 0], "backing not exactly 1 secured")
    req(n, words(POOL, "getBorrowLimit(address)(uint256,uint256)", B) == [UNIT, UNIT], "borrow limit not 1")
    req(n, calln(PROV, "creditScore(address)(uint256)", B) == 0 and calln(POOL, "grantedCredit(address)(uint256)", S) == 0, "officer grant present")
    # refusals before request
    if n == 2:
        expect_rev(n, "borrower cannot back peer with received backing (onward)", B, POOL, "back(address,uint256)", (O, UNIT), "0x8ac4bc73")
    if n == 3:
        expect_rev(n, "borrower cannot onward-back colluder with received backing", B, POOL, "back(address,uint256)", (O, UNIT), "0x8ac4bc73")
        expect_rev(n, "borrower overlimit request 1.01 USDC", B, POOL, "requestLoan(uint256)", (1_010_000,), "0x5d615d32")
        expect_rev(n, "colluder without credit cannot request", O, POOL, "requestLoan(uint256)", (UNIT,), "0x315b0e14")
    # loan
    rc = tx("borrower requestLoan 1", f"s{n}-borrower", K, POOL, "requestLoan(uint256)", (UNIT,))
    topic = keccak("LoanRequested(address,uint256,uint256,uint256)")
    ev = [x for x in rc["logs"] if x["address"].lower() == POOL.lower() and x["topics"] and x["topics"][0].lower() == topic.lower()]
    req(n, len(ev) == 1, "LoanRequested count")
    loan = int(ev[0]["topics"][2], 16)
    R["loan_id"] = loan
    req(n, calln(POOL, "reservedLiquidity()(uint256)") == UNIT, "reservation")
    if n == 3:
        expect_rev(n, "repeat request refused while reservation open", B, POOL, "requestLoan(uint256)", (UNIT,), "0x5d615d32")
        expect_rev(n, "sponsor cannot cut backing while reservation open", S, POOL, "back(address,uint256)", (B, 0), "0x9917947d")
    tx("disburseLoan", f"s{n}-borrower", K, POOL, "disburseLoan(uint256)", (loan,))
    disb_at = int(rpc("eth_getBlockByNumber", [hex(HEAD[0]), False])["timestamp"], 16)
    req(n, calln(USDC, "balanceOf(address)(uint256)", B) == UNIT and calln(POOL, "totalLentOut()(uint256)") == UNIT, "disbursement")
    R["active_snapshot"] = pool_state(); R["disbursed_block"] = HEAD[0]
    # case actions
    if n == 1:
        tx("worker transfers loan to input sink", f"s{n}-borrower", K, USDC, "transfer(address,uint256)", (O, UNIT))
        tx("controller pays worker internal task payment 1", "controller", K, USDC, "transfer(address,uint256)", (B, UNIT))
        payer = f"s{n}-borrower"
    elif n == 2:
        tx("worker transfers loan to controlled input sink (controller)", f"s{n}-borrower", K, USDC, "transfer(address,uint256)", (ctrl, UNIT))
        payer = f"s{n}-other"
    else:
        tx("borrower transfers loan to colluder", f"s{n}-borrower", K, USDC, "transfer(address,uint256)", (O, UNIT))
        expect_rev(n, "colluder still has no credit after receiving cash", O, POOL, "requestLoan(uint256)", (UNIT,), "0x315b0e14")
        payer = f"s{n}-other"
    # repay exact fresh outstanding inside grace
    out = calln(POOL, "getCurrentOutstandingAmount(uint256)(uint256)", loan)
    now = int(rpc("eth_getBlockByNumber", ["latest", False])["timestamp"], 16)
    req(n, out == UNIT and now - disb_at < 3600, f"outstanding {out} / elapsed {now - disb_at}")
    tx("payer approve exact outstanding", payer, K, USDC, "approve(address,uint256)", (POOL, out))
    tx("payer repayLoan full outstanding", payer, K, POOL, "repayLoan(uint256,uint256)", (loan, out))
    req(n, calln(POOL, "getCurrentOutstandingAmount(uint256)(uint256)", loan) == 0 and calln(POOL, "totalLentOut()(uint256)") == 0, "loan not closed")
    R["repaid_block"] = HEAD[0]
    # unwind
    tx("sponsor clears backing", f"s{n}-sponsor", K, POOL, "back(address,uint256)", (B, 0))
    req(n, words(POOL, "getBorrowLimit(address)(uint256,uint256)", B) == [0, 0], "limit not zero")
    tx("sponsor unstake 1", f"s{n}-sponsor", K, POOL, "unstake(uint256)", (UNIT,))
    tx("lender withdraw ALL shares", f"s{n}-lender", K, POOL, "withdrawFunds(uint256)", (UINT_MAX,))
    for r in ("lender", "sponsor", "borrower", "other"):
        w = K[f"s{n}-{r}"]["address"]
        bal = calln(USDC, "balanceOf(address)(uint256)", w)
        if bal: tx(f"sweep {bal} micro-USDC from s{n}-{r} to controller", f"s{n}-{r}", K, USDC, "transfer(address,uint256)", (ctrl, bal))
        al = calln(USDC, "allowance(address,address)(uint256)", w, POOL)
        if al: tx(f"revoke allowance s{n}-{r}", f"s{n}-{r}", K, USDC, "approve(address,uint256)", (POOL, 0))
    if n == 2:
        expect_rev(n, "closed history + removed backing grants no own credit", B, POOL, "requestLoan(uint256)", (UNIT,), "0x315b0e14")
    # reconcile
    a1, per1 = agg(K)
    ps1 = pool_state()
    diffs = {k: (ps0[k], ps1[k]) for k in ps0 if k != "block" and ps0[k] != ps1[k]}
    chk = {"aggregate_equal": a1 == base_agg, "pool_state_diffs": diffs,
           "borrower_completed": calln(POOL, "completedLoans(address)(uint256)", B), "borrower_dues": calln(POOL, "duesPaid(address)(uint256)", B),
           "residual": {}}
    for r in ("lender", "sponsor", "borrower", "other"):
        w = K[f"s{n}-{r}"]["address"]
        chk["residual"][f"s{n}-{r}"] = {"shares": calln(POOL, "sharesOf(address)(uint256)", w), "stake": calln(POOL, "stakeOf(address)(uint256)", w),
            "stakeCommitted": calln(POOL, "stakeCommitted(address)(uint256)", w), "creditCommitted": calln(POOL, "creditCommitted(address)(uint256)", w),
            "activeLoans": calln(POOL, "activeLoanCount(address)(uint256)", w), "allowance_pool": calln(USDC, "allowance(address,address)(uint256)", w, POOL),
            "usdc": per1[f"s{n}-{r}"], "eth_wei": int(rpc("eth_getBalance", [w, hex(HEAD[0])]), 16)}
    R["pool_after"] = ps1; R["aggregate_after_micro"] = a1; R["per_address_after"] = per1; R["reconcile"] = chk
    R["status"] = "reconciled" if (chk["aggregate_equal"] and not diffs and chk["borrower_completed"] == 1 and chk["borrower_dues"] == 0
                                    and all(v["shares"] == v["stake"] == v["stakeCommitted"] == v["creditCommitted"] == v["activeLoans"] == v["allowance_pool"] == v["usdc"] == 0 for v in chk["residual"].values())) else "NOT_RECONCILED"
    R["final_block"] = HEAD[0]
    save()
    log("CASE", n, R["status"], json.dumps(chk)[:600])
    req(n, R["status"] == "reconciled", f"case {n} not reconciled")

if __name__ == "__main__":
    if sys.argv[1] == "init": init()
    elif sys.argv[1] == "case":
        for n in sys.argv[2:]: run_case(int(n))
