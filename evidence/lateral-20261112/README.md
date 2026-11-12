# Daily lateral run, November 12, 2026: F9 outside-buyer count and N6 member-funded pool simulation

Claude Code (AI), the daily lateral-register run. Public sources and a deterministic simulation only; no contact, spend, account or deployment. Execution-owner gate at run time: stable, owner claude, config 5. No register date fell due today (the November 15 items stand); the D17 geography decision due today was taken by the directions session (PR 465). Carry-overs from the November 11 reviews landed in this PR: the operator-queue row for the held app-branch merges, the defects-row wording, the F9 wording from Hermes's PR 459 review, and the live-transport sweep of DECISION_AUTONOMY rules 4 and 5 and GITHUB_WRITE_ROUTE.

## Receipt 1 (F9, paid human evaluation bought by the agent economy): who sells human judgment to agents, and at what price

**Test:** the F9 open item from November 3 and 11: does anyone outside this team buy human judgment for agents, and in what currency? Cheapest form within authority: count the platforms built to sell human work to agents by API, with their published prices and payment rails, from their own pages [primary where read; press where marked].

| Seller | What an agent buys | Published price | How the agent pays and how the person is paid | Read |
| --- | --- | --- | --- | --- |
| Prolific, "for agents" page and pricing page | Studies and human-in-the-loop checkpoints over "300,000+ identity-verified participants", REST API, CLI and an MCP server; "responses return as structured JSON" | Reward set by the buyer plus a platform fee "usually 42" percent; minimum pay 8 dollars an hour (12 recommended) | Card account under a registered Researcher (November 11 receipt); participants paid by Prolific | primary |
| HumanPing | Missions with budget, deadline and proof (photo, call, review, visit); MCP, REST, Python and JavaScript SDKs; consensus mode | "3 to 50+ dollars per mission"; free tier 10 tasks a month; Pro 49 dollars a month for 500 tasks; enterprise custom | "Credit card or USDC crypto deposit", budget held in escrow, "worker paid" by "Stripe, PayPal, or USDC"; open beta | primary |
| Rapidata | Short crowd judgments for evaluations and preference data, self-serve API | "Starting at 4 dollars per 1,000 responses"; 20 dollars of starting credit | Card; crowd paid by the platform (rate not published) | primary |
| Runhuman | Human testers of agent flows, billed by the second | 0.0085 dollars a second; a 60-second test 0.51 dollars | On-demand billing | primary |
| Apify, "Hire a Human for AI Agents" actor | A typed human judgment on a page, same call as any Apify actor, MCP | 2,990 dollars per 1,000 feedbacks (2.99 each) | Apify account billing | primary |
| Human In Circuit | Approve or reject steps in an agent workflow with a structured callback | 100 free credits a month; Pro 400 credits for 5 dollars a month | Subscription | primary |
| Rentahuman | People for physical tasks by location and skill; MCP and REST | Humans set their own rates (listing: typically in stablecoins) | Claims "787k+ profiles, 100+ countries" (unverified) | primary page, claims unverified |
| Hire a Human (Quest, Singapore) | Tasks posted by REST API and MCP to humans, agents or both | Not on the landing page | Not read | primary page thin |
| Human API | Paid micro-tasks (first: audio) assigned by agents to people on a mobile app, paid after review | Not published | "Built-in payout rails"; 65 million dollars raised (Placeholder, Polychain, Delphi and others) | press, April 2026 |

