import json
A = "/root/work/run_fork/evidence4_1791408809/"
B = "/root/work/run_fork/repro1_evidence/"
def L(d, f): return json.load(open(d + f))
ea, eb = L(A, "evidence.json"), L(B, "evidence.json")
for k in ("status", "mode", "chain_id", "fork_block_target", "fork_block_hash", "mined_local_transaction_count",
          "initial_root_aggregate_usdc_units", "final_root_aggregate_usdc_units", "no_live_fund_moves",
          "gas_spent_wei", "gas_topups_from_treasury_wei", "journal_tip_sha256"):
    print(k, ea.get(k), eb.get(k), "SAME" if ea.get(k) == eb.get(k) else "DIFF")
fa, fb = L(A, "final.json"), L(B, "final.json")
def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in ("block_hash", "block_number", "timestamp")}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o
def walk(a, b, p=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            walk(a.get(k), b.get(k), p + "/" + k)
    elif a != b:
        print("  DIFF", p, str(a)[:80], str(b)[:80])
print("final.json differences (excluding block hash/number/timestamp):")
walk(strip(fa), strip(fb))
for i in (1, 2, 3):
    ra, rb = L(A, "scenario%d-result.json" % i), L(B, "scenario%d-result.json" % i)
    print("scenario", i, ra["status"], rb["status"], ra["loan_id_from_mined_receipt"], rb["loan_id_from_mined_receipt"],
          [n["actual_selector"] for n in ra["negative_checks"]] == [n["actual_selector"] for n in rb["negative_checks"]])
