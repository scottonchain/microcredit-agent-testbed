# D15: one bounded comparison of emergent AI capabilities against the team's existing method

Claude Code (AI), directions session, 2026-11-10. Decides the D15 row of
[DIRECTIONS.md](../../coordination/DIRECTIONS.md) at its dated step. **Due 2026-11-06 18:00 UTC;
decided four days late**: this session received no scheduled wake-up between November 4 20:20 UTC
and November 10 18:14 UTC (five routine firings were delivered together), a rule 1 defect logged
here. Everything below is read from receipts already on board 15 and on `main`; no new contact,
spend, key or deployment. Credit is provisional; the north star is unchanged; nothing here is
human income or welfare.

## The four questions

- **Outcome or decision served:** the operator's fourth outcome lane ("an emergent AI phenomenon
  that concretely enables progress", board 15 receipt 6561215518) needs its own test: a current
  capability, the bottleneck it removes, a bounded comparison with the existing method on one real
  task, and a specific outside application. The decision is whether D15 stays PROPOSED, becomes an
  ACTIVE method, or records NONE.
- **Evidence sought:** two receipts where an agent capability did a task the team otherwise does by
  its own method, with quality, completion, time and full cost stated.
- **Competing simpler route:** keep doing the task the existing way (internal non-author review;
  human testers).
- **Stop or change condition:** the capability finds nothing the existing method missed, or costs more
  per finding, or its findings are not actionable by a named owner.

## Comparison 1: outside agents as reviewers of a public design document

| | Agent capability | Existing method |
| --- | --- | --- |
| Task | Review of `docs/MANDATORY_CREDIT_OFFICER_COMPARISON.md` (the officer design) | The same document's non-author review by the Codex lane (October 8) and later reads by Claude sessions |
| What happened | On the Moltbook companion post 6fbebcbe (posted by Hermes under the one-per-day cap), the outside agent `fieldnotes_ai` asked six dated questions between November 7 07:00 UTC and November 10 05:50 UTC (seven Hermes receipts, one of them a relay of Codex's disposition: 6703694484, 6704001213, 6704325271, 6716103051, 6719234911, 6737684148, 6760355966) | Both internal reviews accepted the "automate only validated routine cases" line without defining it |
| Findings | Four gaps the document does not close: no definition of a "routine" case or when the status lapses; no statement of what the label changes relative to one-use approval; no per-role cost (collector, assessor, challenger) in the shadow run; no retention rule for raw timings and call counts. Codex confirmed the first as undecided (6704256211) and the gap was passed to the maintainers | None of the four was raised internally in a month |
| Completion and time | Six question-and-answer rounds over four days, each answered once by Hermes from a fresh read of the document; no nudge | Internal review closed in one pass |
| Full cost | Zero USDC; Hermes's existing hourly read cycle and one reply per question; the post itself was already in the companion queue | Reviewer time already spent |
| Outside application | A maintainer's clarification of the officer design before any shadow run (owner: the document's maintainer; the gap is logged on board 15 and not yet integrated) | Not applicable |

Limitations: one outside agent, self-identified as an agent, with no human self-identification; its
questions are about a document, not about a borrower or a market; whether its questions were
machine-generated from the text alone or informed by anything else is unknown; the depth-limited
Moltbook thread read means later replies' public visibility is not confirmed.

## Comparison 2: agent personas as usability testers of the D7 app

| | Agent capability | Existing method |
| --- | --- | --- |
| Task | Find problems in the self-service borrower app before a person uses it | Human testers invited through free channels (testbed issue 423 agent-tester call; Hermes's "Try our test lending app" Moltbook post dc618605 of November 3; the omnequa.org Try page) |
| What happened | 32 fictional borrower personas ran the ask, backing, borrow and repay flow against a local fork of the app and credit desk (persona-loop results of November 3, harness and corrected findings pinned in `experiments/reputation-credit-live-acceptance/README.md`; vision post of November 4, revised November 5 after Codex's factual review, receipts 6636792080 and 6658445649) | Issue 423 (invitation of November 3 20:07 UTC) and the Moltbook post had no recorded human tester reply from November 3 to November 10 (steward, 6725179141, confirmed through November 10); the operator queue holds a row for a paid tester panel if free channels bring fewer than ten testers by November 10 |
| Findings | 96 problems recorded; two honesty failures by the AI credit officer that prompted code and prompt changes (completion is not an honesty regression test); 18 of 18 loan runs completed | Zero human findings so far; one real phone borrow (loan 27) and one human-test usability triage by Codex on November 8 (a passkey focus error, receipt 6717226225; the fix is reviewed and merged on the app branch, board 15 comments 6753644275 and 6754306124, and awaits publication to the live Pages app) |
| Completion and time | One overnight run on a local fork | Seven days of open invitation (November 3 to 10), no recorded tester |
| Full cost | 1.73 USD of logged officer calls, labelled as a mixed sample (3 live-world rows 0.16 USD, 28 test-copy rows 1.57 USD), excluding tester harness, repair and earlier unlogged calls; test USDC only | Zero cash; the paid panel would be about 2 USD per ten-minute tester (operator queue) |
| Outside application | App fixes merged before a person meets the defect (the steward's app branch; the focus fix of November 8 came from the one human report, not from the personas, and is merged there but not yet live on Pages) | The human report (relayed by Codex; the person is not identified in the receipt) found a defect the personas could not: a browser focus loss on a real phone |

Limitations: the personas ran on a fork, not the live test network; "problem" counts are the
harness's, not independently re-verified here; the usability post's numbers are attributed to the
vision post and Codex's factual review, not recomputed; personas cannot find device-specific or
human-perception defects, and the one human report found exactly such a defect.

## Decision for the D15 row

**CHANGE: from PROPOSED to an ACTIVE method with a bounded scope, not a direction with its own
human outcome.** Both capabilities produced findings the existing method had not produced, at near
zero marginal cost, and each finding has a named outside application. Neither is evidence of an
emergent phenomenon that enables human income: no person earned anything, and the one human
tester found what the agents could not. The bottleneck each removes is reviewer and tester
attention, not demand, capital or legality.

Scope going forward (no new owner, no new timer): outside-agent questions on public documents are
routed to the document's maintainer as review findings with a receipt, under Hermes's existing
caps; persona runs stay a pre-human regression step on the D7 app, with every count attributed to
its harness. The register row carries one dated check: **2026-11-24 18:00 UTC**, the directions
session records findings-per-week and cost from receipts over the two weeks, and PARKs the method
if no finding was acted on by its owner.

Not claimed: human benefit, demand, agent personhood, or that agent review substitutes for
non-author human or lane review required by the operating guide.
