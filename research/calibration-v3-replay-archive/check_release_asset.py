#!/usr/bin/env python3
"""Verify a recorded release tag, asset identity, byte count and SHA-256.

Usage: check_release_asset.py REVEAL.json [download_dir]
The tag is always resolved to its commit, even if release metadata names that
commit. Downloaded bytes replace the output only after verification succeeds.
This checks the published asset; it does not execute or rebuild the archive.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request

UA = {"User-Agent": "calibration-v3-reveal-check"}


class VerificationError(ValueError):
    pass


def get_json(url):
    req = urllib.request.Request(url, headers={**UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode())


def tag_commit(repo, tag):
    encoded = urllib.parse.quote(tag, safe="")
    obj = get_json(f"https://api.github.com/repos/{repo}/git/ref/tags/{encoded}").get("object", {})
    seen = set()
    for _ in range(16):
        sha, kind = obj.get("sha"), obj.get("type")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            break
        if kind == "commit":
            return sha
        if kind != "tag" or sha in seen:
            break
        seen.add(sha)
        # Resolve inside the expected repository, rather than trusting an API-provided URL.
        obj = get_json(f"https://api.github.com/repos/{repo}/git/tags/{sha}").get("object", {})
    raise VerificationError("RELEASE_COMMIT_MISMATCH unresolved or cyclic tag")


def verify(reveal, outdir):
    repo, tag, name = reveal["repo"], reveal["release_tag"], reveal["asset_name"]
    if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise VerificationError("invalid repository")
    if not isinstance(tag, str) or not tag:
        raise VerificationError("invalid release tag")
    if not isinstance(name, str) or name in ("", ".", "..") or "/" in name or "\\" in name:
        raise VerificationError("invalid asset filename")
    if (type(reveal["asset_id"]) is not int or reveal["asset_id"] < 1
            or type(reveal["byte_count"]) is not int or reveal["byte_count"] < 0
            or not isinstance(reveal["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", reveal["sha256"])):
        raise VerificationError("invalid recorded asset identity, size or digest")
    rel = get_json(f"https://api.github.com/repos/{repo}/releases/tags/{urllib.parse.quote(tag, safe='')}")
    if reveal.get("release_commit"):
        commit = tag_commit(repo, tag)
        if commit != reveal["release_commit"]:
            raise VerificationError(f"RELEASE_COMMIT_MISMATCH tag->{commit} recorded {reveal['release_commit']}")
    assets = [asset for asset in rel.get("assets", []) if asset.get("name") == name]
    if not assets:
        raise VerificationError(f"RELEASE_ASSET_MISSING {name}")
    if len(assets) != 1:
        raise VerificationError(f"RELEASE_ASSET_REPLACED ambiguous asset name {name}")
    asset = assets[0]
    for key, expected in (("id", reveal["asset_id"]), ("size", reveal["byte_count"])):
        if asset.get(key) != expected:
            raise VerificationError(f"RELEASE_ASSET_REPLACED {key} {asset.get(key)} != recorded {expected}")
    url = asset.get("browser_download_url")
    if not isinstance(url, str) or not url.startswith("https://") or (reveal.get("url") and url != reveal["url"]):
        raise VerificationError("RELEASE_ASSET_REPLACED download URL differs or is not HTTPS")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    target = outdir / name
    # A corrupt or interrupted download must not replace a previously verified file.
    temporary = None
    try:
        digest, count = hashlib.sha256(), 0
        with tempfile.NamedTemporaryFile(dir=outdir, prefix=".release-", delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as response:
                for chunk in iter(lambda: response.read(1 << 20), b""):
                    digest.update(chunk)
                    output.write(chunk)
                    count += len(chunk)
                    if count > reveal["byte_count"]:
                        raise VerificationError("RELEASE_ASSET_REPLACED download exceeds recorded byte count")
        if count != reveal["byte_count"] or digest.hexdigest() != reveal["sha256"]:
            raise VerificationError(f"RELEASE_ASSET_REPLACED downloaded {count} bytes sha256 {digest.hexdigest()}; "
                                    f"recorded {reveal['byte_count']} bytes sha256 {reveal['sha256']}")
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return f"OK {name} id={asset['id']} bytes={count} sha256={digest.hexdigest()} -> {target}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reveal", type=Path)
    parser.add_argument("download_dir", nargs="?", default=".", type=Path)
    args = parser.parse_args(argv)
    try:
        reveal = json.loads(args.reveal.read_text(encoding="utf-8"))
        print(verify(reveal, args.download_dir))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
