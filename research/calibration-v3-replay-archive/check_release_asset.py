#!/usr/bin/env python3
"""Check a GitHub release asset against REVEAL.json (stdlib only, unauthenticated).

usage: python3 check_release_asset.py REVEAL.json [download_dir]

REVEAL.json fields: repo ("owner/name"), release_tag, release_commit, asset_id (int),
asset_name, byte_count (int), sha256 (hex), url (browser_download_url).

Exit 0 and print OK when the asset the API serves for (repo, tag, asset_name) has the
recorded id and size, the release points at the recorded commit, and the downloaded
bytes hash to the recorded sha256. Any other outcome prints RELEASE_ASSET_REPLACED
(id, size or digest differ), RELEASE_ASSET_MISSING (no such asset) or
RELEASE_COMMIT_MISMATCH and exits 1. Nothing is extracted; verify the digest first,
then extract elsewhere.
"""
import hashlib, json, os, sys, urllib.request

UA = {"User-Agent": "calibration-v3-reveal-check"}


def get_json(url):
    req = urllib.request.Request(url, headers={**UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    reveal = json.load(open(sys.argv[1]))
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    repo, tag = reveal["repo"], reveal["release_tag"]
    rel = get_json("https://api.github.com/repos/%s/releases/tags/%s" % (repo, tag))
    problems = []
    if reveal.get("release_commit") and rel.get("target_commitish") not in (reveal["release_commit"], None):
        # target_commitish may be a branch name; resolve the tag to a commit as well
        try:
            ref = get_json("https://api.github.com/repos/%s/git/ref/tags/%s" % (repo, tag))
            obj = ref.get("object", {})
            sha = obj.get("sha")
            if obj.get("type") == "tag":
                sha = get_json(obj["url"]).get("object", {}).get("sha")
            if sha != reveal["release_commit"]:
                problems.append("RELEASE_COMMIT_MISMATCH tag->%s recorded %s" % (sha, reveal["release_commit"]))
        except Exception as e:  # noqa
            problems.append("RELEASE_COMMIT_MISMATCH (could not resolve tag: %s)" % e)
    assets = [a for a in rel.get("assets", []) if a.get("name") == reveal["asset_name"]]
    if not assets:
        print("RELEASE_ASSET_MISSING", reveal["asset_name"])
        sys.exit(1)
    a = assets[0]
    if a.get("id") != reveal["asset_id"]:
        problems.append("RELEASE_ASSET_REPLACED id %s != recorded %s" % (a.get("id"), reveal["asset_id"]))
    if a.get("size") != reveal["byte_count"]:
        problems.append("RELEASE_ASSET_REPLACED size %s != recorded %s" % (a.get("size"), reveal["byte_count"]))
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    dl = a.get("browser_download_url")
    if reveal.get("url") and dl != reveal["url"]:
        print("RELEASE_ASSET_REPLACED url %s != recorded %s" % (dl, reveal["url"]))
        sys.exit(1)
    path = os.path.join(outdir, reveal["asset_name"])
    h = hashlib.sha256()
    n = 0
    with urllib.request.urlopen(urllib.request.Request(dl, headers=UA), timeout=600) as r, open(path, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            f.write(chunk)
            n += len(chunk)
    digest = h.hexdigest()
    if n != reveal["byte_count"] or digest != reveal["sha256"]:
        print("RELEASE_ASSET_REPLACED downloaded %d bytes sha256 %s; recorded %d bytes sha256 %s" % (n, digest, reveal["byte_count"], reveal["sha256"]))
        sys.exit(1)
    print("OK %s id=%s bytes=%d sha256=%s -> %s" % (reveal["asset_name"], a["id"], n, digest, path))


if __name__ == "__main__":
    main()
