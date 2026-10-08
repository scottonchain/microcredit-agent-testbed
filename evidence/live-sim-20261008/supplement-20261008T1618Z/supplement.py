#!/usr/bin/env python3
"""Read-only supplement for HERMES-LIVE-COMMUNITIES-20261008-r1 (both passes). Reads Base Sepolia RPC only; no signed bytes, no state change.
Writes supplement/passN_receipts.json, supplement/fee_ledger.json. Reconstruction time is recorded honestly (RECON_TS)."""
import json, os, time, urllib.request
RPC = "https://sepolia.base.org"
D = "/root/work/live-sim-20261008"
OUT = D + "/supplement"
os.makedirs(OUT, exist_ok=True)
USDC = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
T_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
POOL = "0x73872b8fb7f1771c67911f03edc75aebdc9514973".replace("aebdc", "aedc75aebdc")  # placeholder replaced below
POOL = "0x73872B8fB7F1771C67911f03edc75aBdc9514973".lower()
CTRL = "0x108450c748eef7aef23e64739bc508f56e596247"

def rpc(m, p):
    for i in range(8):
        try:
            r = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                       headers={"Content-Type": "application/json", "User-Agent": "hermes-agent-909"})
            d = json.load(urllib.request.urlopen(r, timeout=30))
            if "error" in d: raise RuntimeError(json.dumps(d["error"])[:200])
            return d["result"]
        except Exception as e:
            if i == 7: raise
            time.sleep(1.5)

def keccak_topic(sig):
    import subprocess
    return subprocess.run(["/root/.foundry/versions/foundry-rs/foundry/v1.8.4/cast", "keccak", sig], capture_output=True, text=True).stdout.strip()

T_REPAID = keccak_topic("LoanRepaid(address,uint256,uint256)")
T_RAPPLIED = keccak_topic("RepaymentApplied(uint256,uint256,uint256,uint256)")
RECON_TS = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def hx(x): return int(x, 16)

def decode(l):
    t = l["topics"]; a = l["address"].lower()
    if a == USDC and t and t[0] == T_TRANSFER:
        return {"event": "USDC.Transfer", "from": "0x" + t[1][-40:], "to": "0x" + t[2][-40:], "value_micro": hx(l["data"])}
    if a == POOL and t and t[0] == T_RAPPLIED:
        d = l["data"][2:]; w = [int(d[i*64:(i+1)*64], 16) for i in range(3)]
        return {"event": "Pool.RepaymentApplied", "loanId": hx(t[1]), "interest": w[0], "principal": w[1], "fee": w[2]}
    if a == POOL and t and t[0] == T_REPAID:
        return {"event": "Pool.LoanRepaid", "borrower": "0x" + t[1][-40:], "loanId": hx(t[2]), "amount": hx(l["data"])}
    return {"event": "other", "address": a, "topic0": t[0] if t else None}

ledger = {"recon_time_utc": RECON_TS, "passes": {}}
for name, path in (("pass1", D + "/results.json"), ("pass2", D + "/pass2out/results.json")):
    R = json.load(open(path))
    wallets = json.load(open(D + ("/scenario_wallets_public.json" if name == "pass1" else "/pass2out/scenario_wallets_public.json")))
    scen = {v.lower() for v in wallets.values()}
    rows = []; fee_scen = 0; fee_ctrl = 0; fee_rec_scen = 0
    for t in R["txs"]:
        rc = rpc("eth_getTransactionReceipt", [t["hash"]]); tx = rpc("eth_getTransactionByHash", [t["hash"]])
        l2 = hx(rc["gasUsed"]) * hx(rc["effectiveGasPrice"]); l1 = hx(rc.get("l1Fee", "0x0"))
        fee = l2 + l1
        frm = tx["from"].lower()
        row = {"hash": t["hash"], "label": t["label"], "from": frm, "to": tx["to"], "nonce": hx(tx["nonce"]), "input": tx["input"],
               "value_wei": hx(tx["value"]), "block": hx(rc["blockNumber"]), "blockHash": rc["blockHash"], "status": hx(rc["status"]),
               "gasUsed": hx(rc["gasUsed"]), "effectiveGasPrice": hx(rc["effectiveGasPrice"]), "l1Fee": l1, "fee_wei_l2": l2, "fee_wei_total": fee,
               "recorded_cost_wei": t["cost_wei"], "decoded": [decode(l) for l in rc["logs"]]}
        rows.append(row)
        if frm in scen: fee_scen += fee; fee_rec_scen += t["cost_wei"]
        else: fee_ctrl += fee
    json.dump(rows, open(f"{OUT}/{name}_receipts.json", "w"), indent=1)
    funded = sum(r["value_wei"] for r in rows if r["from"] == CTRL and r["to"].lower() in scen)
    # residual balances at the run's final block
    final_block = max(c.get("final_block", 0) for c in R["cases"].values())
    bal = {k: hx(rpc("eth_getBalance", [v, hex(final_block)])) for k, v in wallets.items()}
    # scenario-wallet ETH moved between scenario wallets / out (value txs from scenario wallets)
    out_value = sum(r["value_wei"] for r in rows if r["from"] in scen)
    ledger["passes"][name] = {
        "n_tx": len(rows), "all_status_1": all(r["status"] == 1 for r in rows), "final_block": final_block,
        "funded_wei": funded, "scenario_wallet_balance_at_final_block_sum": sum(bal.values()),
        "scenario_fee_total_with_l1fee": fee_scen, "scenario_fee_recorded_l2_only": fee_rec_scen,
        "recorded_vs_l2_recomputed_diff": fee_rec_scen - sum(r["fee_wei_l2"] for r in rows if r["from"] in scen),
        "sum_l1Fee_scenario": sum(r["l1Fee"] for r in rows if r["from"] in scen),
        "controller_fee_total_with_l1fee": fee_ctrl, "scenario_value_sent_out_wei": out_value,
        "identity_funded_minus_balance_minus_fees_minus_valueout": funded - sum(bal.values()) - fee_scen - out_value,
        "all_senders_fee_total_with_l1fee": fee_scen + fee_ctrl, "recorded_gas_cost_field": R["gas_wei"]["gas_cost"]}
json.dump(ledger, open(OUT + "/fee_ledger.json", "w"), indent=1)
print(json.dumps(ledger, indent=1))
