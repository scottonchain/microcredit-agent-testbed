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
report. The JSON on stdout carries the reason. The OpenAI-side dispatcher must call this
before it dispatches; that part is outside this repository and is not covered by these
tests. Repository tests are not an end-to-end switching claim.

## Switching

| Step | Who | State after |
| --- | --- | --- |
| `request --to X --by Y --reason ... --drain-deadline T` | either lane, when low on tokens | draining: nobody starts heavy work; the source lane may finish and checkpoint in-flight work |
| `accept --by X --receipt gh:...` | the destination lane, after the request | acceptance recorded with a board reference |
| `drained --by <source> --in-flight 0 --lease-released` | the source lane | handover |
| `complete --by X --lease-head <sha>` | the destination lane | stable, owner is X, the lease head X acquired is named |

`complete` is refused unless X accepted after the request, so an earlier acceptance
never carries over. `cancel --by Y` returns an unfinished switch to stable with the
owner unchanged. A repeated identical request changes nothing (deduplication). A switch
past its drain deadline is reported by `status` and is not completed automatically; it
needs `cancel` or an explicit decision.

The global project lease (`run_lock.py`) is a separate mutex. The source lane releases
it before `drained`; the destination lane acquires it before `complete`. This toggle
records those facts and does not touch the lease.

## Recording a change

The file changes by a normal reviewed commit, or by a leased write when a lane is out
of tokens. The CLI writes the file atomically and prints the new status; the caller
commits it with a noreply identity. Every change adds a `history` entry.

## Current state

Owner `claude` since 2026-11-01T17:29:00Z (reason: OpenAI token budget, declared).
Claude accepted at 17:50:04Z (board 15 comment 6561624731). OpenAI has not accepted the
owner role because it is the non-owner; a switch back needs its fresh acceptance.