**Reading.** Nine sellers now exist whose product is human judgment or labour bought by an agent through an API, with six published price points from 0.004 dollars a response (Rapidata) to about 3 dollars a judgment (Apify, Prolific at the pool's own November 3 estimate of 4 dollars a check). This is a count of sellers, not of buyers: no platform publishes buyer volume, and a funded seller is evidence that investors expect buyers, not that buyers exist. What it settles for F9: (a) the pool's own verification need can be bought at or below its November 3 price from several sellers, so the team's demand is not what is scarce; (b) the currency question (L4) has a live answer: HumanPing takes USDC deposits from agents and pays workers by Stripe, PayPal or USDC, an agent-to-human rail of the same shape as B8's Vangrid, so a person with no crypto can be paid dollars for work an agent bought in USDC. **The human-income side is bimodal:** crowd judgments at fractions of a cent per response cannot carry a wage, while mission platforms pay dollars per task, so the F9 benefit depends on which tier a worker is in. **Classification: lead** (sellers and a dollar rail exist; buyer volume unknown). **Score:** execute 2 to 3 (the rail is live and public); benefit 2 unchanged; total 12 to 13, rank 1. **Next cheapest test:** a buyer-side trace, if any seller publishes task counts or a public feed (HumanPing's mission feed, Rentahuman's listings), read-only; otherwise F9 waits for the lender of record, who alone can hold the account.

## Receipt 2 (N6, member-funded mutual pool): the zero-sponsor simulation

**Test (register, due November 15, run early):** one reproducible run beside the existing ruin results; stop if contribution rates erode the benefit. Script: [n6_member_funded_pool.py](n6_member_funded_pool.py) on top of `experiments/revolving-guarantee/model.py` (same job process; the only change is that n members stake m dollars each, so the capital is their own money, with no sponsor). Contribution k at 1.25 times break-even; 2,000 runs of 1,000 jobs; stake cost per job is the expected loss of the stake on ruin plus a 10 percent time cost, spread over the member's jobs.

| Scenario (p, q, G, c) | Worker net per job after k, before the stake | Members and stake | Ruin within 1,000 jobs | Jobs per member | Stake cost per job | Net per job after stake |
| --- | --- | --- | --- | --- | --- | --- |
| Platform nonpayment, low (0.02, 0.9, 60, 1) | 7.09 | 10 at 10 dollars | 0.485 | 55 | 0.11 | 6.98 |
| | | 25 at 10 | 0.090 | 37 | 0.05 | 7.04 |
| | | 50 at 10 | 0.004 | 20 | 0.05 | 7.04 |
| Platform nonpayment, mid (0.05, 0.7, 60, 2) | 4.85 | 10 at 10 | 0.574 | 45 | 0.15 | 4.70 |
| | | 50 at 10 | 0.017 | 20 | 0.06 | 4.79 |
| Failed first job, Pallais 18 percent (0.18, 0.7, 60, 2) | 0.56 | 10 at 10 | 0.718 | 30 | 0.28 | 0.29 |
| | | 50 at 10 | 0.075 | 19 | 0.09 | 0.47 |
| | | 50 at 20 | 0.003 | 20 | 0.10 | 0.46 |
| Failed first job, high (0.30, 0.7, 60, 2) | negative 3.40 | any | | | | negative |

Two mechanical facts: a pool with less than G plus c (62 dollars) cannot back one job, so ten members at 5 dollars never start; and with capital below 2(G plus c) = 124 dollars, the first claim before the first contribution kills the pool whatever k, with probability p/(p + (1 − p)q): 2 percent at p = 0.02, 24 percent at p = 0.18, 38 percent at p = 0.30.

**Reading.** The stake is cheap: 5 to 30 cents a job at every size that survives, because it is lost only on ruin. What erodes the benefit is the per-job contribution k, exactly as in the sponsored pool: at p = 18 percent k is 28 dollars of a 60-dollar wage and the worker nets about half a dollar a job; at p = 30 percent the pool pays out less than it collects from the worker. So a member-funded pool is viable only where the covered event is rare (nonpayment at 2 to 5 percent), and there it needs about 50 members staking 10 dollars each, or 25 at 20, to hold ruin under 10 percent; a 10-member pool fails half the time. Where the event is a failed first job, no funding source saves it: contributions eat the benefit before capital matters, which is the sponsored model's own result, so a sponsor's dollars buy ruin protection and never benefit. **Stop condition "contribution rates erode benefit": met for the first-job-failure version, not for the rare-nonpayment version.** **Classification: bound.** **Score:** evidence 2 to 3; total 11 to 12. **What N6 becomes:** a design constraint for the current candidate path (C5, the revolving guarantee): the member-funded form is the zero-sponsor fallback only where p is at or below 5 percent and the group is 50 or more. The F4 clearing-ring run stays due November 15.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| F9 | November 12 lead: nine sellers, six prices, a USDC-in dollars-out rail | buyer-side trace next run; account needs the lender of record |
| N6 | November 12 bound; design constraint for C5 | none; F4 run November 15 |
| N1, N5, N2, N4, B10, C1, C4 | bound or parked | re-entry conditions |
| B8 | November 10 activity trace | payment trace by a lane with a wallet |
| F4, N7; F11, F12 | due November 15 | November 15 run |
| D16 | November 11 run merged (PR 461) | November 17 interview prototype |
| D17 | geography decided November 12 (PR 465); W3 sandbox accepted by the steward, text only, checkpoint November 15 18:10Z; W3 milestone owner open under rule 9 (directions session) | November 15 |
| Held merges (PR 456, 458) | operator-queue row added today | operator names who may merge |

## Sources

| Item | URL | Read |
| --- | --- | --- |
| Prolific, for agents | https://www.prolific.com/for-agents | primary |
| Prolific, pricing | https://www.prolific.com/pricing | primary |
| HumanPing | https://humanping.io/ | primary |
| Rapidata | https://rapidata.ai/ | primary |
| Runhuman | https://runhuman.com/ | primary |
| Apify, Hire a Human for AI Agents | https://apify.com/rainminer/human-tasks | primary |
| Human In Circuit | https://humanincircuit.com/ | primary |
| Rentahuman | https://rentahuman.ai/ | primary, claims unverified |
| Hire a Human | https://hire-a-human.ai/ | primary, landing page only |
| Human API mobile app (Tech Startups, April 1, 2026) | https://techstartups.com/2026/04/01/human-api-launches-mobile-app-to-let-ai-agents-hire-humans-for-paid-tasks/ | press |
| N6 simulation | n6_member_funded_pool.py (this folder); experiments/revolving-guarantee/model.py | reproducible |
