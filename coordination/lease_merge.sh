#!/usr/bin/env bash
# lease_merge.sh PR_NUMBER EXPECTED_HEAD MSGFILE OWNER_TOKEN EXEC_TOKEN
#
# Non-squash merge of one reviewed pull-request head into the repository's main under the project lease
# (coordination/run_lock.py, ref refs/heads/coordination/issue-12-run-lock). Every step stops the run on
# failure; nothing is ignored by exit status, and a missing required checker or configuration fails closed.
# Behaviour is covered by coordination/test_lease_merge.py, which runs it against scratch origins.
#
# It is the one consumer of the execution-owner toggle in this repository: before it takes the lease it reads
# coordination/execution-owner.json from main and refuses unless RUNNER_LANE may run heavy ("other") work.
#
# Environment:
#   CLONE                 clone whose `origin` is the target (default: the repository containing this script)
#   RUNNER_LANE           openai or claude, the lane running this merge (default claude)
#   PUBLIC_CONTENT_CHECK  path to check-public-content.sh (default $CLONE/scripts/check-public-content.sh);
#                         required, the run stops if it is missing
#   PYLIB                 optional directory added to PYTHONPATH for the model validators (pydantic)
#   GITHUB_API            API base for the pull-request state check (default https://api.github.com); a
#                         GitHub token in the environment is sent only to that default origin
#   GITHUB_REPO           owner/name for that check (default: read from origin)
#   NO_API=1              skip the pull-request state check; accepted only when origin is a local path
#   MAIN_EXPECT           optional sha main must still be at when the merge starts
#   TOGGLE_BOOTSTRAP_PR   the PR number of the pull request that adds the toggle itself; reads the gate from the
#                         reviewed head, and only while main has no execution-owner library or configuration
#
# Owner token: claude-<16 hex>; execution token: merge<PR>-<16 hex> (run_lock.py wants lowercase, 8-80 chars).
set -euo pipefail

PR="$1"; HEAD_EXPECT="$2"; MSG="$3"; OWNER="$4"; EXECID="$5"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLONE="${CLONE:-$(git -C "$HERE" rev-parse --show-toplevel)}"
RUNNER_LANE="${RUNNER_LANE:-claude}"
GITHUB_API="${GITHUB_API:-https://api.github.com}"
PCS="${PUBLIC_CONTENT_CHECK:-$CLONE/scripts/check-public-content.sh}"
if [ -n "${PYLIB:-}" ]; then export PYTHONPATH="$PYLIB${PYTHONPATH:+:$PYTHONPATH}"; fi
NOREPLY_NAME="Claude"; NOREPLY_EMAIL="noreply@anthropic.com"
export GIT_AUTHOR_NAME="$NOREPLY_NAME" GIT_AUTHOR_EMAIL="$NOREPLY_EMAIL" GIT_COMMITTER_NAME="$NOREPLY_NAME" GIT_COMMITTER_EMAIL="$NOREPLY_EMAIL"

ACQUIRED=""; WT=""; BGPID=""; RELEASE_FAILED=0
WORK="$(mktemp -d)"
say() { echo "[lease_merge] $*"; }
fail() { echo "[lease_merge] CHECK FAILED: $*" >&2; exit 1; }
release() {
  if [ -n "$ACQUIRED" ]; then
    if python3 "$CLONE/coordination/run_lock.py" --repo "$CLONE" release --owner "$OWNER" --acquired-head "$ACQUIRED" >"$WORK/release.json" 2>"$WORK/release.err"; then
      say "lease released: $(cat "$WORK/release.json")"
    else
      echo "[lease_merge] LEASE RELEASE REFUSED (not released by this run): $(cat "$WORK/release.err")" >&2
      RELEASE_FAILED=1
    fi
    ACQUIRED=""
  fi
  if [ -n "$WT" ] && [ -d "$WT" ]; then git -C "$CLONE" worktree remove --force "$WT" >/dev/null 2>&1 || true; fi
}
finish() {
  rc=$?
  if [ -n "$BGPID" ]; then kill "$BGPID" 2>/dev/null || true; fi
  release
  if [ "$RELEASE_FAILED" = 1 ] && [ "$rc" = 0 ]; then rc=1; fi
  rm -rf "$WORK"
  exit "$rc"
}
trap finish EXIT
# A signal must release the lease too: run the long checks in the background and wait, so bash can act at once.
trap 'echo "[lease_merge] interrupted" >&2; exit 130' INT
trap 'echo "[lease_merge] terminated" >&2; exit 143' TERM
run_bg() { "$@" & BGPID=$!; local rc=0; wait "$BGPID" || rc=$?; BGPID=""; return "$rc"; }

