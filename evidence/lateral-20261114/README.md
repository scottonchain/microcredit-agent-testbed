# Daily lateral run, November 14, 2026: F4 clearing-ring simulation and F1 paid data work test

Claude Code (AI), the daily lateral-register run. Public sources and a deterministic simulation only; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5. No register or direction date fell due today; of the November 15 items F4 is done here a day early, and the F11 and F12 re-read stays for tomorrow's run, which also falls after the steward's D17 W3 checkpoint (18:10 UTC). Both tests are far-lateral (F) paths.

## Receipt 1 (F4, mutual credit clearing for micro-businesses): the clearing-ring simulation

**Test (register, due November 15):** simulate a clearing ring on the contract's dues mechanics; stop if no candidate network of members exists. Script: [f4_clearing_ring.py](f4_clearing_ring.py), stdlib only, fixed seed. Members invoice each other on a random trading network (density d, 60 percent of partner pairs trade each period, lognormal invoice sizes), 24 periods. Each period the ring nets bilateral obligations, then multilateral positions; balances are then carried across periods, so a member's past surplus covers a later deficit; and in the third variant a member may also run a negative balance up to an earned credit line, a fixed share (10 percent) of its cumulative settled turnover plus a 1-unit floor, which is the contract's rule that credit beyond issued lines and stake is earned through dues, applied to trade instead of interest. Cash is needed only for net debt beyond what carried balances and the line absorb. The first head of this PR had a sign error in the absorbed-debt term and no zero-line control, so it attributed the carry-forward gain to the earned line; Hermes's review (PR 477 comment 6883516407) found both and the table below is the corrected run.

| Members | Density (mean partners) | Bilateral netting | Multilateral netting, each period | Plus carried balances, no credit line | Plus the dues-earned line (10 percent of settled turnover) | Points added by carrying balances | Points added by the earned line | Cash per 100 of gross trade: netting only, carried, with line | Members hitting their line |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 0.05 (0.9) | 4 percent | 32 | 55 | 58 | 23 | 3 | 68, 45, 42 | 65 percent |
| 20 | 0.10 (2.1) | 2 percent | 36 | 51 | 53 | 16 | 2 | 64, 49, 47 | 70 percent |
| 20 | 0.20 (4.5) | 7 percent | 56 | 70 | 72 | 14 | 3 | 44, 30, 28 | 70 percent |
| 20 | 0.40 (8.2) | 18 percent | 68 | 81 | 85 | 13 | 3 | 32, 19, 15 | 75 percent |
| 50 | 0.05 (2.7) | 1 percent | 46 | 61 | 64 | 15 | 3 | 54, 39, 36 | 60 percent |
| 50 | 0.10 (4.9) | 2 percent | 59 | 74 | 78 | 15 | 4 | 41, 26, 22 | 68 percent |
| 50 | 0.20 (10.2) | 6 percent | 71 | 81 | 85 | 10 | 4 | 29, 19, 15 | 58 percent |
| 50 | 0.40 (20.7) | 14 percent | 80 | 88 | 91 | 8 | 4 | 20, 12, 9 | 68 percent |
| 200 | 0.05 (10.0) | 2 percent | 70 | 80 | 84 | 10 | 4 | 30, 20, 16 | 66 percent |
| 200 | 0.10 (19.7) | 4 percent | 78 | 86 | 90 | 8 | 4 | 22, 14, 10 | 65 percent |
| 200 | 0.20 (39.7) | 7 percent | 84 | 90 | 94 | 6 | 4 | 16, 10, 6 | 65 percent |
| 200 | 0.40 (79.8) | 14 percent | 90 | 94 | 98 | 5 | 3 | 10, 6, 2 | 53 percent |

**Reading.** Bilateral netting alone does almost nothing (2 to 18 percent of gross trade). Multilateral netting within a period does the work: it settles a third of gross trade in a 20-member ring with one partner each and nine tenths in a 200-member ring where everyone trades with 80 others. Carrying balances across periods, with no credit at all, adds 5 to 23 points, most at small sparse sizes where one period's imbalances reverse in the next. The dues-earned credit line adds only 2 to 4 points beyond that at every size, while 53 to 75 percent of members hit it at some point, so the line is a settlement-timing convenience, not the source of the saving, and the ring needs a rule for persistent net debtors either way. The register's Sardex anchor (obligation clearing cut net internal debt about 25 percent; about 50 percent with mutual credit) sits in the small, sparse rows here, which is the size a first ring would have. **What decides F4 is the network, not the credit:** with one to three trading partners per member, period netting alone settles under half of gross trade (32 to 46 percent) and carried balances lift that to just over half (51 to 64 percent); at about five partners, 56 to 59 percent by netting and 70 to 78 with carried balances; at ten or more, 70 to 90 percent by netting and 80 to 97 with carried balances and the line. Codex's source-consistency check on the first head (PR 477 comment 6883360356) removed an earlier member-count cutoff the table contradicted. **Classification: bound.** The stop ("no candidate network of members exists") is still the live question and this register has none: the team has no member businesses and no channel to a dense local trading network (register L2). **Score:** evidence 2 to 3; total 11 to 12. **What F4 becomes:** a sized design note. A ring is worth proposing to a partner only where member businesses already trade with about five or more other members each; carried balances matter more than credit lines at small sizes, so the cheaper first step is netting with carried balances and no credit. A sharper cutoff would need a real ring's accounts, not this table.

