# Scenario-wallet lifecycle

Claude (AI), 2026-11-05. Answers the board request x-20261104-scenario-wallet-lifecycle-r1 (testbed issue 15, comment 6636628939) and Codex's exact-head review of the first head (comment 6643854505). Operator requirement, as relayed: scenario wallets run from keys the orchestrator controls, and they empty back to the funding wallet at the end.

**Scope: this is a mock-tested component, not completion of the requirement.** No current runner calls it. The obligation stays open until a runner is wired (see the integration proposal below).

`wallet_lifecycle.mjs` is decision and journal logic with injected ports. It imports no network library, holds no key, never signs and sends nothing itself. A runner supplies ports that wrap its own signer. `test_wallet_lifecycle.mjs` (32 tests, in-memory chain, no network) runs with `node --test scripts/test_wallet_lifecycle.mjs` and is part of `tools/check.py`.

## The journal is private, not public evidence

It stores the signed raw transaction of every unsettled sweep, on purpose: a retry rebroadcasts the identical bytes and never signs again. Keep the file private (it is written mode 0600, atomically, with fsync of the file and of its directory). `publicView(journal)` drops the raw bytes and is the only form that may leave the runner. Errors from providers or signers are never stored, because their text can carry credentials or private endpoints; only a short code is (`port_error`, `save_error`). A test checks a credential-bearing error message does not reach the journal.

## Before a run

`verifyControl` asks the runner whether the orchestrator controls each scenario signer, without signing to prove it, and records `control_ok` or `control_check_failed`. A failed wallet is `signer_lost` before any funds are placed. Wallet ids must be non-empty, unique and well-formed, addresses must be unique, and the funding wallet may not be a scenario wallet. A loaded journal is validated the same way, so a tampered or inconsistent file is refused.

## At the end (success, failure, timeout or interruption)

`runCleanup` sweeps each wallet's test tokens to the funding wallet, then returns recoverable native gas. It is safe to call again after any interruption and always reads fresh balances (a cached `empty` or `swept` closes nothing). `terminalVerify` re-reads every token balance last, so a later deposit reopens that wallet.

| Wallet state | Meaning | Counts as |
| --- | --- | --- |
| `empty`, `swept` | nothing left, or swept and the receipt verified | emptied |
| `dust_accepted` | at or below the declared dust threshold | named exception |
| `locked_contract` | an address that is a contract holding tokens | named exception only if its address is in the approved list; otherwise open |
| `needs_gas`, `signer_lost`, `failed`, `unknown`, `pending` | not done | open |

Gas return: `returned` (including nothing left), or a `residual` at or below the return fee or the gas dust, which is a named exception. `signer_lost`, `failed`, `unknown` and `pending` are open.

Run status: `failed_cleanup` while anything is open, the gas phase was skipped or not run, or a journal write failed; `pending_reconciliation` when everything is settled but no reconciliation has been recorded; then, after a matching reconciliation, `closed` (every wallet emptied, no exception) or `closed_with_exceptions` (every remainder is a named, approved residual). A failed reconciliation is stored, persisted and sticky: `finalize` and further cleanup passes keep `failed_cleanup` until a later reconciliation matches. Skipping the gas phase is allowed but recorded, and such a run can never close.

## Idempotency, durability, unknown outcomes

- The sweep's hash and signed bytes are written to the journal before the first broadcast. If that write fails, nothing is broadcast and the wallet is `unknown`.
- A save failure after a broadcast marks the journal `persistence.failed` and the run `failed_cleanup`; the in-memory and last durable intents are kept, never overwritten by a generic unknown state. Resuming from the last durable journal checks the recorded hash, rebroadcasts the identical bytes if needed, and does not sign again.
- Only the receipt decides an outcome, and the receipt must bind to the prepared intent: from, to (the configured funding wallet), amount and nonce, and the token when given. A receipt for another recipient or amount is a `mismatch`; the wallet stays `unknown`, the run open.
- No rebroadcast happens unless the journal can be saved first: a retry that cannot persist returns `unknown` and sends nothing (tokens and gas, any number of passes).
- A receipt `mismatch` is sticky. Later passes, a reload or a zero reconciliation do not clear it; only `resolveMismatch(journal, id, {evidence, decidedBy})` records a human disposition (`dispositioned`) and that is stored and persisted.
- A reconciliation is bound to a fingerprint of the journal. If a later sweep changes the journal, the stored reconciliation moves to `staleReconciliations`, the status returns to `pending_reconciliation`, and a new cumulative reconciliation is required.
- A terminal status is never returned unless its final save succeeded: if the last write fails, `finalize`, `reconcile` and `terminalVerify` return `failed_cleanup`, and the last durable file is the recovery point.
- A journal written by an earlier version (reconciliation without a fingerprint) is migrated on load: the old reconciliation is kept as a legacy stale record and the run is `pending_reconciliation` until a fresh cumulative one is recorded.
- The journal is saved through a unique, exclusively created temp file forced to 0600 (an existing or world-readable `.tmp` is never reused), written in full with a byte-count loop (zero progress or an error fails the save), renamed into place, and the directory is fsynced.
- An error from `broadcast` is never read as failure. A sweep not yet mined after one identical rebroadcast stays `unknown`.
- Persistence is required. `runCleanup`, `verifyControl` and `reconcile` throw unless given a `save` function (an explicit `ephemeral: true` exists for tests only).

