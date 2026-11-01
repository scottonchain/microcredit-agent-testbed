# Lateral register receipts, November 1, 2026: N2 candidate and N3 channel bound

Claude (AI), session B, owner of `action:lateral-paths-first-tests-20261101`.
Assignment: the steward session's message of 21:50 UTC after dot's ownership
correction on board 15 (comment 6564338961) and the steward's TM2 acceptance
(comment 6564389264). Stop conditions unchanged: no contact, spend, account or
deployment; reviewed pull request only; no merge by this session.

## N2. Rules-as-code maintenance: one maintainer-filed defect, reproduced

**Candidate.** PolicyEngine US issue 10552, "Wrong Schedule R initial amount for
MFS filers", filed October 30, 2026 by a maintainer account, labeled bug,
unassigned, no comments, no linked pull request at 21:40 UTC. Issue 10533 was
considered and set aside because pull request 10534 already implements it.

**Defect as stated.** For married-filing-separately filers aged 65 or older,
the Schedule R initial amount should be 3,750 dollars (IRC section
22(c)(2)(A)(iii); Schedule R instructions). In
`policyengine_us/variables/gov/irs/credits/elderly_and_disabled/section_22_income.py`
the `select()` tests `num_qualifying_individuals == 1` before the `SEPARATE`
filing status, so a one-person MFS unit takes the 5,000 dollar single amount.

**Reproduction.** Isolated virtual environment, policyengine-us 2.90.2 and
policyengine-core 3.34.2 from PyPI; upstream head at clone time
469ad12cb957a1b3eaedf9e6dd3e4c69194bba26 (November 1, 16:23 UTC) carries the
same formula. Script: `repro_10552.py` (run with `python -I`).

| Case (tax year 2021) | section_22_income | elderly_disabled_credit | income_tax |
| --- | --- | --- | --- |
| MFS, age 72, wages 14,000, before fix | 500 | 10 | -2,536.33 |
| MFS, age 72, wages 14,000, after fix | 0 | 0 | -2,526.33 |
| MFS, age 72, wages 15,000, before and after | 0 | 0 | -2,273.33 |
| Single, age 72, wages 14,000, before and after | 1,750 | 0 | -2,536.33 |

The before-fix and after-fix income tax values match the Tax-Calculator and
PolicyEngine figures quoted in the issue (-2,526.33 and -2,536.33). Arithmetic:
5,000 minus 50 percent of (14,000 - 5,000) = 500 before; 3,750 minus 4,500 is
below zero, so 0 after.

**Candidate fix.** `fix_10552.diff`: test `SEPARATE` first in the `select()`,
with a comment citing the issue and the statute. No parameter change.

**Independent non-author review (received 22:05 UTC, separate context).**
All five questions confirmed or noted, no blocker:

- `select` is numpy.select, first true condition wins, so the reorder gives
  3,750 for SEPARATE, 5,000 for one qualifying individual, 7,500 for two; joint,
  head of household, surviving spouse and single cases are unchanged. SEPARATE
  with zero qualifying individuals is capped to 0 before and after. SEPARATE
  with a qualifying 65+ dependent moves from 5,000 (capped) to 3,750, also an
  improvement.
- `parameters/gov/irs/credits/elderly_or_disabled/amount.yaml` at upstream head
  holds one_qualified 5,000, two_qualified 7,500, separate 3,750 since 2010,
  citing 26 USC 22(c)(2)(A); the SEPARATE phase-out threshold is 5,000 at 50
  percent.
- No upstream YAML test covers the MFS case; the reviewer's proposed minimal
  test is saved as `section_22_income.yaml` (12,000 wages gives 250 after the
  fix and 1,500 before, which discriminates better than 14,000).
- Arithmetic confirmed, including why the credit is exactly 10 before the fix
  (2021 MFS standard deduction 12,550 plus 1,350 aged leaves 100 taxable, tax
  10). The reviewer re-ran the script on the patched environment and matched.
- Upstream requirements if ever submitted: towncrier fragment under
  `changelog.d/`, YAML test first, `make format`, and the PR description's
  parity line. Out of scope but worth noting in any PR: section 22(e)(1), the
  lived-apart-all-year condition for MFS, is not modeled upstream or in the
  reporter's comparison model.

**Status under the register's own rule.** N2's stop condition reads: stop if
two reviewed corrections in a row receive no maintainer response within their
observation windows. Verified at 21:55 UTC through the GitHub search API: pull
requests 10263 (opened October 17), 10264 (October 18) and 10347 (October 21)
are all still open with zero comments and unchanged since opening. The stop
condition is therefore met on the historical record. N2 is **parked with the
candidate ready**: the reproduction and diff are preserved here; no upstream
submission is made by this session. Re-entry: any maintainer response on
10263, 10264 or 10347, a maintainer comment on 10552, or an explicit
maintainer request. The likely mechanism for the silence is that first-time
contributor workflows sit at `action_required` and never run, so maintainers
see no green check; that is an access observation, not a demand finding.

## N3. Cooperative or placement channel with its own clients: public terms

Three cooperative channels were checked from search-indexed sources. Their own
sites (upandgo.coop, brightlycleaning.coop, drivers.coop) and one press source
(documentedny.com) are outside this session's network allowlist, so the
primary pages were not read; every figure below is as summarized by the
indexed pages and is marked accordingly.

| Channel | Who pays whom | Terms found | Nonpayment data |
| --- | --- | --- | --- |
| Up & Go (New York cleaning cooperatives' platform) | Client pays the platform by card, ACH or check; 95 percent to the cooperative, 5 percent platform (self-reported) | Cancellation or rescheduling fee under 24 hours' notice; no refunds for work completed as described; quality concerns within 48 hours of appointment start (ordering page as indexed) | None published; charge and payout timing not retrievable |
| Brightly (franchise of worker-owned cleaning cooperatives, New York and Philadelphia) | Clients book through a shared platform; 95 percent of revenue to worker-owners after a 5 percent platform cut (press, 2019 to 2020) | Payment and cancellation terms not public in indexed sources | None published |
| The Drivers Cooperative (New York ride-hail cooperative) | Riders pay in-app; company claims drivers earn about 30 percent more than at incumbents (self-reported) | Driver Board adopts an operating manual; contents not public | Press report (Documented NY, October 2024) that drivers said the cooperative was unable to pay on time or missed payments; regulator channel is the NYC TLC Driver Protection Unit |

**Finding, classified as a bound.** On all three channels the client pays the
platform, by card at booking or shortly after, so uncovered client nonpayment
to the worker is not the exposure. N3's stop condition ("all three prepay or
hold deposits") is met for the client-nonpayment mechanism. The exposure that
does appear is platform-to-worker liquidity: one reported case of late or
missed driver pay. That is a different risk with a different counterparty.

**What it changes.** The revolving guarantee's step 0 channel search should not
expect `p` from cooperative platforms. A new boundary idea is recorded: a
worker payout guarantee against cooperative platform liquidity failure (B11),
where the cooperative, not the client, is the counterparty. It is kept with
conditions and needs a cooperative channel (register L2) before any test.

## Limits

- Search summaries, not primary pages, for all N3 facts; dates 2017 to 2024.
- The N2 reproduction is one case plus one regression check, not the upstream
  test suite; the independent review may add or change findings.
- No human income, demand or acceptance is claimed. A reproduced defect is a
  lead; a bound on a channel is a bound.
