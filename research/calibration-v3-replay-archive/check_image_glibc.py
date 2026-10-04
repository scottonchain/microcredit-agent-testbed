#!/usr/bin/env python3
"""Does a public container image carry the glibc that calibration-v3's replay archive binds? (stdlib only, unauthenticated)

usage: python3 check_image_glibc.py REVEAL.json [image_ref] [download_dir]

image_ref defaults to docker.io/library/almalinux:9.8; a digest reference (almalinux@sha256:...) is accepted and preferred.
Pulls the image index and the linux/amd64 manifest from the Docker Hub registry API, downloads each layer, verifies the
layer digest while writing, then hashes /usr/lib64/libc.so.6 and /usr/lib64/ld-linux-x86-64.so.2 inside the layer tar
(later layers override earlier ones; a whiteout removes the file). Compares with REVEAL.json glibc.libc_so_6_sha256 and
glibc.ld_linux_x86_64_so_2_sha256. Nothing is extracted to disk except the layer blobs. Exit 0 and print GLIBC_MATCH when
both digests equal the bound values; otherwise GLIBC_DIFFERENT (or GLIBC_MISSING) and exit 1. A match means a verifier
who runs the acceptance test inside this image (by digest, network disabled) runs on the bound glibc ABI; it does not
make the image an authority for anything else.

Exercised 2026-10-04 (operator host, unauthenticated pulls): docker.io/library/almalinux:9.8 -> GLIBC_MATCH
(linux/amd64 sha256:dc973f4dffd28a1e6ae4d1662086d83bac34cd26f3b701e7ba51f4dcb300c80d); almalinux:9.8-minimal -> GLIBC_MATCH
(sha256:6eb4108a747b549f552caa7b60a50c3b3262d61dae34cc6d4fe3a231de439d6e); almalinux:9.5 -> GLIBC_DIFFERENT (negative control,
sha256:91387bd5b12c2626c9b01a8062e6dd02cdf3a9d4b9ba705631c01597f9e3ae06). Tags move; record the amd64 manifest digest.
"""
import hashlib, json, os, sys, tarfile, urllib.request

UA = {"User-Agent": "calibration-v3-reveal-check"}
WANT_PATHS = ("usr/lib64/libc.so.6", "usr/lib64/ld-linux-x86-64.so.2")
ACCEPT = ", ".join(["application/vnd.docker.distribution.manifest.list.v2+json", "application/vnd.oci.image.index.v1+json",
                    "application/vnd.docker.distribution.manifest.v2+json", "application/vnd.oci.image.manifest.v1+json"])


def parse_ref(ref):
    ref = ref.replace("docker.io/", "", 1)
    if "@" in ref:
        name, digest = ref.split("@", 1)
    elif ":" in ref.rsplit("/", 1)[-1]:
        name, digest = ref.rsplit(":", 1)
    else:
        name, digest = ref, "latest"
    if "/" not in name:
        name = "library/" + name
    return name, digest


def fetch(url, headers, raw=False):
    req = urllib.request.Request(url, headers={**UA, **headers})
    if raw:
        return urllib.request.urlopen(req, timeout=600)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), dict(r.headers)


def main():
    reveal = json.load(open(sys.argv[1]))
    ref = sys.argv[2] if len(sys.argv) > 2 else "docker.io/library/almalinux:9.8"
    outdir = sys.argv[3] if len(sys.argv) > 3 else "."
    want = {WANT_PATHS[0]: reveal["glibc"]["libc_so_6_sha256"], WANT_PATHS[1]: reveal["glibc"]["ld_linux_x86_64_so_2_sha256"]}
    repo, tag_or_digest = parse_ref(ref)
    tok_body, _ = fetch("https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s:pull" % repo, {})
    H = {"Authorization": "Bearer " + json.loads(tok_body)["token"], "Accept": ACCEPT}
    body, hdrs = fetch("https://registry-1.docker.io/v2/%s/manifests/%s" % (repo, tag_or_digest), H)
    top_digest = "sha256:" + hashlib.sha256(body).hexdigest()
    if tag_or_digest.startswith("sha256:") and top_digest != tag_or_digest:
        print("MANIFEST_DIGEST_MISMATCH", top_digest); sys.exit(1)
    doc = json.loads(body)
    print("image", ref, "| top-level digest", top_digest, "| mediaType", doc.get("mediaType"))
    if "manifests" in doc:  # index: pick linux/amd64
        pick = [m for m in doc["manifests"] if (m.get("platform") or {}).get("architecture") == "amd64" and (m.get("platform") or {}).get("os") == "linux"]
        if not pick:
            print("GLIBC_MISSING no linux/amd64 manifest in index"); sys.exit(1)
        mdigest = pick[0]["digest"]
        body, _ = fetch("https://registry-1.docker.io/v2/%s/manifests/%s" % (repo, mdigest), H)
        if "sha256:" + hashlib.sha256(body).hexdigest() != mdigest:
            print("MANIFEST_DIGEST_MISMATCH", mdigest); sys.exit(1)
        doc = json.loads(body)
        print("linux/amd64 manifest digest", mdigest, "(use %s@%s to pin this exact image)" % (repo.replace("library/", ""), mdigest))
    else:
        mdigest = top_digest
    print("config", doc["config"]["digest"], "| layers", len(doc["layers"]))
    found = {}
    for l in doc["layers"]:
        path = os.path.join(outdir, l["digest"].replace(":", "_") + ".tar.gz")
        if not (os.path.exists(path) and os.path.getsize(path) == l["size"]):
            h = hashlib.sha256()
            with fetch("https://registry-1.docker.io/v2/%s/blobs/%s" % (repo, l["digest"]), H, raw=True) as r, open(path, "wb") as fo:
                for ch in iter(lambda: r.read(1 << 20), b""):
                    h.update(ch); fo.write(ch)
            if "sha256:" + h.hexdigest() != l["digest"]:
                print("LAYER_DIGEST_MISMATCH", l["digest"]); sys.exit(1)
        print("layer", l["digest"], l["size"], "bytes, digest verified")
        with tarfile.open(path, "r:gz") as tf:
            for ti in tf:
                name = ti.name.lstrip("./")
                d, b = os.path.split(name)
                if b.startswith(".wh.") and os.path.join(d, b[4:]) in want:
                    found[os.path.join(d, b[4:])] = None
                if name in want:
                    found[name] = hashlib.sha256(tf.extractfile(ti).read()).hexdigest() if ti.isfile() else ("link->" + ti.linkname)
    ok = True
    for p, w in want.items():
        got = found.get(p)
        status = "MATCH" if got == w else ("MISSING" if got is None else "DIFFERENT")
        ok = ok and status == "MATCH"
        print(" ", p, "bound", w, "image", got, status)
    print("GLIBC_MATCH" if ok else ("GLIBC_MISSING" if any(found.get(p) is None for p in want) else "GLIBC_DIFFERENT"), "amd64", mdigest)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
