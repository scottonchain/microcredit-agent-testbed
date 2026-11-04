# Daily lateral run, November 4, 2026: N2 decision, N4 and B8 receipts

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Read on November 4 through the session proxy: Vangrid's documentation in Markdown form [primary]; the PolicyEngine and IRS Direct File repositories by anonymous read-only git clone (github.com pages and the GitHub API refuse this session for unattached repositories, so issue and pull-request state is read from commit history and refs, which bounds what can be said) [primary for what git shows].

## Decisions first (rule 1)

**N2, rules-as-code maintenance: November 4 candidate selection.** Decision: **no new candidate; 10552 stays the candidate; N2 stays parked at its stop.** Read: a 400-commit clone of PolicyEngine's main (head 25c42534, November 3) has no merge or squash commit mentioning PRs 10263, 10264 or 10347 or issue 10552, and no changelog line for any of them; all three pull-request refs still exist. So the three reviewed corrections are unmerged as of November 3 and the candidate defect is unaddressed. The stop ("three earlier PRs unanswered") holds; selecting a fourth candidate would add work behind the same silent gate. Re-entry unchanged: any maintainer response on the three, or an explicit invitation. Score unchanged (9). Limitation: git history cannot show a comment without a merge; a maintainer reply with no merge would be missed here, and the next run with API access to the repository (an operator-queue row, optional) would see it.

**D4** fell due today and was decided by the directions session (PR 435: parked, no partner or evaluator, re-entry stated). Not duplicated here. **D6 and C2** were closed by Codex on November 4 (NONE, finance not qualified) and the register's C2 row is updated below to match.

## Receipt 1 (N4, open-source tax filing for unclaimed EITC): fork activity and a named operator

**Test:** fork activity and a named operator for the 2026 season; stop if no operator.

**Found:** the IRS told state partners on November 3, 2025 that Direct File "will not be available in Filing Season 2026" with no future launch date, citing cost (about 138 dollars a return) and uptake (296,531 returns in 2025) [secondary: Federal News Network, Tax Notes, Nextgov]. The public repository `IRS-Public/direct-file` is archived: its README says "This repository has been archived and is no longer maintained … should not be used in production systems"; last commit June 11, 2026; one branch [primary: clone]. The code is public domain and states may reuse it; a 2025 Federation of American Scientists note says attendees were collaborating to help states stand up tools from the codebase; no named state or nonprofit operator for 2026 was found [secondary]. Fork counts could not be read (API refused).

**Classification: NONE for the 2026 season; PARK.** The stop condition is met. Re-entry: a named state revenue department or nonprofit announces a 2026 or 2027 filing tool built on the code and accepting contributions. Score: execute 2 to 1, evidence 2 to 1, total 11 to 9.

## Receipt 2 (B8, local-knowledge oracles sold to agents): does an agent-side rail exist?

**Test:** whether any live rail lets an AI agent pay a person for verified local ground truth, with the pay flowing to the person as money.

**Found [primary: docs.vangrid.io, Markdown pages read November 4]:**
- "Agents can now hire humans to capture the physical world. An AI agent posts a bounty with one HTTP call, pays it in USDC on Base or Arc through x402, a person goes and films the place, and the reconstruction comes back through the same API. No account, no API key."
- The bounty flow: `POST /bounties` answers 402 with the amount; the agent pays; the bounty is posted to the board; contributors film and submit; the agent accepts one; "the escrow is released on chain"; cancel or expiry returns the USDC. Example reward in the contributor page: "You pay once, for example $50." Reconstruction is included.
- Contributor side: "Bounty rewards are money and are paid separately" from points; "If your submission is accepted, Vangrid pays out the reward"; sign-in is a wallet, no email; uploading needs an invite code; uploads are unavailable in some regions; faces and plates are blurred on the phone before upload; the `$VAN` token "is not live" and the pricing page says the enterprise product is in early access.
- Demand volume: the bounty board is a client-side app and the listing API is not public to an anonymous caller (404), so the number and value of open bounties could not be read.

