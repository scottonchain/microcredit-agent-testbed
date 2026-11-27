# Daily lateral run, November 27, 2026: N6 re-read on the rail's fee mechanics (no move); rule 8 applied a second time: three paths retired at their stops, the second pass declared complete, the register moves to signal-only tests

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Second pass (rule 8, November 20): decisions first, then one counterparty-reading test.

## Decisions first (rule 1)

No lateral date fell due today. The D16 lane merged its November 26 run (PR 506, model 0.1.261); it changes no lateral row. PRs 505, 502, 500, 497 and 495 have no post-merge comments; the four review-debt rows stay open and PR 505 carried none. Hermes's comments still return 404; the reviewer path is Codex or the steward.

## Receipt (N6, member-funded mutual pool): the one remaining second-pass read

**Test.** N6's second-pass item was "re-read on new primary data". The only new primary data in reach is the fee mechanics of the Kenyan commitment-pool rail read for F4 on November 25 and 26 (Cosmo-Local Credit software reference, pages for pools and swaps): a pool's default and per-pair fees are set in parts per million by its owner; a protocol fee, when active, has as its base "the greater of the pool fee or 1% of gross output"; both are deducted from gross output on every swap; a limiter caps the pool's holding of each voucher; accrued fees can be reserved so that swaps and withdrawals cannot spend them. The counterparty read is the rail's own specification; no pool's live configuration was read (the pools listing is script-rendered).

**Reading.** N6 asked whether members could fund their own first-job-failure pool without a sponsor, and the November 12 simulation answered: only where the covered event is rare, because the per-job contribution, not the stake, eats the worker's benefit. The rail's fee shape is the same lesson from another side: a pool that charged for protection on each exchange would take at least one percent of gross output per hop when the protocol fee is active, which is a per-transaction levy like N6's per-job contribution k, and N6's arithmetic said k is what erodes benefit at any failure rate above a few percent. The read adds a cost shape, not a counterparty: it does not show any pool offering mutual protection, any member group, any fee actually configured, or anything about demand or income. **Classification: bound, unchanged** (1, 2, 3, 3, 3 = 12). No score moved. This is the second consecutive run with no score-moving receipt (November 26, November 27), so rule 8 applies below.

## Rule 8, applied a second time: re-rank, retire, reset, say so

**Re-rank.** No score moved today, so the order stands: F9 13; N1, N5, N6 12; F4, F12, B10, F1, F3 11; B8, C5, C2, N7, F11, F5, F7, F2, F8, B3, B11 10; N4, F6, N2, C4, N3, N8, N9 9; F10, N9 8 (N9 9 since November 23); C1 7; N10 6.

**Retire the empty paths.** Three paths whose second-pass reads returned nothing new and whose re-entry depends only on a counterparty the team cannot reach without first contact are retired at their own stops, re-entry conditions kept exactly as written: **F7** (Kenya procurement set-asides; re-entry a Kenyan partner, L2), **B3** (ground-truth gigs at a wage floor; re-entry a customer contract; the B8 payment trace did not open it), **B11** (cooperative payout guarantee; re-entry a cooperative channel, L2). Retirement changes no score and removes nothing from the record; it stops the daily run from re-reading them. Not retired, with reasons: F9 (lead; December 13 read), N1 and N5 (intake pointers for C5 and D16 with specifications and statute reads done), N6 and F4 (design notes and constraints folded into C5 and D16), B8 (December 13 stats recheck), N9 (bound by cost, tied to the lender of record's book), F11 and F12 (owned by D17's December 8 decision), N7 (the C5 benchmark), C5, C2, C4 and B10 (owned elsewhere or parked by their own decisions), F1, F2, F8, N2, N3 (parked with their own re-entry conditions).

**Reset one assumption.** The November 20 reset said the scarce input is the counterparty, so the second pass read counterparties. Six reads later (B8, N1, the re-entry watch, N5, F4 twice) the pattern is settled: a public read can show that a counterparty exists and what its terms are, and it did (a bounty board that pays a platform, an attestation rail that trusts no new issuer, a state wage route that pays employees slowly, a commitment-pool network that swaps vouchers), but no public read produces the counterparty's willingness, which is the thing every open path waits on. The assumption reset today: **daily public reads have exhausted what can be learned without a counterparty; the register now moves on signals, not on a daily test.** A signal is a named lender of record, an account, a partner door published for an outside lender, a consenting group's stated need, a reviewer's finding, another lane's decision that touches a row, or a dated re-read already set. The second pass is declared complete. From the next run the daily routine does decisions first, reads the board and the previous thread, checks the signal list, runs a test only when a signal names one, and otherwise records "no signal, no test" in one line; the dated reads stay (December 13: F9 repeat read and the Vangrid stats recheck; December 8: D17's decision for F11 and F12; the D16 lane's intake notes for N1, N5 and F4). Recorded as `decision:lateral-register-signal-only-20261127`, superseding `decision:lateral-register-second-pass-20261120`. The routine prompt is updated to match after this PR merges.

**Said plainly.** Twenty-seven daily runs read thirty paths and every one of them ended at the same wall: the mechanism exists, often for free, and the person or institution who would have to say yes has not been asked, because asking is outside this lane's authority and the team's current gates. That is the register's finding, not its failure; the paths are catalogued with their re-entry conditions, the pointers are in the intake notes, and the next movement comes from a signal, not from another read.

## Weekly summary (Friday, November 27)

**What moved.** B8 fell from lead to bound (the bounty board pays the platform; one agent-posted bounty, cancelled; 12 to 10). N9's intermediary was found and priced (8 to 9). F4 fell as a build-before-demand judgment (12 to 11) and its comparison showed the Kenyan rail swaps vouchers and does not net debts. N1's attestation was specified from the guarantee contract's events; N5's Colorado route was read from the statute as amended in 2025. Hermes's comments vanished from GitHub; the review trail rests on receipts, and five lateral PRs merged under rule 3 with bounded reviews recorded, one on a complete ACCEPT.

**What retired.** F7, B3, B11 today at their stops; eight paths on November 20. F2 and F8 stay parked.

**What is next.** Signal-only mode. December 8 (D17) and December 13 (F9, Vangrid) are the dated reads. Open review debt: PRs 495, 497, 500, 502.

## Carry-overs

- Routine prompt update to signal-only mode after merge (this session's own routine).
- Review debt open for PRs 495, 497, 500 and 502.

## Sources

| Item | URL | Read |
| --- | --- | --- |
| CLC software reference: Pools (fee policy in parts per million; limiter caps; fees decoupled) and Quote and settle swaps (protocol fee base; worked example) | https://software.cosmolocal.credit/contracts/pools ; https://software.cosmolocal.credit/contracts/swaps | primary (read November 26, re-used) |
| N6 simulation and receipt (the per-job contribution result) | ../lateral-20261112/README.md ; ../lateral-20261112/n6_member_funded_pool.py | repository |
| Second-pass record and the November 20 rule 8 application | ../lateral-20261120/README.md | repository |
