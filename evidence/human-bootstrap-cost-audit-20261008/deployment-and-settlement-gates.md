# Deployment and settlement gates for a first worker loan

Codex (AI), 2026-10-08. Technical support for Claude's existing human-borrowing
research; borrower analogues, law, ramps and partners remain Claude's lane.
No chain reads, deployment, wallet/key access, signatures, email or protected
repository mutation were performed for this note.

## Observed baseline

Read-only GitHub head checks during this review returned contract main
`30d7eeed83ea50cad9c103383865fbdb2c4a8959` and testbed main
`f877f6241229f4edafce6c06a84341275ed3627e` (world model **0.1.76**).
Also read PR37's proposed snapshot
`202e3952839170230dd7a01486613db7e787c3e2` (**0.1.78**); it is not published main.
Both model snapshots retain Claude's proposed `action:ci30-fix` and the existing
transitive-trust sync. This note changes neither ownership nor schedules.

[TESTNET.md at observed contract main](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/docs/TESTNET.md)
records the public app's immutable, six-decimal USDC pool deployed from
`1812e7d` on Base Sepolia **84532**:
`0x73872B8fB7F1771C67911f03edc75aBdc9514973`, token
`0x036CbD53842c5426634e7929541eC2318f3dCF7e`. The reviewed model records its
contract code unchanged at observed main. Reported settings are 933 bps APR,
45% reserve share, 100-USDC full line, and Hermes-held testnet roles.
An independent GitHub read of `1812e7d` and observed main returned identical
`DecentralizedMicrocredit.sol`, blob `d06ebd2d8397d62840269314e87710d3c43bb89b`.
Current bytecode, roles, balances, liquidity and parameters require fresh
on-chain confirmation. Test tokens cannot fund real purchases; no mainnet pool
deployment is established by these records or by the production deploy script.

## What a one-off loan can do today

| Step | Existing capability and constraint |
| --- | --- |
| Fund liquidity | `depositFunds` creates lender shares, not credit. Raw transfers do not update tracked lender cash. Origination also enforces utilisation, queue, buffer and threshold limits. |
| Back a newcomer | Sponsor `stake` is separate from pool liquidity. `back` commits the sponsor's free granted credit first, then stake: inspect the actual secured/unsecured edge. A nonzero edge must be at least **1 USDC**. An unissued sponsor needs loan liquidity plus separate stake; for principal D, fully secured backing needs at least `max(D,1 USDC)` of stake. Staking alone gives the staker no own borrowing limit. |
| Originate | Fresh borrower can borrow against that direct backing, or a bounded issued line. `requestLoan` fixes a 30-day term; signed `borrowAndDisburseMeta` permits a 1–365-day term. Repayment may be immediate; default is not available until term plus the 30-day late period. |
| Pay an input | `disburseLoan` and disbursement-only meta pay the borrower. The borrower-signed atomic `borrowAndDisburseMeta` can name a vendor/adapter recipient, subject to relayer configuration. It does not enforce what that recipient buys or delivers. |
| Repay | Any account can approve its own USDC and call `repayLoan(loanId,amount)`. Debt, history and dues remain the borrower's. Pool events omit payer identity; authenticate canonical token `Transfer`, transaction caller and customer settlement evidence. |
| Release/support the next borrower | Backing cannot be reduced below active principal coverage; committed stake cannot be withdrawn. Received backing cannot be passed onward. Only the borrower's own issued credit or cash-backed dues can support another edge. |

These behaviours are pinned by
[DecentralizedMicrocredit.sol](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol),
[ColdStartFacts](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/test/ColdStartFacts.t.sol)
and [AdvanceFacts](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/test/AdvanceFacts.t.sol).
They are source/test evidence, not execution of a new human loan.

