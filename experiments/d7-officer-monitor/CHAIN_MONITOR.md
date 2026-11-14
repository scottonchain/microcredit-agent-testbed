# Chain-only officer monitor: reader, adapter and scoped acceptance request (DRAFT, source only)

Status: draft for review, stacked on PR 473 (`../d7-officer-collector/`) and PR 470. Nothing here has been run against a live node, no
workflow is active, no credential, signer, wallet, host or spend exists because of it. It is not an acceptance of any officer runtime,
not hosting, and not a route around the held merges of PRs 456, 458 and 464. Selected by OpenAI on tb#462 (comment 6874000762):
public Base Sepolia RPC, board 462 as the routine public status destination, approved static sanitized health metadata only, a draft
workflow that stays unactivated.

## What it sees and what it does not

It sees CHAIN SYMPTOMS only: whether the CreditDesk pending queue can be read consistently, how many applicants are waiting, and how
long the oldest has waited. It does not see the officer log, the heartbeat, the runtime hash, held replies, model failures or the
journal. It therefore complements the host collector (PR 473) and never replaces it, and a healthy reading here proves neither officer
liveness nor correctness of any reply. It is a host-independent "is a waiting applicant being served" signal.

## The reader (`reader.mjs`)

One snapshot is one provider, one chain and one block: check `eth_chainId` equals 84532; read the latest block (number, hash, time);
call `CreditDesk.pending()` and, for each pending applicant, `thread(applicant)` and `unanswered(applicant)` with the block parameter pinned to
that block number; read the block hash again by number and require it to be unchanged; return only times.

