# ACP public job trace: bounded no-spend test

Owner: roadmap issue 396. Research date: 1 November 2026. Bounded public retrieval session: **17:17:27 to 17:19:43 UTC**. No signup, installation, account, wallet, transaction, or contact was created. This is a narrow follow-up to `productive-markets.md`.

**Result: one historical settlement trace found; zero fully qualified independent service orders established.** The trace proves more than an advertised job mechanism, but does not establish useful output, independent customer demand, a financing gap, or human benefit. The inability to retrieve some public pages does not establish no demand or a platform outage.

## Concrete trace

Official ACP documentation identifies Base-mainnet core contract `0x238E541BfefD82238730D00a2208E5497F1832E0`. [1]

The indexed BaseScan transaction record contains the following fields. A direct open returned HTTP 403, so these are **search-indexed explorer observations**, not a fresh JSON-RPC replay. [2]

| Field | Observed value |
|---|---|
| Transaction | `0xc767da642b7647c7b3b8324f404cf5270532a43bcc084c355077ef1c8ab0d880` |
| Time | 28 May 2026, 17:09:29 UTC |
| Block / status | 46,599,411 / success |
| Job ID | 13868 |
| Events | `JobSubmitted`, `JobCompleted`, `PaymentReleased` |
| Provider | `0xDF5e15C898c869340135F39040bdf451a93f9dD8` |
| Provider payment | 9,500 base units, shown as 0.0095 USDC |
| Other ACP payment | 0.0005 USDC to `0x3F833Be7447F82E8654Bc634981899db0ee8042E` |
| Total ACP USDC outflow | 0.01 USDC |
| Evaluator in completion event | Zero address |
| Completion reason hash | `0x21839c16fffc4e30c1271a759e7416c0f68b207f691676a4b950d85bd27964b8` |

The two transfers are arithmetically consistent with ACP's documented 95% provider / 5% protocol split. [3] This is a consistency check, not a verification of the recipient's ownership. The outer transaction is an account-abstraction bundle containing another operation and unrelated token transfers. Its outer sender is not evidence of the service's original customer. The reason hash is not the readable deliverable. [2]

**Important counterexample to overclaiming:** the official Python SDK README tells testers to create buyer and seller agents, fund the buyer with USDC, and recommends a $0.01 service price. [4] This does not show job 13868 was a test; it shows why a mainnet USDC transfer at that price is insufficient evidence of independent demand.

## Qualification checklist

| Required evidence | Status for job 13868 |
|---|---|
| Stable job ID and contract | Present in indexed primary records |
| Completion and monetary release | Present in indexed primary records; fresh replay outstanding |
| Service-only classification | Unknown; do not infer from the small amount or unrelated bundled operations |
| Actual deliverable and quality | Not retrieved; only event names and a completion reason hash |
| Original buyer and funding transaction | Not retrieved |
| Buyer/provider beneficial ownership | Unknown |
| Independent customer versus self-test | Unknown |
| Incentives, rebates, operator subsidy | Unknown |
| Repeat purchases by independent customers | Unknown |
| Provider's API, compute, labor and cashout costs | Unknown |
| Input cost incurred before usable customer funds | Unknown |
| Additional spendable human income | Unknown |

Therefore the sample is **one partial settlement observation, no audited demand cohort**. It must not be reported as a successful microloan prospect or a completed 20-job audit.

## Exact public endpoints and retrieval results

All entries below were attempted within this session beginning 2026-11-01T17:17:27Z. The search service did not expose a separate HTTP timestamp for each request. No invented per-request timing is supplied.

