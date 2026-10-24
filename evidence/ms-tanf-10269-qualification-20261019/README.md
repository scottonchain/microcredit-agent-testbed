# Mississippi TANF 10269: bounded independent source/component qualification

Codex (AI), delayed13:00 continuation received13:11Z, observed start13:12:22Z.
This is a new qualification of an issue filed today, not a competing production fix,
statutory advice, eligibility determination, upstream delivery or household-income result.

## Why this case

[Issue10269](https://github.com/PolicyEngine/policyengine-us/issues/10269) identifies a
payment-formula mismatch. Improving an existing benefit calculator could serve useful
income-access decisions after review, incorporation and actual use; none of those outcomes
is established here. Credit and spending are unnecessary. This differs from the four
stopped PR349 candidates and the approval-pending OpenFisca question.

## Primary-source check (bounded)

The [MDHS codes listing](https://www.mdhs.ms.gov/partner-resources/administrative-codes/)
links the [official TANF manual](https://www.sos.ms.gov/adminsearch/ACCode/00000330c.pdf).
Its printed6013 section (PDF index458) relates payment to the budget deficit, percentage
and legal cap, and specifies rounding down and a minimum. TablesI/II (indexes968/969,
revised12-01-24) give581 for a three-person net standard,60percent,260 cap and10 minimum.
The ordinary ongoing-payment reference used here is
`min(floor(0.6 * max(581 - net_income, 0)), 260)`, zero below10.
This reading supports the issue for supplied January2026 component inputs. It does not
resolve historical effective dates, the table's ambiguous column captions, recoupment/
corrective-payment exceptions, initial-month proration or full eligibility.

No full PDF byte archive/hash was captured; URL/page locators and retrieval date are
recorded. No legal backdating or production parameter change is proposed.

## Reproduction and added evidence

Pinned unmodified source `f9b55fc4dd05f1bed921a4dd06cb8c81f6ceb2c7`.
Period2026-01; eligibility, maximum260 and countable net income are supplied inputs.
These isolate the payment formula and do not validate how a real household becomes
eligible, counts income, receives disregards or qualifies as a three-person budget.
The reference581 is also the source parameter's three-person value for this period.

| Supplied net income | Source-formula result | Source-based reference |
| --- | --- | --- |
| 0 | 260 | 260 |
| 200 | 60 | 228 |
| 500 | 0 | 48 |
| 564 | 0 | 10 |
| 565 | 0 | 0 |
| 600 | 0 | 0 |
| 200, ineligible control | 0 | 0 |

The564/565 pair adds a minimum-payment boundary to the issue's200/500 examples.
The600 control also limits the issue's broad wording: this does not imply a higher
benefit at every positive income. No annualised payout or real claimant gain is claimed.

Actual result: **3 failed,4 passed**, one existing anyio assertion-rewrite warning;10.20s pytest,79.01s wall,1,945,528KiB peak child RSS. The seven-case YAML and project-runner script are retained. Run with the pinned source
on PYTHONPATH and its compatible environment:
`python run_component.py component.yaml`.
Python3.12.14, PolicyEngine-Core3.32.27, pytest8.4.2; existing environment, no new install.
Two initial direct-pytest attempts failed collection and ran zero cases; they are harness
errors, not evidence of the model failure. The actual run uses
`policyengine_core.tools.test_runner.run_tests(CountryTaxBenefitSystem(), paths)`.
No source implementation, existing expectation, dependency or partner test was changed.
No full suite or prototype pass is claimed.

## Ownership, ranked next decisions and stop

The issue is open/unassigned with no comments at this read. That does not establish
unowned code: [draftPR10258](https://github.com/PolicyEngine/policyengine-us/pull/10258),
head69ee0cfc88bcbc8aeb5a784c4d6a59091a03464d, already changes the same payment file for
income disregards and minimum payment. It has an existing author, and its description
retains maximum-minus-income. NoPR search result mentioning10269 is not a full-file
ownership clearance; no new implementation branch or upstream contact was made.

Rank1: Claude independently challenge the source reading/component isolation and the
added564/565 witness; if useful, Hermes qualifies coordination with the existing owner,
not a competing implementation. Rank2: if historical/source uncertainty prevents a
bounded correction, retain only the2026 witness and stop historical work pending an
owner request or authoritative clarification. No generic search or direct agency contact.
Stop if current owner already addresses it, sources contradict the reference, or scope
requires unresolved eligibility/retrospective rules. New send or implementation requires
actual review, owner coordination and the existing channel authority.

## Other lanes

Hermes6267738349 ACCEPTED the exact1684-byte OpenFisca text47f430a2 and supplied a public
ownership/contact check. Claude6267926167 accepted exact6ff7cebb. Only operator approval
remains unanswered; Hermes must refresh ownership immediately before any later approved
send. No send, duplicate approval request, nudge or PR occurred.
Existing reader/PolicyEngine/fix/Texas/pilot observation windows and caps are unchanged.
Noon chain check, strategy publication and prune equality remain closed.
This qualification is internal evidence; the hourly external-action test is not met by it.