**Request time = the OLDEST unanswered message, found by thread order, not by comparing timestamps.** The unanswered suffix is every
message after the latest officer message (`from` 1) in the thread. A pending applicant must have a non-empty suffix; its length must be at most 3
and must equal `unanswered(applicant)` read at the same block; the request time is the time of the first message in the suffix. A fresh
follow-up therefore does not reset a stale first request (an earlier version of this reader used the NEWEST applicant message, which would
have hidden a stalled demo as soon as the borrower wrote again; found by OpenAI's review of c3243b1c). Several messages can share a block
timestamp, so timestamps are only validated (non-decreasing in thread order, none after the block's own time), never used to decide who
answered what. A pending list that contradicts its thread (no unanswered suffix), a disagreeing `unanswered()` or any bad time is a failure.

ABI results are decoded strictly (exact length, in-bounds offsets, padded strings fully present, at most 80 messages, `from` 0 or 1, time
under 2^40); message text is bounds-checked and discarded, applicant addresses are used for the calls and dropped. Selectors `0xe20ccec3`
(`pending()`), `0xd0aac15e` (`thread(address)`) and `0x1bee4aef` (`unanswered(address)`) were computed from the CreditDesk ABI and are
checked against the fixture generator's output.

**Contract provenance (source evidence).** `experiments/d7-live/contracts/CreditDesk.sol` at PR 458 head `9c181672`, blob
`3d5034349ec58096733ead7d50a633a867ee165d`: `Msg { uint8 from; uint40 at; string text; }`, `at = uint40(block.timestamp)` (seconds),
`MAX_MSGS` 80, `MAX_UNANSWERED` 3, `say()` appends an applicant message and increments `unanswered[applicant]`, `reply()` appends an officer
message and resets it to 0, `pending()` lists applicants whose `unanswered` is above 0. This closes the timestamp-units question as SOURCE
evidence; it is not proof that the deployed bytecode equals this source, and it is not a live non-empty run.

Providers are tried in order (default: primary `https://base-sepolia-rpc.publicnode.com`, fallback `https://sepolia.base.org`), each
as a whole with two attempts and a bounded backoff (500 ms). A failed snapshot restarts entirely on the next provider; fields are never
combined across providers or blocks, and an unavailable queue is never an empty queue. Endpoint URLs must be https with no credentials,
query or fragment, so no key can sit in a URL.

## The adapter (`adapter.mjs`), the one message that may leave, and the CLI

`chainOnlyCheck` runs the snapshot through the collector's validation (fresh, bounded, block-bound evidence) and raises PENDING_AGE
when the oldest request exceeds the budget (default 600 s). `boardMessage` builds the only thing that may leave: a fixed-shape TM2
message whose text is built from a template and whitelisted values:

`Officer chain monitor <OK|ALERT> (<codes>): block <n>, pending <n>, oldest pending <n> s, reader <primary|fallback|none>, at <UTC time>. chain symptoms only: no officer log, heartbeat or runtime hash is seen.`

Approved fields requested: status, alert codes (from the fixed table), block number, pending count, oldest pending age in seconds,
reader label, snapshot time. No hash, address, URL, applicant data or free text. `validateBoardComment` is the sender-side gate: exact keys, exact
shape, a text pattern built only from that template, and CANONICAL BYTES (the JSON text must equal `JSON.stringify` of itself, which refuses duplicate keys, escaped keys and spacing tricks, so the bytes posted are exactly the bytes validated); anything else is refused. The posted body must keep its final newline, so a future dedup design must not reuse this validator unchanged on bodies read back from the board. `run-chain-monitor.mjs <config>` prints the validated
comment and nothing else (exit 0 OK, 2 ALERT, 3 invalid config or message); it posts nothing. `validate-comment.mjs <file>` is the gate as a command.

## The draft workflow (`draft-workflow/officer-chain-monitor.yml`) is NOT ACTIVE

It lives outside `.github/workflows`, and both jobs are also disabled with `if: ${{ false }}`. As drafted it would run every 15 minutes
with a snapshot job that has `contents: read` only, then an isolated sender job with `issues: write` that re-validates the comment before
posting the exact validated bytes to board 462 with the repository token (`jq -Rs` into `gh api --input -`, not command substitution). The snapshot job no longer swallows failures with `|| true`: exit 0 and the ALERT exit 2 continue, any other exit fails the job visibly. No wallet secret, no signer, no pull-request or comment trigger. The existing
signer-capable comment launcher is `if: false` and is not touched. Dedup across ephemeral runs is now designed, implemented as a pure tested decision and wired into the draft send job (see `DEDUP_DESIGN.md`); O4 is still NOT
ACCEPTED, and O6 must exist before activation. A scheduled job cannot detect its own missed dispatch, so something else must watch for missing receipts.

## Scoped operating-owner acceptance request (separate from the officer host and from the held merges)

| Line | Question | Decision | By | Date |
| --- | --- | --- | --- | --- |
| O1 | Named operating owner for this read-only monitor only | NOT ACCEPTED | | |
| O2 | The approved health fields above, and board 462 as their destination | NOT ACCEPTED | | |
| O3 | The two public RPC endpoints (no credential, no paid provider) | NOT ACCEPTED | | |
| O4 | The dedup design in `DEDUP_DESIGN.md` (written; review and decision pending), including its defaults: ALERT repeat 3600 s, OK receipt 21600 s, 8 posts an hour, halt at 2400 comments | NOT ACCEPTED | | |
| O5 | Adding the workflow to `.github/workflows` in a separate reviewed change, and its schedule. Requires O4 written and reviewed AND O6 accepted first; the Actions used are tag-pinned, and whether to pin them to commit SHAs is decided here | NOT ACCEPTED | | |
| O6 | An independent watcher of missing workflow receipts (not this workflow), accepted BEFORE O5. A failed or empty run must never read as successful monitoring | NOT ACCEPTED | | |

None of these is the officer host (PR 473 template lines b to e), a signer, a deployment or a merge allowance.

## NOT covered

- Nothing has been run against a node. OpenAI performed one read-only check at block 58601431 (empty queue) and said it proves the
  route works for an empty snapshot, not liveness, a non-empty thread extraction or uptime. The non-empty path is tested only on
  fixtures generated with viem from the ABI.
- Public endpoints are best-effort and rate limited (Base documents this); GitHub scheduled runs can be delayed or dropped and a
  schedule is paused after a long period without repository activity (per GitHub's documentation, as OpenAI verified).
- That the deployed CreditDesk bytecode equals the pinned source (the timestamp units and counters are source evidence only), and any live non-empty run.
- A provider that returns an upper-case block hash is refused (BAD_BLOCK): fail closed, so that provider is never used.
- The desk address in the example config is the current live desk; a redeployed desk needs a config change.
- Dedup, recovery messages, the hourly cap and the comment-capacity halt are designed and tested offline in `DEDUP_DESIGN.md`, not run in Actions. Without dedup a
  monitor posting every 15 minutes would fill a board in about a month (board 15 filled).
- The officer log, heartbeat, runtime identity and journal are covered only by the host collector, which has no host.
