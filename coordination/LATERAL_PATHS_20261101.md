# Lateral paths to the north star: one ranking, one ruled-out register (November 1, 2026, revision 2)

Operator requests, November 1: research online; add lateral paths to the north
star; include the current paths in the same ranking; make the new paths
substantially different, not adjustments; include ideas ruled out on ethical or
operational grounds and ideas ruled out for lack of resources, each marked with
why, because they inspire feasible alternatives; include ten boundary ideas as
creative as the virtual-worlds and human-first paths; prioritize everything not
ruled out in one list and track the rest.

Revision 1 (commit 4bf8b02) held ten paths that were adjustments of existing
work. They are kept here as the "near" tier so the ranking is honest, compressed
to one line each; their full write-ups remain in that commit.

## What lateral thinking is for, who owns it, how it keeps momentum

**Aim.** Since October the team converged three times on a credit-shaped
mechanism (microloan, revolving guarantee, agent credit) and each stopped on the
same missing prerequisites: a channel that reaches a worker or buyer, a payer,
and authority to contact or spend. Lateral thinking here means changing one of
five things so that a path no longer needs the blocked prerequisite: the payer,
the deliverable, the channel, the mechanism, or the asset used. The fixed
objective never changes: measurable, positive, spendable human earnings and
useful economic opportunity.

**Momentum rule.** At every checkpoint at least one cheapest test runs on a path
that does not share the currently blocked dependency, in parallel with the
current path, never only after it fails. Each test returns a receipt classified
as lead, bound or NONE. Receipts move scores; two checkpoints without a
score-moving receipt retire the path. Ruled-out ideas stay in the register below
so their feasible variants can be mined. Natural response windows are not
failures and never justify manufactured activity.

**Ownership, as the repository records it.** The learning procedure
(world-model/LEARNING.md, operator request of November 1) says Codex and Claude
form alternatives independently; Codex retains continuation and selection
ownership, Claude substantive challenge, Hermes bounded channel work. Issue 396
adds: when blocked, produce three distinct options, one avoiding the dependency
and one questioning lending. No record names an owner for a standing lateral
register. This document proposes one: Claude maintains the register and runs the
zero-authority tests it can run (`action:lateral-paths-first-tests-20261101`);
Codex selects which lateral tests enter the hourly cycle and executes those
needing its channels; the operator decides anything that needs money, contact,
accounts or deployment. Acceptance is recorded in the model when given.

**Autonomy, as of November 1, 21:10 UTC.** The operator approved this register,
its integration and autonomous operation on November 1 and directed Claude to
default to accept and approve within the repository's documented gates, without
check-ins. Claude accepts ownership of the register. A daily routine now runs a
fresh Claude session at 12:44 America/Denver: it reads main, recalls lessons,
runs at most two zero-authority cheapest tests, records receipts, validates,
pushes a branch and opens a pull request for review, and announces material
changes on board 15 with a weekly summary on Fridays. It does not merge, spend,
contact anyone, open accounts, deploy or create timers; those limits are in its
prompt. Merging remains a reviewed maintainer step. The routine's sessions
carry no connector tools, so GitHub writes depend on the attached repository
route; the prompt has fallbacks for that.

## Blocked prerequisite, separated by kind

| Kind | Observed fact | Assumption the lateral paths change |
| --- | --- | --- |
| Economics | No borrower with a necessary financed input and positive net return was found. | Credit is the intervention. Most paths below need no credit and no reserve. |
| Distribution | Invitations reached few readers; one was delayed 22h16m. | Our own channel must carry the intervention. Several paths ride channels people already use. |
| Access | No consented worker, client or partner. | A human must be recruited by us. Several paths improve a tool or process humans already use. |
| Mechanism | On protected platforms nonpayment risk is already covered by escrow. | Nonpayment is the binding barrier. Evidence points at hiring decisions and information frictions. |
| Measurement | Small pilots cannot estimate `p`; publication is not use. | Only a pilot produces evidence. Public RCTs and platform data bound parameters first. |
| Currency and permission | No spend, contact, account or deployment authority; small USDC seed "available in principle" (issue 396). | Money is the lever. Several paths move money that already belongs to the person. |

## Ranking criteria

Each path is scored 0 to 3 on the five criteria of LEARNING.md step 5. Ties break
by credible human benefit, then by ability to execute now. Scores are November 1
judgments from the sources in the register; they are revised when a receipt
returns. Tier labels: C current, N near (revision 1), F far-lateral, B boundary.

| Criterion | 0 | 3 |
| --- | --- | --- |
| Credible human benefit | No causal evidence | Randomized evidence of an earnings or employment effect on a comparable barrier |
| Ability to execute now | Needs money, contact or an account we lack | Zero spend, zero contact, capability already demonstrated |
| Useful evidence | The cheapest test teaches little | The cheapest test resolves a named parameter or kills the path |
| Full costs and downside | Spend, legal exposure or participant risk | Near-zero, reversible, no participant risk |
| Reusable value | Nothing carries over | Reuses the contract, review capability or evidence base |

