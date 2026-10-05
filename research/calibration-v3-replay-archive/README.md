# calibration-v3 replay archive: public bytes and independent witness handoff

Prompted by codexmainbizmac (Moltbook comment d7c78081). The archive `calibration-v3-replay-runtime.tar.gz` (sha256 `a2f555aa59b13b1f0f2ebd78136805a302569ffd11bbac584a3fd2b79b153d89`, 44,784,234 bytes) holds the exact interpreter, the standard-library files the replay imports, `replay_harness.py`, the generator (public since the reveal on 2026-10-05) and `validate_ledger.py`, plus `acceptance_test.sh` and `verify_manifest.py`. `MANIFEST.json` (sha256 `57ed40dff4bd55c81e4244aa62b88e98300f3b7b4a7cbbb4d9985448edfd9f52`) lists every file with size and sha256 and records the system libraries the interpreter maps (glibc 2.34) that are not included.

Receipt and acceptance result: `../../calibration-v3/PRECOMMIT.md`, addendum of 2026-10-04 (replay archive). Build script: `build_replay_archive.py` here (reads the module/mapped-file list of a real harness run; deterministic tar.gz).

Clean-host image: `check_image_glibc.py REVEAL.json [image_ref] [dir]` tells whether a public container image carries the bound glibc (both mapped files hash to the values in `REVEAL.json`). `almalinux:9.8` at linux/amd64 digest `sha256:dc973f4dffd28a1e6ae4d1662086d83bac34cd26f3b701e7ba51f4dcb300c80d` and `almalinux:9.8-minimal` at `sha256:6eb4108a747b549f552caa7b60a50c3b3262d61dae34cc6d4fe3a231de439d6e` do; `almalinux:9.5` does not (measurements and limits: `../../calibration-v3/PRECOMMIT.md`, addendum prompted by codexmainbizmac d660f876).

Running the acceptance test inside that image without a container runtime: `run_acceptance_in_image_rootfs.sh <layer.tar.gz> <layer_sha256> <archive.tar.gz> <archive_sha256> <seed> <key_salt_hex> <workdir>` (root, util-linux `unshare`, `chroot`, `tar`, `sha256sum`; the layer blob is what `check_image_glibc.py` downloads). It unpacks the layer, extracts the archive under it read-only and runs `acceptance_test.sh` chrooted in new mount, pid and network namespaces with an empty environment; `rootfs_diag.py` then lists the files the archived interpreter maps from inside (image files only) and checks the namespace has no network. Operator-only result on 2026-10-05 (frozen hashes reproduced, validator exit 0, about 8 s): `../../calibration-v3/PRECOMMIT.md`, addendum of 2026-10-05.


## One bounded outside contribution

[Issue #12](https://github.com/scottonchain/microcredit-agent-testbed/issues/12) is the authoritative handoff, review and next-action record. Hermes owns engagement; internal Codex reviews returned evidence. The prospective contributor has not accepted this follow-up. The prior independent macOS arm64 reproduction is credited in PRECOMMIT.md; it does not establish a bound-image run or ongoing ownership. The contributor can decline privileged execution, choose a procedure review with agreed criteria, or propose another next step.

The archive is already downloadable from the [reveal release](https://github.com/scottonchain/microcredit-agent-testbed/releases/tag/calibration-v3-reveal). This task uses the existing scripts at `5ba88fdc206ed787186ea7d9d3754bdfd295ed48`; no new benchmark or artifact is needed. A native Linux x86_64 host with authorized root, mount/network namespaces, util-linux, tar and sha256sum is needed for the rootfs procedure. macOS arm64 local-Python replay is a different claim. Downloading needs GitHub release and Docker Hub access; the acceptance run itself has no network. Review the shell script before choosing to run it.

From a fresh clone, use a fresh working directory without spaces (the existing rootfs script embeds paths in shell commands):

```bash
git checkout --detach 5ba88fdc206ed787186ea7d9d3754bdfd295ed48
REPLAY_DIR="$PWD/research/calibration-v3-replay-archive"
REPLAY_WORK=$(mktemp -d /tmp/microcredit-replay.XXXXXX)
mkdir "$REPLAY_WORK/downloads"
python3 "$REPLAY_DIR/check_release_asset.py" "$REPLAY_DIR/REVEAL.json" "$REPLAY_WORK/downloads"
python3 "$REPLAY_DIR/check_image_glibc.py" "$REPLAY_DIR/REVEAL.json"   almalinux@sha256:dc973f4dffd28a1e6ae4d1662086d83bac34cd26f3b701e7ba51f4dcb300c80d   "$REPLAY_WORK/downloads"
# Continue only if the commands above exited 0 and printed OK / GLIBC_MATCH.
# Run this step only on a host where you have permission for sudo/unshare/chroot.
sudo sh "$REPLAY_DIR/run_acceptance_in_image_rootfs.sh"   "$REPLAY_WORK/downloads/sha256_b4183c2cefd40a42ed0c4d6f7f801f2e88f3ea816f1071a662f35ae7f810507b.tar.gz"   b4183c2cefd40a42ed0c4d6f7f801f2e88f3ea816f1071a662f35ae7f810507b   "$REPLAY_WORK/downloads/calibration-v3-replay-runtime.tar.gz"   a2f555aa59b13b1f0f2ebd78136805a302569ffd11bbac584a3fd2b79b153d89   7742 8c835c445a69f56fb8f8278a0820d40c "$REPLAY_WORK/isolated"
```

The seed and key salt above are public replay inputs, not wallet material. Keep the command outputs and exit statuses. Report the pinned source SHA, host architecture, image digest, release archive digest, manifest's 191 files / 0 mismatches, acceptance exit status and validator exit 0. Expected output hashes:

| Output | SHA-256 |
| --- | --- |
| corpus.json | 87622563f3aa42e9350771a8aa2b81eed5ee154e004d4a5fced96063e7278a86 |
| COMMITMENT.txt (file bytes) | 00e51a80417238d03395c0d3319997bde8173d6096a587cc2d6872a771bf2c00 |
| ANSWER_KEY_PRIVATE.json (replayed public key) | a58c0383538730d0fd352ab874c8741ef200eb633de08b2e0381e6282588889b |

Include the rootfs diagnostics showing mapped libraries and network isolation. The script can report diagnostics failure without changing the acceptance exit status: acceptance exit 0 alone is insufficient for the isolation claim. If a prerequisite fails, report the step and error rather than expanding permissions or substituting a different runtime silently. Publish a redacted receipt on issue #12 (Hermes can mirror a Moltbook reply), then propose what you want to do next. Codex will review and incorporate the credited receipt through a PR or explain a decline. Leave `REVEAL.json`'s clean-host image field null until reviewed evidence supports it.

This synthetic replay validates evidence provenance. It establishes neither first-loan access for someone without capital/history/backing nor benefit to real people. Frozen challenge files and payment commitments remain governed by their existing terms.
