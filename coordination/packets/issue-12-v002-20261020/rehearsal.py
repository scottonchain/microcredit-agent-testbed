#!/usr/bin/env python3
"""Offline rehearsal of the proposed invocation. Usage: rehearsal.py CHECKOUT BASELINE CANDIDATE VERIFY_CMD_JSON.
Everything is local: a loopback HTTP stand-in for the comment, a throwaway bare git remote that receives a copy of main and of
the lock ref, and a throwaway clone of it. It never touches GitHub, the real lock ref or any token. The stand-in reuses the
fixture classes of coordination/test_issue12_canonical_write.py."""
import hashlib, http.server, json, os, subprocess, sys, tempfile, threading
from pathlib import Path

checkout, baseline, candidate, verify_json = [Path(a).resolve() for a in sys.argv[1:5]]
sys.path.insert(0, str(checkout))
from coordination import test_issue12_canonical_write as t

NOREPLY = {'GIT_AUTHOR_NAME': 'Claude', 'GIT_AUTHOR_EMAIL': 'noreply@anthropic.com',
           'GIT_COMMITTER_NAME': 'Claude', 'GIT_COMMITTER_EMAIL': 'noreply@anthropic.com'}
base_text = baseline.read_bytes().decode('utf-8')
cand_bytes = candidate.read_bytes()
STAMP = '2026-10-19T22:03:30Z'
sha = lambda b: hashlib.sha256(b).hexdigest()
verify = verify_json.read_text()
helper = sha((checkout / 'coordination' / 'run_lock.py').read_bytes())


def sh(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=dict(os.environ, **(env or {})))


def scenario(name, mutate=None, patch_mode='ok', release_first=False, dry=False, extra=None, run_twice=None, optimize=False,
             bad_candidate_hash=False, pre_state=None):
    with tempfile.TemporaryDirectory(prefix='rehearsal-') as tmp:
        tmp = Path(tmp)
        remote, work = tmp / 'remote.git', tmp / 'work'
        sh('git', 'init', '--bare', '-q', str(remote))
        r = sh('git', '-C', str(checkout), 'push', '-q', str(remote), 'HEAD:refs/heads/main',
               'refs/remotes/origin/coordination/issue-12-run-lock:refs/heads/coordination/issue-12-run-lock')
        assert r.returncode == 0, r.stderr
        r = sh('git', 'clone', '-q', '-b', 'main', str(remote), str(work), env=NOREPLY)
        assert r.returncode == 0, r.stderr
        state = t.Comment(body=base_text, stamp=STAMP)
        if pre_state:
            pre_state(state)
        state.patch_mode = patch_mode
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), t.make_handler(state))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:%d' % server.server_address[1]
        lock = lambda *a: sh(sys.executable, str(work / 'coordination' / 'run_lock.py'), '--repo', str(work), *a, env=NOREPLY)
        acq = lock('acquire', '--owner', 'rehearsal-owner-1', '--execution', 'rehearsal-exec-1')
        head = json.loads(acq.stdout)['acquired_head']
        if release_first:
            assert lock('release', '--owner', 'rehearsal-owner-1', '--acquired-head', head).returncode == 0

        def run(extra_args=()):
            argv = [sys.executable] + (['-O'] if optimize else []) + [str(work / 'coordination' / 'issue12_canonical_write.py'),
                    '--candidate', str(candidate), '--candidate-sha256', ('0' * 64 if bad_candidate_hash else sha(cand_bytes)),
                    '--expected-body-sha256', sha(base_text.encode('utf-8')), '--expected-updated-at', STAMP,
                    '--owner', 'rehearsal-owner-1', '--acquired-head', head, '--repo', str(work), '--api-base', base,
                    '--verify-cmd', verify, '--lock-helper-sha256', helper] + list(extra_args)
            env = dict(os.environ, GITHUB_TOKEN=t.TOKEN)
            env.pop('PYTHONOPTIMIZE', None)
            done = subprocess.run(argv, capture_output=True, text=True, env=env, cwd=str(work))
            try:
                rep = json.loads(done.stdout) if done.stdout.strip() else None
            except ValueError:
                rep = None
            return done.returncode, rep

        if mutate:
            mutate(state)
        results = []
        code, rep = run(['--dry-run'] if dry else [])
        results.append({'exit': code, 'outcome': rep and rep.get('outcome'), 'reason': rep and rep.get('reason'),
                        'comment': rep and rep.get('comment'), 'semantic_verified': rep and rep.get('semantic_verified')})
        for step in (run_twice or []):
            if step == 'release':
                assert lock('release', '--owner', 'rehearsal-owner-1', '--acquired-head', head).returncode == 0
                results.append({'step': 'released lease'})
                continue
            code, rep = run(step)
            results.append({'extra_args': [os.path.basename(a) for a in step], 'exit': code, 'outcome': rep and rep.get('outcome'),
                            'reason': rep and rep.get('reason'), 'comment': rep and rep.get('comment'),
                            'semantic_verified': rep and rep.get('semantic_verified')})
        final = state.body.encode('utf-8')
        out = {'scenario': name, 'runs': results, 'gets': state.gets, 'patches': state.patches,
               'final_equals_baseline': final == base_text.encode('utf-8'), 'final_equals_candidate': final == cand_bytes}
        server.shutdown()
        return out


report = [
    scenario('dry run', dry=True),
    scenario('apply, rerun without baseline, rerun with baseline, release, rerun', run_twice=[[], ['--baseline', str(baseline)], 'release', ['--baseline', str(baseline)]]),
    scenario('stale baseline (one byte appended to the live body)', pre_state=lambda s: setattr(s, 'body', s.body + ' ')),
    scenario('lease released before the run', release_first=True),
    scenario('PATCH acknowledged but not stored', patch_mode='ignore'),
    scenario('PATCH stored but reported failed', patch_mode='apply_then_fail'),
    scenario('wrong candidate hash', bad_candidate_hash=True),
    scenario('optimized interpreter (-O)', optimize=True),
]
print(json.dumps(report, indent=2))
