#!/usr/bin/env python3
"""Classify this execution's Git route without publishing or printing secrets.

The optional remote probe is a Git push dry run, not proof of a successful write,
an exact lease, persisted credentials, or authorization for any action.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess


IDENTITY = re.compile(r"[^\r\n<>]+ <([^<>\r\n]+)> [0-9]+ [+-][0-9]{4}")
NOREPLY = re.compile(r"[A-Za-z0-9][A-Za-z0-9+._-]{0,100}@users\.noreply\.github\.com")
REMOTE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}")


def safe_identity(raw):
    match = IDENTITY.fullmatch(raw.strip())
    return bool(match and (NOREPLY.fullmatch(match[1]) or match[1] == "noreply@anthropic.com"))


def failure_kind(stderr):
    """Return a static diagnosis, never the remote's possibly sensitive text."""
    text = stderr.lower()
    if any(x in text for x in ("could not read username", "could not read password", "authentication failed",
                                "permission denied (publickey)", "terminal prompts disabled")):
        return "GIT_AUTHENTICATION_UNAVAILABLE"
    if any(x in text for x in ("repository not found", "permission to", "write access to repository not granted")):
        return "REPOSITORY_OR_AUTHORIZATION_FAILURE"
    if any(x in text for x in ("could not resolve", "connection timed out", "network is unreachable", "proxy", "403")):
        return "NETWORK_OR_POLICY_FAILURE"
    return "GIT_OPERATION_FAILED"


def run_git(repo, *args):
    # Preserve configured proxy, trust and credential providers. Never prompt for
    # a token, print stderr, or rewrite an inherited authentication configuration.
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], env=env,
                                capture_output=True, text=True, timeout=25)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "connection timed out"
    except (OSError, UnicodeError):
        return 125, "", ""


def inspect(repo, remote="origin", probe_remote=False):
    if not REMOTE.fullmatch(remote):
        raise ValueError("NAMED_REMOTE_REQUIRED")
    report = {"format": "github-route-preflight-v1",
              "checked_at": datetime.now(timezone.utc).isoformat(),
              "publishes": False, "authority_granted": False,
              "persistent_setup_verified": False, "protected_lease_verified": False}
    code, _, _ = run_git(repo, "rev-parse", "--git-dir")
    if code:
        return dict(report, status="NOT_A_READABLE_CHECKOUT", next_action="USE_VERIFIED_WRITER")
    for label in ("AUTHOR", "COMMITTER"):
        code, value, _ = run_git(repo, "var", "GIT_" + label + "_IDENT")
        report[label.lower() + "_noreply_configured"] = code == 0 and safe_identity(value)
    code, _, _ = run_git(repo, "remote", "get-url", "--push", remote)
    report["push_remote_configured"] = code == 0
    report["credential_helper_configured"] = run_git(repo, "config", "--get-all", "credential.helper")[0] == 0
    # Presence is diagnostic only. A provider may inject credentials elsewhere;
    # absent env variables alone never establish unavailable authentication.
    report["credential_environment_present"] = any(os.environ.get(key) for key in
        ("GITHUB_TOKEN", "GH_TOKEN", "GIT_ASKPASS", "SSH_ASKPASS", "SSH_AUTH_SOCK"))
    report["remote_probe"] = "NOT_REQUESTED"
    if probe_remote and report["push_remote_configured"]:
        code, _, stderr = run_git(repo, "push", "--dry-run", "--porcelain", remote,
                                  "HEAD:refs/heads/codex/route-preflight-no-write")
        report["remote_probe"] = "DRY_RUN_ACCEPTED" if code == 0 else failure_kind(stderr)
    identities_ready = report["author_noreply_configured"] and report["committer_noreply_configured"]
    if report["remote_probe"] == "DRY_RUN_ACCEPTED" and identities_ready:
        report.update(status="CANDIDATE_ROUTE_ONLY", next_action="RUN_AUTHORIZED_WRITE_AND_READBACK")
    elif report["remote_probe"] == "NOT_REQUESTED":
        report.update(status="LOCAL_CHECK_ONLY", next_action="PROBE_AUTHORIZED_ROUTE_OR_USE_VERIFIED_WRITER")
    else:
        report.update(status="ROUTE_NOT_READY", next_action="REPAIR_SUPPORTED_SETUP_OR_USE_VERIFIED_WRITER")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--probe-remote", action="store_true", help="perform one noninteractive Git push dry run")
    args = parser.parse_args(argv)
    try:
        report = inspect(args.repo, args.remote, args.probe_remote)
    except ValueError:
        report = {"status": "NAMED_REMOTE_REQUIRED", "publishes": False, "authority_granted": False}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "CANDIDATE_ROUTE_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
