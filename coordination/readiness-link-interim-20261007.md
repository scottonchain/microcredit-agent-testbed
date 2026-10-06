# Readiness link: interim report (action:readiness-link, 2026-10-07 12:00 UTC checkpoint)

Owner: Claude Code (agent:claude). Deliverable of the action: map the risk note's assumptions and the receipt and retry failure classes onto one existing contract or testbed readiness requirement, stating exactly what risk is reduced and what remains unproved. This interim report, written ahead of the checkpoint, gives the available evidence and the missing prerequisites; the final mapping is due 2026-10-08 16:00 UTC. Every number below is one a script in the cited repository produced; none is estimated here.

## The one requirement

`docs/DEPLOYMENT.md` in the contract repository, approval gate 2: "Owner approval. The project owner approves the exact environment (the parameter values below) and the saved dry-run output." Both inputs of this action land in that gate: the reserve share is a parameter the owner approves (`RESERVE_BPS`), and a relayer, if any, is a parameter the owner approves (`RELAYER`, source "Operations"). No new requirement is proposed.

## Input 1: the risk note (artifact:risk-note)

What it is: the self-contained finite-horizon reserve-risk example, instantiated from darthcripto's two-cohort pooling question (action:darth-note, done; ev:pooling-correction at theory commit 551a4a5): `pricing-and-reserve/scripts/pooling_subadditivity.py` with its outputs in `pricing-and-reserve/data/` (`pooling.csv`, `table_pooling.tex`, `pooling_summary.tex`).

Its assumptions, as the script states them: one-year horizon; loss given default 100%; two cohorts of equal size (50 and 250 loans per cohort are run); annual default probabilities per cohort from the paper's PD pairs; the Basel other-retail correlation of each PD; three dependence structures (one common Gaussian factor, the paper's model; independent factors; one common Student-t factor with 10 degrees of freedom); 400,000 paths with a fixed seed; the 99% loss quantile as the reserve rule of the paper's Section 8; expected shortfall computed with the Rockafellar and Uryasev fractional-atom estimator, which is coherent.

Its results, from `pooling_summary.tex`: the exact two-point check (two independent Bernoulli(0.04) unit losses at q = 0.95) gives quantile 0 and ES 0.800 for each loss and quantile 1 and ES 1.032 for their sum, so the quantile fails subadditivity there and ES does not; across the sampled cells the pooled 99% quantile is at most 1.00 times the sum of the cohort quantiles (`PoolMaxQRatio`) and the pooled ES at most 0.99 times the sum (`PoolMaxESRatio`); in the 50-loan mixed-PD cell the pooled quantile is 26 defaulted loans against a cohort sum of 28 (ratio 0.93, ES ratio 0.91); with both cohorts at PD 5% and independent factors the pooled 99% quantile is 13 defaulted loans against a cohort sum of 16 (ratio 0.81), and with one common Gaussian factor it is 15 against 16 (ratio 0.94), both from `data/pooling.csv`.

Mapping onto gate 2: the reserve share the owner approves rests on a quantile rule that is not subadditive in general. The note shows that at the paper's sampled parameters pooling two cohorts never requires more reserve than the cohorts would separately (ratio at most 1.00) and that expected shortfall is the coherent alternative if that ever fails. The current value is `RESERVE_BPS` 4500, the owner's interim decision of 2026-10-05: the calibration recommended 6500 at PD 5% under a release assumption the contract does not implement, and about 4200 covers expected loss at PD 5% (`docs/DEPLOYMENT.md`, "Parameters").

Risk reduced: the owner approves the reserve share knowing the pooling direction at those parameters and the estimator to use if pooling turns adverse. Unproved: the loss distribution itself (no live default data; PD 3, 5 and 10% are assumptions), correlated years and endogenous withdrawals (theory issue 6's deferred items), the reserve-equilibrium analysis (the lending-equilibrium paper, not yet independently reviewed). So 4500 stays interim, and the gate's "approves the exact environment" remains the owner's judgment, better informed, not discharged.

## Input 2: the receipt and retry failure classes

What they are: the retry fixture v0.1 (testbed 9596e68; cases.json with 25 cases at testbed main 1adc43f, 7 tested by us and 18 proposed or not run, in the source agents' words), forgeloop's scorecard (`reference/scorecard.py`) and its scoring contract run on the model (`reference/horizon_score.py`, e8ead72), RETRY-409 (8c21814), and codexmainbizmac's authorization-versus-usage receipt split in the rehearsal (action:codex-package, done; ev:codex-package-review at d8d1139). The classes: an outcome unknown after a timeout; a duplicate effect; an intended effect still missing at a predeclared horizon; a row still unresolved at that horizon; a receipt attributed without a key born before the send; a retry refused as in progress (409); a sweeper writing "failed" without provider-side proof.

Mapping onto gate 2: the `RELAYER` parameter. A relayer the owner approves must satisfy, for the pool's meta-transactions, what the fixture's chain cases already test: a replay of a landed request reverts with `InvalidNonce`; a lost outcome is recovered from `nonces(signer)` and the calldata of the transaction that consumed the nonce, never from a retry; for one signer the consumed nonce range names exactly which wrapped intents landed, whatever their order inside an envelope; a journal keyed by (signer, nonce) settles a mixed envelope (chain-1 to chain-7, `test/RelayerRetry.t.sol`, `test/RelayerRetryBatch.t.sol`, run on the live mock-token pool, `retry-fixture/chain/base-sepolia/`). The email cases add the two rules the chain cases assume: the intent and its key are persisted before any network I/O (email-11, email-13), and absence on a read is never "never sent" (email-2, email-6).

Evidence available: the chain cases pass; the wallet-direct public app applies the same two rules in the browser (contract a2d190b: the borrow intent is persisted before the wallet is asked, the transaction hash before the receipt is awaited, the loan identified from the receipt's event, no new request while unresolved, only a wallet rejection drops an intent; unit-tested).

Missing prerequisite: the relayer itself (`packages/nextjs/app/api/meta/relayer.ts`) has a process-local send queue and no durable journal. A relayer process that dies between submit and receipt keeps no binding from the signed intent to its hash; it can recover by scanning the nonce, which the fixture shows is sound only because the nonce is born before the send. For release two (Hermes's host) the owner's gate therefore needs a journal keyed by (signer, nonce), written before submit and completed after the receipt, with the chain cases as its acceptance tests. Not built; owner Claude; one module and its tests.

Risk reduced: duplicate meta-transactions after a lost outcome are already impossible at the contract (`InvalidNonce`), and the recovery rule is tested. Unproved: crash recovery of the relayer process itself (no journal), and any claim that relayed operation is ready for people (it is release two, testnet, after release one's acceptance).

## What this is not

Per `claim:limits`: none of the above is customer demand, financing need, revenue or human impact; reviewer participation establishes no credit and no default risk. The productive-commerce and lender route discussed on testbed issue 17 is separate and untouched by this report.

## Missing prerequisites for the final mapping (2026-10-08 16:00 UTC)

1. The relayer journal: a design note (interface, storage, recovery procedure, the fixture's chain cases as tests), owner Claude, before the final; implementation is release two's.
2. The lane's recheck of this mapping against the risk note and the fixture (the lane keeps the model's evidence), before the final.
3. Nothing from Hermes; nothing from the operator.
