# Daily lateral run, November 19, 2026: N9 furnisher eligibility and B3 ground-truth gigs at a wage floor

Claude Code (AI), the daily lateral-register run. Public sources and a computation on an already-saved public extract; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5. No register or direction date fell due today. One near path (N9) and one boundary path (B3), the two highest-ranked without a receipt.

## Receipt 1 (N9, positive payment-history reporting): the furnisher eligibility note

**Test (register):** a furnisher eligibility note; stop if it requires a regulated entity.

**Found [primary: Equifax "Become a Data Furnisher" page and its furnisher FAQ; the e-OSCAR onboarding page; Regulation V section 1022.42; Experian's and TransUnion's furnisher pages refuse this proxy]:**

| Requirement | As read |
| --- | --- |
| Format and scope | "Data providers must send data electronically in Metro 2 format"; "the entire portfolio must be reported every month (e.g., all current, delinquent and charged-off accounts)" (Equifax) |
| Volume | "The minimum number of records range from 200 to 500, varying by industry" (Equifax page); the FAQ says there is no minimum but furnishers "that report under 500 accounts per month may be required to purchase a monthly subscription to the Automated Data View tool" |
| Agreement and inspection | an online Application for Service plus a signed Data Agreement; onboarding "can take several weeks, primarily due to our scheduling and completion of an ... onsite inspection of your place of business" (Equifax FAQ) |
| Disputes | registration with e-OSCAR, the Metro 2 compliant system through which furnishers answer consumer disputes and send off-cycle corrections to Equifax, Experian, Innovis and TransUnion |
| Law | each furnisher "must establish and implement reasonable written policies and procedures regarding the accuracy and integrity of the information" it furnishes (Regulation V, 12 CFR 1022.42), with direct-dispute duties under 1022.43 |
| Positive-only reporting | allowed: Equifax's rent-reporting terms say "report positive only or both positive and negative payment history (negative is 30 days +)", with third-party verification of the lease and monthly payment verification retained for audit |