## Unified priority list (everything not ruled out; 29 paths after the November 1 evening receipts)

| Rank | ID | Path | Benefit | Execute | Evidence | Cost | Reuse | Total | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | N1 | Verifiable skill signals and public work evaluations | 3 | 2 | 2 | 3 | 3 | 13 | Receipt: a platform displays partner-issued credentials |
| 2 | B10 | Agent as employer of first resort: a needed first job, prepaid, with a public evaluation | 3 | 1 | 3 | 2 | 3 | 12 | Boundary, kept with conditions; fuses N1 with the issue 396 roadmap |
| 3 | F9 | Paid human evaluation and jury work bought by the agent economy | 2 | 2 | 3 | 2 | 3 | 12 | Far; our own verification need is the first demand trace |
| 4 | B8 | Local-knowledge oracles sold to agents | 2 | 2 | 2 | 2 | 3 | 11 | Boundary, kept |
| 5 | N4 | Open-source tax-filing continuation for unclaimed EITC | 2 | 2 | 2 | 3 | 2 | 11 | Release status recorded |
| 6 | N5 | Nonpayment recovery through existing law | 2 | 2 | 2 | 3 | 2 | 11 | Recovery-rate map specified |
| 7 | F4 | Mutual credit clearing for micro-businesses, no sponsor capital | 1 | 2 | 2 | 3 | 3 | 11 | Far; reuses contract and simulation |
| 8 | N6 | Member-funded mutual pool | 1 | 2 | 2 | 3 | 3 | 11 | Zero-sponsor simulation specified |
| 9 | F3 | Index insurance payouts through the conditional-payment contract | 3 | 1 | 2 | 1 | 3 | 10 | Far; regulated, capital needed |
| 10 | F1 | Paid data work in low-resource languages, agents as quality layer | 2 | 2 | 2 | 2 | 2 | 10 | Far; payer exists (AI labs) |
| 11 | C5 | Revolving first-job payment guarantee | 2 | 1 | 2 | 2 | 3 | 10 | Current conditional hypothesis |
| 12 | C2 | Productive service, API and compute markets with shared human and agent roles (ACP) | 1 | 2 | 2 | 2 | 3 | 10 | Current; one indexed settlement, payer unknown |
| 13 | F5 | Appeals of wrongly denied claims and benefits | 3 | 1 | 2 | 2 | 1 | 9 | Far; template only, no filing |
| 14 | N7 | First-wage subsidy voucher as the direct-sponsorship comparator | 3 | 1 | 2 | 1 | 2 | 9 | `M` comparison specified |
| 15 | F6 | Unclaimed property recovery | 2 | 2 | 1 | 3 | 1 | 9 | Far; information only |
| 16 | N2 | Rules-as-code maintenance for benefits calculators | 2 | 1 | 1 | 3 | 2 | 9 | Receipt Nov 1: candidate 10552 reproduced and fix drafted; parked at its own stop (three earlier PRs unanswered) |
| 17 | C4 | Human-first lending: bounded advance on one real order at a human-owned business (issue 392) | 2 | 1 | 3 | 1 | 2 | 9 | Current; one request sent, reply pending |
| 18 | F2 | Remittance corridor cost reduction | 2 | 1 | 2 | 2 | 2 | 9 | Far; licensing bounds it |
| 19 | F7 | Public procurement set-asides for micro-vendors | 2 | 1 | 2 | 2 | 2 | 9 | Far; no vendor channel |
| 20 | F8 | Payments for ecosystem services with agent-run verification | 2 | 1 | 2 | 2 | 2 | 9 | Far; no farmer channel |
| 21 | B3 | Ground-truth gigs subcontracted by agents at a wage floor | 2 | 1 | 2 | 2 | 2 | 9 | Boundary, kept with conditions |
| 22 | N3 | Cooperative or placement channel with its own clients | 1 | 2 | 1 | 3 | 2 | 9 | Receipt Nov 1: clients pay the platform up front; stop met for client nonpayment; spawned B11 |
| 23 | C1 | Virtual and creator worlds with human co-creators (Roblox, Second Life) | 1 | 2 | 2 | 2 | 2 | 9 | Current research slice |
| 24 | N8 | Payment timing instead of nonpayment insurance | 1 | 2 | 2 | 2 | 2 | 9 | Specified |
| 25 | B11 | Worker payout guarantee against cooperative platform liquidity failure | 1 | 1 | 2 | 2 | 3 | 9 | Boundary from the N3 receipt; needs a cooperative channel (L2) |
| 26 | F10 | AI tutoring for earnings-relevant skills | 2 | 1 | 1 | 2 | 2 | 8 | Far; long horizon |
| 27 | N9 | Positive payment-history reporting | 1 | 1 | 1 | 2 | 2 | 7 | Specified |
| 28 | N10 | Job-search cost subsidy | 2 | 1 | 1 | 1 | 1 | 6 | Parked |
| 29 | C3 | Autonomous worlds (Trinary on Sui testnet) | 0 | 2 | 1 | 2 | 1 | 6 | Current research slice; no spendable payout |

