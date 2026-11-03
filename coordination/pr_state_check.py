#!/usr/bin/env python3
"""Is a pull request open, not a draft and not merged? Used by lease_merge.sh.

Exit 0 only for an open, non-draft, unmerged pull request; anything else, including an unreadable
state, exits 1. A credential is sent only to the approved GitHub API origin, never to a configured
test endpoint, and redirects are never followed, so a token cannot be forwarded to another origin.
Standard library only.
"""
import json
import os
import sys
import urllib.error
import urllib.request

APPROVED_API = "https://api.github.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # a redirect becomes an HTTPError: the state is unreadable, so the merge is refused


def request_headers(api_base, token):
    """Headers for one request. The Authorization header exists only for the approved API origin."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "lease_merge"}
    if token and api_base.rstrip("/") == APPROVED_API:
        headers["Authorization"] = "Bearer " + token
    return headers


def pull_request_is_mergeable(api_base, repo, number, token=None, timeout=60):
    url = api_base.rstrip("/") + "/repos/" + repo + "/pulls/" + str(number)
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers=request_headers(api_base, token))
    try:
        with opener.open(request, timeout=timeout) as response:
            state = json.load(response)
    except (urllib.error.URLError, OSError, ValueError):
        return False
    return state.get("state") == "open" and state.get("draft") is False and state.get("merged") is False


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: pr_state_check.py PR_NUMBER (GITHUB_API and REPO_SLUG in the environment)", file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    api = os.environ.get("GITHUB_API", APPROVED_API)
    ok = pull_request_is_mergeable(api, os.environ["REPO_SLUG"], argv[0], token)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