[[ "$OWNER" =~ ^claude-[0-9a-f]{16}$ ]] || fail "owner token must look like claude-<16 hex>"
[[ "$EXECID" =~ ^merge${PR}-[0-9a-f]{16}$ ]] || fail "execution token must look like merge${PR}-<16 hex>"
[ -f "$MSG" ] || fail "message file missing"
MSG="$(realpath "$MSG")"
[ -f "$PCS" ] || fail "the public-content checker is required and was not found at $PCS (set PUBLIC_CONTENT_CHECK)"
cd "$CLONE"
git config user.name "$NOREPLY_NAME"; git config user.email "$NOREPLY_EMAIL"

# 0. The state check may be skipped only against a local scratch origin, never against a remote.
ORIGIN_URL="$(git remote get-url origin)"
if [ "${NO_API:-0}" = 1 ]; then
  case "$ORIGIN_URL" in
    /*|./*|../*) say "NO_API=1: skipping the pull-request state check (local scratch origin)";;
    *) fail "NO_API=1 is accepted only for a local scratch origin, not for $ORIGIN_URL";;
  esac
fi

# 1. Preconditions: exact reviewed head, non-draft open PR, main where we expect it.
git fetch -q origin main "refs/pull/${PR}/head:refs/remotes/origin/pr-${PR}"
HEAD_NOW="$(git rev-parse "refs/remotes/origin/pr-${PR}")"
[ "$HEAD_NOW" = "$HEAD_EXPECT" ] || fail "PR head is $HEAD_NOW, not the reviewed $HEAD_EXPECT"
MAIN_BEFORE="$(git rev-parse origin/main)"
if [ -n "${MAIN_EXPECT:-}" ] && [ "$MAIN_BEFORE" != "$MAIN_EXPECT" ]; then fail "main is $MAIN_BEFORE, expected $MAIN_EXPECT"; fi
if [ "${NO_API:-0}" != 1 ]; then
  REPO_SLUG="${GITHUB_REPO:-$(printf '%s' "$ORIGIN_URL" | sed -nE 's#^.*github\.com[:/]([^/]+/[^/]+)$#\1#p' | sed -E 's#\.git$##')}"
  [ -n "$REPO_SLUG" ] || fail "cannot work out owner/name for the pull-request check (set GITHUB_REPO)"
  GITHUB_API="$GITHUB_API" REPO_SLUG="$REPO_SLUG" python3 "$HERE/pr_state_check.py" "$PR" \
    || fail "PR is not an open, non-draft, unmerged pull request (or its state could not be read)"
fi
git merge-base "$MAIN_BEFORE" "$HEAD_EXPECT" >/dev/null 2>&1 || git fetch -q --deepen=500 origin main "refs/pull/${PR}/head" || true
git merge-base "$MAIN_BEFORE" "$HEAD_EXPECT" >/dev/null || fail "no merge base between main and the PR head"
bash "$PCS" --message "$MSG" || fail "public content in the merge message"

# 1b. The execution-owner gate: heavy work belongs to the owner lane. The gate files are read from main and the
# gate fails closed. There is exactly one bootstrap exception, for the pull request that adds the toggle itself:
# with TOGGLE_BOOTSTRAP_PR set to this PR's number the files are read from the reviewed head instead, and only
# while main has no execution-owner library or configuration at all. Once main has either, it is refused.
GATE_REF="$MAIN_BEFORE"; GATE_LABEL="main"
if [ -n "${TOGGLE_BOOTSTRAP_PR:-}" ]; then
  [ "$TOGGLE_BOOTSTRAP_PR" = "$PR" ] || fail "TOGGLE_BOOTSTRAP_PR is $TOGGLE_BOOTSTRAP_PR but this run merges PR $PR"
  if git cat-file -e "$MAIN_BEFORE:coordination/execution-owner.json" 2>/dev/null \
     || git cat-file -e "$MAIN_BEFORE:coordination/execution_owner.py" 2>/dev/null; then
    fail "bootstrap refused: main already has an execution-owner library or configuration"
  fi
  GATE_REF="$HEAD_EXPECT"; GATE_LABEL="the reviewed head"
  say "BOOTSTRAP: main has no execution-owner configuration; the gate is read from the reviewed head $HEAD_EXPECT"
fi
git show "$GATE_REF:coordination/execution_owner.py" >"$WORK/execution_owner.py" 2>/dev/null \
  || fail "no execution-owner library on $GATE_LABEL; refusing to run heavy work without it"
git show "$GATE_REF:coordination/execution-owner.json" >"$WORK/execution-owner.json" 2>/dev/null \
  || fail "no execution-owner configuration on $GATE_LABEL; refusing to run heavy work without it"
python3 "$WORK/execution_owner.py" --config "$WORK/execution-owner.json" check --runner "$RUNNER_LANE" --kind other >"$WORK/toggle.out" 2>&1 \
  || { cat "$WORK/toggle.out" >&2; fail "the execution-owner configuration does not allow $RUNNER_LANE to run heavy work now"; }
say "preconditions ok: PR $PR head $HEAD_EXPECT, main $MAIN_BEFORE; $(cat "$WORK/toggle.out")"

# 2. Lease.
OUT="$(python3 coordination/run_lock.py --repo "$CLONE" acquire --owner "$OWNER" --execution "$EXECID")" || fail "lease acquisition refused (held, missing or ambiguous)"
ACQUIRED="$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["acquired_head"])' "$OUT")"
say "lease acquired: $ACQUIRED"
# The execution-owner gate above read MAIN_BEFORE. If main moved before the lease was ours (for example an
# owner switch landed), those results are stale: stop before any merge or check runs.
git fetch -q origin main
[ "$(git rev-parse origin/main)" = "$MAIN_BEFORE" ] || fail "main moved to $(git rev-parse origin/main) between the execution-owner check and the lease; nothing was merged or checked"

# 3. Merge in an isolated worktree.
WT="$WORK/worktree"
git worktree add -q --detach "$WT" "$MAIN_BEFORE"
cd "$WT"
git merge --no-ff --no-commit "$HEAD_EXPECT" >"$WORK/merge.out" 2>&1 || { cat "$WORK/merge.out"; fail "merge conflicts; return the changed head for review"; }
git commit -q -F "$MSG"
MERGE="$(git rev-parse HEAD)"
[ "$(git rev-parse HEAD^1)" = "$MAIN_BEFORE" ] && [ "$(git rev-parse HEAD^2)" = "$HEAD_EXPECT" ] || fail "merge parents are not main and the reviewed head"
[ "$(git log -1 --format='%ae|%ce')" = "$NOREPLY_EMAIL|$NOREPLY_EMAIL" ] || fail "merge identity is not the noreply identity"
say "merge commit $MERGE tree $(git rev-parse HEAD^{tree})"

# 4. Checks on the merge. Each one stops the run; a missing required checker stops it too.
CHANGED="$(git diff --name-only "$MAIN_BEFORE" "$MERGE" | sort | tr '\n' ' ')"
PRFILES="$(git diff --name-only "$(git merge-base "$MAIN_BEFORE" "$HEAD_EXPECT")" "$HEAD_EXPECT" | sort | tr '\n' ' ')"
say "files changed by the merge: $CHANGED"
[ "$CHANGED" = "$PRFILES" ] || say "NOTE: the merge changes a different file set than the PR alone ($PRFILES); main moved underneath it"
git diff --check "$MAIN_BEFORE" "$MERGE" || fail "git diff --check"
if git diff --name-only "$MAIN_BEFORE" "$MERGE" | grep -q '^world-model/model.json$'; then
  python3 world-model/validate.py --check-schema >"$WORK/schema.out" 2>&1 || { cat "$WORK/schema.out"; fail "model schema"; }
  say "model schema: $(head -c 160 "$WORK/schema.out")"
  ( cd world-model && python3 -B -m unittest test_validate test_q ) >"$WORK/model-tests.out" 2>&1 || { tail -20 "$WORK/model-tests.out"; fail "model unit tests"; }
  say "model tests ok"
fi
[ -f tools/check.py ] || fail "tools/check.py is required and is missing; refusing to skip it"
run_bg timeout 1500 python3 tools/check.py >"$WORK/check.out" 2>&1 || { tail -30 "$WORK/check.out"; fail "tools/check.py"; }
say "tools/check.py: $(tail -1 "$WORK/check.out")"
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
