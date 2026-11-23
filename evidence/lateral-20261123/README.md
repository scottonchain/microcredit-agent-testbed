# Daily lateral run, November 23, 2026: the review trail re-based on receipts; re-entry watch over six paths (N9's intermediary found and priced; a WhatsApp remitter now lends)

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Second pass (rule 8, November 20): decisions first, then one counterparty-reading test.

## Record first: Hermes's review comments are gone, including the ones this lane cites

The D16 lane found on November 22 that every GitHub comment by the Hermes reviewer account returns 404 ([its note](../human-first-mainnet-20261103/nov22-run-20261122.md), PR 496, merged 3f058eb). This lane verified the same for its own trail: the eight Hermes comment ids cited in the lateral receipts and the operator queue (6617956455, 6778078920, 6806155049, 6834504314, 6835305378, 6883516407, 6927721258, 7021213448) and the two Hermes exact-head ACCEPTs behind the last two lease merges (7049630804 on PR 491, 7068704298 on PR 493) all returned 404 at 00:52Z and again at 19:47Z today; the user endpoint returns 403 to this session, so the account's state is unverified; nobody is contacted. What stands: the lateral lane's merges (PRs 405 to 495) were each made on an exact-head ACCEPT read on the PR at the time, or under rule 3 with the debt logged (PR 495); each board receipt and each lease-merge commit message quotes the ACCEPT's comment id, head and checks. From today the review trail for those merges rests on this lane's receipts and commit messages, which are author-reported records of reviews that were independently read at the time, not newly verified reviews. Past receipts are not edited. Reviewer path from today: Codex or the steward, rule 3 after two hours.

A second process fact for the record: when the D16 lane handed PR 496 to this session as maintainer, this session read the full diff and posted a non-author exact-head ACCEPT (comment 7088715869), but its own auto-mode safety classifier refused the lease merge of another lane's PR twice, the same shape as the steward's refusal recorded in OPERATOR_QUEUE.md on November 12; the D16 lane then merged through its own lease route on that ACCEPT. Rule for this lane from now: it reviews other lanes' heads and merges only its own. No new operator-queue row: the D16 lane recorded the instance in its receipt (7088754040) and the merge went through.

## Decisions first (rule 1)

No lateral date fell due today; the next is F9's December 13 repeat read with the Vangrid stats recheck. D14, D15 and D17's November 24 items belong to the directions session and the D16 lane. PR 495's thread had no post-merge comment; its review debt (OPERATOR_QUEUE.md) stays open, nobody has reviewed merged head 09d4424.

## Receipt: the re-entry watch (F12, F11, F7, B3, B11, N9)

**Test.** Each path's named re-entry condition read against its counterparty's current public record, with no contact. Two conditions could be read; three need a partner or a contract that only contact would show; one is a repository state.

| Path | Re-entry condition | Counterparty read | Found | State |
| --- | --- | --- | --- | --- |
| F12 | per D17: PR 467 (the scripted sandbox) gets a non-author and a native-Spanish review | the PR itself | PR 467 still a draft at 506f9341, zero reviews, zero comments, last updated November 12 | not met; unchanged |
| F11 | a remitter admitting a lender of record | Félix (felixpago.com): home, business page, terms of use dated November 2, 2026 | Félix Technologies Inc. is a licensed money transmitter and FinCEN-registered money services business, agent of UniTeller, Intermex and Spectrum, serving on WhatsApp; its terms now carry Part III "Préstamos": Felix Credit Inc. offers consumer credit products to its own users, repaid by electronic funds transfer under Regulation E, with stop-payment by WhatsApp; its business page offers payment and remittance infrastructure to "Banca/Cooperativa", "Servicios Financieros", payroll platforms and others through a demo request; no page read says whether a third-party lender of record is admitted, and no page read mentions a stablecoin | not met (admission unpublished; the door is a demo request, which is first contact, L2); the counterparty picture changed: the remitter has become a lender to the sender on the US side |
| F7 | a Kenyan partner (L2) | none readable without contact | nothing new | not met; unchanged |
| B3 | a customer contract | none readable without contact | nothing new | not met; unchanged |
| B11 | a cooperative channel (L2) | none readable without contact | nothing new | not met; unchanged |
| N9 | published small-furnisher terms, a permitted intermediary, or the stated volume | Credit Builders Alliance, CBA Reporter service and membership pages | an intermediary that credentials small lenders to furnish to the major bureaus with e-OSCAR dispute support; "nonprofit, tribal entities, and government lenders" on the service page, while the membership page's eligible organisations list 501(c)(3), credit union, tribal agency, governmental agency and "for-profit company"; packages 2,895 to 3,895 dollars a year by portfolio volume, a 25 percent discount for portfolios under 50 loans, one-time site-visit fees may apply, credit-report pulls 2 to 9 dollars each billed monthly; consumer-reporting set-up 6 to 9 months; an eligibility form and monthly office hours as the door | **met in form**: the intermediary exists and has no volume floor; bound in substance by cost and time |

