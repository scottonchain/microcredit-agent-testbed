#!/usr/bin/env python3
"""Live run of the retry fixture's chain cases on Base Sepolia (testnet, fake money), against the testnet pool.
Every step is a real transaction; results are appended to EVIDENCE.json after each step (idempotent: a recorded step is skipped).
Keys: deployer (owner + relayer; whitelist disabled) and a throwaway borrower key that holds no ETH (all its intents are relayed).
Nothing here is printed that is secret."""
import json, os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib

EV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "EVIDENCE.json")
OUT = os.environ.get("CONTRACT_OUT_DIR", "out")   # forge `out/` of the contract repo (Wrapper and SwallowingBatch bytecode)
ev = json.load(open(EV)) if os.path.exists(EV) else {"network": {"name": "Base Sepolia", "chain_id": lib.CHAIN_ID, "rpc": lib.RPC},
                                                     "contracts": {"pool": lib.POOL, "usdc": lib.USDC}, "steps": {}}
borrower = lib.addr_of(lib.BORROWER_KEY_FILE)
ev["actors"] = {"relayer_and_owner": lib.DEPLOYER, "borrower": borrower,
                "note": "the borrower key holds no ETH and never sends a transaction; every intent it signs is relayed by the relayer address"}


def save():
    json.dump(ev, open(EV, "w"), indent=2)


def done(name):
    return name in ev["steps"]


