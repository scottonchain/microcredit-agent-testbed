"""Regression check: a rewrite of /out/diag.py by the acceptance step must not change the receipt gate's verdict.

run_acceptance_in_image_rootfs.sh copies rootfs_diag.py to <rootfs>/out/diag.py, runs /out/diag.py first in its
own namespace and captures its output outside the rootfs, then runs the acceptance step (archive-controlled code,
uid 0, /out is its output directory), and gates the receipt on the diagnostics lines captured before that step.
Like test_hardening.py this needs no root and runs no archive code: id, uname, tar and unshare are PATH stubs. The
unshare stub runs whatever file is at <rootfs>/out/diag.py with the host python (no namespace, no chroot), so the
genuine rootfs_diag.py sees the test host's network and fails the gate; the check is skipped on a host where it
would pass. The rewrite case replaces /out/diag.py from inside the acceptance stub, as code running in that step
could; because the diagnostics ran and were captured before the acceptance step, the forged file is never run and
the verdict stays the same.

Covers only the /out/diag.py path. The diagnostics interpreter (/replay/.../bin/python3.14) is archive content
and writable by uid 0 during the acceptance step as well; the stub uses the host python, so that path is not
exercised here.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
FORGED = (
    "import sys\n"
    "print('sha256 /usr/lib64/libc.so.6', sys.argv[1])\n"
    "print('sha256 /usr/lib64/ld-linux-x86-64.so.2', sys.argv[2])\n"
    "print('glibc: bound')\n"
    "print('network: isolated')\n"
)
# The script calls: unshare -m -p -f -n sh -c <source> <name> <rootfs> <arg> <arg>
UNSHARE = r'''name=$8; root=$9
case "$name" in
replay-acceptance)
  echo acceptance
  if [ "$REWRITE" = yes ]; then cp "$FORGED_SRC" "$root/out/diag.py"; fi
  exit 0;;
replay-diagnostics)
  exec python3 -I -B "$root/out/diag.py" "${10}" "${11}";;
esac
echo "unexpected unshare call: $name"; exit 99'''
STUBS = {
    'id': 'echo 0',
    'uname': 'if [ "$1" = -m ]; then echo x86_64; else echo Linux; fi',
    'tar': 'while [ "$1" != -C ]; do shift; done; shift; mkdir -p "$1/dev"; '
           'touch "$1/dev/null" "$1/dev/zero" "$1/dev/random" "$1/dev/urandom"',
    'unshare': UNSHARE,
}


class DiagnosticsRewrite(unittest.TestCase):
    def gate(self, rewrite):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            bins = d / 'bin'
            bins.mkdir()
            for name, body in STUBS.items():
                p = bins / name
                p.write_text('#!/bin/sh\n' + body + '\n')
                p.chmod(0o755)
            forged = d / 'forged_diag.py'
            forged.write_text(FORGED)
            blob = d / 'blob'
            blob.write_bytes(b'fixture')
            digest = hashlib.sha256(b'fixture').hexdigest()
            env = dict(os.environ, PATH=str(bins) + ':' + os.environ['PATH'], REPLAY_DISPOSABLE_VM='yes',
                       REWRITE='yes' if rewrite else 'no', FORGED_SRC=str(forged))
            r = subprocess.run(['sh', str(HERE / 'run_acceptance_in_image_rootfs.sh'), str(blob), digest, str(blob),
                                digest, '7742', 'publicsalt', str(d / 'work')],
                               env=env, text=True, capture_output=True, cwd=d)
            return r.returncode, r.stdout + r.stderr

    def test_rewritten_diagnostics_do_not_change_the_verdict(self):
        rc0, out0 = self.gate(rewrite=False)
        if rc0 == 0 or 'RECEIPT_GATE_OK' in out0:
            self.skipTest('genuine diagnostics pass on this host; the check needs a host where they fail')
        rc1, out1 = self.gate(rewrite=True)
        self.assertNotIn('RECEIPT_GATE_OK', out1, 'gate accepted diagnostics rewritten by the acceptance step')
        self.assertNotEqual(rc1, 0)


if __name__ == '__main__':
    unittest.main()
