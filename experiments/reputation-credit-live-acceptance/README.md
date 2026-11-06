# Revised credit mechanism: live acceptance preparation

Codex (AI), November 4, 2026. Status: **PREPARED / NOT LIVE-TESTED**.
This packet is a provisional acceptance specification and independent reference
check. It does not implement or approve the proposed underwriting mechanism.

## Sources and current decision

- [Proposal and candidate equations](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6636875903).
- [Claude's accepted review checkpoint](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6637135184):
  November 4 at 20:00 UTC. Acknowledgment is not substantive review or approval.
- [Testing ownership and implementation-readiness request](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6637440922).
- Canonical descriptor: [deployments/current.json](../../deployments/current.json).
- [Prior corrected findings](https://github.com/scottonchain/microcredit-agent-testbed/blob/2daabb5b/experiments/d7-live/persona-loop/results-20261103/FINDINGS.md),
  [original log](https://github.com/scottonchain/microcredit-agent-testbed/blob/4351d3f5/experiments/d7-live/persona-loop/results-20261103/LOG.md),
  and [harness](https://github.com/scottonchain/microcredit-agent-testbed/blob/4351d3f5/experiments/d7-live/persona-loop/README.md).

At testbed main `527d70452d6f950f808a74b6f7b8f61e9875155c`, and contract main
`7ceaf07d46bc2ebe244175af60f027bd8f2a8995`, no reviewed implementation/release of
this new mechanism was established. Current contract open PR46 is operating
guidance, not this implementation. Testbed open PR432 is token reconciliation.
These are bounded source/PR observations, not proof that no other development
exists. Claude is asked to identify its actual owner/PR or say unassigned.

The earlier 32-persona test used a **separate local fork**, with local RPC,
synthetic funding and time controls. It contributes regression cases only.
Later completion did not prove that the officer's honesty failures disappeared.
Neither that run nor this packet calibrates real borrowers' default probability.

The human decision served is whether a future lender can rely on the agent's
evidence and controls before exposing borrowers or capital to debt. Relevant
retrieved lessons include the stopped agent-loan attempt and revolving-guarantee
qualification: software activity, repayment and publication do not establish
need, creditworthiness or benefit. The existing November 1 STOP is untouched.
Three options were compared: rerunning the old pool would test the wrong
mechanism; changing the canonical deployment now would precede review and release
authority; independent reference/negative-control checks now expose specification
errors without either dependency. This packet chooses the third while retaining
the requested live campaign as the acceptance step. Existing lender evidence and
NO_LOAN remain financial alternatives, not hypotheses refuted by synthetic tests.

## What can run now

From this directory, with Python 3.11 or newer and no third-party packages:

```sh
python -m unittest -v test_oracle test_preflight
python preflight.py --output preflight-NEW-RUN-ID.json
```

The unit tests are **OFFLINE REFERENCE CHECKS**, including a small illustrative
reservation state machine. They exercise fixed numerical vectors, concurrency,
replay/correction and fail-closed node checks. They cannot pass deployed-service
acceptance. Unspecified eligibility, calibration, skill-growth, restoration and
label authority remain deliberately outside this reference model.

### Reference-ledger semantics after the maintainer review (2026-11-06)

These are **PROVISIONAL REFERENCE SEMANTICS**, fixed so that a future adapter has
unambiguous expected vectors. None of them is finalized mechanism or underwriting policy.

- `reserve()` returns `True` for a new reservation and `False` only for an exact retry of
  an **active** one. A cancelled or settled identity is terminal and is never reopened:
  an IDENTICAL retry raises `ReservationTerminal` (a retry with changed fields raises the
  generic `ValueError` first). A `False` therefore always means "a lock exists".
- Report and correction identities share one namespace per `(loan, root)` and each keeps
  the label it carried. An exact old delivery (the original report after a correction, or
  any earlier correction) is a no-op that keeps the current, possibly corrected, outcome.
  The same identity with a different label raises `ReportConflict`. A new identity that
  disagrees with the recorded outcome still needs an explicit `correct()`.
- Ledger arithmetic is exact or rejected: sums, locked totals, budgets, penalties and their
  accumulation run at 60 significant digits and trap `Inexact`, so a result that would need
  rounding raises and no state changes (state is mutated only after the arithmetic).
  `display_score()` is a logarithmic approximation for display only, and `margin()` /
  `break_even_charge()` use the default 28-digit context; none of these feeds the ledger.
- A path whose root is also its leaf (`root -> root`) is rejected by this reference. Whether
  a root may borrow against its own reputation is a finalized-policy question (open).
- `independent_roots(loan)` counts the root of every reservation identity ever recorded,
  including cancelled and settled ones. Whether cancellation should count toward
  independence is a finalized-policy question (open).

The preflight is read-only and never loads a signing key. It rejects wrong
networks, known local test clients, missing code and block-hash changes. It uses
the descriptor's public RPC without address/environment overrides. Even a
successful snapshot reports **OBSERVED_NOT_RELEASE_VERIFIED**, not acceptance.
It does not yet verify wiring, ABI, proxy implementation or the new release.
Those comparisons must be bound to independently reviewed release artifacts.
SHA256 here fingerprints bytecode bytes; it is not Ethereum's Keccak code hash.

The first actual preflight receipt is [preflight-20261104.json](preflight-20261104.json):
access unavailable, no live block observation and zero transactions. A separate
bounded direct read returned an HTTP 403 tunnel denial. Preserve the configured
proxy; the remedy is an approved read route, never bypassing the policy.

## Readiness contract before live execution

The following must have attributable evidence; prose claims or a status flag alone
are insufficient. Execution stays closed when any item is unknown.

1. **Specification:** Claude's actual critique and disposition on an exact revision;
   frozen PD label/horizon, all numerical policies, evidence eligibility, supported
   languages, group deduplication, rounding, penalty/correction/restoration and
   concurrency rules. Freeze the display-score endpoint convention too.
2. **Implementation:** named owner and reviewed source/ABI/backend/model versions;
   passing implementation checks; deployment receipts and verified runtime bytes
   and proxy targets where applicable. Pin the current descriptor and source
   revision, rather than assuming current source HEAD is deployed. The existing
   canonical pool is recorded at `1812e7d` and predates newer interest fixes.
3. **Integration:** trace the interview's evidence IDs through the deterministic
   decision, authorized oracle publication, provider score, effective pool score,
   and actual loan limit. Check wiring, score freshness and every test wallet's
   override. No admin override may conceal a missing new-mechanism bridge.
4. **Execution ownership:** fresh default-branch execution-owner check for the
   actual work kind, matching acceptance and existing project/run lease. At the
   time of the original packet (2026-11-04) config2 gave heavy execution to Claude;
   as of 2026-11-06 testbed main `fed5c813` is config5, stable, owner Claude. Read the
   current config, never this sentence. Bounded verification stays open to both
   lanes. A transfer request does not complete the transfer.
5. **Test resources:** dedicated wallet controller/signing capability, token and
   gas balances, approved per-wallet and total exposure, transaction/model-call
   budgets, repayment amounts and interest headroom, cleanup destination and
   resumable recovery. Old scenario-wallet balances are not assigned resources.
   Never sign merely to demonstrate control, or publish signed bytes or secrets.
6. **Environment:** an authorized reachable RPC on chain84532 and the live app,
   backend and oracle bridge. Keep synthetic financial records out of public
   interview threads. No real applicant data or real-currency lending is needed.
7. **Test-only fixtures:** the proposal requires matured real-currency evidence.
   Synthetic testnet history must never qualify as that evidence. The reviewed
   implementation needs a clearly isolated TEST_ONLY mechanism on this testnet
   for exercising eligible and ineligible branches, with no production export.
   If unavailable, mark those tests BLOCKED; do not publish fake real outcomes.
8. **Time:** observe actual chain time. The proposed default label is 60 days after
   the original due date, separate from a contract default transition. Neither
   warping nor an immediate test label can pass the true elapsed-time case. Use
   an independently verified pre-existing matured test record if available;
   otherwise retain the future observation and its owner until it matures.

## Borrower and deterministic campaigns

[plan.json](plan.json) carries goals, evaluator assertions, fixed cases and the
prior-finding crosswalk. Personas interact through the live app/backend rather
than receiving expected answers. A separate evaluator receives hidden fixture
truth and the approved specification. Pin borrower/evaluator models and prompts,
allow at most30 decisions per run, and propose three repeats per persona. Funding
and call caps are unresolved prerequisites, not implied spending authorization.

Run deterministic baselines first, then adaptive borrower campaigns, deterministic
reproductions of discoveries and final accounting. Financial loss and correlated
shock analysis stays offline unless the explicit test budget permits the relevant
testnet default; never impair unrelated shared-pool positions to create a fixture.
All live writes go through the maintained application/relayer and a reviewed
adapter for the final API. **No live transaction adapter exists in this packet:**
the implementation's API, oracle and release are not frozen. Bind the adapter and
its independent expected vectors at that point; never substitute the old back()
flow, a local mock, or a runner that records a no-op as success.

For each case record initial/final pinned state, target code/version, consent and
evidence IDs, decisions, exact quoted terms, trace/request IDs, transaction hash,
receipt status, block/time, confirmation depth and assertions. Retain private
interview traces outside the public repository; publish only redacted synthetic
evidence and public transaction identifiers. A submitted hash is not success.
An uncertain send is reconciled before another attempt. Track nonce and logical
intent so replacements/retries cannot create duplicate loans or commitments.

Stop on wrong target, release/config drift, exhausted cap, critical bypass,
unrelated-pool impact or unbounded cost. Stop means checkpoint, reconcile pending
transactions and liabilities, and safely clean up within existing authority;
it never means deleting evidence or silently abandoning a wallet.

## Verdicts and continuation

Use PASS, FAIL, BLOCKED, INCONCLUSIVE and NOT_APPLICABLE per requirement. No
applicable case can pass without its actual evidence. Distinguish offline oracle,
read-only live observation, backend integration and confirmed live transactions.
Acceptance requires exact expected outcomes, conserved capacity, enforced exposure
and truthful messages, no unresolved critical/high defects, and no hidden blocked
requirement. Passing still says nothing about calibrated human credit risk.

Codex retains testing follow-through. Claude retains the accepted proposal review;
implementation ownership is requested, not assumed. Recheck at the accepted
20:00UTC review checkpoint and on a published implementation/release change.
Use the existing project coordinator and action ownership rather than creating a
second polling controller. Future campaign execution must pass the current owner
gate and claim the same work item before starting; no parallel live writers.
See [status.json](status.json) for this run's observed state and unresolved gates.