| Exact URL | Result and fields not visible |
|---|---|
| https://os.virtuals.io/acp/overview | Readable official documentation. Identified current Base contract; no actual job rows. |
| https://os.virtuals.io/acp/architecture | Readable lifecycle documentation; no actual job rows. |
| https://app.virtuals.io/acp/scan/offerings | Official homepage link. Extracted only a JavaScript-required message; no job IDs, amounts, outputs, settlements or payer data. |
| https://app.virtuals.io/acp/agent-details/123 | Direct open returned JavaScript-required message. Search index showed review-linked IDs `1001890370`, `1001875621`, `1001875613`, `1001713933`, with truncated reviewer wallets. No linked settlement/output/payer provenance established. These are not qualified completed-job traces. |
| https://basescan.org/address/0x238E541BfefD82238730D00a2208E5497F1832E0 | Web tool reported URL inaccessible; no live contract/transaction table obtained. |
| https://basescan.org/tx/0xc767da642b7647c7b3b8324f404cf5270532a43bcc084c355077ef1c8ab0d880 | Direct open returned HTTP 403. Targeted search retrieved the indexed transaction and completion/payment event details reported above. No new chain query executed. |
| https://base.blockscout.com/address/0x238E541BfefD82238730D00a2208E5497F1832E0 | Web tool reported URL inaccessible; no live state obtained. |
| https://blockscan.com/tx/0xc767da642b7647c7b3b8324f404cf5270532a43bcc084c355077ef1c8ab0d880 | Web tool reported URL inaccessible; no independent receipt obtained. |
| https://os.virtuals.io/acp/cli/reference | Readable current command index. Describes OAuth configuration and job inspection commands; no documented anonymous global jobs endpoint on this page. Nothing installed or authenticated. |
| https://os.virtuals.io/acp/sdk/getting-started | Readable current SDK guide. Registered-agent prerequisite and wallet-based examples; no anonymous global jobs endpoint found. |
| https://github.com/Virtual-Protocol/acp-python | Readable official repository/README. Established test-flow confound and job-query methods; no runtime executed. |
| https://github.com/Virtual-Protocol/acp-python/tree/main/virtuals_acp | Tool retrieval failed as restricted URL. No further alternate-path probing performed. |
| https://github.com/Virtual-Protocol/openclaw-acp/blob/main/references/acp-job.md | Readable official historical reference, repository archived 1 June 2026. Lists authenticated current-agent completed-job access and example outputs. Examples were not treated as observations or current API guarantees. |

Targeted searches for job 13868's creation/funding events and the full provider address did not return an attributable original payer in this session. Search non-retrieval is not proof that the events or payer information do not exist.

## Cheapest material alternatives

1. **Finish this exact public trace, rather than repeat broad scouting.** A runner with an already available ordinary public-chain reader can retrieve this transaction receipt, then read the job's original creation/funding events using the verified deployment ABI and a documented read-only RPC endpoint. Require chain ID, block, buyer, provider, escrow amount, settlement, and output reference. No signer, wallet, installation or payment is needed for chain reads. This is a proposed handoff, not a completed RPC audit. Stop again if an account or paid access is required. Even successful chain reads do not by themselves establish independent beneficial ownership, net margin, or a human beneficiary.
2. **Use existing business records when the already-open consent request returns.** A redacted order, accepted output, input invoice and customer payment can answer the financing question more directly than platform-wide counters. Preserve the existing response window and do not send a duplicate request.
3. **Question the loan mechanism.** If a real order is found, compare customer-funded input costs or milestone payments before credit. A payment rail that permits buying an input after collecting the sale can eliminate the proposed gap.

Recommendation for issue 396: record this as **partial technical settlement evidence / independent productive demand unverified**. Do not promote ACP to a funded pilot from this observation. The next artifact should close a specific missing field in this trace or use the existing consenting-business records, not commission another general marketplace survey.

## Source references

1. Official ACP overview, current contract identity: https://os.virtuals.io/acp/overview (`turn72view0`, `turn74search2`).
2. BaseScan transaction and logs, historical 28 May 2026 record, search index crawled about five months before retrieval: https://basescan.org/tx/0xc767da642b7647c7b3b8324f404cf5270532a43bcc084c355077ef1c8ab0d880 (`turn76search0`, `turn77search0`, `turn79search0`; direct-fetch failure `turn75view0`).
3. Official fee mechanics: https://os.virtuals.io/acp/concepts (`turn48view1`).
4. Official SDK test instructions: https://github.com/Virtual-Protocol/acp-python (`turn78view0`, especially README Testing Flow).
5. Current CLI reference: https://os.virtuals.io/acp/cli/reference (`turn73view2`).
6. Current SDK getting started: https://os.virtuals.io/acp/sdk/getting-started (`turn73view3`).
7. Historical, archived job-query reference: https://github.com/Virtual-Protocol/openclaw-acp/blob/main/references/acp-job.md (`turn79view0`).
8. Agent page search-index evidence and direct-load limitation: https://app.virtuals.io/acp/agent-details/123 (`turn76search1`, `turn75view1`).

Publishing discipline: reopen source URLs when citing. Describe the receipt as indexed historical explorer evidence. Do not present the stale search-index read as an independent chain audit or this job as a verified external customer order.
