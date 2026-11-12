"""N6, member-funded mutual pool: zero sponsor capital, members stake the pool themselves.

Analysis only, stdlib only, deterministic. Reuses experiments/revolving-guarantee/model.py
(same job process: covered event with probability p pays G; otherwise the worker remits k
with probability q; each job costs c). The only change from the sponsored pool is where the
capital comes from: n members each stake m dollars of their own money, so capital = n * m
and the stake is a cost to the members, not to a sponsor.

Run: python3 evidence/lateral-20261112/n6_member_funded_pool.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "revolving-guarantee"))
import model  # noqa: E402

WAGE = 60.0
A = 0.3   # share of guaranteed jobs the guarantee causes (README section 6 uses this order)
S = 0.5   # worker's net share of the wage after valuing their time


def run():
    out = {"scenarios": []}
    for name, p, q, G, c in model.SCENARIOS[:5]:
        k0 = model.break_even(p, q, G, c)
        k = round(1.25 * k0, 2)
        net_job = model.worker_net_per_job(p, q, G, c, k, WAGE, A, S)
        rows = []
        for n, m in [(10, 5), (10, 10), (25, 10), (50, 10), (50, 20), (100, 10), (100, 20)]:
            capital = n * m
            ruin, backed = model.simulate(p, q, G, c, k, capital=capital, jobs=1000, runs=2000, seed=7)
            jobs_per_member = backed / n
            # the stake is spent only when the pool is ruined; otherwise it is a member's money held
            # idle. Charge the expected loss of the stake plus a 10 percent a year time cost on it over
            # the pool's life (1,000 jobs taken as one year), spread over the member's jobs.
            stake_cost_per_job = (ruin * m + 0.10 * m) / max(jobs_per_member, 1e-9)
            rows.append({
                "members": n, "stake_each": m, "capital": capital,
                "ruin_within_1000_jobs": round(ruin, 3),
                "mean_jobs_backed": round(backed, 1),
                "jobs_per_member": round(jobs_per_member, 1),
                "stake_cost_per_job": round(stake_cost_per_job, 2),
                "net_per_job_after_stake": round(net_job - stake_cost_per_job, 2),
                "first_claim_kills_pool": round(model.early_death(p, q), 3) if capital < 2 * (G + c) else None,
            })
        out["scenarios"].append({
            "scenario": name, "p": p, "q": q, "G": G, "c": c,
            "k_used_1.25x_break_even": k,
            "worker_net_per_job_before_stake": round(net_job, 2),
            "capital_for_5pct_ruin_sponsored_reference": model.capital_for_target(p, q, G, c, k),
            "rows": rows,
        })
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
