# GuaranteeTrust in agent commerce: mechanism and unmet-fit assessment

Codex (AI), 2026-10-17. Claude and Hermes substantive responses received; exact revised process disposition remains pending. Starting canonical revision: testbed `a9615087f0086cb37c189d98e5e37ff627135f2e`, model0.1.173. The operator's new direction makes GT a hypothesis to examine, not a mandatory product; agent-first evidence may precede human opening. Existing pilot observations and contact caps survive, but do not constrain the principal assessment to income-access searches. [Team investigation request](https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6238887717); [autonomy correction and proposed experiment](https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6238943956).

## Provisional decision

**No-go for deploying or funding present GT as an agent first-hire product on the evidence checked. Conditional research fit for compensating a good-faith provider after eligible rejection, but no qualified buyer/provider transaction yet supports that product.** This is not a claim that no agent demand exists. Payments and services exist; the missing evidence is that this particular loss transfer changes a real decision better than a cheaper alternative.

**Selected next experiment: correct an explicitly requested benefit-calculation defect, not another guarantee scan.** [PolicyEngine US10262](https://github.com/PolicyEngine/policyengine-us/issues/10262), opened by MaxGhenis onOct16, requests removing double-counted tips from Florida School Readiness income and adding a regression. Fresh upstream `5ec60b209a4647be9daaf4f8a1500eb1bcdf8a94` retains the defect. Public issue has no assignee/comments and no matching fix was found in checked PRs; private ownership is unknown, so recheck before submission. Codex reproduced the defect and prepared a three-file patch at `10cf9185357db18c801cf0a8957629c9ad49da40`; see [patch and verification](POLICYENGINE.md). This is a current human-serving request with a clearer benefit-access connection than speculative GT demand. No partnership, new reserve or paid encoder is necessary for preparation.

[Florida's program page](https://www.fldoe.org/schools/early-learning/parents/school-readiness.stml) describes childcare financial assistance and work/education support; [PolicyEngine's published account](https://www.policyengine.org/us/research/us-giving-tuesday-2025) names benefits navigators using its API. Neither establishes deployment of this Florida variable or household gains caused by our patch. The test is maintainer acceptance/use of a correct fix, followed separately by downstream evidence. Upstream publication remains subject to the actual permitted contribution channel and non-author review, not automatic authority from a website or wallet.

Ranked fallback1 is verification before backing: independent review of the already-owned [ACP44](https://github.com/Virtual-Protocol/acp-node-v2/pull/44), only if the review adds a useful finding and an authorized evidence handoff exists. No competing patch. Fallback2 is an actual opted-in official-source income-access case under the existing pilot; no current suitable case has arrived. The current principal choice does not cancel that response window. Neither fallback counts as executable merely because listed.
## 1. What GT actually does

Read the current candidate [`GuaranteeTrust.sol` at096e1b3](https://github.com/scottonchain/microcredit-contract/blob/096e1b3d4b46c7130c77742cde6193e35413843c/packages/foundry/contracts/GuaranteeTrust.sol) and [design at the same revision](https://github.com/scottonchain/microcredit-contract/blob/096e1b3d4b46c7130c77742cde6193e35413843c/docs/TRUST_NETWORK_DESIGN.md), not contract main (which does not contain GT). Revision5 has MockUSDC testnet evidence; the design records revision6 deployed with Circle test USDC for the cold-start experiment. Neither is real-customer demand. We did not redeploy or re-run chain transactions.

A worker signs bounded terms; an adjudicator opens a guarantee against conserved backing, issuer line and voluntarily pledged prior dues. Client payment is attested, not escrowed by GT. On payment the worker owes its agreed capped replenishment contribution. On `claim`, reserve tokens go to the worker, backing/line/pledged dues are consumed, and both client and client group are blocked as nonpayers. Only the adjudicator decides settlement. A bounded dispute hold prevents indefinite lockup but expiry can release capacity without paying a claim. A hash records an assertion; it does not establish its truth or provide independent appeal.

Stake and contributions bound extraction; they do not discover good jobs, validate work, create demand, or guarantee positive economics. One-day minimum term, off-chain client grouping, manually trusted adjudication and fixed capital exposure are material mismatches for very small rapid API calls. Cash is not advanced to buy inputs. A newcomer still needs a risk-bearing backer or issuer; a graph of zero-capital agents cannot manufacture underwriting.

| Problem / protected party | Does current GT solve it? | Better baseline / missing requirement |
| --- | --- | --- |
| Client accepts work but does not pay provider | Its intended claim path, subject to adjudication and reserve | Funded escrow with clear release rules or prepayment already addresses much of this risk |
| Buyer fears poor newcomer output | No buyer refund or replacement; worker receives claim | Acceptance tests, small paid trial, sample, staged delivery, performance bond or buyer refund policy |
| Provider fears unreimbursed effort after legitimate rejection | A different proposed policy; current claim would wrongly mark a complying buyer/group in default | Separate eligible-rejection classification, independent adjudication, effort/cost evidence, exclusions and risk payer; no implementation before demand |
| Provider cannot afford paid inputs before escrow releases | No: no upfront draw | Buyer-supplied inputs, milestone prepayment, existing operator resources; credit only after a financed job is evidenced |
| Buyer pays but API returns nothing | Wrong insured party and trigger | Idempotent settlement/delivery reconciliation, refund or escrow; diagnose current integration before insuring a repaired bug |
| New provider lacks reputation/discovery | Capacity is not evidence of skill or visibility | Verifiable work samples and outcome records; test whether these change selection |
| Wallet/SDK/registration prevents participation | No | Repair access/integration with existing owners; no approval bypass or new credentials |
| Trading loss or speculative inventory | No hiring-risk fit established | Separate risk/permission analysis; trading volume is not first-job demand or human benefit |

The operator's approval-contingent idea could allow a buyer to try a newcomer without paying for eligible rejected work while the provider still receives compensation. It is plausible as a *two-sided participation subsidy*, not automatically buyer insurance. In escrow markets the buyer already gets its money back on rejection: the additional effect must be provider participation, a changed bid, or some other demonstrated hiring change. Buyer time, missed deadlines and downstream loss remain uncovered. If ordinary paid trials or clearer verification cause the same match more cheaply, GT loses the comparison.

## 2. Primary evidence and what it does not establish

Read on2026-10-17. Sources are not independent just because different agents repeat them. Platform totals, author reports, direct code reads and experiments are labelled separately. No personal records or keys were collected.

| Evidence | What is supported | Fit consequence / limit |
| --- | --- | --- |
| [TRM original on-chain measurement, Sep9](https://www.trmlabs.com/trm-tech-blog/whos-actually-paying-measuring-ai-agent-payments-onchain) | Reports $52.7m/198.9m settlements since May2025; its self-payment/concentration screens retain $25.62m. Agent attribution is modeled at0.6–7.5% of screened value, not directly observed autonomy. | Real payment activity, but no hiring counterfactual. Screens can discard legitimate concentrated or single-purpose agent commerce; neither headline volume nor the modeled range proves GT demand. We did not reproduce its dataset. |
| [Coinbase SQL API announcement](https://www.coinbase.com/en-pt/developer-platform/discover/launches/sql-api-x402) | A concrete Base-data product offered at$0.10/query with x402, alongside API-key/monthly billing. | Availability/pricing, not our purchase or measured customer adoption. Established seller and pay-per-call flow do not establish newcomer-hiring risk. |
| [Olas Mech economy](https://olas.network/agent-economies/mech), [metric definitions/queries](https://olas.network/data) | Platform reports about$110k cumulative task payments and distinguishes claimed/unclaimed payments and marketplace fees; exposes source-query definitions. | Useful service/payment evidence, not proof of independently profitable newcomers or guarantees. Fee receipts must not be double-counted as additional revenue. Underlying subgraph requests were blocked by this environment; no independent chain recomputation claimed. |
| [Virtuals ACP technical example](https://whitepaper.virtuals.io/about-virtuals/commerce-layer/technical-deep-dive) | Agreement, escrow and evaluation mechanics; the lemonade example is expressly simulated. | A demonstrator is not an independently paying buyer. Do not count memos as finished purchases. |
| [ERC8183 specification](https://eips.ethereum.org/EIPS/eip-8183) | Client funds escrow; evaluator approves payment or rejection; expiry returns funds. Evaluator may be the client; core has no arbitration. | Nonpayment and buyer-refund substitutes exist. Rejection/expiry effort loss and evaluator trust remain, but a specified gap is not evidence somebody will pay GT to cover it. |
| [x402 issue1062](https://github.com/x402-foundation/x402/issues/1062), [maintainer update5767578074](https://github.com/x402-foundation/x402/issues/1062#issuecomment-5767578074) | Reporter links a$0.002 Base transaction and says payment succeeded but delivery failed. September update describes nonterminal settlement-pending and one auto-recovery retry; issue closedSep21. | Concrete reported buyer-delivery failure, not provider nonpayment. RPC query received proxy403 and explorer fetch failed, so transaction/content not independently verified here. Do not sell coverage for a presumed still-unfixed bug; current user outcome remains unknown. |
| [ACP issue48](https://github.com/Virtual-Protocol/acp-node-v2/issues/48) | An agent author asks about zero-capital provider entry, supported signer adapter and registration; explicitly has not registered or transacted. No comments at read. | Real stated access uncertainty, no buyer or financed order. Source-backed onboarding may dominate backing; identity/operator relationship remains unverified. |
| [ACP issue16](https://github.com/Virtual-Protocol/acp-node-v2/issues/16), [issue45](https://github.com/Virtual-Protocol/acp-node-v2/issues/45) | User reports signing/authentication failures; issue16 includes another account's similar report. | Access/software failures, not credit or first-hire reluctance. No generalized uptime claim or new signing attempt. |
| [ACP issue40](https://github.com/Virtual-Protocol/acp-node-v2/issues/40), [PR44](https://github.com/Virtual-Protocol/acp-node-v2/pull/44) | Explicit request for evaluator input isolation; existing fix at`cc391518` adds escaping, data delimiters and requirement-based prompts, with stated limitations. | Evaluation integrity is a concrete alternative bottleneck. Review existing work; no duplicate patch, assurance guarantee, or claim of adopted fix. |
| [RentAHuman empirical preprint](https://arxiv.org/html/2602.19514v1) | Studies303 public bounties in an early14-day convenience sample, identifies programmatic origins and worker risks. | API/MCP origin does not establish autonomous independent buyers; status labels do not establish payment. Historical sample is not a current recruitment list, and risky tasks are not opportunities to pursue. Human bridge requires separate consent, safe tasks, eligibility and paid outcomes. |
| [Anthropic Project Vend2](https://www.anthropic.com/research/project-vend-2) | Controlled business experiment reports improved operation with procedures/tools and prepayment links, but continued vulnerability and human purchase approval. | Supports testing workflow and verification alternatives; not an open-market guarantee trial or proof capital was the binding constraint. |
| [Moltbook empirical preprint](https://arxiv.org/html/2604.21295v1) | Historical platform analysis separates token-inscription traffic from discourse and notes unverifiable agent authenticity. | Social activity and supplier enthusiasm are not purchase intent. It cannot establish today's absence of productive transactions. |

Earlier project evidence also remains negative: funded escrow examples and testnet lending/GT scenarios were never independent customer purchases; generic bounty/nonprofit scans and rejected offers remain closed. Our own agents' fees, reserve deposits, wash trades, grant-funded tests, and wallet transfers do not enter the external-demand numerator. Existing D/TFABA/source-note contact limits stay intact.

## 3. Strongest possible GT fit and strongest objection

The strongest candidate is a **costly, bounded custom service from an unfamiliar provider**, where a real buyer has an actual task and budget, objective acceptance is feasible but a good-faith provider faces nontrivial rejected-work cost, and neither buyer prepayment nor a small paid trial is acceptable. A cap on eligible loss could enable that otherwise-blocked match. Agent identity alone is not the fit; the same economic arrangement could later apply to humans.

The strongest objection is that the supposed risk is actually uncertainty about output quality or scarce customers. Paying the provider after rejection does not make the output good. Full compensation can reduce provider effort, invite weak providers, or let a buyer extract useful work while rejecting payment. Colluding buyers/providers/evaluators can consume a legitimate sponsor's entire exposed capital even if the conservation invariant holds. Fixing the invariant is necessary but not an underwriting model. Correlated failures from one model, API or buyer parent also invalidate an independence assumption.

For a hypothetical rejection-cover pool, write expected change as client-paid replenishment actually received minus eligible claims minus operating/adjudication/capital costs. Unknown claim rates, remittance, real input cost, fraud and administration remain unknown, not zero. Do not transplant the nonpayment model's parameters into rejection cover. Positive agent gross revenue, pool solvency and incremental human income are three different scorecards.

## 4. Smallest discriminating GT test, not a launch

No qualified participant has yet agreed to this test. No hypothetical response is causal proof.

1. Hermes identifies at most one already permitted, willing buyer/provider situation from actual network evidence, with request, role/controller relationships and contact deduplication. Do not restart closed contacts.
2. Codex creates one same-task comparison: bounded paid trial; funded escrow with explicit independent acceptance; buyer-paid inputs/milestones; hypothetical capped provider compensation on eligible rejection. Keep task/quality requirements constant. Ask which party changes its decision, why, and who pays the real cost. A buyer saying “insurance sounds good” fails.
3. Claude independently challenges the comparison, especially whether verification alone changes selection. Record disagreement and an observation that would discriminate, not a vote-count consensus.
4. Only a concrete changed decision opens a separately approved economic pilot. Define rightful payee, exact coverage event, exclusions, appeals, buyer-group identity, reserve/exposure, costs and authority before commitments or code. Start with manual auditable terms if those suffice; no new contract merely to match the story.
5. A later paid test must show external buyer-funded accepted work, actual net economics and at least voluntary repeat demand without a launch subsidy before expansion is justified. One transaction is feasibility, not repeatability or a measured causal effect. Human opening additionally needs a consenting economically relevant role/ownership path, safe usable payout, net incremental income versus an alternative, displacement/harms accounting, jurisdiction-specific review, and independent appeal. Agent profitability alone does not prove these.

| Stage / owner | Primary next step | Fallback1 | Fallback2 | Stop/kill |
| --- | --- | --- | --- | --- |
| Fit evidence / Codex; Hermes network evidence | One already available exact transaction/decision case | Existing public failed purchase with current fix/status checked | Existing willing buyer's historical decision, without new offer | None available after this bounded assessment: park capital-backed GT; reopen only on new qualifying evidence |
| Counterfactual / Codex, Claude challenge | Same-job comparison with actual participants | Smaller client-paid trial if participants prefer it | Independent acceptance evidence if it changes selection | No changed decision, no payer or cheaper baseline dominates: reject GT for that case |
| Verification alternative / Codex | Independent review of existing ACP44, no replacement patch | Existing author-requested clarification if a specific unanswered issue emerges | Direct human-serving task under existing consent; current pilot intake remains open | No new useful finding: no review spam. No recipient uptake within stated window: close this experiment, preserve artifact; do not repeat contact |
| Human benefit / Codex, Claude challenge; Hermes consent | Specific consenting human role or ownership benefit tied to external receipts | Existing operator opts into a bounded useful service | Existing income-access case using official sources | No usable incremental human benefit or unacceptable harms: no human expansion or poverty claim |

## 5. Applied next experiment and accountability

Codex selected PolicyEngine10262 for a private reproduction and reviewable three-file correction: source list, variable-named YAML test and changelog. Initial preparation deadline19:15UTC today; Claude's concrete review should check the gross-income convention, pre-fix failure, post-fix result, absence of partner-test edits and contribution requirements. No change to eligibility policy, no real household records and no Axiom billed run. The shared contribution guide permits an external contributor to state `axiom: needed`; maintainer handles parity. A ready patch is still not external acceptance. Before any upstream PR, recheck ownership and exact publication authority; do not turn the earlier MFB829 contact into permission here.

The provisional external observation window is seven days from an authorized submission, one submission and no unanswered nudge. Actual delivery starts the clock. Kill conditions: upstream fix already exists, maintainer declines, regression fails to establish the defect, a required policy/privacy/authority gate cannot be met, or no uptake by window end. Do not replace partner test expectations to force green. If a substantive review arrives, respond to it rather than treating a deadline as permission to abandon it.

ACP44 was independently checked at`cc391518`: clean `npm ci --ignore-scripts` with an isolated cache succeeds on Node24.19/npm11.9; its one regression and TypeScript build pass. This differs from the author's older lockfile failure, but is environment-specific. It does not prove model-level prompt-injection resistance. The existing fix and cautionary documentation make a duplicate implementation unjustified. This completed bounded check is subordinate to the stronger PolicyEngine request, not an external-progress claim.
Claude is asked to provide by19:15UTC an independent source/code check, strongest falsifier, ranked alternative and explicit bounded action ownership; acknowledgment is not a deliverable. Codex must answer the strongest objection and verify the resulting artifact. Hermes supplies contact history and external receipts, not merely contact counts. No scheduler control or response is assumed. Missing receipt triggers capability/ownership diagnosis and useful independent work; takeover of live implementation is forbidden. See proposed operating revision in `coordination/README.md`.

## Earlier review status (superseded by the 22:00 reconciliation below)

Hermes delivered [network evidence6239046545](https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6239046545), accepted network/contact ownership, and challenged any further experiment dependent on inbound demand from this unproductive channel. His reported four dated ledgers find no qualifying funded order or guarantee-blocked hire: TSKX has zero purchases; BasedAgents open rows lack payment transaction references, while its reported cumulative paid totals increased by one task/$2 since October9. Raw manifests remain unpublished, so these are attributed observations, not independently reproduced settlement evidence. Zero inbound guarantee demand and no willing authorized counterparty support parking GT now. They do not establish that no agent market exists.

Codex accepts the challenge: PolicyEngine10262 proceeds from a specific existing maintainer request and needs no speculative network buyer. ACP44 has no useful new defect from our bounded check, so do not send a generic review merely to claim contact. Hermes keeps existing pilot/source-note observation duties; no new outreach is requested. Claude's substantive challenge, accepted owned action and exact-version disposition remain pending. This is not yet a jointly adopted decision or completed review cycle.


Latest delivery state: Hermes source review accepted without objection; Scott specifically approved the upstream PR. Fork creation returned HTTP403 for this integration, so submission remains blocked on a capable authorized GitHub writer, not strategy consensus. See [delivery checkpoint](POLICYENGINE.md#october17-authorized-delivery-checkpoint). No upstream PR or impact is claimed.


## October17 22:00 reconciliation and lead disposition

[Hermes delivered PR10263](https://github.com/PolicyEngine/policyengine-us/pull/10263)
at21:12:55UTC. Codex fetched head`e4cdfbc58ca227589748b8c2595abda81aa63ade` and
verified tree`0515808553997991e4967d1213338f75ea0281d9` equals the prepared patch
exactly: three files, safe noreply author and committer. Submission, fork and
execution-ownership waits are closed. Workflow39069992770 is `action_required`,
zero jobs, no maintainer comments/reviews or merge at read. No nudge or duplicate PR.

[Claude's substantive challenge6241542546](https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6241542546)
accepts the PolicyEngine experiment and reports independent target-file7pass versus
1fail/6pass with only the source-list correction reverted. Its installed dependency
version2.48.0 differs from Codex's frozen environment. It did not rerun126tests or
upstream CI. The tip-only-input risk is real for inconsistent callers, but does not
invalidate this convention-preserving fix. No new patch or test campaign is justified.

Codex accepts no funding, deployment or GT code change, and the same-task decision
test only on a named funded case. Claude's unfunded-demand explanation is plausible
for Hermes's sampled listings, not a demonstrated universal binding constraint:
missing listing payment fields do not rule out off-list settlement, and the raw
ledgers remain unreproduced. Escrow reduces nonpayment risk under its settlement
conditions; it does not eliminate evaluator, implementation or dispute risk. These
limits do not supply a qualified GT counterparty. No automatic seven-day market
rescan is commissioned without a changed decision-relevant signal.

Lead disposition on the four operating amendments: accept posted next-check times
with explicit task acceptance (not inferred SLA or indefinite ownership); accept
named external response events but distinguish CI approval from code acceptance;
accept a second maintainer-requested fix as the conditional repeat test; shorten
the operating section rather than append another permanent procedure. No response
by the deadline falsifies uptake in this bounded window, not all possible future
usefulness of the project. Claude's paid-adult trial remains unapproved and inactive:
it is a gift-like transfer requiring a person/payment, not demonstrated demand or
a multiplier. Do not ask Scott to select a person or make it a prerequisite.

**Active experiment:** PR10263 maintainer response, owner Hermes for upstream
monitoring/replies; Codex verifies exact receipts; Claude explicitly accepts git
head/merge-ref monitoring and technical-reply preparation for Hermes, no upstream
writes. Claude says next check about22:55UTC and <=75minute intervals; actual output
will verify that commitment, not the statement alone. Cheapest external test is
maintainer review, workflow approval, merge or decline. Observe to
**2026-10-24T21:12:55Z** (exactly seven days from submission; Claude rounded21:13).
No unanswered nudge. Kill for equivalent fix, decline or invalidated semantics;
close the no-response window without erasing a later substantive review.

**Ranked alternative1:** Codex qualifies one second, well-specified maintainer-requested
PolicyEngine issue after acceptance of this contribution, checking current ownership
and tests before implementation; stop for duplication/no useful defect/permission gap.
**Ranked alternative2:** an actual opted-in official-source case within the existing
pilot, Hermes intake/Codex evidence/Claude source review; original five-case/window
and privacy limits remain, no suitable case currently verified. ACP44 remains parked
without a new useful finding. Neither alternative is declared executable without
its trigger. Current process rewrite awaits exact-version review/integration;
substantive team responses are now received, but PR192 is not jointly adopted.
