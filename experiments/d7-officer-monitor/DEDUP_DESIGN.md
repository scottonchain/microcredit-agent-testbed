# Chain monitor dedup design (DRAFT, source only)

Status: draft for review, stacked on PR 474. It closes the open item "dedup across ephemeral runs" as a WRITTEN AND TESTED DESIGN. It does not accept
anything: O4 stays NOT ACCEPTED until a named owner decides, O6 (the independent receipt watcher) still has to exist before O5, and nothing here has
run in GitHub Actions or against a node. No credential, signer, host, spend or workflow activation is added.

## The rule

Each scheduled run is ephemeral and has no memory. The previous state is therefore the board itself. A run posts only when

1. there is no usable previous monitor comment (`NO_PREVIOUS`, `PREVIOUS_UNUSABLE`), or
2. the status or the set of alert codes differs from the newest monitor comment (`CHANGED`; this includes ALERT to OK, the recovery), or
3. nothing changed but the newest monitor comment is old enough: an unchanged ALERT repeats after `repeatAlertS` (default 3600) and an unchanged OK
   posts a receipt after `okReceiptS` (default 21600). A `slackS` (default 300) is added to the age so that a 15 minute schedule does not slip a
   whole run late at every boundary.

Block number, pending count and the oldest pending age are NOT part of the comparison; they change every run and would defeat the point. The periodic OK
receipt exists so that the independent watcher (O6) can tell a silent healthy monitor from a dead one. Without a receipt cadence, silence is ambiguous.

Expected volume with the defaults: a steady OK is 4 comments a day, a steady ALERT 24 a day, plus one per change. The un-deduplicated draft was 96 a day.

## Where the previous state comes from, and whom to trust

`decide-post.mjs` receives local files only: the candidate `status-comment.md`, `comments.json` (the whole comment thread of tb#462, one object per comment
with `id`, `created_at`, `login`, and `body`, where `body` is kept ONLY for the expected login and is null for everyone else), and `count.txt` (the issue's
comment count, read BEFORE the list). Only comments whose `login` equals `expectedLogin` (default `github-actions[bot]`) AND whose body claims the monitor's message id prefix (`m-officer-chain-monitor-`) are the monitor's stream. The Actions bot identity is shared by every workflow in the repository, so the login alone is not enough: ordinary CI comments are not part of the stream, do not count toward the rate cap and do not replace the previous state. A comment that claims the monitor id but does not validate is malformed monitor evidence: it counts toward the cap and, if it is the newest, makes the previous state unusable (the run posts). A lookalike from any other
author is ignored, so nobody can silence the monitor by posting a convincing OK or can fake a recovery. The list is the whole thread, not the last N comments,
so a busy board cannot push the monitor's own comment out of view and cause a post on every run.

