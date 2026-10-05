#!/usr/bin/env python3
"""Post-reveal reproduction of every operator-run number published for calibration-v3, from the public files only.

usage: python3 reproduce_from_public_key.py <clone root> [--null N_TIMING N_ALL]
       (defaults 1000 400 = the recorded draw counts; 0 skips the permutation nulls, which take a few minutes)

Stdlib only. One network read: the GitHub API, unauthenticated, for testbed issue #11 (the submissions exactly as
posted). Everything else is read from the clone. Before the reveal these numbers could only be produced by the
operator, who held the key; after it anyone can run this file. Exit 0 if every check passes, 1 otherwise.

Checks (each prints PASS or FAIL with the observed value):
  1. FREEZE.md hashes of the six frozen files; ANSWER_KEY.json, gen_calibration_v3.py hash as REVEAL.md states
  2. key commitment and seed commitment open (REVEAL.md constructions); FREEZE.md defect (c): 22 planted borrowers,
     all in corpus.json, no borrower in two classes
  3. every scored or paid row of calibration-v1/SLOTS.md: the as-posted bytes from its issue #11 comment hash to the recorded
     sha256, check_submission.py exit 0, score.py gives the recorded summary line
  4. calibration-v3/ext_out_private.txt and ext_out_timing_private.txt == leakcheck_ext.py output (byte for byte)
  5. research/calibration-v3-leakcheck-lobo/lobo_timing_out.txt == lobo_ext.py output (byte for byte)
  6. calibration-v3/validate_ledger_output.txt == validate_ledger.py output (+ the "exit 0" line the publisher added)
  7. research/calibration-v3-graph-baseline: sub.json sha256 as its README states, check_submission exit 0,
     score.py gives the README row (ring found 6 / false+ 4, precision 0.73, recall 0.50, FP rate 0.065)
  8. cp_intervals.py rows appear verbatim in LEAKCHECK_EXT_RESULTS.md
  9. run_null_bonferroni.py reproduces null_timing_1000.json and null_all_400.json (seeded draws; full JSON equality)
"""
import hashlib, json, os, platform, re, subprocess, sys, time, urllib.request

ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.getcwd()
N_TIMING, N_ALL = 1000, 400
if "--null" in sys.argv:
    i = sys.argv.index("--null"); N_TIMING, N_ALL = int(sys.argv[i + 1]), int(sys.argv[i + 2])
V3 = os.path.join(ROOT, "calibration-v3"); V1 = os.path.join(ROOT, "calibration-v1"); RS = os.path.join(ROOT, "research")
TIMING = "disb_lag_s_mean,disb_lag_blocks_mean,first_backing_rel_req_h,last_backing_rel_req_h"
UA = {"User-Agent": "calibration-v3-post-reveal-reproduction", "Accept": "application/vnd.github+json"}
results = []


def rd(p, mode="r"):
    with open(p, mode) as f:
        return f.read()


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def run(args, cwd, env=None):
    e = dict(os.environ); e.update(env or {})
    p = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, text=True, env=e)
    return p.returncode, p.stdout, p.stderr


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  | " + detail) if detail else ""))


head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
print("clone HEAD %s | %s | %s | %s" % (head or "(not a git checkout)", sys.version.split()[0], platform.platform(), time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())))

# 1. frozen files + reveal files
freeze = rd(os.path.join(V3, "FREEZE.md"))
rows = re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|", freeze, re.M)
for f, h in rows:
    got = sha(rd(os.path.join(V3, f), "rb"))
    check("FREEZE.md hash %s" % f, got == h, got[:16])
check("FREEZE.md lists six frozen files", len(rows) == 6, str(len(rows)))
reveal_md = rd(os.path.join(V3, "REVEAL.md"))
key_sha_stated = re.search(r"ANSWER_KEY\.json` \(sha256 `([0-9a-f]{64})`", reveal_md).group(1)
gen_sha_stated = re.search(r"gen_calibration_v3\.py`, sha256 `([0-9a-f]{64})`", reveal_md).group(1)
check("ANSWER_KEY.json sha256 as REVEAL.md states", sha(rd(os.path.join(V3, "ANSWER_KEY.json"), "rb")) == key_sha_stated, key_sha_stated[:16])
check("gen_calibration_v3.py sha256 as REVEAL.md states", sha(rd(os.path.join(V3, "gen_calibration_v3.py"), "rb")) == gen_sha_stated, gen_sha_stated[:16])

