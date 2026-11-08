"""R1 (maintainer review of PR 443): both Node children are launched from a pinned absolute executable with an
explicit minimal environment. Everything is mocked at the subprocess boundary: no Node, viem, key, signer,
provider or chain is touched. The only real files are small temporary stand-ins for an executable."""
import fcntl
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from local_boundary import NodeSignatureVerifier, PinnedNode, node_environment
from submission import InheritedFDSigner


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(os.path.realpath(self.tmp.name))
        self.exe = self.dir / 'node'
        self.exe.write_bytes(b'#!/bin/sh\nexit 0\n')
        self.exe.chmod(0o755)
        self.sha = hashlib.sha256(self.exe.read_bytes()).hexdigest()

    def pinned(self):
        return PinnedNode(self.exe, self.sha)


class PinnedNodeTests(Fixture):
    def test_accepts_an_absolute_owned_executable_with_the_matching_hash(self):
        node = self.pinned()
        self.assertEqual(node.command('a.cjs', '7'), [str(self.exe), 'a.cjs', '7'])

    def test_rejects_a_relative_path(self):
        with self.assertRaises(ValueError):
            PinnedNode('node', self.sha)

    def test_rejects_a_path_with_a_symlink(self):
        link = self.dir / 'link'
        link.symlink_to(self.exe)
        with self.assertRaises(ValueError):
            PinnedNode(link, self.sha)

    def test_rejects_a_group_or_world_writable_file(self):
        for mode in (0o775, 0o757):
            self.exe.chmod(mode)
            with self.subTest(mode=oct(mode)), self.assertRaises(ValueError):
                self.pinned()

    def test_rejects_a_non_executable_and_a_non_regular_file(self):
        self.exe.chmod(0o644)
        with self.assertRaises(ValueError):
            self.pinned()
        with self.assertRaises(ValueError):
            PinnedNode(self.dir, self.sha)

    def test_rejects_a_wrong_or_malformed_pin(self):
        for bad in ('0' * 64, 'abc', None, 12):
            with self.subTest(pin=bad), self.assertRaises(ValueError):
                PinnedNode(self.exe, bad)

    def test_refuses_a_file_replaced_after_pinning(self):
        node = self.pinned()
        self.exe.write_bytes(b'#!/bin/sh\necho replaced\n')
        self.exe.chmod(0o755)
        with self.assertRaises(ValueError):
            node.command('x')

    def test_minimal_environment_inherits_nothing(self):
        with patch.dict(os.environ, {'PATH': '/evil', 'NODE_PATH': '/evil', 'NODE_OPTIONS': '--require /evil', 'LD_PRELOAD': '/evil.so', 'SECRET': 's'}):
            env = node_environment()
        self.assertEqual(env, {'NODE_NO_WARNINGS': '1'})
        env['x'] = 1
        self.assertEqual(node_environment(), {'NODE_NO_WARNINGS': '1'})  # a fresh dict each time


class VerifierLaunchTests(Fixture):
    def test_verifier_runs_the_pinned_path_with_no_inherited_environment(self):
        verifier = NodeSignatureVerifier(self.dir / 'bridge.cjs', self.pinned())
        done = subprocess.CompletedProcess([], 0, stdout='{"signatureValid": true}', stderr='')
        with patch.dict(os.environ, {'PATH': '/evil', 'NODE_PATH': '/evil', 'LD_PRELOAD': '/evil.so', 'SECRET': 's'}), \
                patch('local_boundary.subprocess.run', return_value=done) as run:
            verifier('0x02aa', {'chainId': '0x1'}, {'gas': '1'}, 5)
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], str(self.exe))
        self.assertTrue(os.path.isabs(argv[0]))
        self.assertEqual(run.call_args.kwargs['env'], {'NODE_NO_WARNINGS': '1'})

    def test_verifier_requires_a_pinned_node_object(self):
        for bad in ('node', str(self.exe), None):
            with self.subTest(node=bad), self.assertRaises(ValueError):
                NodeSignatureVerifier(self.dir / 'bridge.cjs', bad)

    def test_verifier_refuses_to_run_a_replaced_executable(self):
        verifier = NodeSignatureVerifier(self.dir / 'bridge.cjs', self.pinned())
        self.exe.write_bytes(b'#!/bin/sh\necho replaced\n')
        self.exe.chmod(0o755)
        with patch('local_boundary.subprocess.run') as run, self.assertRaises(ValueError):
            verifier('0x02aa', {}, {}, 5)
        run.assert_not_called()