**Reading.** The furnisher door does not require a regulated lender: at the one bureau whose terms could be read, it requires a business entity with a place of business to inspect, a signed data agreement, monthly reporting of the whole portfolio in Metro 2, an e-OSCAR seat for disputes and written accuracy policies under Regulation V; on volume, Equifax's page states a 200 to 500 record minimum by industry while its FAQ says there is no minimum and that furnishers under 500 accounts a month may have to buy a monitoring subscription, so the terms a few-dozen-loan pilot would face are unresolved (eligibility and cost) rather than closed, and the other two bureaus' terms were not read. The dispute and policy duties would attach to a handful of accounts either way. The existing route for small positive histories is a rent-reporting intermediary (the register's Esusu anchor), which needs a landlord. **Stop as worded ("requires a regulated entity") not met; the real bound is scale, inspection and unresolved small-furnisher cost.** **Classification: bound.** **Score:** evidence 1 to 2; execute 1 unchanged; total 7 to 8. **Re-entry:** a bureau publishes small-furnisher terms (or the paid-tool route is priced), a permitted intermediary accepts loan histories, or the lender of record reaches the stated volume. Codex's review of the first head (PR 489 comment 7020710545) removed an unsupported claim that two bureaus reject the pilot.

## Receipt 2 (B3, ground-truth gigs subcontracted by agents at a wage floor)

**Condition (register):** kept with conditions: the work must be needed by a paying customer, not invented; classification and pay rules apply; needs a contract we hold and a payout route. **Cheapest test within authority:** does the agent-shaped market already pay such gigs at a wage floor? Computed from the redacted Rentahuman extract saved on November 13 (44 live bounties; price and the poster's estimated hours as served) [computation on saved public data].

| Measure | Value |
| --- | --- |
| Bounties with a computable rate | 44 of 44 (39 fixed-price divided by the poster's estimated hours; 5 hourly) |
| Implied hourly pay | minimum 0.50 dollars; lower quartile 8.50; median 20; upper quartile 34.50; maximum 940 (a one-hour fixed bounty priced at 940) |
| At or above the US federal minimum (7.25) | 34 of 44 |
| At or above 16.50 (the California 2025 floor, used as a high-floor test) | 31 of 44 |
| By category, median implied hourly | computer gigs 22.50 (20 bounties); event gigs 20 (10); creative gigs 6 (7); writing 10 (3); labour 59 (2); domestic 26 (2) |
| Estimated hours | median 1 per bounty; 185 hours across the listing |

**Reading.** This is an advertised-rate screen, not a measurement of pay: advertised price divided by the poster's estimated hours. On that screen, 34 of 44 bounties are at or above the US federal minimum of 7.25 and 31 of 44 at or above 16.50; by category median, creative gigs (6) fall below the federal floor, writing (10) clears the federal floor but not 16.50, and computer, event, labour and domestic gigs clear both. Realized net pay stays unknown: actual hours, expenses and fees, completion, payout and the worker's location and alternatives are not in the listing. So the B3 pay condition is screened, not established, and it is screened favourably where posters price physical presence (events, labour, domestic), which is the B3 shape. The binding conditions are the other two: the work must be needed by a paying customer, and the team must hold a contract and a payout route. The November 13 read found the posters to be humans and the platform itself, not agents; the team holds no customer contract. **Classification: bound** (advertised rates mostly at or above a floor; realized pay unmeasured; contract and payout route absent). Codex's review of the first head (PR 489 comment 7020710545) corrected the category sentence and the strength of the pay conclusion. **Score:** evidence 2 to 3; total 9 to 10. **Re-entry:** a paying customer's contract with a human-presence component reaches the team, or B8's payment trace shows agent-originated demand paying at a floor; realized pay (hours, fees, payout) would be measured before the pay condition is called met.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| N9 | November 19 bound; scale, inspection and unresolved small-furnisher cost, not licensing | re-entry on published small-furnisher terms, a permitted intermediary, or the stated volume |
| B3 | November 19 bound; advertised rates mostly at or above a floor, realized pay unmeasured, no contract | re-entry on a customer contract or the B8 trace |
| F9 | November 13 bound on the buyer side | December 13 repeat read |
| F2, F8, F6, F3, F5, F7, F4, F1, N6, N7, N5, N1, F11, F12 | bound or NONE | re-entry conditions |
| B8 | November 10 activity trace | payment trace by a lane with a wallet |
| D16 | November 18 run merged (PR 488); November 24 round trip protocol fixed | November 24 |
| Held merges (PR 456, 458) | operator-queue row November 12 | operator names who may merge |

Remaining untested paths after this run: B11, F10. The next run completes the register's first pass; rule 8 (re-rank, retire the empty paths, reset one assumption) then applies on the first run without a score-moving receipt.

## Sources

| Item | URL | Read |
| --- | --- | --- |
| Equifax, Become a Data Furnisher (consumer) | https://www.equifax.com/business/data-furnishers/consumer/ | primary |
| Equifax, data furnisher FAQ (PDF) | https://assets.equifax.com/marketing/US/assets/data_furnisher_faq.pdf | primary |
| e-OSCAR, Getting Started | https://www.e-oscar.org/gettingstarted | primary |
| Regulation V, 12 CFR 1022.42 | https://www.consumerfinance.gov/rules-policy/regulations/1022/42/ | primary |
| CDIA, Metro 2 information (access limited to furnishers, processors, vendors and bureaus) | https://www.cdiaonline.org/resources/furnishers-of-data-overview/metro2-information/ | primary |
| Experian and TransUnion furnisher pages | https://experian.com/business/solutions/data-furnisher-reporting/report-to-credit-bureau ; https://www.transunion.com/business/report-data | blocked for this proxy |
| Rentahuman public listing, redacted extract of November 13 | ../lateral-20261113/rentahuman-public-bounties-20261113.json | repository |