# 2. commitments + defect (c)
akey = json.loads(rd(os.path.join(V3, "ANSWER_KEY.json")))
key, salt = akey["key"], akey["salt"]
commit_txt = rd(os.path.join(V3, "COMMITMENT.txt"))
commit_val = re.findall(r"[0-9a-f]{64}", commit_txt)
opened = sha(salt.encode() + json.dumps(key, sort_keys=True).encode())
check("key commitment opens COMMITMENT.txt", commit_val and opened == commit_val[-1], opened[:16])
seed = re.search(r"Seed: `(\d+)`", reveal_md).group(1); nonce = re.search(r"Nonce: `([0-9a-f]+)`", reveal_md).group(1)
seed_commit_stated = re.search(r"Seed commitment \(PRECOMMIT\.md\): `sha256\([^`]*\)` = `([0-9a-f]{64})`", reveal_md).group(1)
check("seed commitment opens (sha256(nonce || seed))", sha((nonce + seed).encode()) == seed_commit_stated, "seed %s" % seed)
check("REVEAL.md seed equals key.seed", str(key.get("seed")) == seed, str(key.get("seed")))
corpus = json.loads(rd(os.path.join(V3, "corpus.json")))
borrowers = {e["args"]["borrower"].lower() for e in corpus["events"] if "borrower" in e["args"]}
classes = {"ring": key["ring"], "sybil_cluster": key["sybil_cluster"], "bust_out": key["bust_out"],
           "late_edge.inside_grace": key["late_edge"]["inside_grace"], "late_edge.outside_grace": key["late_edge"]["outside_grace"]}
planted = [a.lower() for v in classes.values() for a in v]
check("defect (c): 22 planted, all borrowers, disjoint", len(planted) == 22 and len(set(planted)) == 22 and set(planted) <= borrowers,
      "%d planted, %d distinct, %d borrowers" % (len(planted), len(set(planted)), len(borrowers)))

# 3. SLOTS.md scored rows against issue #11 as posted
slots = rd(os.path.join(V1, "SLOTS.md"))
scored = [(int(m.group(1)), m.group(0)) for m in re.finditer(r"^\| (\d) \| .*? \| .*? \| (?:scored|paid) \| .*\|$", slots, re.M)]
# state `paid` keeps the scored line (SLOTS.md rows move scored -> paid after the payment); until 2026-10-05 04:30 UTC this
# selected `scored` only, so a clone taken after rows 1-2 were paid (testbed 1602379) checked 3 rows and printed 33 checks
issue = json.loads(urllib.request.urlopen(urllib.request.Request(
    "https://api.github.com/repos/scottonchain/microcredit-agent-testbed/issues/11/comments?per_page=100", headers=UA), timeout=60).read())
by_id = {str(c["id"]): c["body"] for c in issue}
tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "calv3_repro_%d" % os.getpid()); os.makedirs(tmp, exist_ok=True)


def as_posted(body):
    m = re.search(r"```(?:json)?\r?\n(.*?)\r?\n```", body, re.S)
    if m:
        return (m.group(1) + "\n").encode()          # fenced: the fence content with the newline the fence implies
    return body[body.find("{"): body.rfind("}") + 1].encode()   # unfenced: the JSON object as it stands in the comment


for slot, row in scored:
    cid = re.search(r"comment (\d{9,})", row).group(1)
    rec_sha = re.search(r"submission sha256 ([0-9a-f]{64})", row).group(1)
    rec_line = re.search(r"(overall precision [0-9.]+ recall [0-9.]+; false-positive rate over \d+ borrowers: [0-9.]+)", row).group(1)
    body = by_id.get(cid)
    if body is None:
        check("slot %d comment %s found on issue #11" % (slot, cid), False); continue
    b = as_posted(body); p = os.path.join(tmp, "slot%d.json" % slot)
    with open(p, "wb") as f:
        f.write(b)
    check("slot %d as-posted bytes hash as SLOTS.md records" % slot, sha(b) == rec_sha, "%s (comment %s)" % (sha(b)[:16], cid))
    rc, out, err = run([os.path.join(V3, "check_submission.py"), os.path.join(V3, "corpus.json"), p], V3)
    check("slot %d check_submission.py exit 0" % slot, rc == 0, (out.strip().splitlines() or [err.strip()])[-1][:60])
    rc, out, err = run([os.path.join(V3, "score.py"), os.path.join(V3, "corpus.json"), p, os.path.join(V3, "ANSWER_KEY.json")], V3)
    got = (out.strip().splitlines() or [""])[-1]
    check("slot %d score.py summary line as SLOTS.md records" % slot, rc == 0 and got == rec_line, got)
check("SLOTS.md has scored or paid rows", len(scored) > 0, "%d scored or paid rows" % len(scored))

# 4. leakcheck_ext outputs
for feats, recorded in ((None, "ext_out_private.txt"), (TIMING, "ext_out_timing_private.txt")):
    rc, out, err = run(["leakcheck_ext.py", "corpus.json", "ANSWER_KEY.json"] + ([feats] if feats else []), V3)
    check("leakcheck_ext.py %s == %s byte for byte" % ("timing family" if feats else "all features", recorded),
          out == rd(os.path.join(V3, recorded)), "exit %d, %d lines" % (rc, len(out.splitlines())))

# 5. LOBO
LOBO = os.path.join(RS, "calibration-v3-leakcheck-lobo")
rc, out, err = run([os.path.join(LOBO, "lobo_ext.py"), "corpus.json", "ANSWER_KEY.json", TIMING], V3)
check("lobo_ext.py timing family == lobo_timing_out.txt byte for byte", out == rd(os.path.join(LOBO, "lobo_timing_out.txt")), "exit %d" % rc)

