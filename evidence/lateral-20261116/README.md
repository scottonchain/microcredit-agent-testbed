# Daily lateral run, November 16, 2026: F3 index-trigger simulation and the F5 appeals table

Claude Code (AI), the daily lateral-register run. Public sources and a deterministic simulation only; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5. No register or direction date fell due today. Carry-over landed in this PR: Codex's post-merge correction of the N8 receipt (board 462 comment 6901157376), which separates earnings clearance from withdrawal on Upwork and Fiverr and removes the categorical intake inference; applied to the November 15 receipt, the N8 register row and the owning claim, with Codex's four support-page reads recorded as teammate reads. Both tests today are far-lateral (F) paths, the two highest-ranked without a receipt.

## Receipt 1 (F3, index insurance payouts through the conditional-payment contract): the index-trigger simulation

**Test (register):** an index-trigger simulation on public rainfall data run through the existing ruin machinery; stop if capital or licensing needs exceed any plausible sponsor. Script: [f3_index_trigger.py](f3_index_trigger.py); data: NASA POWER monthly precipitation at 9.40N 0.84W (Tamale, northern Ghana, the Karlan, Osei, Osei-Akoto and Udry site), 1981 to 2025, saved beside the script as served [primary public data]. Index: May to October rainfall; trigger: a season below the record's 20th percentile (792 mm; 9 of 45 seasons: 1990, 1998, 2000, 2001, 2002, 2013, 2017, 2024, 2025; median season 963 mm). Pool: n farmers paying premium k a season, each paid G = 60 on a trigger, c = 2 a policy; seasons drawn by bootstrap from the record; ruin over 30 seasons; the pure premium is p times G plus c, paid every season (the first head priced it with the guarantee model's break-even, which divides by one minus p because the guarantee's contribution is collected only on jobs that do not default; Hermes's review, PR 482 comment 6927721258, caught it, and this is the corrected run).

| Farmers | Premium (multiple of the pure premium 14.00) | Ruin within 30 seasons on 100 dollars of capital | Capital for 5 percent ruin | Capital per farmer | Capital as a multiple of the sum insured |
| --- | --- | --- | --- | --- | --- |
| 1 | 14.00 (pure) | 39 percent | 280 | 280 | 4.7 |
| 1 | 17.50 (1.25) | 20 percent | 200 | 200 | 3.3 |
| 1 | 21.00 (1.5) | 9 percent | 120 | 120 | 2.0 |
| 1 | 28.00 (2.0) | 1 percent | 70 | 70 | 1.2 |
| 10 | 14.00 (pure) | 83 percent | 2,760 | 276 | 4.6 |
| 10 | 28.00 (2.0) | 31 percent | 680 | 68 | 1.1 |
| 100 | 14.00 (pure) | 83 percent | 27,600 | 276 | 4.6 |
| 100 | 17.50 (1.25) | 70 percent | 19,500 | 195 | 3.2 |
| 100 | 21.00 (1.5) | 61 percent | 12,300 | 123 | 2.0 |
| 100 | 28.00 (2.0) | 40 percent | 6,800 | 68 | 1.1 |
| 1,000 | 17.50 (1.25) | 70 percent | 195,010 | 195 | 3.2 |
| Comparison: the guarantee pool's own machinery at the same p = 0.2, independent jobs, 1,000 jobs at 1.25 times its break-even | | | 540 | 0.54 a job | |

**Reading.** The pure premium is 14 dollars, 23 percent of the sum insured (a one-in-five trigger plus costs); the Ghana trial sold at the actuarially fair price and 40 to 50 percent of farmers bought. The pool's problem is not the premium but correlation: every policy on one index pays in the same season, so the capital needed per farmer does not fall with size. It is about 280 dollars per farmer at the pure premium, 200 at 1.25 times, 120 at 1.5 times and 70 at twice (4.6, 3.3, 2.0 and 1.1 times the 60-dollar sum insured, because the record contains back-to-back trigger seasons: 2000 to 2002, and 2024 to 2025); the same machinery with independent claims needs about half a dollar a job. A 100-dollar sponsor pool covers one farmer with a two-in-five chance of ruin at the pure premium, and 100 farmers need 7,000 to 28,000 dollars. This is why index insurance is reinsured, not revolved. **Stop met: capital needs exceed any plausible sponsor at this project's scale, and licensing (regulated insurance) is untouched.** **Classification: NONE** for a sponsor-funded contract; the conditional-payment shape is right and the capital is not. **Score:** evidence 2 to 3; execute 1 unchanged; total 10 to 11 by evidence alone. **What F3 becomes:** a sized fact for the record: a parametric payout of G needs about three to five times G per policy in capital at pure or lightly loaded pricing on this series, which is a reinsurer's balance sheet; re-entry only if a licensed insurer or reinsurer offers to carry the risk and wants the contract as its payout rail.

## Receipt 2 (F5, appeals of wrongly denied claims and benefits): the source-linked table

**Test (register):** a source-linked table of appeal rights, deadlines and overturn rates by programme; stop if existing advocates already saturate the channel.

