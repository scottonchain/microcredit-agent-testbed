#!/usr/bin/env python3
"""Cooperative Git-shell mutex. Never substitutes for connector CAS verification."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

REF = 'refs/heads/coordination/issue-12-run-lock'
PROTOCOL = 'git-explicit-lease-v2'
IDENTITY = '5783027+scottonchain@users.noreply.github.com'


class LockError(RuntimeError):
    pass


class Lock:
    def __init__(self, repo='.', remote='origin', ref=REF):
        if ref != REF and not re.fullmatch(r'refs/heads/coordination/lock-verification-[a-z0-9-]+', ref):
            raise LockError('Only the coordination lock or a dedicated verification ref is allowed')
        self.repo, self.remote, self.ref = str(repo), remote, ref

    def git(self, *args, input=None, env=None):
        p = subprocess.run(['git', '-C', self.repo, *args], input=input, text=True,
                           capture_output=True, env=env)
        if p.returncode:
            # Do not echo URLs, credentials, paths or remote error text into receipts.
            raise LockError('Git operation failed: ' + args[0])
        return p.stdout.strip()

    def read(self):
        lines = self.git('ls-remote', '--refs', self.remote, self.ref).splitlines()
        if len(lines) != 1 or lines[0].split()[1] != self.ref:
            raise LockError('Lock ref missing or ambiguous; do not bootstrap automatically')
        sha = lines[0].split()[0]
        self.git('fetch', '--no-tags', '--no-write-fetch-head', self.remote, sha)
        try:
            state = json.loads(self.git('show', sha + ':LOCK.json'))
        except (ValueError, TypeError) as exc:
            raise LockError('Malformed lock; stop for manual inspection') from exc
        if not isinstance(state, dict) or state.get('protocol') not in ('coordination-branch-cas-v1', PROTOCOL):
            raise LockError('Unknown lock protocol')
        if state.get('state') == 'unlocked':
            if state.get('owner') is not None or state.get('execution') is not None:
                raise LockError('Inconsistent unlocked state')
        elif state.get('state') == 'locked':
            if not state.get('owner') or not state.get('execution'):
                raise LockError('Inconsistent locked state')
        else:
            raise LockError('Unknown lock state')
        return sha, state

    @staticmethod
    def token(value):
        # Use randomly generated public tokens, never a private scheduler/session id.
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{7,79}', value):
            raise LockError('Use an opaque lowercase public run token (8-80 characters)')
        return value

    def candidate(self, parent, state):
        env = dict(os.environ, GIT_AUTHOR_NAME='Codex (AI)', GIT_COMMITTER_NAME='Codex (AI)',
                   GIT_AUTHOR_EMAIL=IDENTITY, GIT_COMMITTER_EMAIL=IDENTITY)
        with tempfile.TemporaryDirectory(prefix='coordination-index-') as d:
            env['GIT_INDEX_FILE'] = str(Path(d) / 'index')
            self.git('read-tree', parent, env=env)
            blob = self.git('hash-object', '-w', '--stdin', input=json.dumps(state, indent=2) + '\n', env=env)
            self.git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',LOCK.json', env=env)
            tree = self.git('write-tree', env=env)
            sha = self.git('commit-tree', tree, '-p', parent,
                           input='Codex coordination lock: ' + state['state'] + '\n', env=env)
        if self.git('show', '-s', '--format=%ae%n%ce', sha).splitlines() != [IDENTITY, IDENTITY]:
            raise LockError('Noreply author and committer check failed')
        return sha

    def publish(self, expected, candidate):
        # Explicit expected OID; never an implicit tracking-ref lease or --force.
        if self.git('show', '-s', '--format=%P', candidate) != expected:
            raise LockError('Candidate must be a direct child of the observed head')
        self.git('push', '--porcelain', '--force-with-lease=' + self.ref + ':' + expected,
                 self.remote, candidate + ':' + self.ref)
        actual, _ = self.read()
        if actual != candidate:
            raise LockError('Unexpected readback; stop all protected work')
        return candidate

    def prepare_acquire(self, owner, execution):
        self.token(owner)
        self.token(execution)
        head, state = self.read()
        if state['state'] != 'unlocked':
            raise LockError('Lock held; age never authorizes takeover')
        state = dict(protocol=PROTOCOL, state='locked', owner=owner, execution=execution,
                     acquired_at_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),
                     released_by=None)
        return head, self.candidate(head, state)

    def acquire(self, owner, execution):
        return self.publish(*self.prepare_acquire(owner, execution))

    def assert_owned(self, owner, acquired_head):
        self.token(owner)
        head, state = self.read()
        if head != acquired_head or state['state'] != 'locked' or state['owner'] != owner:
            raise LockError('Exact acquisition head and owner required')
        return head, state

    def release(self, owner, acquired_head):
        head, _ = self.assert_owned(owner, acquired_head)
        state = dict(protocol=PROTOCOL, state='unlocked', owner=None, execution=None,
                     released_by=owner,
                     released_at_utc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'))
        return self.publish(head, self.candidate(head, state))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', default='.')
    p.add_argument('--remote', default='origin')
    p.add_argument('--ref', default=REF)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('status')
    acquire = sub.add_parser('acquire')
    acquire.add_argument('--owner', required=True)
    acquire.add_argument('--execution', required=True)
    for name in ('assert-owned', 'release'):
        command = sub.add_parser(name)
        command.add_argument('--owner', required=True)
        command.add_argument('--acquired-head', required=True)
    args = p.parse_args()
    lock = Lock(args.repo, args.remote, args.ref)
    try:
        if args.action == 'status':
            head, state = lock.read()
            print(json.dumps(dict(head=head, lock=state)))
        elif args.action == 'acquire':
            head = lock.acquire(args.owner, args.execution)
            print(json.dumps(dict(owner=args.owner, acquired_head=head)))
        elif args.action == 'assert-owned':
            head, _ = lock.assert_owned(args.owner, args.acquired_head)
            print(json.dumps(dict(owner=args.owner, acquired_head=head)))
        else:
            print(json.dumps(dict(released_head=lock.release(args.owner, args.acquired_head))))
    except LockError as exc:
        p.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