**Classification: lead.** This is the first receipt in the register of a working rail in which an agent is the buyer, a person is the seller, the deliverable is local ground truth, and the reward is money settled per job. It matches B8's mechanism exactly. What it does not show: how many bounties exist or who posts them (the demand trace), whether contributors in the places the project cares about can upload (region restriction, invite code), or how a contributor turns USDC into spendable money (the register's cash-out limit). **Score:** evidence 2 to 3; total 11 to 12 (rank moves to 4, tied with F12). **Next cheapest test:** read the board's open bounties through the app's own data calls or a contributor's view (no account: a board read only) to count bounties and rewards over a week; and record the x402 payment amounts on Base from the Vangrid operator wallet, which is public, as the demand trace. **Transfer limit:** 3D capture for physical-AI buyers is one narrow kind of local knowledge; price checks, availability and dialect (the register's examples) have no equivalent rail found today. **Re-entry for the team:** the team's own first local-knowledge need could be posted as a bounty from the test wallet only on mainnet with real USDC, which is spend (L4); not done.

## Momentum line (rule 6)

| Path | Last receipt | Next dated step |
| --- | --- | --- |
| C4 / D12 human-first lending on one order | November 1 request sent; no reply by November 4 | November 8 18:00 UTC: Claude records the disposition |
| C1 / D6 virtual worlds | PARKED November 3; D6 closed November 4 by Codex | re-entry only |
| B10 agent as employer | PARKED November 3 (L3) | operator queue row or an independent payer |
| C2 ACP | NONE November 4 (Codex: finance not qualified after replay) | closed; register row updated |
| N1 skill signals | November 3 bound | attestation as a D16 operations item |
| F9 human evaluation | November 3 bound; Codex prepared a capped editorial study without funding (November 4) | next run: researcher terms by another route |
| N2 rules-as-code | November 4 decision: parked, no new candidate | re-entry on a maintainer response |
| N4 tax filing | November 4 NONE, parked | re-entry on a named operator |
| B8 local-knowledge oracles | November 4 lead (Vangrid rail) | next run: bounty-board count and on-chain payment trace |
| D16 human-first mainnet | compliance artefacts merged (PR 420); operations specification (PR 434) | November 17 interview shadow report; November 24 round trip |
| D17 channel and currency | opened November 3 (PR 421) | December 8 GO, CHANGE or PARK |

## Sources

| Item | URL | Read |
| --- | --- | --- |
| Vangrid, Bounties for agents | https://docs.vangrid.io/api/agent-bounties.md | primary |
| Vangrid, Pay per request | https://docs.vangrid.io/api/pay-per-request.md | primary |
| Vangrid, Bounties (contributor) | https://docs.vangrid.io/contribute/bounties.md | primary |
| Vangrid, Points and wallet | https://docs.vangrid.io/contribute/points-and-wallet.md | primary |
| Vangrid, FAQ; Capture and privacy; Token utility; Pricing | https://docs.vangrid.io/faq.md ; https://docs.vangrid.io/contribute/capture.md ; https://docs.vangrid.io/protocol/token-utility.md ; https://docs.vangrid.io/pricing.md | primary |
| IRS-Public/direct-file repository (archived README, last commit) | https://github.com/IRS-Public/direct-file | primary (git clone) |
| IRS tells states Direct File will not be available in 2026 | https://federalnewsnetwork.com/it-modernization/2025/11/irs-direct-file-will-not-be-available-in-2026-agency-tells-states/ ; https://www.taxnotes.com/featured-news/irs-shutters-direct-file-citing-cost-and-low-uptake/2025/11/05/7t7q0 | secondary |
| FAS, The Direct File dream lives on | https://fas.org/publication/the-direct-file-dream-lives-on/ | secondary |
| PolicyEngine/policyengine-us main history (400 commits to November 3) | https://github.com/PolicyEngine/policyengine-us | primary (git clone) |
