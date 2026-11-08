# Follow-ups from the 2026-11-07 maintainer review

Source: Claude's maintainer review of the original readiness packet (PR 443 comment 6713075636), Parts 1 and 2. Verdict: ACCEPT as source preparation, no blocking defect. None of the items below changes that verdict; each is recorded so it is not silently dropped. Severity is the reviewer's. "Fail-closed" means the behaviour refuses or holds rather than proceeding.

## Operational

| ID | Item | Severity |
| --- | --- | --- |
| C1 | `InventoryProbe` compares the full canonical state to an installed digest, so unrelated deposits, stakes or repayments on a shared pool flip it to False until re-baselined. Fits only a quiet or private pool; scope documented in README and REHEARSAL. | medium, operational |
| A1 | `BackingBook.funding()` and `repayment()` raise "stale or future evidence" for a transaction mined while the supervisor was down for more than 15 minutes. Fail-closed (the draw stays RESERVED and counted). Needs a documented operator reconciliation step, or an operator-supplied `now` bound to the block time. | low (liveness) |
| A2 | Any other pool log or pool-cash Transfer in the same block holds the observation. Fine on the quiet testnet pool; would hold repeatedly on a busy pool. | low |
| C2 | The probes return False on any exception, with no diagnostic; log the reason to the operator-only log. | low |
| C3 | Document that confirmations times block time must stay under the 120 s freshness window, or the probe is always False. | low |

## Code

| ID | Item | Severity |
| --- | --- | --- |
| N1 | `authenticated_reader.bundle()` compares the requested hash to the provider's raw transaction ids; normalize the ids before the membership test. | low (fail-closed) |
| N2 | `DeskSnapshots.snapshot()` raises TypeError, not ValueError, if the provider has no confirmed block yet; hold instead. | low |
| N3 | The witness compares raw JSON results, which can hold falsely on L2 providers that add non-consensus fields; compare the pinned fields. | low (availability) |
| N6 | `probe_source.mjs` hashes the file and then imports it again from disk; import the bytes it hashed. | low |
| N7 | `guardedInterview` does not handle a rejecting promise from an async callback; detect thenables and hold. | low |
| N8 | `facts.backing` accepts fractions (only `repaid` and `open` are safe integers). | nit |
| A3 | `canonical_adapter.decimal_units` uses a 28-digit context and can print scientific notation for absurd amounts; reuse the 60-digit Inexact-trapping context from the PR 433 ledger. | nit |
| B2 | `BackingBook.funding()` does not normalize the loan id as `reserve_draw()` does. | nit |
| D8 | `durable.audit_canonical` compares block hashes without `txhash()` normalization. | nit |
| C4 | Bare `assert` in `replay_inventory.py` (stripped under `python -O`); `Budget.settle` raises KeyError for an unknown intent; `CanonicalInventory` checks `limit` before validating its type. | nit |

## Information (no action requested)

B1 the commitment book refuses any applicant with granted credit, unsecured or other backing; N4 the officer "pending" nonce check is best effort on public RPCs; N5 keyed RPC endpoints are unsupported by design (path must be empty or `/`); C5 registry completeness for never-used grants is a custody/issuer gate, as documented.

## Still owed outside this packet

The independent exact-head review of PR 441 `a04dba8c` (the B2 runner integration) is outstanding review debt (PR 449). The 12-row table in [RUNNER-REVIEW.md](RUNNER-REVIEW.md) is its checklist. This file does not retry, delegate or reroute that review.
