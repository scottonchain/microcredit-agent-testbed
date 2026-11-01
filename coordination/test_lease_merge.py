"""Failure-path tests for lease_merge.sh, run against scratch origins. No network, no real remote.

Each test builds a bare scratch origin with a minimal repository (the run lock, the execution-owner
toggle and stub checkers), a pull-request ref and a clone, then runs the real wrapper against it.
"""
import http.server
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "lease_merge.sh"
LOCK_REF = "refs/heads/coordination/issue-12-run-lock"
OWNER = "claude-0123456789abcdef"
EXECUTION = "merge7-0123456789abcdef"
IDENT = {"GIT_AUTHOR_NAME": "Scratch", "GIT_AUTHOR_EMAIL": "scratch@example.invalid",
         "GIT_COMMITTER_NAME": "Scratch", "GIT_COMMITTER_EMAIL": "scratch@example.invalid"}

CHECK_STUB = '''import os, subprocess, sys, time
action = os.environ.get("CHECK_ACTION", "ok")
if os.environ.get("CHECK_MARKER"):
    open(os.environ["CHECK_MARKER"], "w").write("started")
if action == "advance":      # main moves after the lease was taken
    other = os.environ["OTHER_CLONE"]
    subprocess.run(["git", "-C", other, "pull", "-q", "origin", "main"], check=True)
    subprocess.run(["git", "-C", other, "commit", "-q", "--allow-empty", "-m", "racing commit"], check=True)
    subprocess.run(["git", "-C", other, "push", "-q", "origin", "HEAD:main"], check=True)
elif action == "steal":      # someone else takes the lease while the checks run
    sys.path.insert(0, "coordination")
    from run_lock import Lock, PROTOCOL
    lock = Lock(".")
    head, _ = lock.read()
    state = dict(protocol=PROTOCOL, state="locked", owner="other-owner-0001", execution="other-exec-0001",
                 acquired_at_utc="2026-11-01T00:00:00", released_by=None)
    lock.publish(head, lock.candidate(head, state))
elif action == "sleep":
    time.sleep(60)
elif action == "fail":
    sys.exit(1)
print("stub: 1 check passed")
'''

RACE_SHIM = '''import json, os, runpy, subprocess, sys
if "acquire" in sys.argv and os.environ.get("RACE_ACTION") == "owner_switch":
    other = os.environ["OTHER_CLONE"]
    subprocess.run(["git", "-C", other, "pull", "-q", "origin", "main"], check=True)
    path = other + "/coordination/execution-owner.json"
    cfg = json.load(open(path))
    cfg["owner"] = "openai"
    cfg["override"]["owner"] = "openai"
    json.dump(cfg, open(path, "w"), indent=2)
    subprocess.run(["git", "-C", other, "add", "-A"], check=True)
    subprocess.run(["git", "-C", other, "commit", "-q", "-m", "owner switch lands before acquisition"], check=True)
    subprocess.run(["git", "-C", other, "push", "-q", "origin", "HEAD:main"], check=True)
runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_lock_real.py"), run_name="__main__")
'''

PUBLIC_CONTENT_STUB = '''#!/usr/bin/env bash
case "$1" in
  --message) if grep -q FORBIDDEN "$2"; then echo "forbidden content" >&2; exit 1; fi;;
  --range) if git log --format=%B "$2" | grep -q FORBIDDEN; then exit 1; fi;;
esac
exit 0
'''


TOKEN_VARIABLES = ("GH_TOKEN", "GITHUB_TOKEN")
# The wrapper's own inputs. When the wrapper merges a pull request it runs tools/check.py, which runs this file, so
# the caller's values for these variables are in this process's environment. They must never reach the scratch runs
# below: a stray MAIN_EXPECT or TOGGLE_BOOTSTRAP_PR turns every scratch merge into a refusal about the real repository.
WRAPPER_INPUTS = ("CLONE", "RUNNER_LANE", "PUBLIC_CONTENT_CHECK", "PYLIB", "GITHUB_API", "GITHUB_REPO", "NO_API",
                  "MAIN_EXPECT", "TOGGLE_BOOTSTRAP_PR")
GIT_REPOSITORY_VARIABLES = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR")


