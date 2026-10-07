# Readiness link: final mapping (action:readiness-link, due 2026-10-08 16:00 UTC)

Owner: Claude Code (agent:claude). Status: FINAL, written 2026-10-07 12:28 UTC, a day before its due time. Rechecked by the Codex lane at contract `460875c` (issue 15 comment 6037848516; `coordination/relayer-readiness-recheck-20261007.md`): the unit suites ran and pass, the crash rehearsal was not rerun. Deliverable of the action: map the risk note's assumptions and the receipt and retry failure classes onto one existing contract or testbed readiness requirement, stating exactly what risk is reduced and what remains unproved. The interim report (`coordination/readiness-link-interim-20261007.md`) holds the first mapping; this final replaces its "missing prerequisites" with what now exists. Every number below is one a script produced; none is estimated here.

## The one requirement

`docs/DEPLOYMENT.md` in the contract repository, approval gate 2: "Owner approval. The project owner approves the exact environment (the parameter values below) and the saved dry-run output." Both inputs land in that gate: `RESERVE_BPS` (the reserve share the owner approves) and `RELAYER` (the relayer account, if any). No new requirement is proposed. What changed since the interim is that the `RELAYER` row now has its requirements written where the gate lives: the section "What the relayer service must satisfy, if one is named" (contract main 6eef822, model `ev:readiness-link-runbook`).

## Input 1: the risk note, and `RESERVE_BPS`

Unchanged from the interim, and unchanged in its inputs: the pooling check (`pricing-and-reserve/scripts/pooling_subadditivity.py` at theory 551a4a5) shows that at the paper's sampled parameters the pooled 99% quantile is at most 1.00 times the cohort sum and the pooled expected shortfall at most 0.99 times, with the exact two-point check (quantile fails subadditivity, expected shortfall does not) as the reason to keep expected shortfall as the fallback estimator. The current `RESERVE_BPS` is 4500, the owner's interim decision of 2026-10-05.

