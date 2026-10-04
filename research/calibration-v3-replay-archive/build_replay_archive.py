#!/usr/bin/env python3
"""Build the calibration-v3 replay archive (codexmainbizmac d7c78081: create it now, hash it now, publish digest+manifest now,
bytes at reveal). Contents: the exact interpreter binary, the stdlib files the replay actually imports (whole package for any
package touched), replay_harness.py, the generator (already hash-bound in PRECOMMIT.md), validate_ledger.py, an acceptance
script and MANIFEST.json (per-file sha256 + system dependency report). Excludes site-packages, caches, pyc, credentials,
anything not imported. Deterministic: sorted names, fixed mtime, uid/gid 0, gzip mtime 0 / no filename.
Usage: build_replay_archive.py touched.json outdir   -> writes outdir/calibration-v3-replay-runtime.tar.gz + MANIFEST.json
Prints only hashes/sizes (no private values)."""
import os, sys, json, hashlib, tarfile, gzip, io, subprocess, platform, shutil, stat

touched = json.load(open(sys.argv[1]))
OUTDIR = os.path.abspath(sys.argv[2]); os.makedirs(OUTDIR, exist_ok=True)
PY = os.path.realpath(touched["executable"])
PREFIX = os.path.dirname(os.path.dirname(PY))
STDLIB = os.path.join(PREFIX, "lib", "python3.14")
ROOT = "calibration-v3-replay-runtime"
GEN = "/root/work/agents/gen_calibration_v3.py"
HARNESS = "/root/work/tb_cal/calibration-v3/replay_harness.py"
VALIDATOR = "/root/work/tb_cal/calibration-v3/validate_ledger.py"
MTIME = 1790000000  # fixed, arbitrary, documented

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()

# 1. stdlib files: whole package dir for any touched package, single file for modules; never __pycache__ or site-packages
files = {}  # archive path -> source path
for name, f in touched["modules"].items():
    if f == "<builtin>" or not f.startswith(STDLIB + os.sep):
        continue
    rel = os.path.relpath(f, STDLIB)
    if "site-packages" in rel:
        raise SystemExit("refusing: site-packages module touched: " + rel)
    top = rel.split(os.sep)[0]
    src_top = os.path.join(STDLIB, top)
    if os.path.isdir(src_top):   # package: include all .py under it (no caches)
        for r, ds, fs in os.walk(src_top):
            ds[:] = [d for d in ds if d != "__pycache__"]
            for x in fs:
                if x.endswith(".py"):
                    p = os.path.join(r, x)
                    files[os.path.join(ROOT, "lib", "python3.14", os.path.relpath(p, STDLIB))] = p
    else:
        files[os.path.join(ROOT, "lib", "python3.14", rel)] = f
files[os.path.join(ROOT, "bin", "python3.14")] = PY
files[os.path.join(ROOT, "replay_harness.py")] = HARNESS
files[os.path.join(ROOT, "gen_calibration_v3.py")] = GEN
files[os.path.join(ROOT, "validate_ledger.py")] = VALIDATOR

# extension modules actually imported from lib-dynload: none expected (all builtin); verify and record
dyn = os.path.join(STDLIB, "lib-dynload")
dyn_used = sorted(m for m in touched["maps"] if m.startswith(dyn))
if dyn_used:
    for m in dyn_used:
        files[os.path.join(ROOT, "lib", "python3.14", os.path.relpath(m, STDLIB))] = m

# 2. acceptance script
ACCEPT = r'''#!/bin/sh
# Acceptance test (codexmainbizmac d7c78081): run from the extracted, read-only archive on a host with no network.
# usage: sh acceptance_test.sh <seed> <key_salt_hex> <outdir>
# expected: the three sha256 values printed match calibration-v3/PRECOMMIT.md (corpus, COMMITMENT.txt, key file content
# is checked by the commitment) and validate_ledger.py exits 0.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SEED=$1; SALT=$2; OUT=$3
mkdir -p "$OUT"
"$HERE/bin/python3.14" -I -B "$HERE/verify_manifest.py"
"$HERE/bin/python3.14" -I -B "$HERE/replay_harness.py" "$HERE/gen_calibration_v3.py" "$SEED" "$OUT" "$SALT"
sha256sum "$OUT/corpus.json" "$OUT/COMMITMENT.txt" "$OUT/ANSWER_KEY_PRIVATE.json"
"$HERE/bin/python3.14" -I -B "$HERE/validate_ledger.py" "$OUT/corpus.json" && echo "validator exit 0"
'''
VERIFY = r'''#!/usr/bin/env python3
"""Verify every file listed in MANIFEST.json (next to this script) by size and sha256. Exit 0 only if all match."""
import json, hashlib, os, sys
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here.rstrip("/")) if os.path.basename(here) != "calibration-v3-replay-runtime" else os.path.dirname(here)
man = json.load(open(os.path.join(here, "MANIFEST.json")))
bad = 0
for ent in man["files"]:
    p = os.path.join(root, ent["path"])
    try:
        h = hashlib.sha256(open(p, "rb").read()).hexdigest(); ok = (h == ent["sha256"] and os.path.getsize(p) == ent["size"])
    except OSError:
        ok = False
    if not ok:
        bad += 1; print("MISMATCH", ent["path"])
print("manifest: %d files, %d mismatches" % (len(man["files"]), bad))
sys.exit(1 if bad else 0)
'''
stage = os.path.join(OUTDIR, "stage"); shutil.rmtree(stage, ignore_errors=True); os.makedirs(stage)
acc_path = os.path.join(stage, "acceptance_test.sh"); open(acc_path, "w").write(ACCEPT)
files[os.path.join(ROOT, "acceptance_test.sh")] = acc_path
ver_path = os.path.join(stage, "verify_manifest.py"); open(ver_path, "w").write(VERIFY)
files[os.path.join(ROOT, "verify_manifest.py")] = ver_path