def clean_environment():
    """The caller's environment without any GitHub credential, wrapper input or repository-selecting git variable."""
    drop = TOKEN_VARIABLES + WRAPPER_INPUTS + GIT_REPOSITORY_VARIABLES
    return {key: value for key, value in os.environ.items() if key not in drop}


def run(cmd, cwd=None, env=None, check=True):
    merged = dict(clean_environment(), **IDENT)
    if env:
        merged.update(env)
    result = subprocess.run(cmd, cwd=cwd, env=merged, capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError("%s failed: %s" % (cmd, result.stderr))
    return result


def git(cwd, *args, **kwargs):
    return run(["git", "-C", str(cwd), *args], **kwargs).stdout.strip()


class Scratch:
    """A scratch origin, a clone the wrapper works in, and a second clone for racing pushes."""

    def __init__(self, toggle_on_main=True):
        self.tmp = Path(tempfile.mkdtemp(prefix="lease-merge-test-"))
        self.origin = self.tmp / "origin.git"
        run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)])
        seed = self.tmp / "seed"
        run(["git", "init", "-q", "-b", "main", str(seed)])
        toggle_files = (("coordination/execution_owner.py", (HERE / "execution_owner.py").read_text()),
                        ("coordination/execution-owner.json", (HERE / "execution-owner.json").read_text()))
        for relative, content in (("coordination/run_lock.py", (HERE / "run_lock.py").read_text()),
                                  *(toggle_files if toggle_on_main else ()),
                                  ("tools/check.py", CHECK_STUB),
                                  ("scripts/check-public-content.sh", PUBLIC_CONTENT_STUB),
                                  ("README.md", "scratch\n")):
            path = seed / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "seed")
        git(seed, "remote", "add", "origin", str(self.origin))
        git(seed, "push", "-q", "origin", "main")
        lock = self.tmp / "lockseed"
        run(["git", "init", "-q", "-b", "lock", str(lock)])
        (lock / "LOCK.json").write_text(json.dumps({
            "protocol": "git-explicit-lease-v2", "state": "unlocked", "owner": None, "execution": None,
            "released_by": "seed", "released_at_utc": "2026-11-01T00:00:00"}, indent=2) + "\n")
        git(lock, "add", "-A")
        git(lock, "commit", "-q", "-m", "lock")
        git(lock, "push", "-q", str(self.origin), "lock:" + LOCK_REF)
        git(seed, "checkout", "-q", "-b", "pr")
        (seed / "feature.txt").write_text("the reviewed change\n")
        if not toggle_on_main:  # the reviewed pull request is the one that adds the toggle
            for relative, content in toggle_files:
                (seed / relative).write_text(content)
        git(seed, "add", "-A")
        git(seed, "commit", "-q", "-m", "the reviewed change")
        self.head = git(seed, "rev-parse", "HEAD")
        git(seed, "push", "-q", "origin", "HEAD:refs/pull/7/head")
        self.seed = seed
        self.clone = self.tmp / "clone"
        run(["git", "clone", "-q", str(self.origin), str(self.clone)])
        self.other = self.tmp / "other"
        run(["git", "clone", "-q", str(self.origin), str(self.other)])
        git(self.other, "config", "user.name", "Other")
        git(self.other, "config", "user.email", "other@example.invalid")
        self.message = self.tmp / "message.txt"
        self.message.write_text("Merge the reviewed change\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n")

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def main_head(self):
        return git(self.origin, "rev-parse", "refs/heads/main")

    def lock_state(self):
        return json.loads(git(self.origin, "show", LOCK_REF + ":LOCK.json"))

    def push_main_change(self, remove=None, add=None):
        """Change main through the `other` clone (before the wrapper runs)."""
        git(self.other, "pull", "-q", "origin", "main")
        if remove:
            git(self.other, "rm", "-q", remove)
        if add:
            (self.other / add[0]).write_text(add[1])
            git(self.other, "add", add[0])
        git(self.other, "commit", "-q", "-m", "change main")
        git(self.other, "push", "-q", "origin", "HEAD:main")

    def install_race_shim(self):
        """Make the clone's run_lock.py land an owner switch on main just before it acquires the lease."""
        directory = self.clone / "coordination"
        shutil.copyfile(directory / "run_lock.py", directory / "run_lock_real.py")
        (directory / "run_lock.py").write_text(RACE_SHIM)

    def command(self, head=None):
        return ["bash", str(SCRIPT), "7", head or self.head, str(self.message), OWNER, EXECUTION]

    def environment(self, **extra):
        env = {"CLONE": str(self.clone), "NO_API": "1", "CHECK_MARKER": str(self.tmp / "checker-started"),
               "PUBLIC_CONTENT_CHECK": str(self.clone / "scripts" / "check-public-content.sh"),
               "OTHER_CLONE": str(self.other)}
        env.update(extra)
        return env

    def run(self, head=None, **extra):
        return run(self.command(head), env=self.environment(**extra), check=False)