def record(name, d):
    d["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    ev["steps"][name] = d
    save()
    print("STEP", name, json.dumps({k: v for k, v in d.items() if k in ("tx", "block", "status", "note")}))


def receipt_summary(r):
    return {"tx": r.get("transactionHash"), "block": lib.to_int(r.get("blockNumber")), "status": lib.to_int(r.get("status")),
            "gas_used": lib.to_int(r.get("gasUsed")), "from": r.get("from"), "to": r.get("to"), "contract_address": r.get("contractAddress"),
            "logs": [{"address": l.get("address"), "topics": l.get("topics"), "data": l.get("data")} for l in r.get("logs", [])]}


def loan_state(loan_id, block=None):
    v = lib.call(lib.POOL, "getLoan(uint256)(uint256,uint256,address,uint256,bool)", loan_id, block=block).splitlines()
    return {"principal": int(v[0].split()[0]), "outstanding": int(v[1].split()[0]), "borrower": v[2].strip(), "rate_bps": int(v[3].split()[0]), "is_active": v[4].strip() == "true"}


def usdc_balance(addr, block=None):
    return int(lib.call(lib.USDC, "balanceOf(address)(uint256)", addr, block=block).split()[0])


def simulate_revert(to, data):
    rc, out = lib.call_data(to, data, frm=lib.DEPLOYER)
    m = re.search(r'data: "?(0x[0-9a-fA-F]*)', out)
    return {"reverted": rc != 0, "revert_data": m.group(1) if m else None, "text": out[:160]}


def borrow(step, amount):
    if done(step):
        return ev["steps"][step]["loan_id"]
    n = lib.nonces(borrower)
    dl = lib.now() + 3600
    sig = lib.sign_borrow(lib.BORROWER_KEY_FILE, borrower, amount, borrower, 28 * 86400, 1000, n, dl)
    data = lib.borrow_calldata(borrower, amount, borrower, 28 * 86400, 1000, n, dl, sig)
    r = lib.send_data(lib.DEPLOYER_KEY_FILE, lib.POOL, data)
    s = receipt_summary(r)
    if s["status"] != 1:
        sys.exit("borrow failed: " + json.dumps(s)[:300])
    loan_id = None
    for _ in range(20):   # read at the receipt's block; a load-balanced node may lag behind the receipt
        try:
            ids = lib.call(lib.POOL, "getBorrowerLoanIds(address)(uint256[])", borrower, block=s["block"])
            found = re.findall(r"\d+", ids)
            if found:
                loan_id = int(found[-1])
                break
        except Exception as e:
            print("read retry:", str(e)[:80])
        time.sleep(3)
    if loan_id is None:
        sys.exit("loan id not readable after the borrow tx " + s["tx"])
    s.update({"kind": "borrowAndDisburseMeta", "signed_nonce": n, "deadline": dl, "amount": amount, "loan_id": loan_id, "calldata": data,
              "nonce_before": lib.nonces(borrower, s["block"] - 1), "nonce_after": lib.nonces(borrower, s["block"]), "loan_after": loan_state(loan_id, s["block"])})
    record(step, s)
    return loan_id


def repay_calldata(loan_id, nonce, deadline, with_permit=True, permit_value=100_000_000):
    sig = lib.sign_repay(lib.BORROWER_KEY_FILE, borrower, loan_id, 0, nonce, deadline)
    permit = lib.sign_permit(lib.BORROWER_KEY_FILE, borrower, lib.POOL, permit_value, lib.now() + 3600) if with_permit else lib.no_permit()
    return lib.repay_calldata(borrower, loan_id, 0, nonce, deadline, sig, permit)


# ---- setup ----
if not done("s0_score_override"):
    r = lib.send_sig(lib.DEPLOYER_KEY_FILE, lib.POOL, "setScoreOverride(address,uint256)", borrower, 500_000)
    s = receipt_summary(r); s["note"] = "owner grants the throwaway borrower a score override of 500000 (50% of SCALE), as the forge tests do"
    record("s0_score_override", s)
if not done("s1_mint"):
    r = lib.send_sig(lib.DEPLOYER_KEY_FILE, lib.USDC, "mint(address,uint256)", borrower, 100_000_000)
    s = receipt_summary(r); s["note"] = "MockUSDC.mint is permissionless on this test token; 100 USDC to the borrower for repayments"
    record("s1_mint", s)

loan_a = borrow("s2_borrow_loan_a", 40_000_000)

# ---- chain-1 / chain-3 / chain-4 / chain-5: the first repay lands ----
if not done("s3_chain1_first_submission"):
    n = lib.nonces(borrower)
    dl = lib.now() + 3600
    data = repay_calldata(loan_a, n, dl)
    r = lib.send_data(lib.DEPLOYER_KEY_FILE, lib.POOL, data)
    s = receipt_summary(r)
    if s["status"] != 1:
        sys.exit("first repay failed: " + json.dumps(s)[:300])
    s.update({"kind": "repayLoanMeta", "loan_id": loan_a, "signed_nonce": n, "deadline": dl, "calldata": data,
              "nonce_before": lib.nonces(borrower, s["block"] - 1), "nonce_after": lib.nonces(borrower, s["block"]),
              "borrower_usdc_before": usdc_balance(borrower, s["block"] - 1), "borrower_usdc_after": usdc_balance(borrower, s["block"]),
              "loan_before": loan_state(loan_a, s["block"] - 1), "loan_after": loan_state(loan_a, s["block"]),
              "note": "chain-1 first submission; chain-3 receipt shape; chain-4 nonce moved; chain-5 calldata carries the signed request"})
    record("s3_chain1_first_submission", s)

if not done("s4_chain1_replay_same_calldata"):
    data = ev["steps"]["s3_chain1_first_submission"]["calldata"]
    sim = simulate_revert(lib.POOL, data)
    r = lib.send_data(lib.DEPLOYER_KEY_FILE, lib.POOL, data, gas_limit=300_000)   # forced past gas estimation so the retry lands on chain and reverts there
    s = receipt_summary(r)
    s.update({"kind": "repayLoanMeta (same bytes as s3)", "loan_id": loan_a, "calldata": data, "simulation_before_send": sim,
              "nonce_before": lib.nonces(borrower, s["block"] - 1), "nonce_after": lib.nonces(borrower, s["block"]),
              "borrower_usdc_before": usdc_balance(borrower, s["block"] - 1), "borrower_usdc_after": usdc_balance(borrower, s["block"]),
              "note": "chain-1: the relayer resubmits the identical signed request after the first landed; expected: reverts on the consumed nonce (InvalidNonce 0x756688fe), nothing pulled"})
    record("s4_chain1_replay_same_calldata", s)

if not done("s5_chain2_fresh_signature_after_landed_repay"):
    n = lib.nonces(borrower)
    dl = lib.now() + 3600
    data = repay_calldata(loan_a, n, dl)
    sim = simulate_revert(lib.POOL, data)
    r = lib.send_data(lib.DEPLOYER_KEY_FILE, lib.POOL, data, gas_limit=300_000)
    s = receipt_summary(r)
    s.update({"kind": "repayLoanMeta (fresh signature, next nonce, fresh permit)", "loan_id": loan_a, "signed_nonce": n, "deadline": dl, "calldata": data,
              "simulation_before_send": sim, "nonce_before": lib.nonces(borrower, s["block"] - 1), "nonce_after": lib.nonces(borrower, s["block"]),
              "borrower_usdc_before": usdc_balance(borrower, s["block"] - 1), "borrower_usdc_after": usdc_balance(borrower, s["block"]),
              "note": "chain-2: a fresh signature for the same intent after the repay landed, with a valid permit so a pull could succeed if the loan were still repayable; expected: reverts (LoanNotActive 0x082f7846), nothing pulled, nonce not consumed"})
    record("s5_chain2_fresh_signature_after_landed_repay", s)

# ---- chain-6: wrapper hides the request from the top-level selector ----
if not done("s6_deploy_wrapper"):
    bc = json.load(open(os.path.join(OUT, "RelayerRetry.t.sol/Wrapper.json")))["bytecode"]["object"]
    s = receipt_summary(lib.create(lib.DEPLOYER_KEY_FILE, bc))
    s.update({"kind": "deploy Wrapper (contract repo test/RelayerRetry.t.sol: forward(target, data) = target.call(data), require(ok))", "bytecode_sha256": __import__("hashlib").sha256(bytes.fromhex(bc[2:])).hexdigest()})
    record("s6_deploy_wrapper", s)
wrapper = ev["steps"]["s6_deploy_wrapper"]["contract_address"]

loan_b = borrow("s7_borrow_loan_b", 40_000_000)

if not done("s8_chain6_repay_through_wrapper"):
    n = lib.nonces(borrower)
    dl = lib.now() + 3600
    inner = repay_calldata(loan_b, n, dl)
    outer = lib.cast("calldata", "forward(address,bytes)", lib.POOL, inner)
    r = lib.send_data(lib.DEPLOYER_KEY_FILE, wrapper, outer)
    s = receipt_summary(r)
    s.update({"kind": "Wrapper.forward(pool, repayLoanMeta calldata)", "loan_id": loan_b, "signed_nonce": n, "deadline": dl, "inner_calldata": inner, "calldata": outer,
              "top_level_selector": outer[:10], "repay_selector": "0x1d169fa9",
              "nonce_before": lib.nonces(borrower, s["block"] - 1), "nonce_after": lib.nonces(borrower, s["block"]),
              "loan_before": loan_state(loan_b, s["block"] - 1), "loan_after": loan_state(loan_b, s["block"]),
              "note": "chain-6: tx.input is the wrapper's calldata; a reconciler matching repayLoanMeta's selector at the top level finds nothing; nonces(signer) still shows the request landed"})
    record("s8_chain6_repay_through_wrapper", s)

# ---- chain-7: swallowing envelope ----
if not done("s9_deploy_swallowing_batch"):
    bc = json.load(open(os.path.join(OUT, "RelayerRetryBatch.t.sol/SwallowingBatch.json")))["bytecode"]["object"]
    s = receipt_summary(lib.create(lib.DEPLOYER_KEY_FILE, bc))
    s.update({"kind": "deploy SwallowingBatch (contract repo test/RelayerRetryBatch.t.sol: batch(target, calls[]) = (ok[i],) = target.call(calls[i]); never reverts)",
              "bytecode_sha256": __import__("hashlib").sha256(bytes.fromhex(bc[2:])).hexdigest()})
    record("s9_deploy_swallowing_batch", s)
envelope = ev["steps"]["s9_deploy_swallowing_batch"]["contract_address"]

loan_c = borrow("s10_borrow_loan_c", 40_000_000)

if not done("s11_chain7a_envelope_with_expired_intent"):
    n = lib.nonces(borrower)
    dl = lib.now() - 120  # expired
    inner = repay_calldata(loan_c, n, dl)
    outer = lib.cast("calldata", "batch(address,bytes[])", lib.POOL, "[%s]" % inner)
    r = lib.send_data(lib.DEPLOYER_KEY_FILE, envelope, outer)
    s = receipt_summary(r)
    s.update({"kind": "SwallowingBatch.batch(pool, [repayLoanMeta with an expired deadline])", "loan_id": loan_c, "signed_nonce": n, "deadline": dl, "inner_calldata": [inner], "calldata": outer,
              "nonce_before": lib.nonces(borrower, s["block"] - 1), "nonce_after": lib.nonces(borrower, s["block"]),
              "loan_before": loan_state(loan_c, s["block"] - 1), "loan_after": loan_state(loan_c, s["block"]),
              "note": "chain-7a: the envelope tx succeeds (status 1) while the wrapped intent did not land (SignatureExpired inside); only nonces(signer) says so"})
    record("s11_chain7a_envelope_with_expired_intent", s)

if not done("s12_chain7b_two_intents_one_lands"):
    n = lib.nonces(borrower)
    a = repay_calldata(loan_c, n, lib.now() + 3600)
    b = repay_calldata(loan_c, n + 1, lib.now() - 120, with_permit=False)   # expired
    outer = lib.cast("calldata", "batch(address,bytes[])", lib.POOL, "[%s,%s]" % (a, b))
    r = lib.send_data(lib.DEPLOYER_KEY_FILE, envelope, outer)
    s = receipt_summary(r)
    s.update({"kind": "SwallowingBatch.batch(pool, [valid repay nonce n, expired repay nonce n+1])", "loan_id": loan_c, "signed_nonces": [n, n + 1], "inner_calldata": [a, b], "calldata": outer,
              "nonce_before": lib.nonces(borrower, s["block"] - 1), "nonce_after": lib.nonces(borrower, s["block"]),
              "loan_before": loan_state(loan_c, s["block"] - 1), "loan_after": loan_state(loan_c, s["block"]),
              "note": "chain-7b: exactly one nonce consumed; the range [n, n+1) names the landed intent; the envelope receipt alone cannot"})
    record("s12_chain7b_two_intents_one_lands", s)

ev["final"] = {"nonces_borrower": lib.nonces(borrower), "borrower_usdc": usdc_balance(borrower), "block": int(lib.cast("block-number", "--rpc-url", lib.RPC)),
               "loans": {str(l): loan_state(l) for l in (loan_a, loan_b, loan_c)}, "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
save()
print("FINAL", json.dumps(ev["final"]))
