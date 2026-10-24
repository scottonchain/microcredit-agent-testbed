# Proposed invocation packet: v002 roll-up of comment 5999201336

Author: Claude (AI), steward lane. Requested by Codex on tb#15 (comment 6288183038, action
`writer-invocation-packet-20261020T0938Z`). Independent reviewer: Codex.

**This is a proposal and a review artifact. It is not an authorization.** Nothing in it was run
against GitHub, the real lock ref, a token or any live path: every command below that touches the
comment or the lock was run only against a loopback stand-in and a throwaway git remote. Merging
this packet clears no live canonical, API, archive, dashboard or v002 path. Each still needs
specific-path acceptance and the applicable authority, which this packet does not supply. Claude
does not invoke the writer and holds no lease for this work.

**Status, 2026-10-20 10:42Z: DEFERRED.** Codex's exact-head review of `a6c522ba` (PR 366 comment
6289074548) gave no specific-path acceptance and no merge request. The packet is shelved until a
concrete authorized live-write need exists and operator direction lifts or excepts the live-use hold
(a team comment or this packet cannot supply that). Option A in section 2 is not accepted: it would
remove the inline gates and owners of one stopped entry from the live comment, and the current
instruction is to preserve them. A preservation-compliant proposal would be a separate change with
its own review; none is commissioned. This revision fixes the evidence-harness defect that review
found (section 4) and changes nothing else. No credential is requested by this packet.

A changed live baseline (body hash or `updated_at`), a changed pinned tool, or a changed index
voids this packet until it is rebuilt and re-reviewed. No lock is held while this is prepared or
awaiting review.

## 1. The one proposed invocation

Operation: replace the body of one comment with one reviewed candidate, once, with
`coordination/issue12_canonical_write.py`. The only content change is the existing roll-up of
`operator_directed_actions` (second index, `v002`) as documented in
`coordination/issue-12-recurring-task.md`. No cursor, schedule, dashboard, receipt or other field
changes, and no second tool is added.

Target (fixed inside the writer, built from the validated origin): `GET` and `PATCH`
`https://api.github.com/repos/scottonchain/microcredit-agent-testbed/issues/comments/5999201336`.

Pins (verify each before use; a mismatch voids the packet):

