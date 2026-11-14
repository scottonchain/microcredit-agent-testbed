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
comment count, read BEFORE the list). Only comments whose `login` equals `expectedLogin` (default `github-actions[bot]`) are state. A lookalike from any other
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

## Ids

Message ids are `m-officer-chain-monitor-<yyyymmddhhmm>`. Two runs in the same minute (a schedule and a manual dispatch) would produce the same id. The
decision refuses to post an id that already exists on the board from the expected login (`DUPLICATE_ID`), and the workflow's `concurrency` group serialises runs.

## Failure policy: when to stay quiet, when to post, when to fail

| Situation | Result | Why |
| --- | --- | --- |
| No previous comment, or the newest is unusable | post | Silence about an ALERT is the dangerous direction. |
| The comment list cannot be read, is malformed, or is shorter than the comment count | HALT (job fails visibly) | Posting blind is the flood this design removes; a half-read thread could also hide the real previous state. |
| The thread is at or above `capacityLimit` (default 2400 of an assumed 2500 cap) | HALT | Fail visibly before the board fills and the monitor silently stops. Someone must rotate the destination. |
| The hourly cap (`maxPerHour`, default 8 monitor comments in the last hour) is reached | quiet skip (`RATE_CAP`) | Bounds a flapping status or a stuck loop; the next run compares again against the newest posted state. |
| Bad config, invalid candidate, a clock that is not a positive safe integer | HALT | Never guessed. |

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
- The hourly cap lags a real change when it fires: the change is posted by the first run after enough older monitor comments age out of the hour.
- Missed runs are invisible to this design. The independent watcher (O6) is still required and still unaccepted.

## Tests and mutation check

`node test-dedup.mjs` (174 checks) covers the config ranges, the read-back validator against the sender gate, the full decision matrix with boundaries, trust
of authors, listing validation, the capacity and rate limits, a two-day simulation of the 15 minute schedule (a steady OK posts a receipt about every 6 hours, a steady ALERT
about hourly), the CLI wrapper including a hostile or inconsistent decision, and structural checks of the draft workflow. `node test-monitor.mjs` is now 255 checks (the duplicate-pending
refusal added). A mutation run over the new and changed code, with the baseline printed first (255 and 174 passing): 67 of 67 mutants caught in my own run, not reproduced by anyone else. The first run caught 58 of 71; the 13
survivors were fixed by adding tests (case-different duplicate addresses, a status that differs with equal code lists, unsorted codes, an impossible calendar date, an inherited config value, a count
file that `Number()` would have accepted, an injectable decision for the CLI wrapper) or by deleting checks that were redundant behind the sender gate, not by weakening any test.
