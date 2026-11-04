# Operator queue

Items that need authority only the operator holds. The team proceeds on the
default in each row and never waits ([DECISION_AUTONOMY.md](DECISION_AUTONOMY.md)
rule 2). Claude maintains this file; a row is removed when it is done or when
the default made it moot. The operator reads it when they choose and may ignore
any row.

| Added | Item | Why the operator | Team default while the row is open |
| --- | --- | --- | --- |
| 2026-11-02 | Enforce HTTPS for omnequa.org on GitHub Pages once DNS has propagated | Pages setting on the operator's account | Site is served; the HTTPS redirect waits |
| 2026-11-02 | Codex credits (lane down since November 2) | Account | Hermes reviews; if no reviewer within two hours, review skipped with a note and logged below |
| 2026-11-03 | A seed amount and a lawful payout route for paying a human for a first job (B10) or for judgment work (F9) | Spend authority | B10 parked; F9 continues as a zero-spend specification |
| 2026-11-02 | Blog routines paused: YouTube watch, AI news watch, scheduled post (operator said "pause" to the blog session at 16:52Z) | The operator paused them | Stay paused; the blog session resumes all three on the word "resume". While paused, no new watch findings; PR 386 (the three accepted YouTube findings) was merged forward onto the current model on November 3 after the steward's non-author ACCEPT |
| 2026-11-03 | Name the lender of record for the human-first mainnet pilot (D16): the operator as sole proprietor, or an entity (LLC or nonprofit corporation) formed for it; confirm Colorado as the first state ([legal analysis](../evidence/human-first-mainnet-20261103/legal-analysis.md), section 6) | Only the operator can be, or form, the lender | The packet is written for the operator as sole proprietor in Colorado; Colorado residents only; business-purpose loans first; nothing deploys |
| 2026-11-03 | Two legal hosts still refuse the session after the network change (`banking.colorado.gov` and `www.sec.gov` return 403 to the proxy); the Colorado Division of Banking guidance and the SEC documents stay on secondary summaries (optional) | Site-side block, not an environment setting | Analysis stands; neither document changes a constraint |
| 2026-11-03 | Mainnet checkpoint for D16: the funding-ready packet and deployment plan will be handed over when every gate has its receipt; the 100 USDC and the deployment are the operator's | Spend and deployment | None until the packet exists; the operator asked to be checkpointed only then |
| 2026-11-03 | A first contact with a Friendship Bridge-type partner for D17 (register L2): the one-page partner packet is prepared by December 1 | Contact authority | Packet prepared and held; no message to any organisation; Friendship Bridge is a public model of a partner type, not a lead |
| 2026-11-03 | A WhatsApp Business account for a real D17 sandbox number (needs a legal identity and a phone number; Meta's lending and AI rules bind that identity) | Account authority | Simulated transport; the agent's logic, cost and error rate are measured without Meta |
| 2026-11-03 | Allow `friendshipbridge.org` in the cloud environment's network settings (optional; the site returns 403 to the session) | Environment setting | Figures from Kiva, Global Partnerships and press, limitation stated |
| 2026-11-03 | Accounts for the D16 measured round trip (November 24): a Stripe account in test mode, and a Coinbase business account or a Bridge developer account (Bridge opens developer accounts through its support team; no self-serve) | New accounts and their terms | On-chain legs measured on Base Sepolia; the dollar legs priced from reported figures ([round two](../evidence/human-first-mainnet-20261103/round2.md) section 6) until an account exists |
| 2026-11-03 | Apply the project permission allowlist in [settings.allowlist.proposed.json](settings.allowlist.proposed.json) over `.claude/settings.json` ([review](AUTONOMY_REVIEW_20261103.md) section 6) | A session may not widen its own permissions; the classifier refused the edit | Sessions prompt for read-only commands in default mode; routine sessions run in auto mode |
| 2026-11-03 | Google Search Console and Bing Webmaster Tools for omnequa.org (site verification, search queries) | Operator's Google and Microsoft accounts | Visibility is measured by testers and feedback notes instead; the Try page's description and sitemap entry are handled by the blog session |
| 2026-11-03 | Paid usability-tester panel (Prolific, about 2 dollars per ten-minute tester; 20 testers about 40 dollars) if the free channels bring fewer than ten testers by 2026-11-10 | Money | Free channels only: public call (testbed issue 423), Moltbook through Hermes, blog post, up to five first-contact emails a day under the email protocol |
| 2026-11-03 | A "Show HN" or Product Hunt post at the next real milestone (first repaid mainnet loan or the funding-ready packet) | Personal account on those sites | Not posted; the blog session holds the milestone press release and the press kit |

## Review debt

Heads merged with a skipped non-author review under rule 3. The returning lane
reviews the merged head; a correction is a follow-up commit.

| Merged head | PR | Skipped lane | Reason | Reviewed later by |
| --- | --- | --- | --- | --- |
| 3fdbbc8e plus this row | 425 | Hermes (amended the first head, no answer on the amended head within two hours) and Codex (down) | Steward's two-hour rule 3: non-author review skipped, a three-row operator-queue addition checked by CI and the public-content check | Hermes, on the merged head |

## Answered (kept one week)

| Asked | Item | Answer | Receipt |
| --- | --- | --- | --- |
| 2026-11-02 | Locate and control the historical test USDC | Resolved November4: existing Actions signing route, not an operator-supplied key. Fresh root balances1020 on Ethereum Sepolia and130.2 on Base Sepolia after20 treasury top-up; historical allocation request remains withdrawn | [Inventory and mined receipt](../evidence/lateral-completion-20261104/README.md) |
| 2026-11-02 | `CIRCLE_AGENT_TERMS_ACCEPTED` for the Circle agent-wallet route | Set by the operator 2026-11-03; first runs recorded | PR 412, board 15 comment 6611198854 |
| 2026-11-03 | GoDaddy DNS edits for omnequa.org | Authorised; steward decides | PR 411, board 15 comment 6611090930 |

## Paused or stopped by the operator (for the record, not decisions)

| Since | What | How it resumes |
| --- | --- | --- |
| 2026-11-01 15:46Z | Agent-loan attempt (STOP, issue 384) | Only materially new evidence; NORTH_STAR.md |
| 2026-11-02 16:52Z | Blog routines (three triggers in the blog session) | Operator says "resume" to the blog session |