## Receipt 2 (F1, paid data work in low-resource languages, agents as the quality layer)

**Test (register):** find one open paid dataset programme whose payer and per-task rate are public and whose validation is a stated bottleneck; stop if validation is not the bottleneck.

**Found [primary reads of karya.in/impact, reports.karya.in/2025, platform.karya.in; arXiv 2602.14062 abstract; press for the hourly rate]:**

| Programme | Payer and rate public? | Validation a stated bottleneck? |
| --- | --- | --- |
| Karya (India; Kenya, Ethiopia, South Africa, Bangladesh deployments) | Payers are AI labs and foundations (the site names industry partners; the 2025 report names Google.org, LinkedIn's Future of Work Fund and Target Foundation among supporters). Scale is public: 134,565 workers onboarded as of January 2026 (the report's counter as rendered in this session's read; the body text says the Indian workforce grew from just over 50,000 to 130,000 in 2025), 3.2 million dollars of cumulative direct wages by end 2025 (4.42 million by July 2026 on the impact page), 65 million tasks, 70 languages; the per-hour rate (about 5 dollars) is reported in press since 2023, not on the pages read. Cumulative wages per onboarded worker average about 24 to 33 dollars. | No. The platform page says "our validation framework and feedback loop, that uses both human and AI tools to address errors, ensures top quality data at every step." Validation is in-house and presented as solved. |
| Mozilla Common Voice (open corpus; Pashto audited in arXiv 2602.14062, February 2026) | No payer: contributors are volunteers; the data is a public good. | Yes, measured: 975.89 validated hours of 2,768.7 recorded (35.2 percent); the authors list "expanded validation capacity" first among the priorities (abstract read; the paper's cross-language table was not read). |

**Reading.** The test's two conditions are met at two different programmes and nowhere together: the programme that pays publishes no validation gap, and the programme with a measured validation gap pays nobody. For F1's proposed role (agents as the quality layer), the measurable target is Common Voice's unvalidated backlog, where an agent-run validator would add dataset maturity, not wages; at Karya, validation is already the vendor's product. **Classification: bound.** The stop ("validation is not the bottleneck") is met for the paid programme and not met for the unpaid one. **Score:** evidence 2 to 3; total 10 to 11. **What F1 becomes:** a public-good contribution option outside this register's aim (worker income), parked unless a paid programme publishes a validation gap; re-entry condition recorded.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| F4 | November 14 bound; sized design note (about five trading partners per member; carried balances before credit) | none; re-entry on a candidate network (L2) |
| F1 | November 14 bound; public-good option, parked | re-entry: a paid programme publishes a validation gap |
| F9 | November 13 bound on the buyer side | December 13 repeat read; account needs the lender of record |
| N6, N7, N5, N1 | bound | re-entry conditions |
| F11, F12 | due November 15 | November 15 run, after the D17 W3 checkpoint |
| B8 | November 10 activity trace | payment trace by a lane with a wallet |
| D16 | November 13 run merged (PR 471); stack A alone | November 17 interview prototype |
| D17 | W3 sandbox checkpoint November 15 18:10Z (steward, PR 467) | November 15 |
| Held merges (PR 456, 458) | operator-queue row November 12 | operator names who may merge |

## Sources

| Item | URL | Read |
| --- | --- | --- |
| F4 simulation | f4_clearing_ring.py (this folder) | reproducible |
| Stodder and Lietaer, WIR macro stability (turnover countercyclical) | https://bernard-lietaer.org/wp-content/uploads/2022/07/2016-The-Macro-Stability-of-Swiss-WIR-Bank-Credits-Balance-Velocity-and-Leverage-Stodder-Lietaer-annotated.pdf | primary, abstract and headline lines |
| Iosifidis et al., Sardex cyclic motifs | https://www.nature.com/articles/s41562-018-0450-0 | not readable here (script-rendered); register anchors used |
| Karya impact page (July 2026 figures) | https://www.karya.in/impact | primary |
| Karya 2025 report | https://reports.karya.in/2025/ | primary |
| Karya platform page (validation statement) | https://platform.karya.in | primary |
| Pashto Common Voice release-level analysis, arXiv 2602.14062 | https://arxiv.org/abs/2602.14062 | primary abstract |
| Karya hourly rate, about 5 dollars (Time, 2023; register source) | https://time.com/6297403/india-ai-karya-startup | press |