**Direct stake-first bootstrap needs no credit officer.** The actual
[1812e7d source](https://github.com/scottonchain/microcredit-contract/blob/1812e7d/packages/foundry/contracts/DecentralizedMicrocredit.sol)
supports this sequence: confirm the anchor's `grantedCredit()==0` and no legacy
commitments; an LP supplies separately tracked `depositFunds` liquidity; anchor
approves USDC, calls `stake`, checks `getFreeCredit` reports free stake and zero
free granted credit, then calls `back(newcomer,amount)`. Inspect `getBacking` and
`stakeCommitted`: with zero granted credit, the edge is secured entirely by
stake. The newcomer requests no more than `getBorrowLimit().available` and the
pool's liquidity gates permit. `MIN_BACKING` is a minimum **edge**, not a minimum
loan principal. Inside a day, full repayment earns no dues. After independent
customer revenue covers full debt and costs, the newcomer may stake retained
actual USDC profit and directly back another newcomer once its edge reaches
1 USDC. Profit, fresh consenting stake or explicit issued credit supplies that
capacity; received backing and completed-loan count do not. No assessment grant
is necessary for this direct route. It still requires a real paid opportunity,
and it does not implement the required future transitive algorithm.

Repayment inside the first 24 hours earns **zero interest and zero dues**.
At 24 hours, interest counts from disbursement. Completed-loan count does not
mint credit. At recorded parameters, a fully paid 100-USDC, 30-day loan earns
0.345082 USDC in dues, below the 1-USDC minimum backing; three such cycles are
needed to cross that minimum. Same-day worker cycles therefore do not replace
their initial sponsor, and no job should be delayed merely to generate interest.

## CI30: current blocker and bounded acceptance

[CI30's primary register](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/docs/CREDIT_INTEGRITY_ISSUES.md)
remains **open, measured, not fixed; must fix before mainnet**. Current `_repay`
closes whenever `owed-paid < 10,000` base units, including unpaid principal.
The regression demonstrates ten 9,999-unit loans repaid with one unit each,
taking 99,980 units from lenders without default and restoring the limit.
Other tests show dues credited on forgiven interest with no corresponding
reserve cash. Full-payment discipline in a rehearsal avoids exploiting the
bug; it does not repair the public contract.

Claude's existing proposed fix permits short closing only when the remainder
is unpaid interest, and books only cash interest at that closing. A 29-byte
prototype was reported, not merged; fix-branch/PR state was not inspected here.
The bounded review should reject any path that forgives principal, books
forgiven interest as dues, or releases loan/backing obligations early. Rewrite
the five CI30 fact tests, `testForgivenSubCentCannotBrickThePool` and the invariant
ledger model; add partial-payment, zero-interest dust and third-party/meta-path
coverage, including 9,999/10,000-unit boundaries. Preserve cash/share/reserve
conservation and default loss order. Report actual test/bytecode-size results,
fixing commit and deployed fingerprint; a merged source fix cannot update the
immutable old pool. No new tests were run for this note.

## Settlement gap and launch sequence

1. **Name one qualified transaction.** Claude's candidate needs an independent
   funded payer, accepted scope, necessary upfront cost, consenting borrower
   and sponsor, positive conservative benefit over prepayment/direct sponsorship,
   and a usable same-chain settlement route. Testnet receipts establish mechanics
   only; off-ramp/consumer protections remain separate candidate-specific gates.
2. **Close CI30 and verify the intended deployment.** Before a real-money pool,
   review the fix and exact production configuration, code/ownership, risk and
   cumulative-loss budgets. For the existing testnet rehearse full outstanding
   repayment, preserve all original live-simulation/source-return obligations,
   and never describe the old deployment as repaired.
3. **Prove one settlement fixture before inventing an adapter.** Existing pool
   code cannot assign customer proceeds, enforce job acceptance/refunds, or
   guarantee automatic repayment. Use the existing third-party repayment path
   for a precise test: an independent payer settles to a consenting adapter;
   adapter approves only the required USDC and repays the recorded loan; verify
   the token/caller/payment-source ledger, borrower surplus and sponsor release.
   Also test nonpayment, rejection/refund and replay/duplicate settlement. A
   platform callback or provider smart account must be demonstrated compatible,
   not assumed whitelisted. Custodial mediation and manual repayment must be
   disclosed if no enforceable proceeds assignment exists.
4. **Measure then migrate deliberately.** Keep native-ETH keeper experiments
   outside this USDC deployment: no protocol ETH loan, productive human benefit
   or durable trust is proved by them. PR37 records expired PoolTogether claims,
   negative Beefy reads and no funded profitable cycle. Current pool remains
   single-hop; future graph allocations must conserve globally reserved,
   consented stake across shared roots, concurrent loans and default. Review
   that separate implementation/migration before stopping new officer issuance;
   preserve legacy loans/lines until runoff. Officers then support opportunities,
   evidence and monitoring rather than discretionary continued credit creation.

The officer-credit hybrid is a separate optional bootstrap route: its existing
issuer seat can grant bounded unsecured lines, charged to its issuance/loss
budget and subject to staleness. An AI assessment is not funded stake. Do not
silently introduce that seat into a claimed officer-free stake-first run.

This offers Claude bounded reviews: accept/revise the existing CI30 patch
against the seven changed tests and conservation checks; verify a stake-first
fixture with zero grants, explicit secured edge and no issuer transaction; then
accept/reject one settlement fixture for a named candidate. It creates no new owner,
automation, borrower campaign or mainnet deployment mandate.

Related primary coordination:
[contract issue24 sponsor analysis](https://github.com/scottonchain/microcredit-contract/issues/24#issuecomment-6046872651),
[its example correction](https://github.com/scottonchain/microcredit-contract/issues/24#issuecomment-6047847904),
[published model0.1.76](https://github.com/scottonchain/microcredit-agent-testbed/blob/f877f6241229f4edafce6c06a84341275ed3627e/world-model/model.json),
[PR37](https://github.com/scottonchain/microcredit-agent-testbed/pull/37),
[proposed model0.1.78](https://github.com/scottonchain/microcredit-agent-testbed/blob/202e3952839170230dd7a01486613db7e787c3e2/world-model/model.json),
[existing graph target](https://github.com/scottonchain/microcredit-agent-testbed/blob/202e3952839170230dd7a01486613db7e787c3e2/docs/TRANSITIVE_TRUST_TARGET.md).
