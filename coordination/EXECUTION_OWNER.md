# Execution-owner toggle

Claude (AI), November 1, 2026. The user's instruction in this session: all scheduled
tasks transfer to Claude, and the lanes can toggle scheduled and other work back and
forth, so that when one lane is low on tokens the other takes up the compute-intensive
work. This file, `execution-owner.json`, `execution_owner.py` and
`test_execution_owner.py` are the repository half. They decide and record; they do not
schedule, run work or hold credentials. No budget telemetry is read or invented: a
reason is a stated declaration.

## What is governed

- **Heavy work** (`scheduled`, `other`): scheduled dispatches and any other
  compute-intensive execution. Only the execution owner starts it.
- **Light work** (`review`, `verification`, `access_bridge`): open to both lanes in
  every state, so the non-owner can still review, check receipts and bridge a
  necessary permission.
- The owner is `owner` in `execution-owner.json`. `default_owner` (`openai`) never
  silently overrides it; moving back is the same handover as moving out.

## Runner contract

Before dispatching heavy work, a runner reads the file from the default branch and runs

```sh
python3 coordination/execution_owner.py check --runner <openai|claude> --kind <scheduled|other>
```

Exit 0: proceed. Exit 3: not the owner, do light work only. Exit 4: a switch is in
progress, start nothing new. Exit 2: the file is missing or invalid, start nothing and
report. The JSON on stdout carries the reason. The library decides and records; it is not
an enforced dispatcher. Nothing stops a runner that does not call `check`.

Enforcement boundary. The one consumer in this repository is `lease_merge.sh`, which reads
`execution-owner.json` and `execution_owner.py` from main and refuses to take the lease unless
`RUNNER_LANE` may run heavy (`other`) work. It fails closed: a missing library or configuration,
a switch in progress, or a non-owner lane stops the merge. Every other consumer, including the
OpenAI-side dispatcher and any scheduled runner, is outside this repository, is not covered by
these tests and has to call `check` itself. Repository tests are not an end-to-end switching claim.

## Switching

| Step | Who | State after |
| --- | --- | --- |
| `request --to X --by Y --reason ... --drain-deadline T` | either lane, when low on tokens | draining: nobody starts heavy work; the source lane may finish and checkpoint in-flight work |
| `accept --by X --receipt gh:...` | the destination lane, after the request | acceptance recorded with a board reference |
| `drained --by <source> --in-flight 0 --lease-released` | the source lane | handover |
| `complete --by X --lease-head <sha>` | the destination lane | stable, owner is X, the lease head X acquired is named |

`complete` is refused unless X accepted after the request, so an earlier acceptance
never carries over. "After" is bound to the configuration version, not to a clock: the
request records the version it created (`transition.requested_config_version`), each
acceptance records the version it created (`acceptance.<lane>.config_version`), and an
acceptance counts only if its version is higher. An acceptance made in the same second
before the request, or before a cancelled request, therefore never satisfies a later one.

`cancel --by Y` returns an unfinished switch to stable with the owner unchanged and the
lease unheld (the owner acquires it again before heavy work). Cancelling a handover also
needs `--destination-lease-released`: once the source lane has drained, the destination
lane may already hold the lease, so it attests that it released it. A repeated request
changes nothing only if it is identical in every field (lane, requester, reason and
drain deadline); a retry with different terms is refused until the open switch is
cancelled. A switch past its drain deadline is reported by `status` and is not completed
automatically; it needs `cancel` or an explicit decision.

A configuration whose receipts or times are not the expected types is invalid (exit 2,
file untouched), never a crash.

The global project lease (`run_lock.py`) is a separate mutex. The source lane releases
it before `drained`; the destination lane acquires it before `complete`. This toggle
records those facts and does not touch the lease.

## The merge wrapper

`lease_merge.sh PR HEAD MSGFILE OWNER_TOKEN EXEC_TOKEN` merges one reviewed pull-request
head into main under the project lease (non-squash, isolated worktree, noreply identity,
expected-main compare-and-swap push, readback). Configuration is by environment: `CLONE`,
`RUNNER_LANE`, `PUBLIC_CONTENT_CHECK` (required; the checker is not in this repository),
`PYLIB`, `GITHUB_API`, `GITHUB_REPO`, `NO_API` (accepted only for a local scratch origin),
`MAIN_EXPECT`. It holds no machine-specific path. The pull-request state check is
`pr_state_check.py`: a GitHub token from the environment is sent only to the approved API
origin (`https://api.github.com`), never to a configured test endpoint, and redirects are
never followed, so a token cannot be forwarded elsewhere. The toggle is read from main before
the lease; right after the lease is acquired the wrapper reads main again and stops if it
moved, so an owner switch that lands in between cannot leave the checks running on a stale
answer. `test_lease_merge.py` runs it against
scratch origins and covers: a clean merge, a refused lane, a missing configuration, a switch
in progress, main moving after the lease, a lost lease (the other owner's lease is never
released), a refused push, a readback mismatch, a missing or failing checker (fails closed),
a missing public-content checker, forbidden message content, a wrong head, a held lease,
`NO_API` against a remote origin, a signal during the checks (the lease is released), an owner
switch landing between the gate and the lease (the checker never starts), a sentinel token that
must never reach a test endpoint, a redirect that must not be followed, and draft, merged, closed,
unreadable and unreachable pull-request states. Scratch runs strip any inherited GitHub token. It does not cover
the real GitHub API or a real remote.

## Recording a change

The file changes by a normal reviewed commit, or by a leased write when a lane is out
of tokens. The CLI writes the file atomically and prints the new status; the caller
commits it with a noreply identity. Every change adds a `history` entry.

## Current state

Owner `claude` since 2026-11-01T17:29:00Z (reason: OpenAI token budget, declared).
Claude accepted at 17:50:04Z (board 15 comment 6561624731). OpenAI has not accepted the
owner role because it is the non-owner; a switch back needs its fresh acceptance.
