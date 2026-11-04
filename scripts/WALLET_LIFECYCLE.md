# Scenario-wallet lifecycle

Claude (AI), 2026-11-05. Answers the board request x-20261104-scenario-wallet-lifecycle-r1 (testbed issue 15, comment 6636628939). The operator's requirement, as relayed: scenario wallets run from keys the orchestrator controls, and they empty back to the funding wallet at the end.

`wallet_lifecycle.mjs` is the decision and journal logic only. It imports no network library, holds no key, never signs and sends nothing itself. A runner supplies ports that wrap its own signer. The journal holds public addresses, roles, amounts, nonces and transaction hashes; a test checks that no key-like field is stored. `test_wallet_lifecycle.mjs` runs it against an in-memory chain (no network): `node --test scripts/test_wallet_lifecycle.mjs`, also part of `tools/check.py`.

## Before a run

`verifyControl` asks the runner whether the orchestrator controls each scenario signer, without signing anything to prove it, and records `control_ok` or `control_check_failed` per wallet. A wallet that fails is marked `signer_lost` before any funds are placed. The funding wallet may not appear in the roster and addresses may not repeat.

## At the end (success, failure, timeout or interruption)

`runCleanup` sweeps each wallet's test tokens to the funding wallet, then returns recoverable native gas. It is safe to call again after any interruption.

| State | Meaning | Closes the run? |
| --- | --- | --- |
| `empty`, `swept` | nothing left, or swept and receipt verified | yes |
| `dust_accepted` | residual at or below the declared dust threshold, listed | yes, as a named exception |
| `locked_contract` | the address is a contract holding tokens; not a wallet sweep | yes, as a named exception |
| `needs_gas` | tokens but not enough gas to send; numbers recorded | no |
| `signer_lost` | tokens but the signer is not controlled | no |
| `failed` | a recorded sweep reverted | no (a later run retries) |
| `unknown` | balance unreadable, or a sweep outcome not established | no |

Gas return is separate: `returned` or a declared `residual` (below the return fee, or signer gone) do not block; an `unknown` or `failed` gas return does. The run status is `closed` only when every wallet is in a closing state; otherwise it is `failed_cleanup` and cannot be reported as closed. `reconcile` compares the funding wallet's gain with the settled sweeps; a mismatch sets `failed_cleanup`.

## Idempotency and unknown outcomes

The sweep's hash and signed bytes are written to the journal before the first broadcast. A retry never signs again while a recorded sweep is unsettled: it reads the receipt for the recorded hash, rebroadcasts the identical bytes if there is none, and reads once more. If it is still not mined, the wallet stays `unknown` and the run stays open. An error from `broadcast` is never read as failure; only the receipt decides.

## What this does not do

It does not hold or derive keys, does not send gas to wallets that lack it (`needs_gas` is reported with the amounts; topping up is a separate authorized transfer), and does not recover anything by itself. No real transfer is made by this change. Historical balances are a separate matter: see `evidence/test-usdc-reconciliation-20261104/README.md` (nothing shown as demonstrably unrecoverable; signer control and the contract's withdrawal conditions are unverified).

## Runner integration (not part of this change)

A runner (for example `coldstart.mjs`) would: build the roster from its derived public addresses, call `verifyControl`, refuse to fund a roster with a missing signer, and in its terminal handler (success, failure, timeout, signal) call `runCleanup` with ports over its own provider and signer, `save` set to `saveJournal`, then `reconcile` against the funding wallet's before and after balances. That wiring touches a credential-bearing runner and needs its own review and authorization.
