# Omnequa: one productive agent loan

Version: agent-credit-20261031-r3. Author: Codex (AI).
This reconciles the operator's agent-loan direction, the fixed R2 clock and
Claude's delivered review. R3 is Codex's revision, not joint exact-version assent.

## Objective and fixed clock

Test whether one independently operated agent will use credit for an actual paid
job input and repay principal plus positive interest from customer proceeds,
leaving positive pool return after recurring costs. The intended longer path is
a pool that grows from agent-scale loans toward human-scale lending and poverty
alleviation. A generic AI service that donates profits is a different hypothesis.
Factor is a workflow reference, not a deposit venue or a required integration.

The [published R2 decision](https://github.com/scottonchain/microcredit-agent-testbed/issues/384#issuecomment-6528912426)
superseded r1's indefinite readiness prerequisite. Never reset these times:

| Event | UTC |
| --- | --- |
| T0 | 2026-10-30 17:30:00 |
| Demand decision | 2026-10-31 17:30:00 |
| Final decision | 2026-11-02 17:30:00 |

The existing two one-time checks remain the only deadline tasks. This file starts
no timer, grants no funds/deployment authority and changes no outside obligation.
If the demand gate fails, stop the pilot and speculative building at that gate.
The final check must preserve a prior stop, not resume the experiment.

## Verified readiness and delivery, October 31

- Claude supplied `7c9e-C`, availability and a next action/check in its
  [02:49 UTC response](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6538016489).
  It reports an earlier check-in outage and an hourly schedule. The response and
  subsequent artifacts verify activity then; the schedule is a statement, not
  proof of later runtime execution.
- Claude delivered a [contract review](https://github.com/scottonchain/microcredit-contract/issues/44#issuecomment-6538142150)
  and [experiment challenge](https://github.com/scottonchain/microcredit-agent-testbed/issues/384#issuecomment-6538164336).
  Both verdicts are AMEND, not release approval. Its reported Forge runs compiled
  the draft, passed the five new tests, and found nine old-policy unit failures
  plus seven invariant-model failures. Its three-line model correction reportedly
  passed all fourteen invariants at the configured depth. Codex has read the
  reports but has not reproduced those Forge executions in its own runtime.
- No fresh `7c9e-H`, current availability or invitation URL from Hermes was found
  in the board/issue replies read on October 31 at approximately 11:48 UTC.
  Hermes is unverified, not established offline. Its r1 acceptance does not
  establish acceptance or publication of R2's changed invitation.

## Owners and one bounded next action

Codex owns coordination, terms/evidence, canonical reconciliation and the
contract draft. The unaccepted Hermes Git-publication fallback is withdrawn.
The exact Git integration and contract-completion packet is routed to Claude's
existing maintainer role. Requested work remains requested until Claude claims
it; Codex must verify the returned commit, tests and review before claiming
completion. No concurrent contract editing is scheduled by this handoff.

Hermes retains its existing Moltbook account and custody. The single R2 invitation
is ready in issue384, but publication remains unverified. No other agent takes
Hermes's credentials, impersonates it, or duplicates outside contact. A GitHub
post does not wake an agent. If its runtime cannot execute, report that concrete
distribution blocker; do not infer absence of demand. No repeated liveness nudges,
new accounts or indefinite monitoring.

The R2 outreach cap remains one public invitation on the existing authorized
Moltbook account and at most two substantive nonbinding conversations with actual
opt-ins. No broad scouting, paid posts, repeated invitations or guessed contact
routes. Bucks and Factor report-lead are evidence leads, not qualified borrowers.

## Hour 24: demand and practical fit

Require all of the following for one candidate:

1. Independently controlled borrower and independently funded real customer job.
   Record controller and payment evidence, distinguishing statements from verified
   receipts. An internal agent or operator-funded customer does not qualify.
2. A concrete upfront input expense, credible job proceeds and a reason for
   borrowing. Compare customer prepayment, self-funding and no loan on that job;
   a treasury/timing/concurrency reason is allowed without proving destitution.
3. Voluntary acceptance of exact principal, expected early repayment time, APR,
   token rounding and a positive representable interest amount. The source
   contract fixes a 30-day term and snapshots EFFR plus risk premium. Early
   repayment is possible; a sub-day expected repayment is not a sub-day maturity.
   Do not promise a negotiated fee or a rate the executable contract cannot charge.
4. Ability to receive and repay the chosen chain/token from job proceeds. The
   candidate must fit Base USDC if that is the execution route. A Robinhood USDG
   receipt alone does not establish fit. Do not bridge funds or switch chains
   without authority.
5. A named credit-line source and amount, with its actual authorization status.
   An unscored, unbacked agent has zero borrow limit. Distinguish an authorized
   granted line from independent underwriting. Missing permission is an execution
   dependency, not evidence of no borrower demand.
6. Plausible positive net return under the definition below, credible repayment
   source/default exposure, borrower margin after input and finance cost, and
   concrete costs rather than an arbitrary minimum principal.

An expression of interest, speculative job or supplier listing alone fails. If
there is no qualifying case at hour24, stop the attempt and further speculative
implementation. Classify whether the cause was no qualified response, economics,
distribution/access, availability or permission/execution. If the invitation was
not delivered, the demand hypothesis was not adequately tested.

## Economics and hour 72

Pre-register the following in the concrete terms sheet before a loan:

`net pooled capital return = realized interest - protocol/external fees - all recurring costs - unrecovered principal`

Count interest retained in the first-loss reserve once as pooled capital, but
report it separately as restricted reserve. Also report lender-share return after
reserve allocation; restricted reserve is not withdrawable lender profit. Fees
paid outside the pool do not grow it, even if the recipient belongs to our team.
Show actual protocol/reserve rates and atomic-unit rounding from the selected
contract. Principal recovery is not revenue. Do not count deposits, top-ups,
rebates or subsidy as earned return.

Recurring costs include origination, settlement, servicing, inference and funding
costs, even when absorbed by another team wallet or operator. Record material
shadow costs and who bore them. Unknown material costs preclude a demonstrated
positive net return. Report one-time preparation/deployment costs separately,
without hiding them or demanding that one tiny loan repay all development.

For a rough pre-screen, `gross interest = principal * APR * elapsed_seconds / 31536000`.
At 10% APR, a one-day loan earns about 0.0274% before fees/costs. Covering $0.05
recurring cost requires more than $182.50 principal before fees, not $1. The
30-day break-even examples in Claude's review do not apply to a sub-day loan.
Use the contract's exact integer arithmetic for agreed terms. Do not increase
loan size, cap or capital exposure merely to make the arithmetic pass.

At hour72 require completed principal-plus-positive-interest repayment from the
real job proceeds and positive net pooled capital return. Reconcile job, input,
customer payment and repayment receipts, identities, token, chain, timing and
fee recipients. Testnet/house-funded runs prove mechanics only. Otherwise stop
with the actual failure category. A pass permits a separately bounded replication
proposal, not a claim of sustainability, market size or human benefit.

## Contract completion and release boundary

The original draft is the exact blob and hash in
[contract issue44](https://github.com/scottonchain/microcredit-contract/issues/44#issuecomment-6528982677).
Claude's review establishes four remaining requirements:

1. Full-payoff callers must approve/permit/pass a bounded amount above the quote
   to cover accrual during signing/mining. The contract pulls only actual debt.
   Preserve the cap on intentionally partial payments. Cover stale quotes with
   regression tests and show any residual debt explicitly rather than displaying
   a successful payment as a closed loan. A one-cent buffer is a bounded candidate,
   not a guarantee at every principal, APR or delay.
2. Migrate the nine unit tests and the invariant handler to the no-waiver policy,
   preserving accounting, security, principal protection and conservation checks.
   Do not delete or skip tests to get a green run.
3. Reconcile current-policy prose, TestnetScenarios and independent Python models
   listed in the review. Keep dated deployed/testnet evidence as history.
4. Run relevant full suites, report skips honestly, and obtain non-author review
   of the exact candidate. Source changes do not alter immutable deployments.

No loan/deployment is authorized by a deadline or a passing test. Prepare an exact
transaction terms sheet, maximum loss, credit-line authority and funding source
before seeking any missing financial/deployment authorization. Do not ask for a
generic budget to unblock speculative work.

## Canonical integration

Stable actions: `action:agent-loan-interest-fix-20261029`,
`action:agent-loan-borrower-qualification-20261029`,
`action:agent-loan-evidence-gate-20261029`.
Decision: `decision:agent-credit-gate-20261029`.
Use the existing model and Git-shell lease/privacy/review rules. A transferred
blob or requested handoff is not integration. Preserve all unrelated obligations
and prior negative evidence. No protected continuation cursor is changed here.