# 3. system dependency report (not included in the archive; recorded)
sysdeps = []
for m in sorted(touched["maps"]):
    if m.startswith(PREFIX):
        continue
    try:
        sysdeps.append({"path": m, "sha256": sha(m), "size": os.path.getsize(m)})
    except OSError as e:
        sysdeps.append({"path": m, "error": str(e)})
glibc = subprocess.run(["ldd", "--version"], capture_output=True, text=True).stdout.splitlines()[0]

# 4. manifest
manifest_files = []
for ap in sorted(files):
    sp = files[ap]
    manifest_files.append({"path": ap, "size": os.path.getsize(sp), "sha256": sha(sp)})
manifest = {
    "archive": ROOT + ".tar.gz",
    "built": "2026-10-04",
    "purpose": "replay of calibration-v3 (generator + exact interpreter + imported stdlib); digest and manifest public now, bytes at reveal",
    "interpreter": {"path": ROOT + "/bin/python3.14", "sys.version": touched["version"], "sha256": sha(PY), "statically_linked_libpython": True},
    "builtin_modules_used": sorted(n for n, v in touched["modules"].items() if v == "<builtin>"),
    "lib_dynload_modules_used": [os.path.basename(m) for m in dyn_used],
    "system_dependencies_not_included": {"glibc": glibc, "kernel": platform.release(), "os": open("/etc/os-release").read().split('PRETTY_NAME="')[1].split('"')[0], "mapped_files": sysdeps},
    "excluded": ["site-packages", "__pycache__ / .pyc", "lib-dynload modules not imported", "tests", "include/", "share/", "credentials, histories, host files"],
    "tar_determinism": {"sort": "name", "mtime": MTIME, "uid_gid": 0, "gzip": "mtime=0, no filename, level 9"},
    "files": manifest_files,
}
man_path = os.path.join(stage, "MANIFEST.json")
json.dump(manifest, open(man_path, "w"), indent=1, sort_keys=True)
files[os.path.join(ROOT, "MANIFEST.json")] = man_path

# 5. deterministic tar.gz
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w", format=tarfile.GNU_FORMAT) as tf:
    # lib-dynload is included as an EMPTY directory: no extension module was imported, but the interpreter looks for the
    # directory to settle exec_prefix and prints a warning without it
    dirs = sorted({os.path.dirname(p) for p in files} | {ROOT, os.path.join(ROOT, "lib", "python3.14", "lib-dynload")})
    seen = set()
    for d in dirs:
        parts = d.split("/")
        for i in range(1, len(parts) + 1):
            dd = "/".join(parts[:i])
            if dd in seen: continue
            seen.add(dd)
            ti = tarfile.TarInfo(dd); ti.type = tarfile.DIRTYPE; ti.mode = 0o755; ti.mtime = MTIME; ti.uid = ti.gid = 0; ti.uname = ti.gname = ""
            tf.addfile(ti)
    for ap in sorted(files):
        sp = files[ap]
        ti = tarfile.TarInfo(ap); ti.size = os.path.getsize(sp); ti.mtime = MTIME; ti.uid = ti.gid = 0; ti.uname = ti.gname = ""
        ti.mode = 0o755 if (ap.endswith("python3.14") or ap.endswith(".sh")) else 0o644
        with open(sp, "rb") as f:
            tf.addfile(ti, f)
raw = buf.getvalue()
out_path = os.path.join(OUTDIR, ROOT + ".tar.gz")
with open(out_path, "wb") as fo:
    with gzip.GzipFile(filename="", mode="wb", fileobj=fo, mtime=0, compresslevel=9) as gz:
        gz.write(raw)
shutil.copy(man_path, os.path.join(OUTDIR, "MANIFEST.json"))
shutil.rmtree(stage)
print("archive:", out_path)
print("archive sha256:", sha(out_path), "size:", os.path.getsize(out_path))
print("tar (uncompressed) sha256:", hashlib.sha256(raw).hexdigest(), "size:", len(raw))
print("files in archive:", len(files), "| stdlib .py:", sum(1 for p in files if "/lib/python3.14/" in p and p.endswith(".py")), "| lib-dynload used:", dyn_used)
print("manifest sha256:", sha(os.path.join(OUTDIR, "MANIFEST.json")))
print("interpreter sha256:", manifest["interpreter"]["sha256"])
print("generator sha256:", sha(GEN), "| harness:", sha(HARNESS), "| validator:", sha(VALIDATOR))
