import subprocess, os, sys, re, json
# usage: run_null.py N [features]   -> per class: distribution of best pairwise F1 under random labels vs observed
N = int(sys.argv[1]); feats = sys.argv[2:] 
K = "/root/work/agents/calibration_v3/ANSWER_KEY_PRIVATE.json"
def run(seed):
    env = dict(os.environ)
    if seed is not None:
        env["NULL_SEED"] = str(seed)
    out = subprocess.run(["python3", "leakcheck_ext.py", "corpus.json", K] + feats, capture_output=True, text=True, env=env).stdout
    sec = out.split("== pairwise")[1].split("== structural")[0]
    res = {}
    for ln in sec.splitlines():
        m = re.match(r"(\w+)\s+.*F1 ([0-9.]+) limit", ln)
        if m:
            res[m.group(1)] = float(m.group(2))
    return res
obs = run(None)
null = [run(s) for s in range(1, N + 1)]
rep = {}
for c in obs:
    xs = sorted(r[c] for r in null)
    rep[c] = {"observed": obs[c], "null_median": xs[len(xs) // 2], "null_p95": xs[int(len(xs) * 0.95)], "null_max": xs[-1],
              "frac_null_ge_observed": sum(x >= obs[c] for x in xs) / len(xs)}
print(json.dumps(rep, indent=1))