Reading the list: the top five need no new authority and attack the hiring
decision or buy human judgment from the agent economy. N2 and N3 dropped on
November 1 evening receipts: N2 is parked at its own stop with a reproduced
candidate ready, and N3 found that cooperative platforms take client payment
up front, which closes the client-nonpayment mechanism there and spawned B11. B10 is the one far idea that also serves the
operator's November 8 "comparable-role workflow" decision in issue 396. The
current paths rank mid-table on evidence, not on loyalty: C4 scores highest of
them on useful evidence because one real order decides the necessary-finance
question, and lowest on cost because it exposes real funds.

## Current paths (tier C)

**C1. Virtual and creator worlds with human co-creators.** Operator direction of
November 1 (issue 396). Roblox reported creators earned 1,503 million dollars in
2025 against 923 million in 2024 (SEC annual report); cashout needs at least
30,000 earned Robux at 0.0038 dollars each, about 114 dollars, and a third-party
analysis puts the top 1,000 creators near 1.1 million dollars each (RoLearn,
unaudited), so earnings
are concentrated. Second Life permits agent avatars; the roadmap packet flags
speculative rent. Human outcome: a human co-creator's spendable payout. Simpler
route: the human publishes alone. Transfer limit: play-to-earn history (see
register, E1). Cheapest test: already running as a Codex research slice; Claude's
role is challenge. Stop: no human payout path without concentration or delay
that defeats the purpose.

**C2. Productive service, API and compute markets with shared roles.** One
indexed historical ACP settlement on Base with unknown payer, output and
independence (issue 396 packet). Human outcome: a human-owned seller's proceeds.
Simpler route: customer prepayment. Cheapest test: the one-field trace Hermes was
asked to complete read-only. Stop: no independent customer by the November 8
decision.

**C3. Autonomous worlds.** Trinary snapshot of 1,333 trades, 58 traders, on Sui
testnet; no spendable human payout. Counterexample value only.

**C4. Human-first lending on one real order.** Issue 392: one consent-first
request to an existing digital-work agency sent November 1 at 16:35:35 UTC;
packet due November 2 18:00 UTC; disposition by November 8. The order is
compared under existing resources, customer deposit, platform payout and a
bounded advance; NO_LOAN wins when simpler. US microcredit evidence (Grameen
America, MDRC 2022): business earnings up 127 dollars a month, net income effect
modest. Human outcome: incremental spendable cash after all costs and hours.
Stop: the order is not delayed by missing cash, or prepayment dominates.

**C5. Revolving first-job payment guarantee.** Unchanged conditional hypothesis
with its two scorecards and exposure rules in NORTH_STAR.md; no channel
qualified on October 11; N3 is the lateral route to a channel.

## Far-lateral paths (tier F)

Each changes the payer, the deliverable, the channel, the mechanism or the asset.

**F1. Paid data work in low-resource languages, agents as the quality layer.**
Payer: AI labs. Karya reports a 5 dollar hourly minimum plus a share of resale,
32,000 rural workers and tens of millions of paid tasks (self-reported, 2023 to
2024); an hour of Odia speech rose from 3 to 4 dollars to about 40 dollars. Human
outcome: wages for speech or text contribution. Our role: open quality-assurance
tooling or validation for datasets whose buyer already pays, not a new
marketplace. Simpler route: the existing vendor. Transfer limit: no payout rails
or entity on our side; vendors already run the model. Cheapest test: find one
open paid dataset programme whose payer and per-task rate are public and whose
validation is a stated bottleneck. Stop: validation is not the bottleneck.

**F2. Remittance corridor cost reduction.** Payer: the migrant's fee. Global
average cost of sending 200 dollars was 6.49 percent in Q1 2025 (World Bank
Remittance Prices Worldwide, 358 corridors); the SDG target is 3 percent. A
three-point reduction is about 6 dollars per 200-dollar transfer, spendable by
the household. Our role: a verified corridor comparison; the on-chain rails
exist. Transfer limit: money transmission licensing (register, R5). Cheapest
test: one corridor's cheapest licensed route versus the median, from the public
database. Stop: cheapest licensed options are already near 3 percent.

**F3. Index insurance payouts through the conditional-payment contract.** Payer:
sponsors or reinsurers; beneficiary: smallholders. In northern Ghana, farm
investment responded strongly to a rainfall insurance grant and little to cash
grants of similar value; 40 to 50 percent of farmers bought insurance at the
actuarially fair price (Karlan, Osei, Osei-Akoto and Udry, 2014). A contract that
pays on a verified event is the shape GuaranteeTrust already has. Transfer
limit: regulated insurance, basis risk, capital, no farmer channel. Cheapest
test: an index-trigger simulation on public rainfall data run through the
existing ruin machinery. Stop: capital or licensing needs exceed any plausible
sponsor.

