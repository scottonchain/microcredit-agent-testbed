# Daily lateral run, November 15, 2026: the November 15 decisions, the F11 and F12 re-read, and the N8 payout-timing comparison

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5.

## Decisions due today (rule 1)

| Item (register and DIRECTIONS, November 15) | Decision | Receipt |
| --- | --- | --- |
| N6 zero-sponsor simulation | DONE November 12 | [receipt](../lateral-20261112/README.md) |
| F4 clearing-ring simulation | DONE November 14 | [receipt](../lateral-20261114/README.md) |
| N7 voucher-versus-guarantee note | DONE November 13 | [receipt](../lateral-20261113/README.md) |
| F11 and F12 score re-read | DONE today, below | this file |
| Rule 8 (two runs without a score-moving receipt) | NOT TRIGGERED: November 13 moved N7, November 14 moved F4 and F1, today moves F11, F12 and N8 | register |

**Observed, not mine to decide:** the steward accepted the D17 W3 sandbox step on November 12 with a first checkpoint at November 15 18:10 UTC (board 462 comment 6833409101). At 19:50 UTC board 462 carried no such receipt and PR 467 was unchanged since November 12 (one commit, draft). Reported to the directions session, which holds D17 under rule 9, by session message; recorded here as the input to the F12 re-read.

## Receipt 1: F11 and F12 re-read against the D16 and D17 receipts of November 11 to 14

**F12, the licensed lender's conversational servicing agent (D17).** Since November 3: the D17 geography was decided November 12 (Kenya rails partner-only after the provider-terms read, Guatemala partner route); the W3 sandbox was accepted by the steward as text-only ("no voice capability, a stated limitation") with zero consented testers recorded, and its first checkpoint has no receipt at the time of this run; no session claims the D17 owner seat. The cheapest test as written in the register (a Spanish voice agent on the test app ledger with five testers, November 17) therefore has no owner, no voice and no testers two days before its date. **Score:** execute 2 to 1; evidence 3 unchanged (the packet, the terms reads and the sandbox design are real); total 12 to 11. **Classification: bound** on capacity, not on evidence; re-entry when a session claims the W3 seat or the sandbox checkpoint lands.

**F11, remittance-linked repayment through a licensed WhatsApp remitter settling in USDC (D17 option M3).** The D16 lane's provider-terms reads of November 12 to 14 (`claim:provider-terms-restrict-lenders-20261113`; evidence `ev:bridge-prohibited-activities-20261113`, `ev:eversend-business-terms-20261113`) found Bridge's developer agreement bars enabling credit services, Eversend's business terms list certain financial services and debt collection as prohibited, and Flutterwave lists lending and collections as prohibited; the W1 pricing (`claim:d17-w1-local-currency-rails-priced-20261111`) put the Kenyan shilling legs at about 3.6 percent before margin. F11 needs a licensed remitter willing to take a lender of record as the receiving counterparty, and every provider read so far excludes or reserves that at approval. **Score:** evidence 2 to 3 (terms read); execute 1 unchanged; total 9 to 10. **Classification: bound** by provider terms; re-entry when a remitter's terms admit a lender of record, which the D17 partner route (Guatemala) is the only live path to.

## Receipt 2 (N8, payment timing instead of nonpayment insurance): the payout-timing comparison

**Test (register):** a payout-timing comparison; stop if channels already pay within days free.

| Channel | Standard payout | Faster option | Read |
| --- | --- | --- | --- |
| DoorDash (Dasher Central, DoorDash Crimson page) | "weekly direct deposits" at no fee | "withdrawing funds daily with FastPay for a $1.99 fee"; with the platform's own account, "payouts after every dash, at no fee ... within minutes" | primary |
| Prolific participants | cash out once 6 dollars or pounds are earned; "instantly transferred to your PayPal" | none needed | primary |
| HumanPing (November 12 read) | "Instant Payout" after proof is verified, by Stripe, PayPal or USDC | none needed | primary |
| Rentahuman (November 13 read) | escrow released to the worker on the buyer's approval | none needed | primary |
| Upwork | a security period of several days after the client is billed; Upwork's support says Top Rated freelancers are paid "five days sooner"; instant transfer to a US debit card for about 2 dollars | secondary (support page blocked here) | 
| Fiverr | a 14-day clearance after order completion (7 for top sellers per guides); instant transfer for select banks | secondary (help pages blocked here) |

**Reading.** On the channels this register has read directly, workers are paid within a day, free or for about 2 dollars, and often within minutes. The waits that remain (Upwork's security period, Fiverr's clearance) are dispute windows built into marketplace design, not a financing gap a third party can close for less than the platforms' own 2-dollar instant options; and the CFPB's December 2025 treatment of certain earned-wage products as outside credit (the register's anchor) is about employer payroll, not these channels. **Stop met: channels already pay within days free.** **Classification: NONE for the lateral path; bound as a fact for intake:** a borrower whose problem is a 5 to 14 day marketplace wait has a 2-dollar option before any loan. **Score:** evidence 2 to 3; execute 2 to 1; total 9 unchanged. Retired from the active list at its own stop; re-entry only if a channel with a wait longer than 14 days and no instant option appears in a borrower's record.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| F12 | November 15 re-read: execute 2 to 1; W3 checkpoint unreceipted at run time | directions session under rule 9; register re-read on a claimed seat |
| F11 | November 15 re-read: bound by provider terms | re-entry on a remitter admitting a lender of record |
| N8 | November 15 NONE; retired at its stop | re-entry condition only |
| F9 | November 13 bound on the buyer side | December 13 repeat read |
| F4, F1, N6, N7, N5, N1 | bound | re-entry conditions |
| B8 | November 10 activity trace | payment trace by a lane with a wallet |
| D16 | November 14 run merged (PR 478) | November 17 interview report |
| Held merges (PR 456, 458) | operator-queue row November 12 | operator names who may merge |

## Sources

| Item | URL | Read |
| --- | --- | --- |
| DoorDash Crimson page (weekly deposits, FastPay 1.99, instant at no fee) | https://dasher.doordash.com/en-us/about/dasherdirect | primary |
| Prolific participants page (cash out from 6 dollars, instant PayPal transfer) | https://www.prolific.com/participants | primary |
| HumanPing payout rails | https://humanping.io/ | primary, November 12 |
| Rentahuman escrow release | https://rentahuman.ai/about | primary, November 13 |
| Upwork faster payouts (support article, blocked here; title read from search) | https://support.upwork.com/hc/en-us/articles/360047676133 | secondary |
| Fiverr clearance (help pages blocked here) | https://help.fiverr.com/hc/en-us/articles/360010978617-Withdrawing-funds | secondary |
| D16 provider-terms claim and evidence | world-model/model.json: claim:provider-terms-restrict-lenders-20261113, ev:bridge-prohibited-activities-20261113, ev:eversend-business-terms-20261113 | repository |
| Steward's D17 W3 acceptance and checkpoint date | https://github.com/scottonchain/microcredit-agent-testbed/issues/462#issuecomment-6833409101 | primary |