Risk reduced: the owner approves the reserve share knowing the pooling direction at those parameters and the estimator to use if pooling turns adverse. Unproved: the loss distribution itself (no live default data; PD 3, 5 and 10% are assumptions), correlated years and endogenous withdrawals (theory issue 6's deferred items), and the reserve-equilibrium analysis (the lending-equilibrium paper, not independently reviewed; its review windows are recorded in theory issue 3). So 4500 stays interim.

New since the interim, and relevant to what the reserve means: CI-30 (contract main ce4a93c, open, low severity, measured and not fixed). A loan's unpaid interest under a cent is forgiven at closing and a repayment is booked as interest first, so a borrower is credited dues (the reserve share of that interest) on interest it never paid in cash, and the reserve absorbs the forgiven balance first: ten daily cycles of a 38 USDC advance earned 43,700 base units of dues with no cash interest and an empty reserve, lenders' totalAssets unchanged (`test/AdvanceFacts.t.sol`, model `ev:advance-facts-ce4a93c`). Dues credit is therefore not always held by reserve cash. It does not change the reserve share the owner approves; it is a known gap in what "dues" backs, listed in `docs/CREDIT_INTEGRITY_ISSUES.md`.

## Input 2: the receipt and retry failure classes, and `RELAYER`

What exists now, for the service that would hold the relayer key (release two):

- The contract makes a duplicate meta-transaction harmless (`InvalidNonce`) and the fixture's chain cases test replay, nonce recovery and batch envelopes (`test/RelayerRetry.t.sol`, `test/RelayerRetryBatch.t.sol`).
- The relayer journal (contract main 1009e6a and after): the intent keyed by (chain, pool, signer, nonce) is fsynced before the first network call; with a local signing key the signed transaction's hash and bytes are journaled before the broadcast; a request already seen is answered from the journal; a different request under the same nonce is refused; recovery reads the receipt, then the signer's nonce; a failed read leaves an entry open; a timeout never becomes a failure.
- Checks that ran: the journal and send-order unit tests (16 and 10), run by Claude and rechecked by the Codex lane at contract `460875c`, where the whole utility suite passes 48 of 48 assertions, 26 of them journal and send-order (Codex ran the same test sources with Node v24 directly, not the exact Yarn command); and a repeatable run through the real API route on a local Anvil chain with the server killed between broadcast and receipt (`relayer:crash-check`, 15 of 15), after which the same request returned 202 while unmined and 200 once mined with one transaction. The crash run is Claude's own and was not rerun independently: Codex's environment has no Anvil.
- The design note (`coordination/relayer-journal-design.md`) maps each fixture chain and email case to what the journal does and where it is checked, and lists seven things not covered.

| Failure class (fixture) | What the relayer does | Where checked |
|---|---|---|
| Outcome unknown after a timeout | Entry stays `submitted`; never treated as failed | Units; crash run |
| Duplicate effect | Same bytes rebroadcast, never new bytes; the contract refuses a reused nonce | Units; crash run; contract tests |
| Intended effect missing at a horizon | The journal never times out into failure; a horizon policy (who decides after how long) is not built | Not covered |
| Row unresolved at a horizon | `consumed_unattributed` or `unresolved` is handed to an operator; attribution by decoding calldata is not built | Units for the states; not for attribution |
| Receipt attributed without a key born before the send | The signed nonce and the transaction hash exist before the first byte is sent | Units; crash run |
| Retry refused as in progress | The same request is answered 202 while unsettled; a different one under the same nonce, 409 | Units; crash run |
| Sweeper writes "failed" without proof | Only "abandoned": no hash at all, or the node's own statement that the nonce was consumed | Units |

Risk reduced: a relayer process that dies between submit and receipt no longer loses the binding from the signed intent to its hash, and cannot send a second transaction for it. Unproved: any run against a public endpoint or a testnet; the seven gaps in the design note (attribution of a consumed nonce, fee replacement of a stuck transaction, more than one relayer process, confirmation depth, the receipt read from the same endpoint that took the write, the weaker key of permit-only routes, and that no one outside the team has used it); the host that would run it: Hermes reports (issue 17 comment 6036631781, observed about 11:05Z 2026-10-07; model `claim:release-two-host-facts-20261007`) one small VPS with 1.6 GB RAM and about 0.55 GB available shared with its agent runtime, a TLS front that proxies only its A2A inbox, no monitoring, alerting or backup, no relayer and no relayer key (the deployer key is also pool owner, oracle and guardian and must not double as a signer), and a capacity check not yet run; Claude measured that a production build of the app peaks at 1,930 MB and the server holds 218 to 235 MB after about 330 requests (`claim:relayer-memory-measured-20261007`), so the build cannot run on that host, and no relayer was run under load; and the live relayed app itself, which does not exist: release one, the wallet-direct app, does not use the relayer.

## What the browser evidence is and is not

Hermes's browser runs (models `ev:sepolia-browser-run-*`) test the wallet-direct app, release one. They show the app's two-step flows, recovery card and stopped-step messages working against the live pool in a rehearsal by the project's own operator, with the failures kept. They are not evidence about the relayer, and not an outside user's experience.

## What this is not

Per `claim:limits`: none of the above is customer demand, financing need, revenue or human impact; reviewer and rehearsal participation establishes no credit and no default risk. The productive-commerce and lender route discussed on testbed issue 17 is separate and untouched by this report. The mapping proposes no deployment, spending or contact; the owner approves or refuses `RESERVE_BPS` and `RELAYER` at gate 2.

## For the owner at gate 2, in one line each

- `RESERVE_BPS` 4500: the owner's interim value of 2026-10-05; the risk note informs it and does not replace a reviewed calibration. CI-30 is open (dues can be credited on up to a cent of each loan's interest unpaid); it is low severity and does not move the value, but the owner should know it when reading "dues back earned credit".
- `RELAYER`: nothing to approve yet. Against the runbook section's six requirements (Codex's recheck): the journal with a local key and hash-first order is confirmed in unit scope; that nothing implies human use is confirmed in the wording; one process with one journal file is stated as a restriction but not enforced; a restart losing nothing is not confirmed end to end by anyone but its author; the acceptance of the seven known gaps, and key custody, rotation, endpoint, uptime and gas, are open. Hermes's host has no relayer key and cannot build the app (it peaks at 1,930 MB), so a release-two relayer also needs a build made elsewhere.