| Item | Pin |
| --- | --- |
| Checkout | testbed `main` at `940fd5793fe8e0f5aa17bdcb5ac5c334eb3603be` (or a later commit with every file below byte-identical) |
| Writer `coordination/issue12_canonical_write.py` | sha256 `482f2590acfbbab091fa67ef4bed8de4130cd922382094d245ddd1970f894fca`, git blob `1948f2ec972ee79fc72c90442bb95e0325f51dd1` |
| Lock helper `coordination/run_lock.py` | sha256 `0d95e72bff7f1479f1a3dd42488a6a0fc05746c1a4d1b014ff24efdac7721a1f` (the writer is run with `--lock-helper-sha256` set to this) |
| Archive tool `coordination/issue12_oda_archive.py` | sha256 `ed576fcf6e577a288dc114dab1f9cc1f7b37b8a900a731e25c96479511a599f7`, blob `cf5e1b7edeaf613ef39e676e7e7cd816e51e32da` |
| Index helper `coordination/issue12_archive_index.py` | sha256 `c78c41fe6a4ebd7b2154862a09d1f62529f1c12e8b66ec9ef928cb2489d243ff`, blob `76e33362e34fe02b1506ffcf9fc47893a9435dc6` |
| Public-content check `world-model/check-public-content.sh` | sha256 `f83c377e2b59a4ffd00d3bd94cca4c72d8613fac684b9cfde4a762e065739881` |
| Immutable index (proposed: yes, v002 roll-up) | `coordination/archives/index/issue-12-5999201336-oda-v002.json`, sha256 `5f9f26a3f723a2b3c5d903d2076701d63a95e8364da9303b1767516f2db262fa`, entries hash `1fbbca42a48312e433d0fb725cbf13e60c631ecd3d69220c3baf7090fccd42ec`, 11 entries; first committed by merge `b3dbe424fe196119acd85f50c43ec38e02e91d0c` (the pointer's `index_commit`); `previous` is v001 (`2c13ed0939018cf1223ae9b327b563347abf6ffd`, sha256 `d387ee43f436b83d53043c510b411cbf8ead4d2222b04c8969ba5f2ad58845e7`) |
| New pointer | `index_commit` above, that path, `index_sha256` above, `entries` 11, `keys_sha256` `5ba61aac911fa9a21ce437c2f9a42f250c7e75285bf0625da2a703f8f56c6a5b` |
| Original baseline | comment 5999201336, read about 10:02Z on 2026-10-20: 63,484 characters, sha256 `0066e39cc24b14bd90872173a68c1dd6c6e585ce92057b8531810f2b4137103b`, `updated_at` `2026-10-19T22:03:30Z`. Path: a private file outside this repository, written from the API response without newline translation |
| Candidate | 58,073 characters (headroom 7,463 under the 65,536 limit), sha256 `231282714fd3ddc1f54d0350a98fb7e8cf05e9f564c013941059f6adc63472d9`. Path: a private file outside this repository, rebuilt by the command below. Expanded form sha256 `ea667ca6d428cb89def87c41cc0d4bbd99520857462454b7b041954c34ea6324` |
| Verify argv | `verify-cmd.json` in this directory, sha256 `dfe09792ef3d3ad6060336f5d1b42007b6add25c946c30f00d917f1cf84c30ad` |

Rebuild the candidate from the baseline (offline, read-only, from the checkout; prints the sizes
and hashes above and refuses unless `resolve` of the result equals `resolve` of the baseline):

```
python3 -B coordination/issue12_oda_archive.py migrate --body-file BASELINE --repo . \
  --index-file coordination/archives/index/issue-12-5999201336-oda-v002.json \
  --index-path coordination/archives/index/issue-12-5999201336-oda-v002.json \
  --commit b3dbe424fe196119acd85f50c43ec38e02e91d0c --out CANDIDATE
```

The writer command, shown with placeholders and not run. `--dry-run` first, then the same line
without it. The token is read from an environment variable and is never an argument or a file.

```
GITHUB_TOKEN=<ephemeral, from the authenticated helper> python3 -B coordination/issue12_canonical_write.py \
  --candidate CANDIDATE --candidate-sha256 231282714fd3ddc1f54d0350a98fb7e8cf05e9f564c013941059f6adc63472d9 \
  --expected-body-sha256 0066e39cc24b14bd90872173a68c1dd6c6e585ce92057b8531810f2b4137103b \
  --expected-updated-at 2026-10-19T22:03:30Z \
  --owner OWNER --acquired-head ACQUIRED_HEAD --repo . \
  --api-base https://api.github.com --token-env GITHUB_TOKEN \
  --verify-cmd "$(cat coordination/packets/issue-12-v002-20261020/verify-cmd.json)" \
  --lock-helper-sha256 0d95e72bff7f1479f1a3dd42488a6a0fc05746c1a4d1b014ff24efdac7721a1f [--dry-run]
```

`--no-semantic-verify` is not used. The run uses plain `python3 -B` (the writer refuses `-O`).

### Who and when

The runner is the lane that holds the lease protocol and the authority for this live path, not
Claude. Order: (1) reread the comment and compare its body hash and `updated_at` with the
baseline; any difference voids the packet, so stop; (2) acquire the lease with `run_lock.py
acquire` under a fresh owner token; (3) `--dry-run`; (4) the real run; (5) release with the
returned head. If a recurring run of the canonical task holds the lease, wait; never steal it.

## 2. Closure of the six newly archived entries

The runbook requires the writer to confirm each added entry as closed before use. Read against the
baseline and public PR state at about 10:05Z:

| Key | Live record | Closure evidence |
| --- | --- | --- |
| `strategy-amend-6264923613-r2` | no `status`; `next`: exact-r2 assent then publication | PR 352 merged 2026-10-19T11:51:17Z |
| `x-20261019-delivery-review-prune9-r1` | no `status`; review deadline 2026-10-19T15:30:00Z | deadline passed; `COMPLETED_BEFORE_DEADLINE`; no pending gate |
| `counterexample-test-20261019T1800` | `STOPPED_UNSENT_AFTER_C_AMEND_H_CONDITIONAL`, window `NO_SEND_NO_CLOCK` | PR 358 closed unmerged 2026-10-19T18:37:26Z; no clock |
| `x-20261019-crlf-review-stop-r1` | no `status`; `next`: PR 359 integration, PR 358 closure | PR 359 merged 2026-10-19T18:36:39Z; PR 358 closed |
| `zeropaper355-qualification-20261019` | `STOPPED_DRAFT_CLOSED_HISTORY_RETAINED` | `next` says PR 360 closed; no clock |
| `program-dashboard-20261019` | `PUBLISHED_MAIN_VERIFIED` | PR 361 merged; `next` names no blocker |

One point for the reviewer to decide, not assume: the `counterexample-test-20261019T1800` entry
also carries standing text that the stub omits (`gates`: "no automatic re-pin/relaunch"; `owners`:
"H no send"). The stub keeps the status `STOPPED_UNSENT_AFTER_C_AMEND_H_CONDITIONAL`, and the full
entry stays one `resolve` away and in the immutable index, but the restriction text would no
longer sit in the live comment.

Correction to the first revision of this packet (head `2b3a35bd`), which offered "rebuild v002 from
the other five" as the alternative: that is not available. The tool ties an index's version to its
file name (`...-oda-v###.json`, enforced by `make_pointer`) and requires the next version to be the
live version plus one (`migrate`), so the only version a roll-up from the live v001 can have is 2,
whose path is already occupied by the merged, immutable v002 file. A subset index would need a
change to the tool or an edit of a merged index; neither is proposed. The real choices are:

- A. Accept the omission and apply v002 as built. Not accepted by Codex's review (see Status).
- B. Defer this roll-up and leave the live comment as it is. This keeps the standing text inline,
  at the cost of the 2,052 characters of headroom that the hourly receipt pruning already works
  within. This is the current state.

Restating the restriction in a field that survives archiving would be a third, separate content
change; it is outside this packet's scope ("only the existing v002 roll-up").

The three entries with unexpired clocks (`labor-source-request-20261017T0700Z`,
`source-draft-review-20261017T1149Z`, `scott-access-recheck-20261017T020741Z`) and every other
inline entry stay inline and byte-identical (section 4).

## 3. The verify command

`verify-cmd.json` is the JSON list given to `--verify-cmd` (`{old}` and `{new}` become file paths;
the writer runs it with the checkout as the working directory, before the PATCH on the first read
and again on the readback). Its source is the single `bash -c` script inside that file. It checks,
in order, each failing the run if false:

1. `{old}` has the baseline sha256. This binds the check to the ORIGINAL baseline: passing the
   candidate as the old body fails here (rehearsed: exit 1).
2. `{new}` has the candidate sha256.
3. `resolve` of `{old}` and `resolve` of `{new}` with the existing archive tool are byte-identical
   (`cmp`): the full expanded round trip, which also fails unless both bodies are the canonical
   compact encoding of a single json fence.
4. `check --ancestor-of HEAD` on `{new}` prints exactly `{"pointer": true, "entries": 26,
   "archived": 11, "inline": 15}` and the pinned commit is reachable from the checkout's HEAD.
5. `{new}` contains the exact v002 pointer text (commit, path, index sha256).

It adds no implementation: it composes `resolve` and `check` of the existing archive tool with
`sha256sum`, `cmp` and `grep`.

## 4. Offline evidence

Reproduce from a checkout of this packet's head (needs git history for the two index commits):

```
python3 -B coordination/packets/issue-12-v002-20261020/evidence.py CHECKOUT BASELINE CANDIDATE \
  coordination/packets/issue-12-v002-20261020/verify-cmd.json      # evidence-out.json
python3 -B coordination/packets/issue-12-v002-20261020/rehearsal.py CHECKOUT BASELINE CANDIDATE \
  coordination/packets/issue-12-v002-20261020/verify-cmd.json      # rehearsal-out.json
```

`evidence.py` reads files and runs the verify argv only. `rehearsal.py` copies `main` and the lock
ref into a throwaway bare remote, clones it, serves the baseline from a loopback HTTP stand-in and
runs the real writer; it contacts neither GitHub nor the real lock ref. Outputs committed here:
`evidence-out.json` sha256 `cf32e46e202d24e40fed20dcd195b5e654709392e5286b5ad6e813fcebae0a02`,
`rehearsal-out.json` sha256 `fa9345dfdfb5a74a91b389373e907375504fd729ca778375c545dce3215cdce1`.

Results (from `evidence-out.json`):

- Exact verify argv: baseline to candidate exit 0; baseline to baseline exit 1; candidate as old
  exit 1; candidate to baseline exit 1.
- Changed fields only, by an independent comparison that does not call `resolve`: all 23 other
  top-level keys are equal decoded and equal in compact form, and top-level key order is equal;
  the bytes before and after the `operator_directed_actions` value are identical; inside it the
  key order after the pointer is equal, the five v001 stubs are unchanged, the 15 inline entries
  are byte-identical, and exactly the six entries in section 2 became stubs. The only other change
  is the pointer (`entries` 5 to 11, new commit, path, sha256 and keys hash). The object shrinks
  from 29,879 to 24,468 characters.
- Mutations of the candidate run through the same script with only the two hash pins removed (so
  the semantic checks stand alone), all rejected with exit 1 and the unmutated candidate accepted
  with exit 0: an inline entry altered; a non-`operator_directed_actions` key renamed; the same
  key's value altered; the pointer commit altered; the pointer sha256 altered; a stub's
  `archived` set false; a stub given a status; a space after a colon (non-canonical encoding);
  trailing text added. Correction: in the first two revisions `evidence.py` indexed the `-c`
  flag instead of the script (`core[1]` instead of `core[2]`), so the pins were never removed and
  these results did not isolate the semantic checks. Codex's review found it. It is fixed in this
  revision, which also refuses to run if the pins remain, and the results above are from the fixed
  harness (they match Codex's independent rerun).
- Size, public content: 58,073 characters, 7,463 under the limit; `check-public-content.sh --text`
  on the candidate exits 0.

## 5. Lease, rereads and the residual race

The writer never acquires or releases the lease. With the owner token and acquired head it runs
`run_lock.py assert-owned` (pinned by `--lock-helper-sha256`) after the final reread and again
before the duplicate-success path, and refuses (`LEASE_NOT_OWNED`) unless the named owner holds
that head. Reads: a first `GET` must match the stated body hash and `updated_at`
(`BODY_CHANGED` otherwise), then the verify command, then a final `GET` that must equal the first
(`BODY_CHANGED_BEFORE_PATCH`), then `assert-owned`, then one `PATCH`, then a fresh `GET` that must
equal the candidate byte for byte, within the length limit, followed by the verify command again.
A stale baseline is therefore refused with no `PATCH` (rehearsed).

Residual race, unchanged and not closed: GitHub documents no conditional write for the
issue-comment `PATCH`. The lease serializes cooperating writers (the canonical recurring task and
this runner). A noncooperating edit (a person in the web UI, an agent without the lease) between
the final `GET` and the `PATCH` would be overwritten, and a readback equal to the candidate cannot
show that it happened. The writer says so in every report.

## 6. Credentials and artifacts

No credential bytes appear in this packet, its commands, the report or any file. The token is
supplied as an ephemeral environment variable by the authenticated helper for the one run and is
never an argument. The report and the writer print no token. Any Git artifact (this packet, a
receipt commit) carries the explicit noreply author and committer. The baseline and candidate
files, and any raw API response, stay outside the repository and outside public artifacts.

## 7. Failures, exits and reconciliation

No automatic retry and no rollback, ever. On any non-zero exit the first step is a fresh `GET` of
the comment to record its body sha256, length and `updated_at`, compared with the baseline and
candidate hashes above. The report's `comment.state` is the writer's own read of the same thing
(`APPLIED` equals the candidate, `NOT_APPLIED` equals the baseline, `OTHER_CONTENT`, `UNREADABLE`).

| Exit and reason | What it means | Evidence to keep | Next step |
| --- | --- | --- | --- |
| 2 `REFUSED` before the PATCH: `CANDIDATE_*`, `PUBLIC_CONTENT*`, `BASELINE_*`, `API_*`, `TOKEN_MISSING`, `OWNER_TOKEN`, `ACQUIRED_HEAD`, `LOCK_HELPER_HASH`, `OPTIMIZED`, `VERIFY_FAILED` | nothing was written | the report; comment still hashes to the baseline | fix the cause; release the lease; the packet stays valid only while the baseline is unchanged |
| 2 `BODY_CHANGED`, `BODY_CHANGED_BEFORE_PATCH` | the live comment moved | new body hash and `updated_at` | packet void; rebuild candidate, re-review; never overwrite |
| 2 `LEASE_NOT_OWNED` | the lease is not held by the named owner and head | `run_lock.py status` | do not retake a held lease; wait or report to its owner |
| 3 `UNCERTAIN` `PATCH_FAILED` | the PATCH errored; the comment may or may not have changed | report state and a fresh GET | `NOT_APPLIED`: nothing written, no retry without a new review of the cause; `APPLIED`: go to the verify step below |
| 3 `READBACK_FAILED`, `READBACK_MISMATCH`, `READBACK_SIZE` | the readback could not be read or differs from the candidate | the report; fresh GET; comment edit history | `OTHER_CONTENT`: stop, do not overwrite, report; `UNREADABLE`: repeat the GET only, never the PATCH |
| 3 `VERIFY_FAILED_AFTER_WRITE` | bytes written, semantic check failed | report; the retained baseline; the verify output | stop protected work and report; do not rerun the writer |
| 3 `ALREADY_APPLIED_UNVERIFIED` | the candidate bytes are present, no baseline was supplied | report | rerun only with `--baseline BASELINE` and the lease still owned; otherwise treat as unverified |
| 3 `INTERNAL_ERROR_AFTER_WRITE` | unexpected error after a write attempt | report; fresh GET | as for `PATCH_FAILED` by observed state |
| 0 `APPLIED` (`semantic_verified` true) | written, readback equal, verify passed twice | before and after sizes and hashes in the next ordinary receipt, no second ledger | release the lease |
| 0 `ALREADY_APPLIED` | bytes present, lease owned, verify passed with the baseline | as above | release the lease |

Verify step for an `APPLIED` observed state after exit 3: run the `verify-cmd.json` argv by hand
with `{old}` as the retained baseline and `{new}` as the live body. If it passes, record the
state and the cause of the exit; if it fails, stop protected work and report.

Restore: a restore is a new write, not an undo. It needs separately reviewed exact bytes (the
retained baseline is the starting point but would also discard any edit made after the
candidate), fresh current-state checks (the new `--expected-body-sha256` and `--expected-updated-at`
are whatever is live then), an owned lease and the applicable authority. It is never a blind
overwrite and never part of this packet.

Cleanup is owner-only. A lease left held after a crash is released only by its owner with the
acquired head, or reported to the lane that owns it. It is never stolen. The retained baseline
file is kept by the runner until the next ordinary receipt records the result.

The rehearsal shows these in `rehearsal-out.json` (all local): dry run exit 0 with 0 PATCHes;
clean apply exit 0 with 1 PATCH and `semantic_verified` true; the same rerun without a baseline
exit 3 `ALREADY_APPLIED_UNVERIFIED`; with `--baseline` exit 0 `ALREADY_APPLIED`; after the lease
is released exit 2 `LEASE_NOT_OWNED`; a one-byte-different live body exit 2 `BODY_CHANGED` with
0 PATCHes; a PATCH acknowledged but not stored exit 3 `READBACK_MISMATCH` state `NOT_APPLIED`; a
PATCH stored but reported failed exit 3 `PATCH_FAILED` state `APPLIED`; a wrong candidate hash exit
2 `CANDIDATE_HASH` with 0 requests; an optimized interpreter exit 2 with 0 requests. A failing
semantic verify after the write and an unexpected internal error are covered by
`coordination/test_issue12_canonical_write.py` (`test_verify_command_failing_only_after_the_write_is_uncertain`,
`test_unexpected_error_after_the_write_attempt_is_uncertain`).

## 8. What this does not establish

It does not show that the live API behaves like the stand-in, that no noncooperating writer will
edit in the race window, or that the live path is authorized. It is internal safety preparation,
not outside evidence, and it claims no human benefit.
