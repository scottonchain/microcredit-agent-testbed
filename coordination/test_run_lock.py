"""Exercise actual git receive-pack through two independent clones, without GitHub."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from run_lock import IDENTITY, Lock, LockError, REF


class GitLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        self.git('init', '--bare', str(self.remote))
        self.clients = []
        for name in ('a', 'b'):
            path = self.root / name
            self.git('clone', str(self.remote), str(path))
            self.clients.append(Lock(path))
        a = self.clients[0]
        a.git('config', 'user.name', 'Codex (AI)')
        a.git('config', 'user.email', IDENTITY)
        (Path(a.repo) / 'LOCK.json').write_text(json.dumps(dict(
            protocol='coordination-branch-cas-v1', state='unlocked', owner=None, execution=None)))
        a.git('add', 'LOCK.json')
        a.git('commit', '-m', 'Test bootstrap')
        a.git('push', 'origin', 'HEAD:' + REF)

    def git(self, *args):
        subprocess.run(['git', *args], check=True, capture_output=True)

    def test_competing_candidates_one_winner_owner_only_release(self):
        a, b = self.clients
        ca = a.prepare_acquire('test-owner-a', 'test-execution-a')
        cb = b.prepare_acquire('test-owner-b', 'test-execution-b')
        self.assertEqual(ca[0], cb[0])
        def publish(lock, candidate):
            try:
                return lock.publish(*candidate)
            except LockError:
                return None
        with ThreadPoolExecutor(2) as pool:
            fa = pool.submit(publish, a, ca)
            fb = pool.submit(publish, b, cb)
            results = [fa.result(), fb.result()]
        self.assertEqual(sum(r is not None for r in results), 1)
        head, state = a.read()
        self.assertIn(head, (ca[1], cb[1]))
        loser = 'test-owner-b' if state['owner'] == 'test-owner-a' else 'test-owner-a'
        with self.assertRaises(LockError):
            b.release(loser, head)
        self.assertEqual(a.read()[0], head)
        release = a.release(state['owner'], head)
        self.assertEqual(a.read()[0], release)
        self.assertEqual(a.read()[1]['state'], 'unlocked')
        # Stale owner/candidate cannot cross an intervening release and new acquire.
        new = b.acquire('test-owner-next', 'test-execution-next')
        with self.assertRaises(LockError):
            a.release(state['owner'], head)
        with self.assertRaises(LockError):
            a.publish(*ca)
        self.assertEqual(a.read()[0], new)

    def test_old_lock_never_expires_or_recovers_automatically(self):
        a, b = self.clients
        old, candidate = a.prepare_acquire('test-owner-old', 'test-execution-old')
        state = json.loads(a.git('show', candidate + ':LOCK.json'))
        state['acquired_at_utc'] = '2000-01-01T00:00:00'
        head = a.publish(old, a.candidate(old, state))
        with self.assertRaises(LockError):
            b.acquire('test-owner-new', 'test-execution-new')
        with self.assertRaises(LockError):
            b.release('test-owner-new', head)
        self.assertEqual(a.read()[0], head)

    def test_identity_overrides_inherited_configuration(self):
        a = self.clients[0]
        env = dict(os.environ)
        try:
            os.environ.update(GIT_AUTHOR_EMAIL='wrong@example.test', GIT_COMMITTER_EMAIL='wrong@example.test')
            head = a.acquire('test-owner-mail', 'test-execution-mail')
            self.assertEqual(a.git('show', '-s', '--format=%ae%n%ce', head).splitlines(), [IDENTITY, IDENTITY])
            released = a.release('test-owner-mail', head)
            self.assertEqual(a.git('show', '-s', '--format=%ae%n%ce', released).splitlines(), [IDENTITY, IDENTITY])
        finally:
            os.environ.clear()
            os.environ.update(env)

    def test_missing_unknown_or_inconsistent_lock_fails_closed(self):
        a = self.clients[0]
        for state in ({'protocol': 'unknown', 'state': 'unlocked'},
                      {'protocol': 'git-explicit-lease-v2', 'state': 'unlocked', 'owner': 'someone'},
                      {'protocol': 'git-explicit-lease-v2', 'state': 'locked', 'owner': 'someone'}):
            parent = a.git('ls-remote', '--refs', 'origin', REF).split()[0]
            candidate = a.candidate(parent, state)
            a.git('push', '--force-with-lease=' + REF + ':' + parent, 'origin', candidate + ':' + REF)
            with self.assertRaises(LockError):
                a.acquire('test-owner-invalid', 'test-execution-invalid')
        a.git('push', 'origin', ':' + REF)
        with self.assertRaises(LockError):
            a.acquire('test-owner-missing', 'test-execution-missing')
        with self.assertRaises(LockError):
            Lock(a.repo, ref='refs/heads/main')


if __name__ == '__main__':
    unittest.main()