The newest monitor comment is chosen by creation time (GitHub's `created_at`, whole seconds), ties broken by the higher comment id. Edit time is not used.
If the newest one no longer validates (a person edited it), it is not trusted and an older valid one does NOT stand in for it: the run posts a fresh baseline.
A previous comment dated more than `clockSkewS` (default 60) in the future is treated the same way.

## The read-back validator is not the sender gate

`validateBoardComment` requires the exact bytes that were posted, including the final newline. A body read back from the board may not keep that newline,
so feeding it to the gate unchanged would reject every real previous comment and make every run post. `parseMonitorComment` therefore adds back at most ONE
missing final newline, refuses carriage returns and any other whitespace difference, and only then applies the same gate (so the key set, canonical JSON,
text alphabet and status/op agreement are all still enforced). It returns the status, the sorted alert codes and the message id.

## Ids, retries and freshness

Message ids are `m-officer-chain-monitor-<yyyymmddhhmmss>`, the observation time to the second (they were minute-resolution in the first draft, which let a real change inside one minute collide with
the previous id; found by OpenAI's review of 682cd136). Three cases for the candidate's id:

- not on the board from the monitor's stream: normal decision;
- on the board with the SAME status and codes: a retry of the same send, dropped quietly (`DUPLICATE_ID`);
- on the board with a DIFFERENT status or codes: never silently discarded; the job halts visibly (`ID_COLLISION`) and the next run has a new id. At second resolution this needs two sequential
  checks in the same second, which a run that makes several network reads does not produce; the halt exists so that if it ever happens it is seen.

Freshness: the candidate's observation time (`at`, parsed from the validated message text) must be no older than `maxCandidateAgeS` (default 600) and no more than `clockSkewS` in the future,
or the job halts (`STALE_CANDIDATE`). A delayed job or a late manual retry therefore cannot turn an old snapshot into a current-looking receipt, even on an empty board. The interval logic uses the
previous comment's `created_at` (delivery time), never its observation time; the two are kept apart on purpose.

## Failure policy: when to stay quiet, when to post, when to fail

| Situation | Result | Why |
| --- | --- | --- |
| No previous comment, or the newest is unusable | post | Silence about an ALERT is the dangerous direction. |
| The comment list cannot be read, is malformed, or is shorter than the comment count | HALT (job fails visibly) | Posting blind is the flood this design removes; a half-read thread could also hide the real previous state. |
| The thread is at or above `capacityLimit` (default 2400 of an assumed 2500 cap) | HALT | Fail visibly before the board fills and the monitor silently stops. Someone must rotate the destination. |
| The previous state is unusable (not parseable, or future-dated) and `unusableMaxPerDay` (default 3) unusable monitor-stream comments already exist within the last 24 hours | HALT (`PREVIOUS_STUCK`) | If GitHub ever returns a body this parser refuses, every tick would otherwise post (the 4 an hour schedule never reaches the cap of 8). A first live run must compare the stored body byte for byte before activation (O6). |
| The hourly cap (`maxPerHour`, default 8 monitor-stream comments in the last hour) is reached | quiet skip (`RATE_CAP`) | Bounds a flapping status or a stuck loop; the next run compares again against the newest posted state. |
| Bad config, invalid candidate, a stale or future-dated candidate, an id reused with a different state, a clock that is not a positive safe integer | HALT | Never guessed, never discarded. |

`RATE_CAP` can hold back a changed ALERT. At the 4 an hour schedule that needs manual dispatches or flapping, and the next tick after the window frees posts it because the state still differs: a bounded delay, not a loss.
`decide()` alone is not a sender gate: it normalises a missing final newline, whereas `validate-comment.mjs` (run first in the same job) refuses such a file.

The module never throws (`decide(null)` halts with `INTERNAL`) and prints only reason codes from three closed lists, so nothing read from the board can
reach `$GITHUB_OUTPUT`. Exit 0 is a decision (post or quiet skip); exit 3 is a halt.

## The draft workflow

The send job now runs, in order: validate the comment; read the issue's comment count; read the whole thread with `gh api --paginate` into a file, then slurp it
with `jq -s` in a separate command (so a failing read is not hidden behind a pipe); run `decide-post.mjs` into the step output; and post only when
`steps.decide.outputs.post == 'true'`, with the same exact-bytes `jq -Rs ... | gh api --input -` as before. Both jobs remain `if: ${{ false }}` and the file stays outside
`.github/workflows`.

**Default shell.** No step sets `shell:`, so each `run` is GitHub's default `bash -e {0}`: errexit but no pipefail. The draft is written for that: every
command whose failure matters is on its own line, nothing important travels through a pipe, and there is no `|| true`. The one pipe left is the final
post, where the API call is the last command. Whether to add `shell: bash` (which adds pipefail) is a question for the O5 reviewers.

## What this is and is not: latest-state delivery, not incident delivery

The board preserves successful posts only, and this design compares each run with the newest successful post. So it is **latest-state-only**. If an ALERT send fails and the next run sees a
recovered system, no record of the failed alert survives: the next run compares OK with the last successful post (also OK) and stays quiet, and that incident is never delivered. A failed send is a
failed workflow run, which is visible in Actions, but that is not a durable undelivered-alert obligation. Nothing here is an outbox, a replay queue or a guarantee that every observed failure reaches the owner,
and successful-post dedup must not be described as one. If the owners need incident delivery, that needs a durable store this draft does not have (for example a second record written BEFORE the send and
cleared after it) and a new design; it is raised as part of O4 and is not implemented here.

## What the six-hourly receipt can and cannot show

The OK receipt cadence is a presence signal, not a liveness check on a 15 minute schedule: a dead monitor is noticed after hours, not minutes. O6 therefore has to observe RUNS, independently of this
workflow: that each scheduled run happened and finished, including runs whose decision was a quiet skip, `RATE_CAP`, a capacity halt, an unavailable list or a stale candidate. To make that possible
without reading board text, the decide step writes its closed-token decision (`post=`, `reason=`) to the job summary of every run, success or halt. Concurrency covers only this workflow's own group, not other writers to the board.

## Historical versus live evidence

The reader's non-empty path has been exercised in two different ways, and they must not be merged into one claim:

- **Fixtures.** ABI results generated with viem from the CreditDesk ABI, decoded by this code in the offline tests. Deterministic, repeatable, source evidence.
- **Historical chain evidence, as reported by OpenAI on the board and not reproduced by me.** A read-only run against ARCHIVED chain state at block
  57458800, with a non-empty queue and a 695 s wait. It shows the reading route and the non-empty extraction worked against past state. It is historical:
  it is not a live run, says nothing about the deployed bytecode today beyond that block, and says nothing about officer liveness or uptime.
- **Live evidence** would be a run against the current head of Base Sepolia while a real applicant is waiting. None exists. The monitor's acceptance
  lines must not cite the historical run as if it were live.

## What CreditDesk can and cannot do (and why the duplicate refusal exists anyway)

CreditDesk cannot list an applicant twice: applicants are pushed once, guarded by the index1 check. The reader nonetheless refuses a `pending()` result
that contains the same address twice (`PENDING_DUPLICATE`, case-insensitive), because a duplicate could only come from a wrong decode or a wrong node, and counting it
twice would inflate the pending count behind a plausible reading.

## NOT covered

- Nothing has run in GitHub Actions. The `gh api` queries, the `--jq` filter shape, the `github-actions[bot]` login of comments posted with the repository token,
  `created_at` precision and the `.comments` count field are written from GitHub's documented API and checked only for the jq syntax and shape locally.
- The 2,500 comment cap is an assumption carried from the board history; the limit itself was not looked up again here.
- Reading the whole thread costs one request per 100 comments every run (up to about 24 near the capacity limit). That is within the repository token's limits but is
  a cost the owners should know about.
- A person with write access can delete or edit monitor comments. Deletion resets the state (one extra post); an edit makes the comment fail validation (one extra post).
  Neither can silence an ALERT.
- The hourly cap lags a real change when it fires (it now counts the monitor's stream only): the change is posted by the first run after enough older monitor comments age out of the hour.
- Missed runs are invisible to this design. The independent watcher (O6) is still required and still unaccepted.

## Review history

Hermes's exact-head ACCEPT of 682cd136 (PR 476 comment 6877454092, source only, non-blocking notes) is for the earlier head and does not cover later heads. Its notes are addressed: repeated unusable previous state now halts (`PREVIOUS_STUCK`), `RATE_CAP` delay and the fact that `decide()` is not a sender gate are stated above.

OpenAI's independent review of 682cd136 (PR 476 comment 6877440773) found: the minute-resolution id collision, the shared bot identity consuming the cap, stale snapshots posting as fresh receipts, and the
latest-state-only delivery limit. The first three are fixed above; the fourth is stated as a limit. The review also asked that fixes introduce no raw board text into logs, outputs or the sender: unchanged (closed tokens only).

## Tests and mutation check

`node test-dedup.mjs` (212 checks) covers the config ranges, the read-back validator against the sender gate, the full decision matrix with boundaries, trust of authors and of the monitor's own stream,
listing validation, the capacity and rate limits, id retries and collisions, snapshot freshness, a two-day simulation of the 15 minute schedule (a steady OK posts a receipt about every 6 hours, a steady ALERT about hourly), the CLI wrapper
including a hostile or inconsistent decision, and structural checks of the draft workflow. `node test-monitor.mjs` is 256 checks (duplicate-pending refusal and the second-resolution id added).

Mutation run over the new and changed code, baseline printed first (256 and 212 passing): 90 of 91 mutants caught in my own run, not reproduced by anyone else. The one survivor, "missing observation time ok", is an equivalent mutant: removing the
explicit `atMs === null` test changes nothing observable, because `nowMs - null` coerces to a huge age and the budget check halts anyway; the explicit test is kept so the intent does not depend on coercion. History: the round before the review
caught 67 of 67 (first run 58 of 71); the run after the review fixes first caught 81 of 85, and its three killable survivors (a status difference under a used id, the id still at minute resolution through `runOnce`, a missing `set +e` in the decide step) were
fixed by adding tests, not by weakening any. The final round added the `PREVIOUS_STUCK` guard (from Hermes's note on repeated unusable previous states) and its six mutants; two survivors there were fixed with tests.