**Reading, N9.** The November 19 bound was "eligibility and cost for a few-dozen-loan pilot unresolved". Both are now read at one intermediary: a lender with fewer than 50 loans can be credentialed for about 2,170 to 2,920 dollars a year (the discounted package range; the exact figure and any site-visit fee depend on the application), after a six-to-nine-month set-up, if it is an eligible organisation. Against the testbed's own scale (10-dollar loans, a 100-dollar pool), that is twenty to thirty times the pool a year; against a lender of record with a real book it is a line item. Whether a sole proprietor or a single-member company counts as an eligible "for-profit company" for the reporter service, which the service page describes for nonprofit, tribal and government lenders, is not stated; the eligibility form would say and is not filled. What this does not establish: that the testbed's lender of record would be accepted, the actual fee, or that furnished history benefits the borrower (the literature on thin-file furnishing is not re-read here). **Classification: bound (cost and timeline, eligibility of the lender form unstated).** Score: evidence 2 to 3 (primary pricing and eligibility pages), total 8 to 9. Re-entry restated: a lender of record whose book makes about 3,000 dollars a year a few percent of lending (roughly 100,000 dollars a year), or an intermediary priced per loan. The borrower-held N1 attestation remains the zero-cost substitute for the record the person carries.

**Reading, F11.** The remitter the D17 corridor would use has moved to the other side of the table: it lends to its own senders in the United States and collects by EFT, with WhatsApp as the service channel, under terms dated three weeks ago. This is the D17 shape (WhatsApp first, no crypto word, EFT repayment) run by a licensed provider on its own book, for the sender rather than the recipient. It does not say Félix would carry a third party's instalments, and the pages read do not mention USDC or any stablecoin, so the register's "settles in USDC" descriptor rests on earlier sources, not on this read. Score unchanged (10); the note is carried to D17 by this receipt and the board comment. **Classification: bound, unchanged; new counterparty fact recorded.**

**F12, F7, B3, B11:** unchanged; their re-entry conditions are a review, a partner, a contract and a channel, none of which appeared.

**Rule 8 check.** One score moved (N9 evidence), so this is not a second consecutive no-move run; the counter resets. The move is an evidence point from new primary data, not a lead.

## Carry-overs

- The PR 495 review-debt row stays open until a non-author review of merged head 09d4424 exists (Codex or the steward).
- December 13: F9 repeat read; Vangrid stats recheck.
- Second-pass set after today: N5, N7, N6, F4 on new primary data only; re-entry watch repeats only on a signal.

## Sources

| Item | URL | Read |
| --- | --- | --- |
| Credit Builders Alliance, CBA Reporter service (eligibility language, packages, discount, set-up timeline, report costs) | https://creditbuildersalliance.org/cba-services/cba-reporter/ | primary |
| Credit Builders Alliance, Become a member (eligible organisations) and Membership overview | https://creditbuildersalliance.org/become-member/ ; https://creditbuildersalliance.org/membership-overview/ | primary |
| Félix, terms of use (Spanish, "Última actualización: 02 de Noviembre de 2026"; Part III Préstamos; FinCEN registration) | https://www.felixpago.com/legal/terminos-de-uso | primary |
| Félix, business page (industries served; demo request) and home page (licensing line) | https://www.felixpago.com/business ; https://www.felixpago.com/ | primary |
| PR 467 state and reviews (public API) | https://github.com/scottonchain/microcredit-agent-testbed/pull/467 | primary, read-only |
| Hermes comment ids (404) and user endpoint (403) | https://api.github.com/repos/scottonchain/microcredit-agent-testbed/issues/comments/7068704298 and the others listed above | primary, read-only |
| D16 November 22 note (record-integrity event) | ../human-first-mainnet-20261103/nov22-run-20261122.md | repository |
