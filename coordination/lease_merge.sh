#!/usr/bin/env bash
# leasedmerge2.sh PR_NUMBER EXPECTED_HEAD MSGFILE OWNER_TOKEN EXEC_TOKEN
#
# Non-squash merge of one reviewed pull-request head into the testbed's main under the project lease
# (coordination/run_lock.py, ref refs/heads/coordination/issue-12-run-lock). Rebuilt on 2026-11-01 after the
# earlier wrapper was lost in an environment reset; it is a different file from that one and is disclosed as such.
# Every step stops the run on failure. Nothing is ignored by exit status.
#
# Environment:
#   CLONE        persistent testbed clone whose `origin` is the target (default /home/user/microcredit-agent-testbed)
#   PYLIB        directory holding pydantic for the model validators (default the scratchpad pylib)
#   NO_API=1     skip the GitHub API state check (scratch-origin tests only)
#   MAIN_EXPECT  optional sha main must still be at when the merge starts
#
# Owner token: claude-<16 hex>; execution token: merge<PR>-<16 hex> (run_lock.py wants lowercase, 8-80 chars).
set -euo pipefail

PR="$1"; HEAD_EXPECT="$2"; MSG="$3"; OWNER="$4"; EXECID="$5"
CLONE="${CLONE:-/home/user/microcredit-agent-testbed}"
PYLIB="${PYLIB:-/tmp/claude-0/-home-user-microcredit-contract/570fe25d-c591-5ade-adbc-064b6b189c41/scratchpad/pylib}"
PCS_FALLBACK=/home/user/microcredit-contract/scripts/check-public-content.sh
export PYTHONPATH="$PYLIB"
NOREPLY_NAME="Claude"; NOREPLY_EMAIL="noreply@anthropic.com"
export GIT_AUTHOR_NAME="$NOREPLY_NAME" GIT_AUTHOR_EMAIL="$NOREPLY_EMAIL" GIT_COMMITTER_NAME="$NOREPLY_NAME" GIT_COMMITTER_EMAIL="$NOREPLY_EMAIL"

ACQUIRED=""; WT=""
say() { echo "[leasedmerge2] $*"; }
fail() { echo "[leasedmerge2] CHECK FAILED: $*" >&2; exit 1; }
release() {
  if [ -n "$ACQUIRED" ]; then
    if python3 "$CLONE/coordination/run_lock.py" --repo "$CLONE" release --owner "$OWNER" --acquired-head "$ACQUIRED" >/tmp/claude-0/lm-release.json 2>/tmp/claude-0/lm-release.err; then
      say "lease released: $(cat /tmp/claude-0/lm-release.json)"
    else
      echo "[leasedmerge2] LEASE RELEASE REFUSED: $(cat /tmp/claude-0/lm-release.err)" >&2
      RELEASE_FAILED=1
    fi
    ACQUIRED=""
  fi
  if [ -n "$WT" ] && [ -d "$WT" ]; then git -C "$CLONE" worktree remove --force "$WT" >/dev/null 2>&1 || true; fi
}
RELEASE_FAILED=0
trap 'rc=$?; release; if [ "$RELEASE_FAILED" = 1 ] && [ "$rc" = 0 ]; then rc=1; fi; exit $rc' EXIT

[[ "$OWNER" =~ ^claude-[0-9a-f]{16}$ ]] || fail "owner token must look like claude-<16 hex>"
[[ "$EXECID" =~ ^merge${PR}-[0-9a-f]{16}$ ]] || fail "execution token must look like merge${PR}-<16 hex>"
[ -f "$MSG" ] || fail "message file missing"
MSG="$(realpath "$MSG")"
cd "$CLONE"
git config user.name "$NOREPLY_NAME"; git config user.email "$NOREPLY_EMAIL"

# 1. Preconditions: exact reviewed head, non-draft open PR, main where we expect it.
git fetch -q origin main "refs/pull/${PR}/head:refs/remotes/origin/pr-${PR}"
HEAD_NOW="$(git rev-parse "refs/remotes/origin/pr-${PR}")"
[ "$HEAD_NOW" = "$HEAD_EXPECT" ] || fail "PR head is $HEAD_NOW, not the reviewed $HEAD_EXPECT"
MAIN_BEFORE="$(git rev-parse origin/main)"
if [ -n "${MAIN_EXPECT:-}" ] && [ "$MAIN_BEFORE" != "$MAIN_EXPECT" ]; then fail "main is $MAIN_BEFORE, expected $MAIN_EXPECT"; fi
if [ "${NO_API:-0}" != 1 ]; then
  python3 - "$PR" <<'PY' || fail "PR is not an open, non-draft, unmerged pull request"
