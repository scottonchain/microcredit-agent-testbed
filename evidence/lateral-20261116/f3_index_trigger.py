"""F3, index insurance through the conditional-payment contract: an index-trigger simulation.

Analysis only, stdlib only, deterministic. Public rainfall: NASA POWER monthly precipitation
(PRECTOTCORR, mm/day) at 9.40N 0.84W (Tamale, northern Ghana), 1981 to 2025, saved beside this
script as served. The growing-season index is May to October rainfall in mm; the trigger is a
season below the 20th percentile of the record (a one-in-five-year drought), the shape of the
Karlan, Osei, Osei-Akoto and Udry (2014) rainfall product.

Pool: n insured farmers, each paying premium k a season and receiving G on a trigger; the pool
pays c per policy per season for verification and payout. Unlike the revolving guarantee's
independent jobs, every policy on one index pays in the same season, so the pool's loss is
n times G at once. Seasons are drawn by bootstrap from the historical index (seed 7). Ruin is
the pool being unable to pay a triggered season in full. The pure premium is p * G + c (paid every
season); the independent-claims comparison uses experiments/revolving-guarantee/model.py.

Run: python3 evidence/lateral-20261116/f3_index_trigger.py
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "experiments", "revolving-guarantee"))
import model  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DAYS = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}


def season_index():
    d = json.load(open(os.path.join(HERE, "nasa-power-tamale-monthly-precip-1981-2025.json")))
    p = d["properties"]["parameter"]["PRECTOTCORR"]
    years = {}
    for key, v in p.items():
        if len(key) != 6 or v is None or v < 0:
            continue
        y, mo = int(key[:4]), int(key[4:])
        if 5 <= mo <= 10:
            years[y] = years.get(y, 0.0) + v * DAYS[mo]
    return dict(sorted(years.items()))


def ruin(index, trigger, n, G, k, c, capital, years=30, runs=4000, seed=7):
    rng = random.Random(seed)
    vals = list(index.values())
    ruined = 0
    for _ in range(runs):
        x = capital
        for _ in range(years):
            x += n * (k - c)
            if rng.choice(vals) < trigger:
                x -= n * G
                if x < 0:
                    ruined += 1
                    break
    return ruined / runs


def capital_for(index, trigger, n, G, k, c, target=0.05):
    lo, hi = 0.0, 200.0 * n * G
    while hi - lo > max(10.0, 0.001 * n * G):
        mid = (lo + hi) / 2
        if ruin(index, trigger, n, G, k, c, mid, runs=1000) <= target:
            hi = mid
        else:
            lo = mid
    return round(hi, -1)


def run():
    idx = season_index()
    vals = sorted(idx.values())
    p20 = vals[int(0.2 * len(vals))]
    p = sum(1 for v in vals if v < p20) / len(vals)
    G, c = 60.0, 2.0
    # the premium is paid every season, so the pure premium is p * G + c; the guarantee model's
    # break_even divides by (1 - p) because its contribution is collected only on jobs that do not
    # default, which does not apply here (Hermes, PR 482 comment 6927721258)
    k_fair = p * G + c
    out = {"station": "NASA POWER 9.40N 0.84W (Tamale), May to October rainfall, mm", "years": len(vals),
           "season_mm_min_median_max": [round(vals[0]), round(vals[len(vals) // 2]), round(vals[-1])],
           "trigger_mm_20th_percentile": round(p20), "trigger_frequency": round(p, 3),
           "trigger_years": [y for y, v in idx.items() if v < p20],
           "G": G, "c": c, "pure_premium_pG_plus_c": round(k_fair, 2), "rows": []}
    for n in (1, 10, 100, 1000):
        for loading in (1.0, 1.25, 1.5, 2.0):
            k = round(loading * k_fair, 2)
            row = {"farmers": n, "premium": k, "loading": loading,
                   "ruin_30y_capital_100": round(ruin(idx, p20, n, G, k, c, 100.0), 3),
                   "capital_for_5pct_ruin_30y": capital_for(idx, p20, n, G, k, c)}
            row["capital_per_farmer"] = round(row["capital_for_5pct_ruin_30y"] / n, 1)
            row["capital_as_share_of_sum_insured"] = round(row["capital_for_5pct_ruin_30y"] / (n * G), 2)
            out["rows"].append(row)
    # the independent-claims comparison: the guarantee pool's own machinery at the same p
    out["independent_claims_capital_for_5pct_ruin_1000_jobs_at_1.25k"] = model.capital_for_target(
        p, 1.0, G, c, 1.25 * model.break_even(p, 1.0, G, c))  # the guarantee pool at its own 1.25 times break-even
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