class LeaseMergeTests(unittest.TestCase):
    def setUp(self):
        self.s = Scratch()
        self.addCleanup(self.s.close)

    def assertNothingPushedAndLeaseFree(self, before):
        self.assertEqual(self.s.main_head(), before)
        self.assertEqual(self.s.lock_state()["state"], "unlocked")

    def test_a_clean_merge_is_pushed_read_back_and_the_lease_released(self):
        before = self.s.main_head()
        result = self.s.run()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        merged = self.s.main_head()
        self.assertNotEqual(merged, before)
        self.assertEqual(git(self.s.origin, "rev-parse", merged + "^1"), before)
        self.assertEqual(git(self.s.origin, "rev-parse", merged + "^2"), self.s.head)
        self.assertEqual(git(self.s.origin, "log", "-1", "--format=%ae|%ce", merged),
                         "noreply@anthropic.com|noreply@anthropic.com")
        self.assertIn("PUSHED and read back", result.stdout)
        self.assertIn("RECEIPT pr=7", result.stdout)
        self.assertIn("runner is the execution owner", result.stdout)
        state = self.s.lock_state()
        self.assertEqual((state["state"], state["released_by"]), ("unlocked", OWNER))

    def test_the_lane_that_does_not_own_heavy_work_is_refused_before_the_lease(self):
        before = self.s.main_head()
        result = self.s.run(RUNNER_LANE="openai")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not allow openai to run heavy work", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)
        self.assertEqual(self.s.lock_state()["released_by"], "seed")  # the lease was never taken

    def test_the_pull_request_that_adds_the_toggle_merges_through_the_bootstrap_path(self):
        s = Scratch(toggle_on_main=False)
        self.addCleanup(s.close)
        before = s.main_head()
        result = s.run(TOGGLE_BOOTSTRAP_PR="7")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("BOOTSTRAP: main has no execution-owner configuration", result.stdout)
        merged = s.main_head()
        self.assertNotEqual(merged, before)
        tree = git(s.origin, "ls-tree", "-r", "--name-only", merged)
        self.assertIn("coordination/execution-owner.json", tree)
        self.assertEqual(s.lock_state()["released_by"], OWNER)

    def test_without_the_bootstrap_variable_a_main_with_no_toggle_fails_closed(self):
        s = Scratch(toggle_on_main=False)
        self.addCleanup(s.close)
        before = s.main_head()
        result = s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no execution-owner library on main", result.stderr)
        self.assertEqual(s.main_head(), before)
        self.assertEqual(s.lock_state()["released_by"], "seed")

    def test_the_bootstrap_is_refused_once_main_has_a_toggle(self):
        before = self.s.main_head()
        result = self.s.run(TOGGLE_BOOTSTRAP_PR="7")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bootstrap refused: main already has an execution-owner", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)
        self.assertEqual(self.s.lock_state()["released_by"], "seed")

    def test_the_bootstrap_for_another_pull_request_number_is_refused(self):
        s = Scratch(toggle_on_main=False)
        self.addCleanup(s.close)
        before = s.main_head()
        result = s.run(TOGGLE_BOOTSTRAP_PR="8")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TOGGLE_BOOTSTRAP_PR is 8 but this run merges PR 7", result.stderr)
        self.assertEqual(s.main_head(), before)

    def test_the_bootstrap_still_enforces_the_owner_lane_from_the_reviewed_head(self):
        s = Scratch(toggle_on_main=False)
        self.addCleanup(s.close)
        before = s.main_head()
        result = s.run(TOGGLE_BOOTSTRAP_PR="7", RUNNER_LANE="openai")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not allow openai to run heavy work", result.stderr)
        self.assertEqual(s.main_head(), before)
        self.assertEqual(s.lock_state()["released_by"], "seed")

    def test_a_missing_toggle_configuration_fails_closed(self):
        self.s.push_main_change(remove="coordination/execution-owner.json")
        before = self.s.main_head()
        result = self.s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no execution-owner configuration on main", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)

    def test_a_switch_in_progress_blocks_the_merge(self):
        path = self.s.other / "coordination" / "execution-owner.json"
        git(self.s.other, "pull", "-q", "origin", "main")
        cfg = json.loads(path.read_text())
        cfg["transition"].update(state="draining", **{"from": "claude", "to": "openai", "requested_by": "claude",
                                                       "requested_at_utc": "2026-11-01T18:00:00Z",
                                                       "reason": "r", "drain_deadline_utc": "2026-11-01T19:00:00Z",
                                                       "requested_config_version": 3})
        cfg["config_version"] = 3
        path.write_text(json.dumps(cfg, indent=2) + "\n")
        git(self.s.other, "add", "-A")
        git(self.s.other, "commit", "-q", "-m", "switch in progress")
        git(self.s.other, "push", "-q", "origin", "HEAD:main")
        before = self.s.main_head()
        result = self.s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("switch to openai is in progress", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)

    def test_main_moving_after_the_lease_pushes_nothing_and_releases_the_lease(self):
        result = self.s.run(CHECK_ACTION="advance")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("after the lease; nothing pushed", result.stderr)
        self.assertEqual(git(self.s.origin, "log", "-1", "--format=%s", "refs/heads/main"), "racing commit")
        self.assertNotIn("feature.txt", git(self.s.origin, "ls-tree", "-r", "--name-only", "refs/heads/main"))
        self.assertEqual(self.s.lock_state()["state"], "unlocked")

    def test_the_checker_marker_proves_a_normal_run_starts_the_checker(self):
        result = self.s.run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.s.tmp / "checker-started").exists())

    def test_an_owner_switch_landing_before_the_lease_stops_the_run_before_any_check(self):
        self.s.install_race_shim()
        before = self.s.main_head()
        result = self.s.run(RACE_ACTION="owner_switch")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("between the execution-owner check and the lease", result.stderr)
        self.assertFalse((self.s.tmp / "checker-started").exists(), "the checker must never start on a stale gate")
        self.assertNotEqual(self.s.main_head(), before)  # the switch did land
        self.assertNotIn("feature.txt", git(self.s.origin, "ls-tree", "-r", "--name-only", "refs/heads/main"))
        state = self.s.lock_state()
        self.assertEqual((state["state"], state["released_by"]), ("unlocked", OWNER))

    def test_a_lost_lease_pushes_nothing_and_never_releases_another_owners_lease(self):
        before = self.s.main_head()
        result = self.s.run(CHECK_ACTION="steal")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lease no longer owned", result.stderr)
        self.assertIn("LEASE RELEASE REFUSED", result.stderr)
        self.assertEqual(self.s.main_head(), before)
        state = self.s.lock_state()
        self.assertEqual((state["state"], state["owner"]), ("locked", "other-owner-0001"))

    def test_a_refused_push_is_a_failure_and_the_lease_is_released(self):
        hook = self.s.origin / "hooks" / "pre-receive"
        hook.write_text('#!/bin/sh\nwhile read old new ref; do\n  [ "$ref" = refs/heads/main ] && exit 1\ndone\nexit 0\n')
        hook.chmod(0o755)
        before = self.s.main_head()
        result = self.s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("push refused", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)

    def test_a_readback_that_differs_is_a_failure_and_the_lease_is_released(self):
        shim = self.s.tmp / "shim"
        shim.mkdir()
        real = shutil.which("git")
        (shim / "git").write_text('#!/bin/bash\nif [ "$*" = "ls-remote origin refs/heads/main" ]; then\n'
                                  '  printf "%s\\trefs/heads/main\\n" "$FAKE_READBACK"; exit 0\nfi\n'
                                  'exec ' + real + ' "$@"\n')
        (shim / "git").chmod(0o755)
        result = self.s.run(PATH=str(shim) + os.pathsep + os.environ["PATH"], FAKE_READBACK="d" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("readback is " + "d" * 40, result.stderr)
        self.assertEqual(self.s.lock_state()["state"], "unlocked")

    def test_a_missing_required_checker_fails_closed_instead_of_being_skipped(self):
        self.s.push_main_change(remove="tools/check.py")
        before = self.s.main_head()
        result = self.s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tools/check.py is required", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)

    def test_a_failing_checker_stops_the_merge(self):
        before = self.s.main_head()
        result = self.s.run(CHECK_ACTION="fail")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CHECK FAILED: tools/check.py", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)

    def test_a_missing_public_content_checker_stops_the_run_before_the_lease(self):
        before = self.s.main_head()
        result = self.s.run(PUBLIC_CONTENT_CHECK=str(self.s.tmp / "absent.sh"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public-content checker is required", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)
        self.assertEqual(self.s.lock_state()["released_by"], "seed")

    def test_forbidden_content_in_the_message_stops_the_run_before_the_lease(self):
        self.s.message.write_text("Merge FORBIDDEN text\n")
        before = self.s.main_head()
        result = self.s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public content in the merge message", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)
        self.assertEqual(self.s.lock_state()["released_by"], "seed")

    def test_a_head_that_is_not_the_reviewed_one_is_refused(self):
        before = self.s.main_head()
        result = self.s.run(head="a" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not the reviewed", result.stderr)
        self.assertNothingPushedAndLeaseFree(before)

    def test_a_held_lease_is_never_taken_over(self):
        sys_path = str(HERE)
        import sys
        sys.path.insert(0, sys_path)
        from run_lock import Lock
        lock = Lock(str(self.s.clone))
        lock.acquire("someone-else-0001", "their-run-0001")
        before = self.s.main_head()
        result = self.s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lease acquisition refused", result.stderr)
        self.assertEqual(self.s.main_head(), before)
        self.assertEqual(self.s.lock_state()["owner"], "someone-else-0001")

    def test_no_api_is_refused_for_a_remote_origin(self):
        git(self.s.clone, "remote", "set-url", "origin", "https://github.com/example/example.git")
        result = self.s.run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("NO_API=1 is accepted only for a local scratch origin", result.stderr)

    def test_a_signal_during_the_checks_releases_the_lease(self):
        before = self.s.main_head()
        process = subprocess.Popen(self.s.command(), env=dict(clean_environment(), **IDENT, **self.s.environment(CHECK_ACTION="sleep")),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            deadline = time.time() + 30
            while time.time() < deadline:
                if self.s.lock_state()["state"] == "locked":
                    break
                time.sleep(0.1)
            self.assertEqual(self.s.lock_state()["state"], "locked")
            time.sleep(1.0)  # let the wrapper reach the long check
            os.kill(process.pid, signal.SIGTERM)
            process.communicate(timeout=30)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
        self.assertIn(process.returncode, (143, -signal.SIGTERM))
        self.assertNothingPushedAndLeaseFree(before)
        self.assertEqual(self.s.lock_state()["released_by"], OWNER)


class PullRequestStateTests(unittest.TestCase):
    """The pull-request check against a local stand-in for the GitHub API."""

    def setUp(self):
        self.s = Scratch()
        self.addCleanup(self.s.close)
        self.reply = {"code": 200, "body": {"state": "open", "draft": False, "merged": False}}
        self.seen = []
        reply, seen = self.reply, self.seen

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append(dict(self.headers.items()))
                payload = json.dumps(reply["body"]).encode()
                self.send_response(reply["code"])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.api = "http://127.0.0.1:%d" % self.server.server_address[1]

    def attempt(self):
        env = self.s.environment(GITHUB_API=self.api, GITHUB_REPO="scratch/test")
        env.pop("NO_API")
        return run(self.s.command(), env=dict(env, NO_API=""), check=False)

    def test_an_open_non_draft_pull_request_proceeds(self):
        result = self.attempt()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_draft_merged_closed_or_unreadable_pull_request_is_refused_before_the_lease(self):
        cases = {
            "draft": (200, {"state": "open", "draft": True, "merged": False}),
            "merged": (200, {"state": "closed", "draft": False, "merged": True}),
            "closed": (200, {"state": "closed", "draft": False, "merged": False}),
            "missing draft flag": (200, {"state": "open", "merged": False}),
            "not found": (404, {"message": "Not Found"}),
            "server error": (500, {"message": "boom"}),
        }
        before = self.s.main_head()
        for name, (code, body) in cases.items():
            self.reply["code"], self.reply["body"] = code, body
            result = self.attempt()
            self.assertNotEqual(result.returncode, 0, name)
            self.assertIn("not an open, non-draft, unmerged pull request", result.stderr, name)
            self.assertEqual(self.s.main_head(), before, name)
            self.assertEqual(self.s.lock_state()["released_by"], "seed", name)  # lease never taken

    def test_a_credential_in_the_environment_never_reaches_a_test_endpoint(self):
        sentinel = "sentinel-token-must-not-leak-0123456789"
        env = self.s.environment(GITHUB_API=self.api, GITHUB_REPO="scratch/test", NO_API="", GH_TOKEN=sentinel,
                                 GITHUB_TOKEN=sentinel)
        result = run(self.s.command(), env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.seen, "the stand-in API was never asked")
        for headers in self.seen:
            self.assertNotIn("Authorization", headers)
            self.assertNotIn(sentinel, " ".join(headers.values()))

    def test_an_unreachable_api_is_refused(self):
        self.server.shutdown()
        self.server.server_close()
        result = self.attempt()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not an open, non-draft, unmerged pull request", result.stderr)
        self.assertEqual(self.s.lock_state()["released_by"], "seed")


class PullRequestHelperTests(unittest.TestCase):
    """pr_state_check.py: where a credential may go, and that redirects are never followed."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("pr_state_check", HERE / "pr_state_check.py")
        self.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.helper)

    def test_the_credential_goes_only_to_the_approved_origin(self):
        headers = self.helper.request_headers("https://api.github.com", "tok")
        self.assertEqual(headers["Authorization"], "Bearer tok")
        self.assertEqual(self.helper.request_headers("https://api.github.com/", "tok")["Authorization"], "Bearer tok")
        for base in ("http://api.github.com", "https://api.github.com.evil.example", "http://127.0.0.1:9",
                     "https://example.test", "https://api.github.com:8443"):
            self.assertNotIn("Authorization", self.helper.request_headers(base, "tok"), base)
        self.assertNotIn("Authorization", self.helper.request_headers("https://api.github.com", None))

    def test_a_redirect_is_not_followed_and_nothing_is_forwarded(self):
        received = []

        class Target(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(dict(self.headers.items()))
                payload = json.dumps({"state": "open", "draft": False, "merged": False}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        target = http.server.HTTPServer(("127.0.0.1", 0), Target)
        threading.Thread(target=target.serve_forever, daemon=True).start()
        self.addCleanup(target.server_close)
        self.addCleanup(target.shutdown)
        where = "http://127.0.0.1:%d/elsewhere" % target.server_address[1]

        class Redirector(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", where)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        origin = http.server.HTTPServer(("127.0.0.1", 0), Redirector)
        threading.Thread(target=origin.serve_forever, daemon=True).start()
        self.addCleanup(origin.server_close)
        self.addCleanup(origin.shutdown)
        base = "http://127.0.0.1:%d" % origin.server_address[1]
        self.assertFalse(self.helper.pull_request_is_mergeable(base, "scratch/test", 7, token="sentinel-token"))
        self.assertEqual(received, [], "the redirect target must never be contacted")

    def test_wrong_usage_exits_2(self):
        self.assertEqual(self.helper.main(["7", "8"]), 2)


class HermeticEnvironmentTests(unittest.TestCase):
    def test_the_callers_wrapper_inputs_do_not_reach_scratch_runs(self):
        polluted = {"MAIN_EXPECT": "0" * 40, "TOGGLE_BOOTSTRAP_PR": "398", "CLONE": "/nonexistent", "RUNNER_LANE": "openai",
                    "PUBLIC_CONTENT_CHECK": "/nonexistent", "GIT_DIR": "/nonexistent", "GITHUB_TOKEN": "t"}
        saved = {key: os.environ.get(key) for key in polluted}
        os.environ.update(polluted)
        try:
            cleaned = clean_environment()
            for key in polluted:
                self.assertNotIn(key, cleaned, key)
            self.assertIn("PATH", cleaned)
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