## What this does not do

It does not hold or derive keys, does not top up gas for wallets that lack it (`needs_gas` is reported with the amounts; a top-up is a separate, separately authorized transfer), does not recover anything by itself, and makes no real transfer. Historical balances are a separate matter: see `evidence/test-usdc-reconciliation-20261104/README.md` (signer control and the contract's withdrawal conditions are unverified).

## Runner adapter (disabled by default; local fixtures only)

`scripts/lifecycle_runner.mjs` is the one place that decides when the component runs around a scenario. It imports no network library, holds no key, signs nothing. A runner passes `ports` that wrap its own signer. It is off unless the caller passes `enabled: true` (the environment switch is `OMNEQUA_WALLET_LIFECYCLE=1`, read by `lifecycleEnabled`); when off it returns `{status:'disabled'}` and calls no port, creates no file and installs no handler.

Order when on: validate the roster; take a single-owner lock beside the journal; if a journal exists, **resume** (never fund again, never rerun the scenario, go straight to cleanup from the last durable intent); otherwise verify control of every signer and **refuse funding** before any transfer if one is missing (`refused_control`, complete inventory kept); record phase `funding` durably, fund (an error or crash here counts as funded); run the scenario with a timeout and an abort signal (SIGINT/SIGTERM abort it); then **always** enter terminal cleanup once: sweep tokens, return gas, re-read every balance, reconcile the funding wallet's gain against settled receipts (the funding balance before the first sweep is stored in the journal so a resumed run reconciles cumulatively). Supervision and ownership: funding and the scenario run under a timeout and the abort signal, and after a timeout or abort they must actually **settle** within `quiesceMs` before anything else happens; if they do not, the run returns `unquiesced` (journal `failed_cleanup`, phase `unquiesced_funding` or `unquiesced_scenario`), runs no cleanup, closes nothing and keeps the lock while this process lives (it is released only when the work really settles; a later run then resumes). Every port call during cleanup is bounded by `portTimeoutMs`; a hung call leaves that wallet `unknown` with its recorded intent. The journal stores the exact identity of the run (sorted roster of ids and addresses, funding wallet, chain id, token, dust and gas policy, approved contracts); a resume with any difference, or a journal without an identity, is refused before a single port call. `chainId` and `token` are mandatory. The lock is published complete (written and fsynced to a private temp file, then hard-linked into place), so no entrant sees a partial lock; a malformed lock fails closed; a lock whose recorded pid is dead is reclaimed under a guard only if it is still the same lock; release removes the lock only if it still carries our token. Only work done inside the scenario promise (or the funding call) counts as covered by the quiescence rule: work a scenario starts and forgets is outside the contract and must register with the scenario.

Exit codes: 0 closed after a successful scenario, 2 anything else, 3 closed with named exceptions, 130/143 interrupted. A resumed run never reports scenario success. Receipts must state the expected chain and token when the runner names them. `checkpoint(journal)` and `publicReport(journal)` are the only forms that may leave the process (no raw bytes, keys or error text).

Run the local tests (generated unfunded identities, a file-backed in-process chain, disposable child processes for signals and SIGKILL at each durable boundary; no live credentials, RPC or transfers):

    node --test scripts/test_lifecycle_runner.mjs scripts/test_wallet_lifecycle.mjs

What this is not: no current runner calls it, and the ports that wrap a real signer (for example the cold start's derived keys) are not written. Wiring that, funding real scenario wallets and the sweep transactions remain separately authorized, as listed under the integration proposal below.

## Integration proposal (disabled by default; nothing below is in this change)

1. **Ports adapter, disabled by default.** (The generic runner adapter above exists; this is the part that is still a proposal.) A module `coldstart-lifecycle-adapter.mjs` next to `coldstart.mjs` builds the ports from the runner's own ethers provider and derived signers (`controls` = the derived address equals the roster address; `prepareSweep` and `prepareGasSweep` sign locally and return hash and bytes; `broadcast` sends bytes; `receipt` decodes the transfer and returns from, to, amount, nonce). A `--lifecycle` flag, default off, enables it. With the flag off the runner behaves exactly as today.
2. **Wiring.** Before funding: `verifyControl` over the roster; refuse to fund if any signer is missing. Terminal handler for success, failure, timeout and SIGINT/SIGTERM: `runCleanup`, `terminalVerify`, `reconcile` against the funding wallet's before and after balances, `saveJournal` to a private path outside the evidence folder; publish only `publicView`.
3. **Tests.** The adapter gets mock-provider tests for the same failure paths (lost signer, no gas, RPC failure, duplicate retry, uncertain sweep, wrong recipient, save failure) and a test that with the flag off the runner makes no extra call.
4. **Exact authorization blocker.** Not a generic credential-bearing-code concern. Two specific approvals are missing: (a) permission to execute any workflow that reads the existing `TEST_WALLET_PRIVATE_KEY` secret for a purpose other than the already-run funding scripts (a new use of the credential, even read-only); and (b) the operator-queue authorization for the sweep transactions themselves (testnet token and gas transfers from role wallets), which the lifecycle request keeps separately gated. Neither is requested here. Writing and reviewing the adapter and its mock tests needs neither.
