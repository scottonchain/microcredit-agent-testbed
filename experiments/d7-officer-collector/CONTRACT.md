# Officer collector and alert integration contract (DRAFT, source only)

Status: draft for review, stacked on the observer in PR 470 (`../d7-officer-observer/`). Nothing here is deployed, run live or
accepted. No host, recipient, alert path, signer, wallet or runner exists because of it. It does not accept any head as the officer
runtime and is not a route around the held merges. Requested by OpenAI on tb#462 (comments 6862497031, 6868733841, 6870385476).
Schema scope: the officer daemon at PR 458 head `9c181672` (daemon blob `455e374971198ec54b4561d83d2331c6c60f2da3`). The running
blob `a322d588` emits none of heartbeat, exit, state-unreadable, earlier-reply-stuck, state-write-error or send-ambiguous, so this
contract cannot observe today's process at all.

## Shape

Three small modules and no I/O. The host does the reading and sending; the code decides.

- `collector.mjs`: `collectOnce({ logText, nowMs, config, fileBytes, fetchPending })` returns `{ status, alerts, collectorRun, meta }`
  and never throws. It parses a bounded tail of the officer log, computes the git blob sha of the daemon file the host runs,
  performs an injected, time-bounded read of the pending desk queue, checks run identity, and feeds the observer's `evaluate()`.
