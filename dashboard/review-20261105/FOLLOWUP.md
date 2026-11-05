# Independent-review follow-up

Codex (AI), November 5 2026. Successor to PR445 head
`4738c05dfe67d163eb1a9ddd21e94183e220b316`, on the same isolated source branch.

The collector checks inventory and stocks against provider-supplied logs requested
over the deployment-to-finalized range. Matching provider state and block headers
are not independent proof that all events were returned. The new regression omits
a matched deposit and withdrawal at unchanged share price: both collections pass,
but gross deposits and withdrawals are each understated by 1 test USDC. The test
uses only actual production getters, with no cumulative per-loan repayment fields.
This passing counterexample documents a limitation; it does not repair it.
Stronger independent log comparison remains a possible separately reviewed change.
No provider requests or new network path were added for this follow-up.

Seven new tests (43 collector tests total) cover:

- Nonzero repayment fee and reserve allocation: gross interest 5479 micro-units,
  fee 547, reserve 2465, lender NAV growth 2467.
- Reserve release: 2 USDC moves from reserve to NAV, with unchanged cash.
- Default recovery: 4 USDC backer stake slashed into cash and 6 USDC reserve
  absorbed cover a 10 USDC default; stake and reserve balances reconcile.
- Overdue active impairment repayment: 87671 micro-units interest plus 2 USDC
  principal reduces impairment by the principal only; fee 8767 and reserve 39451.
- Beyond-day-one interest and the contract's integer operation order: floor the
  annual principal-rate product before multiplying by time. The correct public
  outstanding passes; a one-unit discrepancy fails. Accrued interest is not
  reported as collected interest.
- Balanced omitted-event counterexample described above.
- One micro-unit of forgiven principal: collections at 2, 3, 30 and 365 days all
  fail closed. Because every daily run reads the same full history, later runs
  cannot recover until exact forgiveness accounting is implemented and reviewed.

The five positive accounting cases match contract1812e7d and expose only its
public getters. They revealed no accounting implementation defect. Existing
populated-record unit tests remain synthetic stronger oracles, explicitly
separated from production observations in code and documentation.

The public page now says “Reconciled committed” rather than “Verified committed”,
displays the balanced-omission limitation, and credits “Claude (AI); corrected by
Codex (AI)” in its footer. Privacy controls, historical data, freshness/fallback,
layout and branding remain intact. The only collector changes are qualified
text/comments/error wording; no accounting algorithm or provider calls changed.

## Receipts

- `followup/unit-tests.txt`: **43/43 collector tests**, no skips.
- `followup/render-checks.txt`: **134/134 offline browser checks**, including
  visible AI disclosure and event-completeness qualification in all three views.
- `followup/repo-checks.json`: **33/33 repository checks, 642 unit tests**.
- `followup/dashboard-light-390.png`: successor mobile render. Original screenshots
  and receipts remain as the prior-head evidence, not presented as new renders.
- `git diff --check` and public-content range check pass.

The browser test ran in this worker's existing permitted local loopback harness;
no changes address another reviewer's local socket restriction. No chain calls,
source/Pages integration, schedule/article edits, identity records, signing,
lending or runtime changes. Source acceptance and the first permitted refreshed
snapshot remain pending with their existing owners.
