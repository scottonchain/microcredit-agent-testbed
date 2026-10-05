"""Regression checks without executing archive code or requiring host root."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
LIBC = 'c6b12761834ea9a2fde7a17682ebfaf37982a0df6e9345e5b9d298ac1ca3c746'
LOADER = '58b211cde994b9373c9a39abeb2633191b832574c7ca0bd44e362d33e0cc6111'

class Hardening(unittest.TestCase):
    def test_same_size_cached_replacement_rejected(self):
        spec = importlib.util.spec_from_file_location('image', HERE / 'check_image_glibc.py')
        image = importlib.util.module_from_spec(spec); spec.loader.exec_module(image)
        with tempfile.TemporaryDirectory() as d:
            blob = Path(d) / 'layer.tar.gz'
            with tarfile.open(blob, 'w:gz') as t:
                for name in image.WANT_PATHS:
                    data = b'replaced libc'; info = tarfile.TarInfo(name); info.size = len(data)
                    t.addfile(info, io.BytesIO(data))
            size = blob.stat().st_size
            # Recorded digest names different, same-size bytes. Cached contents
            # contain exactly the glibc bytes requested by the reveal record.
            digest = 'sha256:' + hashlib.sha256(b'x' * size).hexdigest()
            blob.rename(Path(d) / (digest.replace(':', '_') + '.tar.gz'))
            reveal = Path(d) / 'reveal.json'
            want = hashlib.sha256(b'replaced libc').hexdigest()
            reveal.write_text(json.dumps({'glibc': {'libc_so_6_sha256': want, 'ld_linux_x86_64_so_2_sha256': want}}))
            manifest = json.dumps({'config': {'digest': 'config'}, 'layers': [{'digest': digest, 'size': size}]}).encode()
            responses = [(b'{"token":"fixture"}', {}), (manifest, {})]
            with patch.object(image, 'fetch', side_effect=responses), patch.object(sys, 'argv', ['check', str(reveal), 'almalinux:9.8', d]), contextlib.redirect_stdout(io.StringIO()) as out:
                with self.assertRaises(SystemExit) as rc: image.main()
            self.assertEqual(rc.exception.code, 1)
            self.assertIn('LAYER_DIGEST_MISMATCH', out.getvalue())
            self.assertNotIn('GLIBC_MATCH', out.getvalue())

    def diag(self, isolated=True, bound=True, ipv6=False):
        data = {
            '/proc/self/maps': '', '/usr/lib64/libc.so.6': b'libc',
            '/usr/lib64/ld-linux-x86-64.so.2': b'loader', '/etc/os-release': '', '/etc/nsswitch.conf': '',
            '/proc/net/dev': 'header\nheader\n lo: 0\n' + ('' if isolated else ' eth0: 0\n'),
            '/proc/net/route': 'header\n', '/proc/net/ipv6_route': 'route eth0\n' if ipv6 else '',
        }
        def fake_open(path, mode='r', *args, **kwargs):
            value = data[str(path)]
            return io.BytesIO(value) if 'b' in mode else io.StringIO(value)
        hashes = [hashlib.sha256(data[p]).hexdigest() for p in ('/usr/lib64/libc.so.6', '/usr/lib64/ld-linux-x86-64.so.2')]
        if not bound: hashes[0] = '0' * 64
        with patch('builtins.open', side_effect=fake_open), patch.object(sys, 'argv', ['diag', *hashes]), contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(SystemExit) as rc: runpy.run_path(str(HERE / 'rootfs_diag.py'), run_name='__main__')
        return rc.exception.code, out.getvalue()

    def test_diagnostics_accept_isolated_bound(self): self.assertEqual(self.diag()[0], 0)
    def test_diagnostics_reject_network(self): self.assertEqual(self.diag(isolated=False)[0], 1)
    def test_diagnostics_reject_glibc(self): self.assertEqual(self.diag(bound=False)[0], 1)
    def test_diagnostics_reject_ipv6_route(self): self.assertEqual(self.diag(ipv6=True)[0], 1)

    def gate(self, mode):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); bins = d / 'bin'; bins.mkdir()
            commands = {
                'id': 'echo 0', 'uname': 'if [ "$1" = -m ]; then echo x86_64; else echo Linux; fi',
                'tar': 'while [ "$1" != -C ]; do shift; done; shift; mkdir -p "$1/dev"; touch "$1/dev/null" "$1/dev/zero" "$1/dev/random" "$1/dev/urandom"',
                'unshare': '''case "$*" in
*replay-acceptance*) echo acceptance; exit 0;;
*) if [ "$MODE" = crash ]; then exit 7; fi
   [ "$MODE" = missing ] || { if [ "$MODE" = network ]; then echo 'network: NOT isolated'; else echo 'network: isolated'; fi; }
   echo 'glibc: bound'
   echo "sha256 /usr/lib64/libc.so.6 $LIBC"
   if [ "$MODE" != hash ]; then echo "sha256 /usr/lib64/ld-linux-x86-64.so.2 $LOADER"; fi;;
esac''',
            }
            for name, body in commands.items():
                p = bins / name; p.write_text('#!/bin/sh\n' + body + '\n'); p.chmod(0o755)
            blob = d / 'blob'; blob.write_bytes(b'fixture'); digest = hashlib.sha256(b'fixture').hexdigest()
            # Injection-shaped work path must remain a literal argument.
            work = d / "work ' ; touch INJECTED ; #"
            env = dict(os.environ, PATH=str(bins) + ':' + os.environ['PATH'], REPLAY_DISPOSABLE_VM='yes', MODE=mode, LIBC=LIBC, LOADER=LOADER)
            result = subprocess.run(['sh', str(HERE / 'run_acceptance_in_image_rootfs.sh'), str(blob), digest, str(blob), digest, '7742', 'publicsalt', str(work)], env=env, text=True, capture_output=True, cwd=d)
            self.assertFalse((d / 'INJECTED').exists())
            return result
    def test_gate_accepts_complete_receipt(self): self.assertEqual(self.gate('ok').returncode, 0)
    def test_gate_rejects_diag_crash(self): self.assertNotEqual(self.gate('crash').returncode, 0)
    def test_gate_rejects_nonisolated_zero_exit(self): self.assertNotEqual(self.gate('network').returncode, 0)
    def test_gate_rejects_missing_isolation(self): self.assertNotEqual(self.gate('missing').returncode, 0)
    def test_gate_rejects_missing_bound_hash(self): self.assertNotEqual(self.gate('hash').returncode, 0)
    def test_requires_disposable_vm_acknowledgment(self):
        env = dict(os.environ); env.pop('REPLAY_DISPOSABLE_VM', None)
        r = subprocess.run(['sh', str(HERE / 'run_acceptance_in_image_rootfs.sh'), *(['unused'] * 7)], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2); self.assertIn('DISPOSABLE_VM_REQUIRED', r.stdout)

if __name__ == '__main__': unittest.main()