- `alertstate.mjs`: `step(state, result, nowMs)`, `toSend(state)`, `ack(state, key)`, `inspectState(state)`. Dedup, retry of undelivered
  alerts, repeat interval, recovery after consecutive healthy runs. Every item has a persisted occurrence key `kind:o<seq>`; the
  counter lives in the plain-JSON state, so keys stay unique across A to B to A flips, every repeat, steps at the same clock tick and
  restarts, while all retries of one delivery keep the same key. All functions return typed results and none throws:
  `{ ok: true, ... }` or `{ ok: false, error: 'STATE_INVALID' | 'PARAMS_INVALID', code: 'ALERT_STATE_INVALID', salvaged }`. A damaged
  state is never reset: the input is left untouched and every structurally valid undelivered item found in it is returned in `salvaged`.
  The host must deliver the salvaged items, raise ALERT_STATE_INVALID on its independent path (the watchdog's), and keep the
  damaged state file for repair instead of overwriting it.
- `watchdog.mjs`: `checkWatchdog({ nowMs, record, maxSilenceS })` checks the collector's last run record. It imports nothing
  (tested), so it shares no code with the collector, and it must run on a different schedule and host with its own delivery path.

Per invocation the host: reads the log file text, reads the daemon file bytes, calls `collectOnce`, writes `collectorRun` to
the run-record file for the watchdog, runs `step` on the result, sends each `toSend` item through the alert path and calls `ack` only
after a successful delivery. What leaves the host is `result.outbound`, built from a static table (code plus fixed text); a
string from the log, the config, the chain reader or an exception is never copied into it. The proposed interval is five minutes; the owners set it (and the observer's ranges apply).

## Privacy

The log holds applicant addresses, reply text, transaction hashes and the RPC endpoint. Only typed fields leave the collector:
finite numbers (any other value becomes null, which the observer reads as unreadable, never as zero) and strings from a closed list
(`start.mode`, `exit.reason`, `state-unreadable.why`; any other string, object or array becomes `other`). `replied`, `topup`,
`llm-*`, `error`, `backing-unchanged` and unknown or inherited event names are dropped whole, and times are re-serialised, never
forwarded as given. The forwarded fields are mirrored in `fixtures/emitter-schema.json` and a test checks the two agree. Outbound
alerts use fixed text per code (`OUTBOUND_DETAIL`); unknown codes become UNKNOWN_CODE; unknown config key names are counted, never
echoed; an exception contributes no name. Tests serialise the outbound payload and the internal alert list and look for injected
secrets in every path (log fields, config keys, thrown exceptions, reader errors).

## What fails closed (each has tests and a fixture or inline log)

| Condition | Code(s) |
| --- | --- |
| Log missing or not text | LOG_UNREADABLE, HEARTBEAT_MISSING |
| Empty log after rotation, until the next heartbeat | HEARTBEAT_MISSING |
| Partial last line (still being written) | ignored, not evidence, not an alert on its own |
| Log larger than the tail bound | read from the tail; the cut first line is dropped |
| Unparseable lines | LOG_MALFORMED (count) |
| Chain read throws, returns nothing, wrong shape, bad entry times | RPC_UNAVAILABLE, PENDING_UNREADABLE |
| Block evidence missing, non-integer or negative block number, block time in the future, read time far from now | RPC_BLOCK_INVALID, PENDING_UNREADABLE |
| Queue not read at the evidenced block, or an entry dated after that block | RPC_BLOCK_MISMATCH, PENDING_UNREADABLE |
| Chain read does not finish inside the bound | RPC_TIMEOUT, PENDING_UNREADABLE |
| Latest block older than the bound | RPC_STALE, PENDING_UNREADABLE |
| A missing read is never an empty queue | only an explicit empty array is empty |
| Daemon file differs from the pinned 40-hex blob sha, or not reported | RUNTIME_HASH_MISMATCH |
| Exit event after the latest start | PROCESS_EXITED |
| More than the allowed starts inside the window | RESTART_LOOP |
| Heartbeat uptime inconsistent with the latest start, or going backwards | DUPLICATE_RUNNER |
| Config: unknown key, inherited property, non-object, short or uppercase sha, any value out of range | CONFIG_INVALID |
| The collector itself throws | COLLECTOR_FAILURE, run record status `crashed` |
| No collector run inside the silence limit | COLLECTOR_MISSED_INVOCATION (watchdog) |
| Run record missing, damaged, future, or `crashed` | WATCHDOG_RECORD_MISSING, FUTURE_RECORD, COLLECTOR_CRASHED |
| An unusable or inconsistent result handed to alert state | counts as a failure, never a recovery |
| A damaged alert outbox or bad parameters | typed failure ALERT_STATE_INVALID; input untouched; valid undelivered items salvaged |

The observer's own codes (heartbeat, poll, held, model, ambiguous transaction, pending age, journal) pass through unchanged.

## NOT covered

Each line is open; none is closed by this draft or by any source review.

- A real chain reader. `fetchPending` is injected and untested against a live node; the definition of "pending" (the unresolved
  desk requests the daemon itself would answer) must be implemented to match the daemon's poll and has not been verified.
- Archival RPC history for held-reply settlement (a daemon concern; see OFFICER_RUNBOOK.md) and any RPC provider qualification.
- Real log rotation by an actual rotation tool, file replacement semantics, log shipping, and a log written by two processes at
  once. Tests use text only; `DUPLICATE_RUNNER` is a heuristic from heartbeat uptime and cannot see a second process that writes
  a different log file.
- Runtime identity beyond one file: dependencies, the Node version, the `claude` CLI and its model access are not hashed.
- The alert delivery channel, recipient, delivery receipts and recovery in practice. No host, recipient or path is qualified.
- The watchdog's own host and a dead-man service watching the watchdog (the collector's watchdog is itself unwatched here).
- Time synchronisation of the host; the skew bounds are fixed by the observer's ranges.
- Host handling of a damaged alert outbox (delivering salvaged items, raising the alert on the independent path, repairing the file) is specified here but not exercised against a real file or delivery path.
- `logTailChars` bounds UTF-16 characters, not bytes; the log size on disk is not bounded by it.
- That the chain reader's block evidence (number, time, queue read at that block) is what a real node can supply; the shape is specified and tested, not obtained from a node.
- The daemon emitting the heartbeat at all: it does only at the PR 456/458 heads, which no owner has accepted and nothing runs.
- The complete synthetic journey (see `../d7-officer-observer/SYNTHETIC_JOURNEY.md`) and continuity across the old hourly boundaries.

Cutover acceptance still needs a delivered failure alert with recovery, the full journey, and continuity over two old hourly
boundaries, on a qualified host, with the acceptance record (`ACCEPTANCE_RECORD_TEMPLATE.md`) filled in by the accountable people.