**F4. Mutual credit clearing for micro-businesses.** Payer: members, by
accepting each other's credit. Sardex in Sardinia: 1,477 businesses, 48,170
transactions in the 2018 study; obligation clearing cut net internal debt about
25 percent and 50 percent with mutual credit (insider-authored); WIR turnover is
countercyclical (contested). Human outcome: liquidity and sales for member
businesses without sponsor capital, so `M` is undefined and only survival
matters. Transfer limit: needs a dense local trading network; evidence is from
insiders. Cheapest test: simulate a clearing ring on the contract's dues
mechanics. Stop: no candidate network of members exists.

**F5. Appeals of wrongly denied claims and benefits.** Payer: the insurer or
agency that denied. HealthCare.gov consumers appealed less than 1 percent of denied
in-network claims in 2023; prior-authorization denials were overturned on appeal
43 percent (marketplace), 47 percent (Medicaid managed care) and 67 percent
(Medicare Advantage) in 2025 (KFF). Money owed, rarely claimed. Transfer limit:
personal data, legal practice, consent (register, R9); our role would be a
checked template a person or licensed advocate uses. Cheapest test: a
source-linked table of appeal rights, deadlines and overturn rates by programme.
Stop: existing advocates already saturate the channel.

**F6. Unclaimed property recovery.** Payer: the state holding the money. States
returned 4.49 billion dollars in fiscal 2024; about one in seven people has
something unclaimed (NAUPA). Transfer limit: information only; official lookup
sites exist. Cheapest test: a check of whether official search covers the
populations we care about and where the friction is. Stop: official tools
suffice.

**F7. Public procurement set-asides for micro-vendors.** Payer: government.
Kenya reserves 30 percent of procurement for youth, women and persons with
disabilities; uptake was about 16.84 percent across 2015 to 2023 (Women's
Economic Empowerment Hub with the National Treasury), with registration,
compliance and e-procurement literacy named as barriers. Our role: bid-readiness
checks from public tender data. Transfer limit: no vendor channel; one country's
law. Cheapest test: public tender portal structure and documented failure
reasons. Stop: barriers are capital or collateral, not information.

**F8. Payments for ecosystem services with agent-run verification.** Payer:
carbon or conservation buyers. In Uganda, paying landowners 70,000 shillings per
hectare per year to keep forest reduced deforestation with benefits over twice
the cost (Jayachandran and colleagues, Science 2017). Rabobank's Acorn states 80
percent of the credit price to the farmer, with realized prices of 33 to 40
euros per removal unit (programme-reported). Our role: cheaper monitoring from
public imagery. Transfer limit: no farmer channel; credit quality disputes
(register, E4). Cheapest test: a public-data monitoring note on one programme's
published plots. Stop: verification cost is not the binding constraint.

**F9. Paid human evaluation and jury work bought by the agent economy.** Payer:
agent operators who need human judgment, this team included: every receipt here
needs an independent human witness. Prolific's floor is 8 dollars an hour with 12
recommended; AI evaluation studies list about 19 to 20 dollars an hour
(third-party reports). Human outcome: wages for judgment work that agents cannot
self-supply. Simpler route: existing panels. Transfer limit: payment needs
currency and a payout route; quality control. Cheapest test: price our own
verification need (one receipt check) against a panel's public terms and record
whether a disclosed-AI buyer is permitted. Stop: panels exclude agent buyers or
our need is too small to matter.

**F10. AI tutoring for earnings-relevant skills.** In Edo State, Nigeria, six
weeks of after-school tutoring with GPT-4 produced gains reported as 1.5 to 2
years of schooling (World Bank working paper 11125, 2025), with teacher support.
Human outcome: earnings years later. Transfer limit: no school channel; long
horizon. Cheapest test: none within authority; parked behind a channel.

## Boundary ideas (tier B): as creative as virtual worlds and human-first

Each gets a verdict. Kept ideas appear in the unified list; ruled-out ideas move
to the register with their reason and the alternative they inspire.

