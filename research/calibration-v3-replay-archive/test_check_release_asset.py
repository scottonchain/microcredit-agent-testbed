"""Exercise check_release_asset.py against a real public GitHub release (smallest asset of ripgrep's latest release):
expect OK with the true values, RELEASE_ASSET_REPLACED with a wrong digest, RELEASE_ASSET_MISSING with a wrong name."""
import hashlib, json, os, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "/root/.hermes/cache/scratch/run18_release_test"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "calibration-v3-reveal-check", "Accept": "application/vnd.github+json"}

def gj(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read().decode())

repo = "BurntSushi/ripgrep"
rel = gj("https://api.github.com/repos/%s/releases/latest" % repo)
tag = rel["tag_name"]
asset = min(rel["assets"], key=lambda a: a["size"])
ref = gj("https://api.github.com/repos/%s/git/ref/tags/%s" % (repo, tag))
obj = ref["object"]
commit = obj["sha"] if obj["type"] == "commit" else gj(obj["url"])["object"]["sha"]
data = urllib.request.urlopen(urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": UA["User-Agent"]}), timeout=120).read()
reveal = {"repo": repo, "release_tag": tag, "release_commit": commit, "asset_id": asset["id"], "asset_name": asset["name"],
          "byte_count": len(data), "sha256": hashlib.sha256(data).hexdigest(), "url": asset["browser_download_url"]}
print("fixture:", json.dumps(reveal))
assert len(data) == asset["size"]

def run(rv, label):
    p = os.path.join(OUT, label + ".json")
    json.dump(rv, open(p, "w"))
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_release_asset.py"), p, OUT], capture_output=True, text=True, timeout=300)
    print("[%s] rc=%d %s %s" % (label, r.returncode, r.stdout.strip()[:300], r.stderr.strip()[-300:]))
    return r.returncode, r.stdout

rc0, out0 = run(reveal, "true")
rc1, out1 = run({**reveal, "sha256": "00" * 32}, "wrong_digest")
rc2, out2 = run({**reveal, "asset_name": "no-such-asset.bin"}, "wrong_name")
rc3, out3 = run({**reveal, "asset_id": reveal["asset_id"] + 1}, "wrong_id")
ok = rc0 == 0 and out0.startswith("OK") and rc1 == 1 and "RELEASE_ASSET_REPLACED" in out1 and rc2 == 1 and "RELEASE_ASSET_MISSING" in out2 and rc3 == 1 and "RELEASE_ASSET_REPLACED" in out3
print("ALL EXPECTED:", ok)
