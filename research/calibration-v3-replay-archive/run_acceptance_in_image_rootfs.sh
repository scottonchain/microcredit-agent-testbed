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
# Chroot is not containment for uid 0 in the initial user namespace.
# Run ONLY inside an expendable Linux x86_64 VM with no credentials, shared host
# directories or valuable state. Destroy that VM after collecting the receipt.
set -eu
[ "$#" = 7 ] || { echo "expected seven arguments"; exit 2; }
[ "${REPLAY_DISPOSABLE_VM:-}" = yes ] || { echo "DISPOSABLE_VM_REQUIRED: set REPLAY_DISPOSABLE_VM=yes only inside a disposable VM"; exit 2; }
LAYER=$1; LAYER_SHA=$2; ARCH=$3; ARCH_SHA=$4; SEED=$5; SALT=$6; WORK=$7
HERE=$(cd "$(dirname "$0")" && pwd)
[ "$(id -u)" = 0 ] || { echo "needs root inside the disposable VM"; exit 2; }
[ "$(uname -m)" = x86_64 ] || { echo "needs Linux x86_64"; exit 2; }
[ "$(uname -s)" = Linux ] || exit 2
LIBC_SHA=c6b12761834ea9a2fde7a17682ebfaf37982a0df6e9345e5b9d298ac1ca3c746
LOADER_SHA=58b211cde994b9373c9a39abeb2633191b832574c7ca0bd44e362d33e0cc6111
# Hash stdin so path characters are never interpreted as checksum-list syntax.
[ "$(sha256sum < "$LAYER" | cut -d ' ' -f 1)" = "$LAYER_SHA" ] || { echo LAYER_DIGEST_MISMATCH; exit 1; }
[ "$(sha256sum < "$ARCH" | cut -d ' ' -f 1)" = "$ARCH_SHA" ] || { echo ARCHIVE_DIGEST_MISMATCH; exit 1; }
echo "layer digest verified: $LAYER_SHA"
echo "archive digest verified: $ARCH_SHA"
# Reject pre-existing state (including symlinks); do not reuse a prior rootfs.
mkdir "$WORK"
WORK=$(cd "$WORK" && pwd)
ROOT=$WORK/rootfs
mkdir "$ROOT"
tar -xzf "$LAYER" -C "$ROOT" --numeric-owner
mkdir -p "$ROOT/replay" "$ROOT/out" "$ROOT/dev" "$ROOT/proc"
tar -xzf "$ARCH" -C "$ROOT/replay"
chmod -R a-w "$ROOT/replay"
[ -e "$ROOT/dev/null" ] || mknod -m 666 "$ROOT/dev/null" c 1 3
[ -e "$ROOT/dev/zero" ] || mknod -m 666 "$ROOT/dev/zero" c 1 5
[ -e "$ROOT/dev/random" ] || mknod -m 666 "$ROOT/dev/random" c 1 8
[ -e "$ROOT/dev/urandom" ] || mknod -m 666 "$ROOT/dev/urandom" c 1 9
cp "$HERE/rootfs_diag.py" "$ROOT/out/diag.py"
# Constant shell source, arguments passed positionally: quotes/spaces in paths
# and replay inputs cannot become shell syntax.
set +e
unshare -m -p -f -n sh -c '
    set -eu
    root=$1; seed=$2; salt=$3
    mount --make-rprivate /
    mount -t proc proc "$root/proc"
    exec chroot "$root" /usr/bin/env -i PATH=/usr/bin:/bin /usr/bin/sh /replay/calibration-v3-replay-runtime/acceptance_test.sh "$seed" "$salt" /out
' replay-acceptance "$ROOT" "$SEED" "$SALT" > "$WORK/acceptance.log" 2>&1
ACCEPTANCE_RC=$?
unshare -m -p -f -n sh -c '
    set -eu
    root=$1; libc=$2; loader=$3
    mount --make-rprivate /
    mount -t proc proc "$root/proc"
    exec chroot "$root" /usr/bin/env -i /replay/calibration-v3-replay-runtime/bin/python3.14 -I -B /out/diag.py "$libc" "$loader"
' replay-diagnostics "$ROOT" "$LIBC_SHA" "$LOADER_SHA" > "$WORK/diagnostics.log" 2>&1
DIAG_RC=$?
set -e
cat "$WORK/acceptance.log" "$WORK/diagnostics.log"
printf 'acceptance_rc=%s\ndiag_rc=%s\n' "$ACCEPTANCE_RC" "$DIAG_RC"
[ "$ACCEPTANCE_RC" = 0 ] && [ "$DIAG_RC" = 0 ] || exit 1
grep -qx 'network: isolated' "$WORK/diagnostics.log" || exit 1
grep -qx 'glibc: bound' "$WORK/diagnostics.log" || exit 1
grep -qx "sha256 /usr/lib64/libc.so.6 $LIBC_SHA" "$WORK/diagnostics.log" || exit 1
grep -qx "sha256 /usr/lib64/ld-linux-x86-64.so.2 $LOADER_SHA" "$WORK/diagnostics.log" || exit 1
echo "RECEIPT_GATE_OK"
echo "outputs and logs are under $WORK; collect them, then destroy the VM"