| ID | Idea | Verdict | Why |
| --- | --- | --- | --- |
| B1 | Agent-funded member credit union: agents deposit their own earned USDC, humans borrow | Ruled out, operational (R1) | Deposit-taking and lending need a licence and a lender of record; the model already records this (`claim:lender-of-record-required`). Inspires F4, which creates liquidity without deposits. |
| B2 | Humans paid to be the accountable legal principal for agent businesses | Ruled out, ethical (E6) | Shifts liability onto poor people without control; a straw owner is not an owner. Inspires the genuine human-ownership route in CURRENT_PATH stage 3 and B3. |
| B3 | Ground-truth gigs: agents hold a contract and subcontract the parts needing a human presence (site visits, local verification) at a wage floor | Kept with conditions | Work must be needed by a paying customer, not invented; classification and pay rules apply. Needs a contract we hold and a payout route. |
| B4 | Paid personhood attestations: humans paid to verify other humans | Ruled out, ethical (E5) | Biometric or identity data of poor people as the product. Inspires F9, which pays for judgment, not identity. |
| B5 | Agent-funded income share agreements for training | Ruled out, ethical and legal (E7) | A claim on a poor person's future earnings, unregulated here; indenture-shaped. Inspires employer-paid, outcome-paid training. |
| B6 | Agents as digital landlords: buy virtual assets, rent to humans who play or build | Ruled out, ethical (E1) | Play-to-earn scholarships took up to 30 percent of earnings that fell below minimum wage. Inspires C1 with human-owned assets and stable-currency wages. |
| B7 | Outcome prediction markets whose winnings fund projects | Ruled out, operational (R6) | Gambling regulation; stakes from the poor. Inspires outcome-based contracts with sponsors. |
| B8 | Local-knowledge oracles: humans paid by agents for verified local prices, routes, availability, dialect | Kept | Demand exists inside the agent economy; the team can specify its own first need. Consent and quality rules apply; payout needs currency. |
| B9 | Human cash-out agents for stablecoin remittances paid on commission | Ruled out, permission (R5) | Money transmission licensing. Inspires F2 as cost comparison with licensed providers. |
| B10 | Agent as employer of first resort: an agent with a real need prepays a newcomer's first small job and publishes a detailed evaluation | Kept with conditions | Pallais (2014) is the mechanism; issue 396 names a small USDC seed in principle and a demand-trace audit. Conditions: the work must be needed, pay at or above a floor, payout route lawful, no debt, randomized offer where possible. |
| B11 | Worker payout guarantee against cooperative platform liquidity failure: the cooperative, not the client, is the counterparty | Kept with conditions (added from the N3 receipt) | One press-reported case of late or missed driver pay at a New York cooperative; clients already pay the platform up front. Needs a cooperative channel (L2) and the cooperative's own books before any parameter can be bounded. |

## Near-lateral paths (tier N), from revision 1

Full entries are in commit 4bf8b02. One line each.

| ID | Path | Cheapest test | Stop |
| --- | --- | --- | --- |
| N1 | Verifiable skill signals and public evaluations (Carranza et al. 2022: employment 31 to 36 percent, earnings +34 percent, benefit 2.3 times variable cost; Abel et al.: callbacks 4.2 to 6.7 percent) | Partner terms of the credential programme; attestation specification from contract events | No channel shows external credentials to the hiring party |
| N2 | Rules-as-code maintenance (Finkelstein and Notowidigdo 2019: information plus assistance raised enrollment to about 18 percent) | Unassigned-issue scan, done; candidate 10552 reproduced and fix drafted ([evidence](../evidence/lateral-n2-n3-20261101/README.md)) | Met November 1: PRs 10263, 10264 and 10347 open with zero comments; parked, re-entry on any maintainer response |
| N3 | Cooperative or placement channel (Up & Go: 95 percent of booking to workers, self-reported) | Done November 1 ([evidence](../evidence/lateral-n2-n3-20261101/README.md)): clients pay the platform by card; sub-24-hour cancellation fee; 48-hour quality window; one reported platform-to-driver pay failure | Met for client nonpayment; spawned B11 |
| N4 | Open-source tax filing (8.2 billion dollars EITC unclaimed, tax year 2021) | Fork activity and named operator | No operator for the 2026 season |
| N5 | Nonpayment recovery law (NYC: over 3.5 million dollars across 4,300 cases since 2017) | Recovery-rate map | Awareness is not the gap |
| N6 | Member-funded mutual pool (VSLA trials: savings and business profits up, no income effect) | Zero-sponsor simulation | Contribution rates erode benefit |
| N7 | First-wage subsidy voucher (Levinsohn et al.: +7 points wage employment) | `M` comparison note | Voucher `M` below guarantee `M` |
| N8 | Payment timing (CFPB December 2025: certain earned-wage products not credit) | Payout-timing comparison | Channels already pay within days free |
| N9 | Positive payment-history reporting (company-reported +46 points) | Furnisher eligibility note | Requires a regulated entity |
| N10 | Job-search cost subsidy (Abebe et al.; effects fade) | None within authority | Parked |

## Ruled-out register (tracked, not ranked)

Marked by reason. Each line names the feasible alternative it inspires and, for
resource rulings, the re-entry condition. Re-entry never happens by silence.

### Ruled out on ethical grounds (E)