# 6. validator
rc, out, err = run(["validate_ledger.py", "corpus.json"], V3)
rec = rd(os.path.join(V3, "validate_ledger_output.txt"))
check("validate_ledger.py exit 0 and output == validate_ledger_output.txt (minus its appended 'exit 0' line)",
      rc == 0 and rec == out + "exit 0\n", "exit %d" % rc)

# 7. graph baseline
GB = os.path.join(RS, "calibration-v3-graph-baseline")
gb_readme = rd(os.path.join(GB, "README.md"))
gb_sha_stated = re.search(r"graph_baseline\.py [^\n]*sub\.json\s+# sha256 ([0-9a-f]{64})", gb_readme).group(1)
rc, out, err = run([os.path.join(GB, "graph_baseline.py"), os.path.join(V3, "corpus.json")], GB)
p = os.path.join(tmp, "graph_sub.json")
with open(p, "w") as f:
    f.write(out)
check("graph_baseline.py output sha256 as its README states", sha(out) == gb_sha_stated, sha(out)[:16])
rc, o2, err = run(["check_submission.py", "corpus.json", p], V3)
check("graph_baseline.py output passes check_submission.py", rc == 0, (o2.strip().splitlines() or [""])[-1][:60])
rc, o3, err = run(["score.py", "corpus.json", p, "ANSWER_KEY.json"], V3)
row = re.search(r"^\| `graph_baseline\.py` \| found (\d+), false\+ (\d+) \| found (\d+), false\+ (\d+) \| \d+ \| \d+ \| \d+ \| ([0-9.]+) \| ([0-9.]+) \| ([0-9.]+) \|$", gb_readme, re.M)
ring = re.search(r"^ring\s+truth\s+6 found\s+(\d+) false\+\s+(\d+)", o3, re.M); syb = re.search(r"^sybil_cluster\s+truth\s+5 found\s+(\d+) false\+\s+(\d+)", o3, re.M)
summ = re.search(r"overall precision ([0-9.]+) recall ([0-9.]+); false-positive rate over 84 borrowers: ([0-9.]+)", o3)
got = (ring.group(1), ring.group(2), syb.group(1), syb.group(2), summ.group(1), summ.group(2), summ.group(3)) if ring and syb and summ else None
check("graph_baseline.py scores as its README row states", row is not None and got == row.groups(), "ring found %s false+ %s; P %s R %s FPR %s" % ((got[0], got[1], got[4], got[5], got[6]) if got else ("?",) * 5))

# 8. Clopper-Pearson rows
rc, out, err = run([os.path.join(LOBO, "cp_intervals.py")], LOBO)
lk = rd(os.path.join(V3, "LEAKCHECK_EXT_RESULTS.md"))
cp_rows = [l for l in out.splitlines() if l.startswith("| ") and not l.startswith("| class") and not l.startswith("|---")]
check("cp_intervals.py table rows appear verbatim in LEAKCHECK_EXT_RESULTS.md", cp_rows and all(l in lk for l in cp_rows), "%d rows" % len(cp_rows))

# 9. permutation nulls (seeded draws 1..N, NULL_SEED=1..N in leakcheck_ext.py; the recorded files were produced with the
#    private key). null_timing_1000.json is run_null_bonferroni.py output (has "draws"); null_all_400.json is the older
#    calibration-v3/run_null.py format (five fields per class, no draw count; LEAKCHECK_EXT_RESULTS.md says 400 draws).
#    run_null.py reads the key from a path on the operator's host, so it is not run here; run_null_bonferroni.py with
#    KEY_PATH computes the same five fields (same seeds, same quantile rule) plus p99 and the count.
OLD_FIELDS = ("observed", "null_median", "null_p95", "null_max", "frac_null_ge_observed")
for n, feats, recorded in ((N_TIMING, TIMING, "null_timing_1000.json"), (N_ALL, None, "null_all_400.json")):
    rec = json.loads(rd(os.path.join(LOBO, recorded)))
    old_format = "draws" not in rec
    n_rec = 400 if old_format else rec["draws"]
    if n == 0:
        print("SKIP  %s (null draws disabled)" % recorded); continue
    if n != n_rec:
        print("SKIP  %s (recorded %d draws, asked %d)" % (recorded, n_rec, n)); continue
    outp = os.path.join(tmp, recorded); t0 = time.time()
    rc, out, err = run([os.path.join(LOBO, "run_null_bonferroni.py"), str(n), outp] + ([feats] if feats else []), V3, {"KEY_PATH": "ANSWER_KEY.json"})
    got = json.loads(rd(outp)) if os.path.exists(outp) else None
    if old_format:
        same = got is not None and set(got["classes"]) == set(rec) and all(
            all(got["classes"][c][k] == rec[c][k] for k in OLD_FIELDS) for c in rec)
        check("%d null draws (all features) == %s on its five fields per class" % (n, recorded), same, "%.0f s" % (time.time() - t0))
    else:
        check("run_null_bonferroni.py %d draws == %s (full JSON equality)" % (n, recorded), got == rec, "%.0f s" % (time.time() - t0))

fails = [n for n, ok in results if not ok]
print("\n%d checks, %d failed%s" % (len(results), len(fails), (": " + "; ".join(fails)) if fails else ""))
sys.exit(1 if fails else 0)