def sealed_memfd(content=b'not-a-key'):
    """A sealed, immutable in-memory file (what the signer requires). The content is a placeholder, never a key."""
    fd = os.memfd_create('fixture', os.MFD_ALLOW_SEALING)
    os.write(fd, content)
    fcntl.fcntl(fd, getattr(fcntl, 'F_ADD_SEALS', 1033), 0x0f)
    return fd


@unittest.skipUnless(hasattr(os, 'memfd_create') and os.uname().sysname == 'Linux', 'SKIPPED, NOT A PASS: needs Linux memfd')
class SignerLaunchTests(Fixture):
    def setUp(self):
        super().setUp()
        self.fd = sealed_memfd()
        self.addCleanup(lambda: os.close(self.fd) if self._open(self.fd) else None)

    @staticmethod
    def _open(fd):
        try:
            os.fstat(fd)
            return True
        except OSError:
            return False

    def test_signer_runs_the_pinned_path_with_no_inherited_environment_and_only_its_descriptor(self):
        signer = InheritedFDSigner(self.fd, self.dir / 'sign-fd.cjs', self.pinned())
        done = subprocess.CompletedProcess([], 0, stdout='{"serialized": "0x02aa"}', stderr='')
        with patch.dict(os.environ, {'PATH': '/evil', 'NODE_PATH': '/evil', 'LD_PRELOAD': '/evil.so', 'SECRET': 's'}), \
                patch('subprocess.run', return_value=done) as run:
            self.assertEqual(signer({'to': '0x'}, {'gas': '1'}), '0x02aa')
        argv = run.call_args.args[0]
        self.assertEqual(argv, [str(self.exe), str(self.dir / 'sign-fd.cjs'), str(self.fd)])
        self.assertEqual(run.call_args.kwargs['env'], {'NODE_NO_WARNINGS': '1'})
        self.assertEqual(run.call_args.kwargs['pass_fds'], (self.fd,))

    def test_signer_requires_a_pinned_node_object(self):
        for bad in ('node', str(self.exe), None):
            with self.subTest(node=bad), self.assertRaises(ValueError):
                InheritedFDSigner(self.fd, self.dir / 'sign-fd.cjs', bad)

    def test_signer_refuses_to_run_a_replaced_executable(self):
        signer = InheritedFDSigner(self.fd, self.dir / 'sign-fd.cjs', self.pinned())
        self.exe.write_bytes(b'#!/bin/sh\necho replaced\n')
        self.exe.chmod(0o755)
        with patch('subprocess.run') as run, self.assertRaises(ValueError):
            signer({}, {})
        run.assert_not_called()

    def test_signer_refuses_a_descriptor_number_reused_for_another_sealed_object(self):
        signer = InheritedFDSigner(self.fd, self.dir / 'sign-fd.cjs', self.pinned())
        other = sealed_memfd(b'a-different-placeholder')
        os.dup2(other, self.fd)  # the same descriptor number now names a different (but sealed) object
        os.close(other)
        with patch('subprocess.run') as run, self.assertRaisesRegex(ValueError, 'changed since launch'):
            signer({}, {})
        run.assert_not_called()

    def test_signer_refuses_a_descriptor_number_reused_for_an_unsealed_object(self):
        signer = InheritedFDSigner(self.fd, self.dir / 'sign-fd.cjs', self.pinned())
        loose = os.memfd_create('loose', os.MFD_ALLOW_SEALING)  # writable, no seals
        os.dup2(loose, self.fd)
        os.close(loose)
        with patch('subprocess.run') as run, self.assertRaises(ValueError):
            signer({}, {})
        run.assert_not_called()

    def test_signer_refuses_a_closed_descriptor(self):
        signer = InheritedFDSigner(self.fd, self.dir / 'sign-fd.cjs', self.pinned())
        os.close(self.fd)
        with patch('subprocess.run') as run, self.assertRaises(OSError):
            signer({}, {})
        run.assert_not_called()

    def test_the_constructor_still_refuses_unsealed_and_invalid_descriptors(self):
        loose = os.memfd_create('loose', os.MFD_ALLOW_SEALING)
        self.addCleanup(os.close, loose)
        for bad in (loose, 2, -1, '5', None):
            with self.subTest(fd=bad), self.assertRaises((ValueError, OSError)):
                InheritedFDSigner(bad, self.dir / 'sign-fd.cjs', self.pinned())


if __name__ == '__main__':
    unittest.main()