| Programme | Appeal right and deadline | Decision time | Denials and outcomes | Read |
| --- | --- | --- | --- | --- |
| HealthCare.gov marketplace plans, claim denials | Internal appeal within 180 days of the denial notice; external review after, or at the same time if urgent; a state Consumer Assistance Program may file for the consumer | 30 days for a service not yet received, 60 for one already received; an expedited appeal as quickly as the condition requires, at least within 4 business days | 19 percent of in-network claims denied in 2023 (1 to 54 percent by insurer); consumers appealed about 1 percent of denials; insurers upheld 56 percent on internal appeal; external appeals rare | primary (HealthCare.gov internal-appeals page; KFF, January 27, 2025) |
| Marketplace eligibility decisions | 90 days from the eligibility notice; late appeals with a reason | not stated | not stated | primary (HealthCare.gov) |
| Prior authorization, 2025 | per plan rules | per plan rules | denial rates 12 percent (Medicare Advantage), 14 (Medicaid managed care), 18 (marketplace); of the few appealed, 67, 47 and 43 percent overturned | secondary (press on KFF's August 2026 analysis; KFF page not fetched) |
| Medicare | five levels of appeal; a free State Health Insurance Assistance Program counsellor; a representative may be appointed; fast appeal when services are ending | per level | not on the page read | primary (Medicare.gov), deadlines per level not extracted |
| Unemployment insurance, lower-authority appeals | state deadlines, commonly 10 to 30 days from the determination | varies | the Department of Labor publishes reversal rates by state and quarter from the ETA 5130 report; the national claimant reversal rate at lower authority was 28.7 percent for the year to September 30, 2023 (10.7 at higher authority) | primary page for the definition (oui.doleta.gov, the table needs a form selection this proxy did not complete); the figure secondary (Experian citing DOL) |
| Social Security disability, hearing level | reconsideration and hearing requests within 60 days of each notice | months | monthly ALJ disposition data by hearing office (awards, denials, fully and partially favourable) is published; the pages refuse this proxy, so no FY2025 rate is quoted | pointer only (data.gov catalogue; ssa.gov blocked here) |

**Reading.** The channel is not saturated: about one marketplace denial in a hundred is appealed, and where appeals happen roughly half succeed (44 percent of internal marketplace appeals not upheld, KFF's 56 percent upheld; 43 to 67 percent of prior-authorization appeals overturned; 29 percent of unemployment lower-authority appeals reversed). Free help already exists in each programme (Consumer Assistance Programs, SHIP counsellors, appointed representatives), so the gap is use, as with N5. **Stop not met.** **Classification: lead on the information side, bound on execution:** the register's transfer limits stand (personal data, legal practice, consent, R9), so the only thing this team could ship is a checked template a person or licensed advocate uses, and nothing here shows that a template is what stops people appealing. **Score:** evidence 2 to 3; execute 1 unchanged; total 9 to 10. **Next cheapest test:** none within authority beyond reading the DOL and SSA tables when a route to them exists; re-entry if a consumer-assistance programme publishes a stated bottleneck that a template would relieve.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| F3 | November 16 NONE at this scale; sized fact | re-entry on a licensed carrier |
| F5 | November 16 lead on information, bound on execution | re-entry on a stated template bottleneck |
| N8 | November 16 correction applied (Codex) | retired |
| F12 | November 15 re-read | directions session's November 17 decision |
| F9 | November 13 bound on the buyer side | December 13 repeat read |
| F4, F1, N6, N7, N5, N1, F11 | bound | re-entry conditions |
| B8 | November 10 activity trace | payment trace by a lane with a wallet |
| D16 | November 15 run merged (PR 481) | November 17 interview report |
| Held merges (PR 456, 458) | operator-queue row November 12 | operator names who may merge |

## Sources

| Item | URL | Read |
| --- | --- | --- |
| NASA POWER monthly precipitation, point 9.40N 0.84W, 1981 to 2025 | https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR&community=AG&longitude=-0.84&latitude=9.40&start=1981&end=2025&format=JSON | primary; saved beside the script |
| F3 simulation | f3_index_trigger.py (this folder); experiments/revolving-guarantee/model.py | reproducible |
| Karlan, Osei, Osei-Akoto, Udry (register source) | https://www.nber.org/papers/w18463.pdf | register anchor, not re-read |
| HealthCare.gov, internal appeals | https://www.healthcare.gov/appeal-insurance-company-decision/internal-appeals/ | primary |
| HealthCare.gov, marketplace appeals | https://www.healthcare.gov/marketplace-appeals/ | primary |
| KFF, HealthCare.gov insurers denied nearly 1 in 5 in-network claims in 2023 (January 27, 2025) | https://www.kff.org/private-insurance/healthcare-gov-insurers-denied-nearly-1-in-5-in-network-claims-in-2023-but-information-about-reasons-is-limited-in-public-data/ | primary |
| Medicare.gov, how to file an appeal | https://www.medicare.gov/claims-appeals/how-do-i-file-an-appeal | primary |
| Department of Labor, UI appeals reversal rates (definition; table behind a form) | https://oui.doleta.gov/unemploy/ui_appeal_reversal.asp | primary page, table not read |
| National claimant reversal rate, year to September 2023 (Experian citing DOL) | https://www.experian.com/blogs/employer-services/how-often-do-employees-win-unemployment-appeals/ | secondary |
| KFF 2025 prior authorization analysis (press) | https://www.fiercehealthcare.com/payers/insurers-denied-between-12-18-prior-auth-requests-2025-kff | secondary, blocked here; figures as in the register |
| Codex's N8 correction and the four Upwork and Fiverr support pages it read | https://github.com/scottonchain/microcredit-agent-testbed/issues/462#issuecomment-6901157376 | teammate read |
