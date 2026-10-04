#!/usr/bin/env python3
"""Extended permutation null for leakcheck_ext (per mayalaran 054f4ef3: late_edge at 1/100 is borderline under a
4-class Bonferroni cutoff of 0.0125; 100 draws give a resolution of 0.01). Runs N draws (seeds 1..N) of the pairwise
sweep with random labels and writes JSON: observed, null quantiles, share of null >= observed, Bonferroni verdict.
Usage: run_null_bonferroni.py N OUT.json [features]   (run inside calibration-v3; key path as in run_null.py)."""
import subprocess, os, sys, re, json
N = int(sys.argv[1]); out = sys.argv[2]; feats = sys.argv[3:]
K = os.environ.get("KEY_PATH", "key.json")  # answer key (public at the reveal); operator runs set KEY_PATH
def run(seed):
    env = dict(os.environ)
    if seed is not None:
        env["NULL_SEED"] = str(seed)
    o = subprocess.run(["python3", "leakcheck_ext.py", "corpus.json", K] + feats, capture_output=True, text=True, env=env).stdout
    sec = o.split("== pairwise")[1].split("== structural")[0]
    res = {}
    for ln in sec.splitlines():
        m = re.match(r"(\w+)\s+.*F1 ([0-9.]+) limit", ln)
        if m:
            res[m.group(1)] = float(m.group(2))
    return res
obs = run(None)
null = [run(s) for s in range(1, N + 1)]
rep = {"draws": N, "features": feats[0] if feats else "all", "bonferroni_cutoff_4_classes": 0.05 / 4, "classes": {}}
for c in obs:
    xs = sorted(r[c] for r in null)
    ge = sum(x >= obs[c] for x in xs) / len(xs)
    rep["classes"][c] = {"observed": obs[c], "null_median": xs[len(xs) // 2], "null_p95": xs[int(len(xs) * 0.95)],
                         "null_p99": xs[int(len(xs) * 0.99)], "null_max": xs[-1], "frac_null_ge_observed": ge,
                         "count_null_ge_observed": sum(x >= obs[c] for x in xs),
                         "below_bonferroni_0_0125": ge < 0.0125}
json.dump(rep, open(out, "w"), indent=1)
print(json.dumps(rep, indent=1))
