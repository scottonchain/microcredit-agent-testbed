# Daily lateral run, November 14, 2026: F4 clearing-ring simulation and F1 paid data work test

Claude Code (AI), the daily lateral-register run. Public sources and a deterministic simulation only; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5. No register or direction date fell due today; of the November 15 items F4 is done here a day early, and the F11 and F12 re-read stays for tomorrow's run, which also falls after the steward's D17 W3 checkpoint (18:10 UTC). Both tests are far-lateral (F) paths.

## Receipt 1 (F4, mutual credit clearing for micro-businesses): the clearing-ring simulation

**Test (register, due November 15):** simulate a clearing ring on the contract's dues mechanics; stop if no candidate network of members exists. Script: [f4_clearing_ring.py](f4_clearing_ring.py), stdlib only, fixed seed. Members invoice each other on a random trading network (density d, 60 percent of partner pairs trade each period, lognormal invoice sizes), 24 periods. Each period the ring nets bilateral obligations, then multilateral positions, then lets a member carry a negative balance up to an earned credit line: a fixed share (10 percent) of the member's cumulative settled turnover plus a 1-unit floor, which is the contract's rule that credit beyond issued lines and stake is earned through dues, applied to trade instead of interest. Cash is needed only for net debt beyond a member's line.

| Members | Density (mean partners) | Settled by bilateral netting | By multilateral netting | With earned credit lines | Cash per 100 of gross trade, netting only | With credit | Members hitting their line |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | 0.05 (0.9) | 4 percent | 32 percent | 43 percent | 68 | 57 | 65 percent |
| 20 | 0.20 (4.5) | 7 | 56 | 64 | 44 | 36 | 70 |
| 20 | 0.40 (8.2) | 18 | 68 | 77 | 32 | 24 | 75 |
| 50 | 0.05 (2.7) | 1 | 46 | 53 | 54 | 47 | 60 |
| 50 | 0.10 (4.9) | 2 | 59 | 67 | 41 | 33 | 68 |
| 50 | 0.20 (10.2) | 6 | 71 | 78 | 29 | 22 | 58 |
| 50 | 0.40 (20.7) | 14 | 80 | 85 | 20 | 15 | 68 |
| 200 | 0.05 (10.0) | 2 | 70 | 76 | 30 | 24 | 66 |
| 200 | 0.10 (19.7) | 4 | 78 | 83 | 22 | 17 | 65 |
| 200 | 0.20 (39.7) | 7 | 85 | 89 | 16 | 11 | 65 |
| 200 | 0.40 (79.8) | 14 | 90 | 94 | 11 | 6 | 53 |

**Reading.** Bilateral netting alone does almost nothing (2 to 18 percent); the value is in multilateral clearing, which settles a third of gross trade in a 20-member ring with one partner each and nine tenths in a 200-member ring where everyone trades with 80 others. Earned credit lines add 5 to 10 points on top and cut cash needs by a further quarter to a half, but two thirds of members hit their line at some point, so the ring needs a settlement rule for persistent net debtors either way. The register's Sardex anchor (obligation clearing cut net internal debt about 25 percent; about 50 percent with mutual credit) sits inside the 20-to-50-member, sparse-network rows here, which is the size a first ring would have. **What decides F4 is not the mechanism but the network:** the cash saving tracks the mean number of trading partners per member (members times density) more than the member count. With one to three partners per member the ring settles under half of gross trade without cash (32 to 46 percent); at about five partners it settles just over half (56 to 59 percent); at ten or more, 70 percent or more; and most members hit their credit line at every size simulated. Codex's source-consistency check on the first head (PR 477 comment 6883360356) caught the earlier wording, which stated a 50-member cutoff the 20-member rows contradict. **Classification: bound.** The stop ("no candidate network of members exists") is still the live question and this register has none: the team has no member businesses and no channel to a dense local trading network (register L2). **Score:** evidence 2 to 3; total 11 to 12. **What F4 becomes:** a sized design note. A ring is worth proposing to a partner only where member businesses already trade with about five or more other members each (at five, just over half the cash is saved; at ten, about three quarters); with fewer partners per member, netting without credit is the cheaper first step. A sharper cutoff would need a real ring's accounts, not this table.

## Receipt 2 (F1, paid data work in low-resource languages, agents as the quality layer)

**Test (register):** find one open paid dataset programme whose payer and per-task rate are public and whose validation is a stated bottleneck; stop if validation is not the bottleneck.

**Found [primary reads of karya.in/impact, reports.karya.in/2025, platform.karya.in; arXiv 2602.14062 abstract; press for the hourly rate]:**

| Programme | Payer and rate public? | Validation a stated bottleneck? |
| --- | --- | --- |
| Karya (India; Kenya, Ethiopia, South Africa, Bangladesh deployments) | Payers are AI labs and foundations (the site names industry partners; the 2025 report names Google.org, LinkedIn's Future of Work Fund and Target Foundation among supporters). Scale is public: 134,565 workers onboarded as of January 2026, 3.2 million dollars of cumulative direct wages by end 2025 (4.42 million by July 2026 on the impact page), 65 million tasks, 70 languages; the per-hour rate (about 5 dollars) is reported in press since 2023, not on the pages read. Cumulative wages per onboarded worker average about 24 to 33 dollars. | No. The platform page says "our validation framework and feedback loop, that uses both human and AI tools to address errors, ensures top quality data at every step." Validation is in-house and presented as solved. |
| Mozilla Common Voice (open corpus; Pashto audited in arXiv 2602.14062, February 2026) | No payer: contributors are volunteers; the data is a public good. | Yes, measured: 975.89 validated hours of 2,768.7 recorded (35.2 percent); the authors list "expanded validation capacity" first among the priorities; the same paper's cross-language table runs from 27 percent (Urdu) to 87 percent (Persian) validated. |

**Reading.** The test's two conditions are met at two different programmes and nowhere together: the programme that pays publishes no validation gap, and the programme with a measured validation gap pays nobody. For F1's proposed role (agents as the quality layer), the measurable target is Common Voice's unvalidated backlog, where an agent-run validator would add dataset maturity, not wages; at Karya, validation is already the vendor's product. **Classification: bound.** The stop ("validation is not the bottleneck") is met for the paid programme and not met for the unpaid one. **Score:** evidence 2 to 3; total 10 to 11. **What F1 becomes:** a public-good contribution option outside this register's aim (worker income), parked unless a paid programme publishes a validation gap; re-entry condition recorded.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| F4 | November 14 bound; sized design note (about five trading partners per member) | none; re-entry on a candidate network (L2) |
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
