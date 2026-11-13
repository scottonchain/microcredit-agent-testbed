# Daily lateral run, November 13, 2026: F9 buyer-side trace from a public bounty listing; N7 voucher-versus-guarantee multiplier note

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5. No register or direction date fell due today; the November 15 items stand (N7 is done early here; F4 and the F11 and F12 re-read remain). Carry-over landed: the HumanPing fee wording in the November 12 receipt and claim (Hermes, PR 466 comment 6835305378).

## Receipt 1 (F9, paid human evaluation and jury work bought by the agent economy): the buyer side, read from a public listing

**Test:** the November 12 next step: a buyer-side trace from any seller that publishes its task feed. Rentahuman's documentation says "Search and browse flows are free" and `GET /api/bounties` lists public bounties with an optional key; read without a key on November 13 at about 19:50 UTC, one page, `count 44, hasMore false` [primary: a redacted extract of the listing (no titles, descriptions, names or profile ids) is saved beside this file as `rentahuman-public-bounties-20261113.json`, 44 records].

| Measure | Value as served |
| --- | --- |
| Live public bounties | 44 (21 open, 14 partially filled, 9 assigned); created October 2 to November 13 |
| Posted in the last eight days (November 6 to 13) | 21 bounties, 3,078 dollars of posted pay, 19 spots filled; 16 of them in the last three days |
| Pay | all in USD; 39 fixed-price (median 20 dollars, total 4,943) and 5 hourly (median 25 dollars an hour); range 0.50 to 700 dollars |
| Who posts (the listing's `agentType`) | human 25, other 11, admin 8; the eight admin posts and seven more are by "RentAHuman Team" or "rentahuman team"; no value says agent |
| Funding | escrow 36, enterprise 7, admin 1 |
| Spots and applicants | 323 spots, 112 filled, 211 open; 2,226 applications in total, median 25.5 per bounty; 36,729 views |
| Work | computer gigs 20, event gigs 10 (conference sign holders in San Francisco at 580 to 700 dollars for four days), creative 7, writing 3, labour 2, domestic 2; remote allowed on 25, in-person 19; 24 in the United States |
| Flags | three bounties ask the worker to create or set up a Claude subscription account in their own name for a payer (5 to 235 dollars); the listing marks identity as required on 4 |

**Reading.** Buying exists and is small: about 5,000 dollars of posted pay across the whole public marketplace, a few new bounties a day, median 20 dollars a task, with roughly seven applicants for every open spot. The listing does not show that any of it is agent-originated: the poster type is human, other or admin, fifteen of the 44 are the platform's own postings, and the largest sums are event sign-holding. So the F9 buyer side, where it can be read, is human buyers of cheap human tasks through an agent-shaped API, with supply far ahead of demand. The account-creation bounties are a harm to note for any worker-side use: a person is paid to open a subscription in their own name for someone else. **Classification: bound** (a public buyer feed read; volume small, supply-heavy, agent origin unshown). **Score:** unchanged at 13; the November 12 "lead" stands on the seller side and the rail, and the buyer side is now measured at one seller. **Next:** none within authority beyond a repeat read in a month to see whether volume or agent-origin fields change; the account needs the lender of record.

## Receipt 2 (N7, first-wage subsidy voucher as the direct-sponsorship comparator): the `M` note

**Test (register, due November 15, done early):** a reproducible note comparing the voucher's multiplier per sponsor dollar with the guarantee's, using the register's source [primary: Levinsohn, Rankin, Roberts and Schöer, "Wage subsidies and youth employment in South Africa", 3ie Impact Evaluation Report 15, 2014, read in full text].

**The voucher as measured.** A voucher worth R833 a month (almost 40 percent of the median monthly wage of sample members who were working) for up to six months, R5,000 in all, paid to the employer who hired the voucher holder. One year on, voucher holders were seven percentage points more likely to be in wage employment, a 25 percent increase, and the effect persisted two years later after the voucher lapsed. Because vouchers were also redeemed on hires that would have happened anyway, the authors' cost per new job is R25,000 at the observed transition rates (range R8,400 to R55,000), against about R100,000 for the public works programme.

**The voucher's `M`** (NORTH_STAR definition: workers' net gain per sponsor dollar consumed). Earnings in a caused job at the sample median of about R2,100 a month are about R25,000 a year; net of the worker's time at the README's s = 0.5 that is R12,600 per caused job, against R25,000 of sponsor money per caused job: **M of about 0.5 in year one, about 1.0 over two years** if the persistence holds at the same size. The R20,000 of each caused job's cost that went to employers of youths who would have been hired anyway is a transfer to firms and counts zero for workers. Displacement of unsubsidised workers, which the authors could not measure, would lower it further.

**The guarantee's `M`** (README section 6, sponsor-funded client refund): M ≈ a·s/f + (1 − a), where a is the share of guaranteed jobs the guarantee causes. The voucher gives the first measured a for a first-job subsidy of this shape: R5,000 of subsidy per hire against R25,000 per caused hire, so a ≈ 0.2. At a = 0.2, s = 0.5, f = 18 percent: M ≈ 1.36 before costs, of which 0.8 is the one-for-one refund to clients of newcomers whose first job failed on a hire that would have happened anyway. Counting only the caused part, the guarantee's M is a·s/f ≈ 0.56 per sponsor dollar at the same a, the same order as the voucher's year-one figure.

**Reading.** On the paper's own numbers the voucher returns about half to one dollar of worker benefit per sponsor dollar, and the guarantee's design beats it only through the (1 − a) refund that reaches workers rather than firms, and only if its refund really does. The register's stop ("voucher `M` below guarantee `M`") is met on these figures, with the caveat that the voucher's M rests on a randomised trial and the guarantee's on an assumed a and f. **What N7 becomes:** the benchmark the C5 scorecard must beat: **about 0.5 to 1.0 dollars of net worker benefit per sponsor dollar is what the best-evidenced direct first-wage subsidy delivers**, and a ≈ 0.2 is the measured share of subsidised first hires that are caused. **Classification: bound.** **Score:** evidence 2 to 3; total 9 to 10.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| F9 | November 13: buyer side read at one seller; small, supply-heavy, agent origin unshown | repeat read December 13; account needs the lender of record |
| N7 | November 13 bound; benchmark M of 0.5 to 1.0 for C5 | none |
| N6 | November 12 bound | none |
| F4; F11, F12 | due November 15 | November 15 run |
| N1, N5, N2, N4, B10, C1, C4 | bound or parked | re-entry conditions |
| B8 | November 10 activity trace | payment trace by a lane with a wallet |
| D16 | November 12 run merged (PR 468) | November 17 interview prototype |
| D17 | W3 sandbox draft PR 467 (steward), checkpoint November 15 18:10Z | November 15 |
| Held merges (PR 456, 458) | operator-queue row November 12 | operator names who may merge |

## Sources

| Item | URL | Read |
| --- | --- | --- |
| Rentahuman public bounty listing (no key) | https://rentahuman.ai/api/bounties?limit=50 | primary; redacted extract saved as rentahuman-public-bounties-20261113.json |
| Rentahuman API documentation (auth and accounts: "Search and browse flows are free") | https://rentahuman.ai/docs | primary |
| Levinsohn, Rankin, Roberts and Schöer, Wage subsidies and youth employment in South Africa, 3ie IE15, 2014 | https://www.3ieimpact.org/sites/default/files/2019-01/ie15-youth_wage_subsidy.pdf | primary |
| Revolving guarantee README, section 6 (multiplier) | ../../experiments/revolving-guarantee/README.md | repository |