import json, os, sys, urllib.request
tok = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
h = {'Accept': 'application/vnd.github+json', 'User-Agent': 'leasedmerge2'}
if tok: h['Authorization'] = 'Bearer ' + tok
p = json.load(urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/scottonchain/microcredit-agent-testbed/pulls/' + sys.argv[1], headers=h), timeout=60))
sys.exit(0 if p['state'] == 'open' and not p['draft'] and not p['merged'] else 1)
PY
fi
git merge-base "$MAIN_BEFORE" "$HEAD_EXPECT" >/dev/null 2>&1 || git fetch -q --deepen=500 origin main "refs/pull/${PR}/head" || true
git merge-base "$MAIN_BEFORE" "$HEAD_EXPECT" >/dev/null || fail "no merge base between main and the PR head"
PCS="$CLONE/scripts/check-public-content.sh"; [ -x "$PCS" ] || PCS="$PCS_FALLBACK"
bash "$PCS" --message "$MSG" || fail "public content in the merge message"
say "preconditions ok: PR $PR head $HEAD_EXPECT, main $MAIN_BEFORE"

# 2. Lease.
OUT="$(python3 coordination/run_lock.py --repo "$CLONE" acquire --owner "$OWNER" --execution "$EXECID")" || fail "lease acquisition refused (held, missing or ambiguous)"
ACQUIRED="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["acquired_head"])' "$OUT")"
say "lease acquired: $ACQUIRED"

# 3. Merge in an isolated worktree.
WT="$(mktemp -d /tmp/claude-0/lm-wt-XXXXXX)"; rmdir "$WT"
git worktree add -q --detach "$WT" "$MAIN_BEFORE"
cd "$WT"
git merge --no-ff --no-commit "$HEAD_EXPECT" >/tmp/claude-0/lm-merge.out 2>&1 || { cat /tmp/claude-0/lm-merge.out; fail "merge conflicts; return the changed head for review"; }
git commit -q -F "$MSG"
MERGE="$(git rev-parse HEAD)"
[ "$(git rev-parse HEAD^1)" = "$MAIN_BEFORE" ] && [ "$(git rev-parse HEAD^2)" = "$HEAD_EXPECT" ] || fail "merge parents are not main and the reviewed head"
[ "$(git log -1 --format='%ae|%ce')" = "$NOREPLY_EMAIL|$NOREPLY_EMAIL" ] || fail "merge identity is not the noreply identity"
say "merge commit $MERGE tree $(git rev-parse HEAD^{tree})"

# 4. Checks on the merge. Each one stops the run.
CHANGED="$(git diff --name-only "$MAIN_BEFORE" "$MERGE" | sort | tr '\n' ' ')"
PRFILES="$(git diff --name-only "$(git merge-base "$MAIN_BEFORE" "$HEAD_EXPECT")" "$HEAD_EXPECT" | sort | tr '\n' ' ')"
say "files changed by the merge: $CHANGED"
[ "$CHANGED" = "$PRFILES" ] || say "NOTE: the merge changes a different file set than the PR alone ($PRFILES); main moved underneath it"
git diff --check "$MAIN_BEFORE" "$MERGE" || fail "git diff --check"
if git diff --name-only "$MAIN_BEFORE" "$MERGE" | grep -q '^world-model/model.json$'; then
  python3 world-model/validate.py --check-schema >/tmp/claude-0/lm-schema.out 2>&1 || { cat /tmp/claude-0/lm-schema.out; fail "model schema"; }
  say "model schema: $(head -c 160 /tmp/claude-0/lm-schema.out)"
  ( cd world-model && python3 -B -m unittest test_validate test_q ) >/tmp/claude-0/lm-model-tests.out 2>&1 || { tail -20 /tmp/claude-0/lm-model-tests.out; fail "model unit tests"; }
  say "model tests ok"
fi
if [ -f tools/check.py ]; then
  timeout 1500 python3 tools/check.py >/tmp/claude-0/lm-check.out 2>&1 || { tail -30 /tmp/claude-0/lm-check.out; fail "tools/check.py"; }
  say "tools/check.py: $(tail -1 /tmp/claude-0/lm-check.out)"
fi
bash "$PCS" --range "$MAIN_BEFORE..$MERGE" || fail "public content in the merge range"

# 5. Re-assert ownership, then a guarded push and a readback.
python3 "$CLONE/coordination/run_lock.py" --repo "$CLONE" assert-owned --owner "$OWNER" --acquired-head "$ACQUIRED" >/dev/null || fail "lease no longer owned"
git fetch -q origin main
[ "$(git rev-parse origin/main)" = "$MAIN_BEFORE" ] || fail "main moved to $(git rev-parse origin/main) after the lease; nothing pushed"
git push -q --force-with-lease="refs/heads/main:$MAIN_BEFORE" origin "$MERGE:refs/heads/main" || fail "push refused"
READ="$(git ls-remote origin refs/heads/main | cut -f1)"
[ "$READ" = "$MERGE" ] || fail "readback is $READ, not $MERGE"
say "PUSHED and read back: main = $MERGE"
echo "RECEIPT pr=$PR reviewed_head=$HEAD_EXPECT main_before=$MAIN_BEFORE merge=$MERGE tree=$(git rev-parse HEAD^{tree}) lease_acquired=$ACQUIRED"
cd "$CLONE"