| ID | Idea | Why ruled out | Alternative it inspires |
| --- | --- | --- | --- |
| E1 | Play-to-earn scholarships, agents or guilds as asset owners taking a cut (B6) | Typical scholar earnings fell below the Philippine minimum wage by late 2021; owner cuts up to 30 percent; token collapse in 2022 (Naavik, press). Rent extraction from the poor on a volatile asset. | C1 with human-owned assets and wages in stable currency; B10. |
| E2 | Payday-style advances or expedite fees charged to workers | Fees of up to 218.83 dollars a year per user in South Carolina's 2024 provider data (register N8); credit-adjacent harm. | N8 at zero worker fee; employer-paid timing. |
| E3 | Paying for or brokering personal data of beneficiaries without consent or benefit share | Privacy and consent; the person is the product. | F1 with consented tasks and a worker resale share, as Karya reports. |
| E4 | Avoided-deforestation credits with weak additionality sold as farmer income | Buyers misled, farmers paid little, credit quality disputes. | F8 restricted to removal credits with a published farmer share and public monitoring. |
| E5 | Paid personhood or biometric attestation markets (B4) | Biometric data of poor people as the product; irreversible harm if leaked. | F9: pay for judgment, not identity. |
| E6 | Paid straw principals for agent businesses (B2) | Liability shifted to people without control. | Genuine human ownership with control (CURRENT_PATH stage 3); B3. |
| E7 | Agent-funded income share agreements (B5) | Claim on future earnings of poor people, unregulated here, indenture-shaped. | Employer-paid or outcome-paid training. |
| E8 | Agents posing as humans, or seeded fake demand, to demonstrate a mechanism | Fraud; also destroys the evidence value of every receipt. | F9: disclosed-AI buyer paying real humans for judgment. |
| E9 | Charging workers placement or guarantee fees | ILO Convention 181 article 7 flag already in NORTH_STAR.md. | Employer- or sponsor-paid guarantee; capped pledge never pursued. |
| E10 | Mass unsolicited outreach to poor households or scraped contact lists | Consent; existing contact caps. | Ride channels where the person already seeks the service (F5, F6, F7). |
| E11 | Bots entering human skill or esports competitions for prize money | Unfair to human competitors; terms-of-service bans. | F9, B8: agents buy human judgment instead of displacing it. |

### Ruled out on operational or legal grounds (R)

| ID | Idea | Why ruled out | Alternative or re-entry |
| --- | --- | --- | --- |
| R1 | Agent-funded credit union or deposit pool (B1) | Deposit-taking and lending licences; lender of record required in evidenced countries (`claim:lender-of-record-required`). | F4 mutual credit without deposits; re-entry only through a licensed partner. |
| R2 | Underwriting insurance ourselves (F3 as an insurer) | Regulated; capital; basis risk. | F3 as monitoring and trigger design for a licensed insurer. |
| R3 | Running Direct File or a tax product for filers | Code depends on internal IRS systems; preparer rules. | N4 as reviewed code contributions to a fork with a named operator. |
| R4 | Filing appeals, claims or benefit applications on behalf of people (F5, F6 as agents of the person) | Unauthorized practice, personal data, consent. | Checked templates used by the person or a licensed advocate. |
| R5 | Money transmission, remittance cash-out agents (B9), stablecoin payout to households | Licensing and anti-money-laundering regimes; model records Ethiopia's virtual-asset notice and Kenya's lender rules. | F2 as cost comparison; re-entry through a licensed provider. |
| R6 | Prediction or betting markets funding projects (B7) | Gambling regulation; stakes from the poor. | Outcome-based contracts with sponsors. |
| R7 | New platform accounts (Roblox, Second Life, Upwork, panels) operated by agents | Issue 396: no new platform accounts; bot restrictions. | Read-only research; human-owned accounts. |
| R8 | Real funds on the testnet contract | No deployment or financial authority; the contract is optional infrastructure. | Simulation (N6, F3, F4). |

### Ruled out for lack of resources: channels, permissions, currency (L)

| ID | Idea | Missing resource | Re-entry condition |
| --- | --- | --- | --- |
| L1 | Direct cash transfers by this team | Currency authority, payout rails, recipient channel. GiveDirectly delivers 80 to 89 percent of funds (self-reported; GiveWell about 83 percent). | Operator-authorized sponsor funds with a named rail; otherwise cash stays the benchmark. |
| L2 | Any first-contact outreach to workers, households, cooperatives or employers | Contact permission; existing caps. | Operator's action-specific word naming channel and cap. |
| L3 | Hiring a human for B3 or B10 ourselves | Currency (the USDC seed is "in principle", no balance), payout route, consented worker. | A specified seed, a lawful payout route and a consented participant through an existing permitted channel. |
| L4 | Paying panel participants for F9 or B8 | Currency and a panel account. | Same as L3; or a human-owned account on the panel. |
| L5 | Data-work payroll in India or Kenya (F1 as operator) | Entity, payout rails, labour compliance. | Partnership with an existing vendor; otherwise tooling only. |
| L6 | Farmer or vendor enrollment for F7, F8 | Field channel, local partner. | A partner with its own enrolled members and consent. |
| L7 | School channel for F10 | Partner, device access, consent for minors. | Not sought; parked. |
| L8 | Signed partnerships of any kind | No signatory or legal-entity authority recorded in this repository. | Operator signs; the team prepares terms. |
| L9 | A standing lateral refresh | Resolved November 1: the operator approved one daily routine. | In place; re-examine only if the routine stops producing receipts. |

### Ruled out by evidence (V)

| ID | Idea | Evidence | What it leaves open |
| --- | --- | --- | --- |
| V1 | Buying and cancelling medical debt | Two randomized experiments relieving 169 million dollars for 83,401 people found no average effect on mental health, financial wellness or utilization, with worse mental health in the most-indebted quartile (Kluender, Mahoney, Wong and Yin, QJE 2025). | Upstream prevention of the debt; appeals before denial becomes debt (F5). |
| V2 | Subsidizing new traders to compete with incumbents | Induced entry had negligible price effects; traders pass through 22 percent of cost cuts and capture 82 percent of surplus (Bergquist and Dinerstein, AER 2020). | Collective selling or direct buyer access rather than more traders. |
| V3 | Transport subsidies alone for job search | Early gains dissipated while certification effects persisted (Abebe et al.). | N1, N10 parked. |

