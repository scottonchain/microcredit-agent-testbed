#!/bin/sh
# calibration-v3 replay: run the archive's acceptance test INSIDE the root filesystem of a container image, without a
# container runtime. For a rerunner (or anyone) on a Linux x86_64 host with root, util-linux `unshare`, `chroot`, `tar`,
# `sha256sum`. The test runs chrooted into the unpacked image layer in new mount, pid and network namespaces: the host's
# glibc, Python and NSS modules are unreachable, and the network namespace has no interface but loopback.
#
# usage: sh run_acceptance_in_image_rootfs.sh <layer.tar.gz> <layer_sha256_hex> <replay-archive.tar.gz> <archive_sha256_hex> <seed> <key_salt_hex> <workdir>
#
# Get the layer blob with `check_image_glibc.py REVEAL.json almalinux@sha256:<amd64 manifest digest> <download_dir>`: it writes
# every layer, digest-verified, as <download_dir>/sha256_<digest>.tar.gz. almalinux:9.8 at linux/amd64
# sha256:dc973f4dffd28a1e6ae4d1662086d83bac34cd26f3b701e7ba51f4dcb300c80d has exactly one layer,
# sha256:b4183c2cefd40a42ed0c4d6f7f801f2e88f3ea816f1071a662f35ae7f810507b (71,704,075 bytes). This script assumes one layer.
# With a container runtime the equivalent is:
#   docker run --rm --network none -v <dir with the extracted archive>:/replay:ro almalinux@sha256:dc973f4d... \
#     sh /replay/calibration-v3-replay-runtime/acceptance_test.sh <seed> <key_salt_hex> /tmp/out
# Expected: verify_manifest.py prints 0 mismatches, the three sha256 lines match calibration-v3/PRECOMMIT.md, "validator exit 0".
set -eu
LAYER=$1; LAYER_SHA=$2; ARCH=$3; ARCH_SHA=$4; SEED=$5; SALT=$6; WORK=$7
HERE=$(cd "$(dirname "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo "needs root (tar as root, mknod, chroot, unshare)"; exit 2; }
echo "$LAYER_SHA  $LAYER" | sha256sum -c - >/dev/null 2>&1 || { echo "LAYER_DIGEST_MISMATCH $LAYER"; exit 1; }
echo "layer digest verified: $LAYER_SHA"
echo "$ARCH_SHA  $ARCH" | sha256sum -c - >/dev/null 2>&1 || { echo "ARCHIVE_DIGEST_MISMATCH $ARCH"; exit 1; }
echo "archive digest verified: $ARCH_SHA"
ROOT=$WORK/rootfs
mkdir -p "$ROOT"
tar -xzf "$LAYER" -C "$ROOT" --numeric-owner
echo "layer unpacked into $ROOT ($(find "$ROOT" | wc -l) entries)"
mkdir -p "$ROOT/replay" "$ROOT/out" "$ROOT/dev" "$ROOT/proc"
tar -xzf "$ARCH" -C "$ROOT/replay"
chmod -R a-w "$ROOT/replay"
[ -e "$ROOT/dev/null" ] || mknod -m 666 "$ROOT/dev/null" c 1 3
[ -e "$ROOT/dev/zero" ] || mknod -m 666 "$ROOT/dev/zero" c 1 5
[ -e "$ROOT/dev/random" ] || mknod -m 666 "$ROOT/dev/random" c 1 8
[ -e "$ROOT/dev/urandom" ] || mknod -m 666 "$ROOT/dev/urandom" c 1 9
cp "$HERE/rootfs_diag.py" "$ROOT/out/diag.py"
echo "glibc files inside the unpacked layer:"
sha256sum "$ROOT/usr/lib64/libc.so.6" "$ROOT/usr/lib64/ld-linux-x86-64.so.2" | sed "s# $ROOT/#  /#"
echo "=== acceptance test inside the rootfs (unshare -m -p -f -n, chroot, empty environment) ==="
set +e
unshare -m -p -f -n sh -c "mount --make-rprivate / && mount -t proc proc '$ROOT/proc' && exec chroot '$ROOT' /usr/bin/env -i PATH=/usr/bin:/bin /usr/bin/sh /replay/calibration-v3-replay-runtime/acceptance_test.sh '$SEED' '$SALT' /out"
RC=$?
set -e
echo "acceptance_test.sh exit status: $RC"
echo "=== diagnostics inside the rootfs (archived interpreter): mapped files, network, glibc as seen from inside ==="
unshare -m -p -f -n sh -c "mount --make-rprivate / && mount -t proc proc '$ROOT/proc' && exec chroot '$ROOT' /usr/bin/env -i /replay/calibration-v3-replay-runtime/bin/python3.14 -I -B /out/diag.py" || echo "diagnostics exit status: $?"
echo "outputs are in $ROOT/out (corpus.json, COMMITMENT.txt, ANSWER_KEY_PRIVATE.json); remove $WORK yourself"
exit $RC
