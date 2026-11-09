# Per-state checklist row (template), with Colorado filled in

Draft by Claude Code (AI), November 3, 2026. The pilot lends to Colorado residents only until a row exists for another state ([legal analysis](../legal-analysis.md) section 2, step 2). A row is complete when every cell has a primary read or a stated secondary source, a date, and a decision. Adding a state is a lane decision recorded in the model; it never adds money, contact or deployment authority.

## The row (one per state)

| Cell | Question | How to answer | Colorado (filled November 3, from the legal analysis) |
| --- | --- | --- | --- |
| 1. Consumer-loan definition | What makes a loan a "consumer loan" under this state's code, and is business-purpose credit excluded? | Read the state's consumer credit code definitions | Consumer loan: by a person regularly engaged, to an individual, for personal, family or household purpose, with a finance charge or instalments, up to 75,000 dollars; business, investment, commercial and agricultural loans excluded [primary: C.R.S. 5-1-301(15)] |
| 2. Business-purpose lender licence | Does the state license lenders making business-purpose loans? | State licensing statute; secondary nationwide guides as a map | No licence found for business-purpose lending [secondary: nationwide licensing guide]; Door A open |
| 3. Commercial-financing disclosure law | Does the state require disclosures on commercial financing, and what is its volume or amount floor? | State statute list (about ten states have one) | None in Colorado [secondary: law-firm survey] |
| 4. Consumer rate ceiling without a licence | Up to what rate may an unlicensed lender make a consumer loan? | Rate section of the consumer credit code | 12 percent a year on the unpaid balance [primary: 5-2-201(1)] |
| 5. Licence threshold | What makes a consumer loan a licensed (supervised) loan? | Definitions plus licensing section | Above 12 percent [primary: 5-1-301(47), 5-2-301] |
| 6. Notification or registration filing | Does the code require a filing from a lender below the licence line? | Notification part of the code | No; the notification part does not apply to persons making consumer loans [primary: 5-6-201(2)] |
| 7. "Regularly engaged" test | How many loans a year make a person a lender under the code? | Definition or cross-reference to TILA | TILA meaning: more than 25 consumer-credit extensions in the preceding calendar year [primary: 5-1-301(37); 12 CFR 1026.2(a)(17)(v)] |
| 8. Small-loan or payday statute | Is there a separate small-loan act that captures loans of this size regardless of rate? | Search the code for small-loan, deferred-deposit, payday | Colorado's deferred-deposit (payday) article defines its loan as a consumer loan in which the lender accepts a dated instrument from the consumer as sole security, holds it before negotiation or deposit, and pays the amount less the article's charges; "instrument" means a personal check or a signed authorisation to transfer or withdraw funds from an account [primary: C.R.S. 5-3.1-102(3), (4), read 2026-11-09]. A 90-day Door B loan collected by the borrower's own transfer, with a backer's deposit as its only security, is outside it; a Door B loan collected through a debit authorisation signed at origination risks falling inside it, so the agreement takes none (Door A, not a consumer loan, is outside the article) |
| 9. Money transmission and virtual-currency regime | Does lending in dollars with a USDC treasury touch the state's money-transmission or virtual-currency law? | State MTMA version; any virtual-currency guidance | Division of Banking interim guidance of December 18, 2025: virtual currency is not "money" under the MTMA; conversion to fiat is where the licence question returns [secondary, host 403]; the lender does not transmit and converts only its own treasury |
| 10. Usury ceiling (general) | What is the general usury cap and does it reach this loan? | Interest statute | Below every cap found at 9.33 percent [secondary]; the UCCC line of 12 percent is the binding one |
| 11. Data-breach and privacy law | What does the state require on breach notification and data protection? | State statute | C.R.S. 6-1-716 breach notification [secondary; not reached on November 3]; the safeguards page covers it |
| 12. Complaint route | Where does a borrower complain, and what is named in the agreement? | Regulator's consumer page | Colorado Attorney General, Consumer Credit Unit [secondary; page empty to the maintainer session] |
| 13. Decision | Open the state to Door A, Door B, both or neither, with the date and the cells that decided it | Lane decision, recorded in the model | Door A and Door B open from November 3 (legal analysis, decision:d16-compliance-design-20261103) |

## Rules for adding a state

- Cells 1, 4, 5, 6 and 7 need a primary read of the statute; a secondary summary opens nothing.
- A state that licenses business-purpose lenders, or whose consumer rate ceiling without a licence is below the live rate, is closed to that door until a licence exists, which is an operator decision (queue row).
- The app's residence question is the gate: a state with no row is declined with reason code R10 and the applicant is told the state may open later.
- Each new row is one commit in this folder, named `state-XX.md`, and one claim in the model.