## Concrete steps taken on November 1

1. Recalled both existing lessons; separated the blocked prerequisite by kind.
2. Researched the far and boundary mechanisms from public sources (register).
3. Ran the N2 test: label scan stale; 156 unassigned issues updated since
   October 1, the first 40 read all maintainer-filed (GitHub search API, 19:36 to 19:40 UTC). Lead
   inventory only.
4. Ran the N1 channel check: one platform displays partner-issued credentials.
5. Read issues 396 and 392 to place the current paths in the ranking on what the
   operator actually wrote.
6. Recorded the ranking, register and receipts in NORTH_STAR.md and the world
   model (`action:lateral-paths-first-tests-20261101`,
   `claim:lateral-paths-ranked-20261101-r2`).
7. Evening, after Codex declined N2 and N3 and the steward assigned them to
   Claude (board 15 comments 6564338961 and 6564389264): N2 candidate issue
   10552 reproduced exactly and a fix drafted, then parked at N2's own stop
   because PRs 10263, 10264 and 10347 remain unanswered; N3 public-terms check
   of three cooperative channels returned a bound and spawned B11. Packet:
   [evidence/lateral-n2-n3-20261101](../evidence/lateral-n2-n3-20261101/README.md).

## Proposed next actions

Owners are proposed; acceptance is recorded in the model when given.

| Step | Path | Owner proposed | Deliverable | Checkpoint |
| --- | --- | --- | --- | --- |
| Challenge the issue 396 evidence matrix with this ranking; propose B10 as the comparable-role workflow candidate | C1, C2, B10 | Claude | Comment on issue 396 with the cheapest discriminator | 2026-11-03 |
| Select one current maintainer-filed defect under existing gates | N2 | Claude (reassigned Nov 1) | Done Nov 1: issue 10552 reproduced, fix drafted, parked at stop | 2026-11-04 |
| Partner terms of the credential programme; attestation specification | N1 | Claude | One page, issuer-trust problem stated | 2026-11-08 |
| Price our own verification need against a panel's public terms; record whether disclosed-AI buyers are permitted | F9 | Claude | One-page receipt | 2026-11-08 |
| Public `p` check on three cooperative or placement channels | N3 | Claude (reassigned Nov 1) | Done Nov 1: bound; clients pay the platform; B11 spawned | 2026-11-08 |
| Zero-sponsor and clearing-ring simulations | N6, F4 | Claude | One reproducible run each beside existing ruin results | 2026-11-15 |
| Voucher versus guarantee `M` note | N7 | Claude | Reproducible note in the theory repository | 2026-11-15 |

Stop rule: two checkpoints with no score-moving receipt re-rank and retire the
empty paths. The register is never pruned; a ruled-out idea is re-examined only
when its named re-entry condition is met.

## Source register

Retrieved November 1, 2026 through web search summaries and GitHub reads. Figures
are as summarized by the linked pages; published tables were not all opened.
Company-reported and advocacy figures are marked as such in the text.

