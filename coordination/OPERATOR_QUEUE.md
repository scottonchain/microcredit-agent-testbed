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
| 2026-11-02 | 2,000 test USDC in the Codex wallet (1,500 pool deposit, 500 sim treasury) | Key on the Codex host | Drip workflow supplies the treasury and desk within its caps |
| 2026-11-03 | Allow `corp.roblox.com`, `www.sec.gov` and `www.placera.se` in the cloud environment's network settings (optional) | Environment setting | Figures taken from search summaries and the register's earlier reads, limitation stated |
| 2026-11-03 | A seed amount and a lawful payout route for paying a human for a first job (B10) or for judgment work (F9) | Spend authority | B10 parked; F9 continues as a zero-spend specification |
| 2026-11-02 | Blog routines paused: YouTube watch, AI news watch, scheduled post (operator said "pause" to the blog session at 16:52Z) | The operator paused them | Stay paused; the blog session resumes all three on the word "resume". While paused, PR 386 (world-model YouTube findings) is closed as stale after November 10 and recreated from the current model when the watch resumes |
| 2026-11-03 | Name the jurisdiction for the human-first mainnet pilot (D16) and engage counsel on lender of record, licensing, rate caps, disclosure and whether platform-side dollar conversion is money transmission | Legal and signature authority | The lane drafts the counsel brief by November 10 on a US assumption; research and build continue; nothing deploys |
| 2026-11-03 | Mainnet checkpoint for D16: the funding-ready packet and deployment plan will be handed over when every gate has its receipt; the 100 USDC and the deployment are the operator's | Spend and deployment | None until the packet exists; the operator asked to be checkpointed only then |
| 2026-11-03 | Accounts for the D16 measured round trip (November 24): a Stripe account in test mode, and a Coinbase business account or a Bridge developer account (Bridge opens developer accounts through its support team; no self-serve) | New accounts and their terms | On-chain legs measured on Base Sepolia; the dollar legs priced from reported figures ([round two](../evidence/human-first-mainnet-20261103/round2.md) section 6) until an account exists |
| 2026-11-03 | Allow `docs.stripe.com`, `support.stripe.com`, `apidocs.bridge.xyz`, `www.bridge.xyz`, `help.coinbase.com`, `www.fincen.gov` and `www.ecfr.gov` in the D16 session's network settings (optional) | Environment setting | Rails figures taken from search summaries with the limitation stated in every record |
| 2026-11-03 | Apply the project permission allowlist in [settings.allowlist.proposed.json](settings.allowlist.proposed.json) over `.claude/settings.json` ([review](AUTONOMY_REVIEW_20261103.md) section 6) | A session may not widen its own permissions; the classifier refused the edit | Sessions prompt for read-only commands in default mode; routine sessions run in auto mode |

## Review debt

Heads merged with a skipped non-author review under rule 3. The returning lane
reviews the merged head; a correction is a follow-up commit.

| Merged head | PR | Skipped lane | Reason | Reviewed later by |
| --- | --- | --- | --- | --- |
| (none yet) | | | | |

## Answered (kept one week)

| Asked | Item | Answer | Receipt |
| --- | --- | --- | --- |
| 2026-11-02 | `CIRCLE_AGENT_TERMS_ACCEPTED` for the Circle agent-wallet route | Set by the operator 2026-11-03; first runs recorded | PR 412, board 15 comment 6611198854 |
| 2026-11-03 | GoDaddy DNS edits for omnequa.org | Authorised; steward decides | PR 411, board 15 comment 6611090930 |

## Paused or stopped by the operator (for the record, not decisions)

| Since | What | How it resumes |
| --- | --- | --- |
| 2026-11-01 15:46Z | Agent-loan attempt (STOP, issue 384) | Only materially new evidence; NORTH_STAR.md |
| 2026-11-02 16:52Z | Blog routines (three triggers in the blog session) | Operator says "resume" to the blog session |