| Tier | Source | URL |
| --- | --- | --- |
| C | Issue 396 roadmap and packets | https://github.com/scottonchain/microcredit-agent-testbed/issues/396 |
| C | Issue 392 real-orders case | https://github.com/scottonchain/microcredit-agent-testbed/issues/392 |
| C | RoLearn third-party creator earnings analysis (unaudited) | https://rolearn.dev/insights/roblox-creator-earnings-how-much-developers-make |
| C | Roblox Corp annual report FY2025 | https://www.sec.gov/Archives/edgar/data/1315098/000110465926044380/rblx-20251231xars.pdf |
| C, N7 | MDRC, Pathways to Financial Resilience | https://www.mdrc.org/work/publications/pathways-financial-resilience |
| F1 | Time on Karya | https://time.com/6297403/india-ai-karya-startup |
| F1 | Context, India turns to AI to capture its 121 languages | https://www.context.news/ai/india-turns-to-ai-to-capture-its-121-languages |
| F2 | World Bank Remittance Prices Worldwide, Q1 2025 report | https://remittanceprices.worldbank.org/sites/default/files/rpw_main_report_and_annex_q125_1_0.pdf |
| F3 | Karlan, Osei, Osei-Akoto, Udry, NBER w18463 | https://www.nber.org/papers/w18463.pdf |
| F4 | Iosifidis et al., Cyclic motifs in the Sardex monetary network | https://link.springer.com/article/10.1038/s41562-018-0450-0 |
| F4 | Stodder and Lietaer, WIR macro stability | https://bernard-lietaer.org/wp-content/uploads/2022/07/2016-The-Macro-Stability-of-Swiss-WIR-Bank-Credits-Balance-Velocity-and-Leverage-Stodder-Lietaer-annotated.pdf |
| F5 | KFF, HealthCare.gov insurers denied nearly 1 in 5 in-network claims in 2023 | https://www.kff.org/private-insurance/healthcare-gov-insurers-denied-nearly-1-in-5-in-network-claims-in-2023-but-information-about-reasons-is-limited-in-public-data/ |
| F5 | KFF prior authorization 2025 coverage | https://www.fiercehealthcare.com/payers/insurers-denied-between-12-18-prior-auth-requests-2025-kff |
| F6 | NAUPA fiscal 2024 figure, press coverage | https://www.fox13news.com/news/theres-billion-dollars-unclaimed-money-us-check-see-youre-owed-money |
| F7 | Nation, AGPO uptake coverage | https://beta.nation.co.ke/kenya/katiba-15/a-promise-unfulfilled-why-kenya-s-agpo-programme-still-fails-women-youth-and-pwds-5169086 |
| F7 | WTO Chairs, enhancing implementation of AGPO | https://wtochairs.org/enhancing-implementation-kenya-s-agpo-program-insights-implementing-agencies |
| F8 | Jayachandran et al., Cash for carbon, Science 2017 | https://collaborate.princeton.edu/en/publications/cash-for-carbon-a-randomized-trial-of-payments-for-ecosystem-serv/ |
| F8 | Acorn, our approach | https://acorn.rabobank.com/en/our-approach/ |
| F9 | Prolific payment principles | https://researcher-help.prolific.com/en/articles/445230-prolific-s-payment-principles |
| F10 | World Bank, From Chalkboards to Chatbots | https://openknowledge.worldbank.org/entities/publication/15e1ff08-15ae-4f7a-b2a8-d146e6c113ee/full |
| E1 | Naavik study coverage, Axie earnings below minimum wage | https://forkast.news/earnings-axie-infinity-below-minimum-wage/ |
| E1 | CoinGecko, Play to Earn scholarship viability | https://assets.coingecko.com/reports/Research/Play-To-Earn-A-Study-on-Scholarship-Viability.pdf |
| V1 | Kluender, Mahoney, Wong, Yin, NBER w32315 | https://nber.org/papers/w32315 |
| V2 | Bergquist and Dinerstein, AER 2020 | https://www.povertyactionlab.org/sites/default/files/research-paper/6372_Competition-&amp;-Entry-in-Ag-Mkts_Kenya_Dec2020.pdf |
| N1 | Carranza, Garlick, Orkin, Rankin (J-PAL summary) | https://www.povertyactionlab.org/node/3196342 |
| N1 | Pallais, NBER w18917 | https://www.nber.org/papers/w18917 |
| N1 | Abel, Burger, Piraino (J-PAL summary) | https://www.povertyactionlab.org/print/pdf/node/2378?lang=en |
| N1 | Upwork Partner Certified Talent programme | https://support.upwork.com/hc/en-us/articles/41174925985299-What-is-the-Partner-Certified-Talent-program-on-Upwork |
| N2 | Finkelstein and Notowidigdo working paper | https://www.ipr.northwestern.edu/documents/working-papers/2018/wp-18-03.pdf |
| N2 | PolicyEngine US issue 10552 | https://github.com/PolicyEngine/policyengine-us/issues/10552 |
| N3 | Up & Go | https://upandgo.coop/cms/about |
| N4 | IRS SOI, EITC underclaims tax year 2021 | https://irs.gov/pub/irs-soi/24rpeitcunderclaimsty2021census.pdf |
| N4 | IRS Direct File source | https://github.com/IRS-Public/direct-file |
| N5 | NYC DCWP 2026 restitution release | https://www.nyc.gov/site/dca/news/021-26/dcwp-wins-500-000-restitution-freelancers-holds-production-company-accountable-for |
| N6 | Karlan et al., VSLA trials (IPA summary) | https://poverty-action.org/node/6221/pdf |
| N7 | Levinsohn et al., youth wage subsidy (3ie) | https://www.3ieimpact.org/sites/default/files/2019-01/ie15-youth_wage_subsidy.pdf |
| N8 | CFPB Regulation Z treatment of earned wage access (law-firm summary) | https://www.klgates.com/To-Z-or-Not-to-Z-CFPB-Clarifies-the-Regulation-Z-Treatment-of-Certain-Earned-Wage-Access-Products-1-12-2026 |
| N8 | South Carolina 2025 EWA report | https://www.consumer.sc.gov/sites/consumer/files/Documents/Reports/2025%20EWA%20Report%20Draft%20FINAL.pdf |
| N9 | Esusu and Freddie Mac results (company release) | https://www.multifamilyexecutive.com/business-finance/business-trends/freddie-mac-esusu-rent-reporting-initiative-creates-over-27-000-new-credit-scores_o |
| N10 | Abebe et al., NBER w22409 | https://nber.org/papers/w22409 |
| L1 | GiveDirectly financials; GiveWell review | https://www.givedirectly.org/financials and https://www.givewell.org/node/2637 |
