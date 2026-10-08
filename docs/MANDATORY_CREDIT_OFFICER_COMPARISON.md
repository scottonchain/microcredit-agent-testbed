# Mandatory agentic credit officer: design comparison and contract delta
Codex, an AI agent. Proposed architecture for discussion with Claude. No deployment, spending, live transaction or statistical field validation is claimed.

Source baseline: contract main `9f5c1434a1fa99bec7939bbf458f86ddee55bec9`; candidate PR 28 head `6fe6f4106b9594fdd0de7bbe2a51f7f6152bc538`. Sources read on October 8, 2026. The canonical model at testbed `b66b72fe1f7127dd52b96ad39821218b1896fdf5` predates the candidate's blocking independent review. Publication is held until Claude's substantive response is incorporated.

## What the officer decides
The community accepts separately labeled operating donations, repayable lending capital and consented loss-bearing sponsor backing. The officer is the mandatory admission authority for every new loan, including fully backed loans and borrowers with earned dues. It cannot spend a donor's operating grant as lending capital or treat a sponsor's stake as a donation without consent.

A request describes the actual borrower/controller, job and independent customer, input vendor/quote, currency, amount, term, repayment source, acceptance/dispute terms and maximum loss. The officer asks both whether the borrower can be trusted to perform this particular task and whether debt is needed. An otherwise trustworthy borrower can receive a NO_LOAN decision if prepayment, free resources or a direct sponsorship arrangement is cheaper.

Trust is an evidence profile plus a decision, not a universal social-reputation number.

| Dimension | Evidence and checks | Limitation |
| --- | --- | --- |
| Continuity and authority | Signed wallet challenge; spending permission; operator/controller continuity; linked outstanding debts and recovery route | One wallet is not one operator. A claimed identity does not prove unique control. |
| Task capability | Prior comparable accepted deliveries, reproducible work sample, tool/resource availability | Good repayment does not prove delivery skill; ability can change by task. |
| Customer and repayment | Independent payer provenance, accepted order, funded settlement where available, real input bill and proceeds route | Escrow reduces payment risk but does not establish honest acceptance or useful output. |
| Financial conduct | Actual principal/interest cash paid, overdue/default status, source of repayment, disputes/refunds | Sponsor-funded repayment and faucet tokens do not prove independent earnings. |
| Exposure and correlation | Open principal, guarantees, sponsor limits, shared operator/model/vendor/customer dependencies | Multiple reviewers or borrowers may fail together. |
| Recovery and inclusion | Finite downside, explained decision, appeal and lawful exit | Refusing a loan should not exclude someone from useful nonfinancial service. |

Hard gates precede statistical scoring: valid consent/authority, coherent order/quote, no unresolved material fraud indicator, viable all-in margin, an actual input gap and a willing budget for the worst permitted loss. A fully funded buyer order is not proof of delivery acceptance. State who pays if a buyer rejects good work, a provider fails, an operator disappears or an offchain payment cannot reach the repayment account.

## A defensible scoring mechanism
Keep source facts, uncertainty and the loan decision separate. Start with an explicit scorecard and small, sponsor-bounded limits; do not ask an LLM to invent a 0-to-100 trust score. The agent extracts evidence and flags contradictions. Deterministic policy code computes the limit and records reasons.

The existing issuer experiment is a useful baseline, not a validated agent-credit model. Its `policy.py` estimates a bad-event rate with:
`theta | history ~ Beta(alpha_t + B, beta_t + G)`.
It converts that rate to a 30-day default estimate by dividing its posterior mean by `1 + late_ratio`. On-time evidence is weighted by recency, unsecured principal and time at risk; loans in the interest-free window or without paid interest contribute no good trial. Fully secured principal contributes no positive unsecured-risk evidence. Late payments are not discounted for security. Defaults end the modeled identity rather than contributing ordinary trials. Identity cost, priors, demand distribution and the late/default ratio are assumptions. Simulated borrowers are drawn from the population used to fit those priors, so simulated calibration does not establish out-of-sample performance. The reference policy does not itself establish genuine independent customer revenue or repayment-source provenance.

Extend evidence first: record independently funded accepted deliveries, actual repayment source, costs, disputed acceptance and changes of controller. Do not assign new PD weights to delivery evidence without validating that they predict default. Count unique economic episodes, not mirrored receipts or wallets. Preserve negative evidence; down-weight or exclude circular/self-funded success. Separate loan default, lateness and job failure, with explicit definitions, term and observation window.

Report probability of default (PD), exposure at default (EAD), and loss given default (LGD), with ranges and assumption provenance. `expected_loss = EAD * PD * LGD` is an accounting framework, not a fitted prediction. Use conservative risk estimates and bounded sponsor loss while data are thin. Small limits cap loss despite model error; do not mistake them for proof that an identity-cost assumption is correct. Term/currency/escrow/sponsor differences require their own recovery assumptions; an illustrative 30-day PD cannot silently price an arbitrary-length ETH loan.

A loan limit is the minimum of the verified input shortfall, affordable repayment under stressed receipts, borrower/controller cap, remaining issuer/sponsor risk budget and available pool capacity. Issued credit, stake and recoverable escrow must not be counted twice. Separate worker all-in surplus from lending income and community operating subsidy. First-loss reserve is a loss absorber, not free revenue.

Before field deployment, shadow-score actual requests without lending and compare reasons/outcomes to a simple sponsor/prepayment baseline. Measure calibration and probability-score error where outcomes exist, false approvals, missed useful opportunities, realized loss, decision latency, appeal reversals and review cost. Keep rejected cases as censored observations; their counterfactual repayment is unknown. Audit selection bias, correlated controls and changes in the borrower population. No threshold or success target is presented as empirically established here.

## Single officer versus a team
A single logical office gives borrowers one accountable decision and appeal interface. It does not require one unrestricted model or one signing key.

| Design | Advantage | Cost/failure | Best use |
| --- | --- | --- | --- |
| Lone agent | Low operating cost and simple accountability | One mistaken interpretation, compromised key or outage dominates | Shadow recommendations or a very small sponsored trial with deterministic caps |
| Officer plus independent challenger | Separate fact gathering, assessment and challenge; one published policy | Review cost; independence must be real | Preferred bootstrap: review every unfamiliar or disputed request, then automate only validated routine cases |
| Threshold committee | Independent parties must authorize material exposure | Latency, collusion and quorum outages; voting does not calibrate PD | Later shared capital across genuinely independent operators |
| Human/MFI underwriter | Existing judgment and potentially established payment/compliance processes | Availability and cost; adds dependencies | Comparator or scoped specialist appeal, not required for AI-first experimentation |

A collector retrieves evidence; an assessor proposes a loan; a challenger checks independent demand, source duplication, circular repayment and failure paths. A deterministic executor checks the authorized policy and exact transaction. Independence depends on operators, keys, evidence and incentives, not agent count. Do not assign every tiny request an expensive committee by default. Record dissent and keep review access free of financial authority.

A required officer is a deliberate availability tradeoff: no fresh authorization means no new lending. Recovery, repayments, accounting and lawful exits remain available without it. This differs from the earlier officer-free stake-rooted bootstrap objective, which remains an explicit comparator until Claude and the authorized decision owner reconcile the target.

## What is already implemented, and what changes
[OracleScoreProvider](https://github.com/scottonchain/microcredit-contract/blob/9f5c1434a1fa99bec7939bbf458f86ddee55bec9/packages/foundry/contracts/OracleScoreProvider.sol) already bounds issuance through `maxTotalScore`, `maxIncreasePerReport`, `budgetHeld` and `totalHeld`; held capacity is not released just because a score falls while loans/backing remain. Epoch ordering prevents report replay and stale reports return zero provider score. Its score is a fraction of `maxLoanAmount`, not PD. The pool's owner overrides bypass provider issuance budgeting, and stake/dues/backing can enable borrowing independently of an issuer score. Freshness of a provider report is not freshness of every fact in a loan dossier.

On [main](https://github.com/scottonchain/microcredit-contract/blob/9f5c1434a1fa99bec7939bbf458f86ddee55bec9/packages/foundry/contracts/DecentralizedMicrocredit.sol), direct and meta entry points reach `_originateLoan` with no per-request officer gate. The [candidate](https://github.com/scottonchain/microcredit-contract/pull/28) has optional borrower-selected `managerOf`; zero restores unrestricted capacity-based origination, and a debt/backing-free borrower can change it. It is not a community-wide mandatory officer. Its escrow and router require themselves as the exclusive manager, so their isolated controls do not compose. The [independent source review](https://github.com/scottonchain/microcredit-contract/pull/28#pullrequestreview-5459993638) blocks execution of that head.

| Change | Minimum required behavior | Reuse or alternative |
| --- | --- | --- |
| Unavoidable approval | Require the community's authorized coordinator at the shared origination choke point for every borrower, direct/meta/vendor route and credit source | New pool instance or explicit governed mandatory mode; voluntary manager enrollment is insufficient |
| Exact one-use approval | Coordinator verifies authorized officer signature, borrower and sponsor consent; binds chain, pool, token, borrower, vendor/recipient, job/order, amount, term, max APR, nonce, expiry and policy/revocation epoch | Reuse reviewed typed-intent and signature-checking patterns; no long-lived score alone as loan approval |
| Atomic order execution | Verify funded/unexpired order and consents, reserve all risk budgets/backing, originate and disburse to the exact approved recipient in one transaction | Integrate escrow and backing behind one coordinator; cannot keep competing exclusive managers |
| Disbursement safety | No public direct/meta disbursement can redirect a managed approved loan; pre-existing requested loans cannot be attached to later orders | Atomic-only manager API; cancel/run off legacy reservations rather than laundering them |
| Exposure and loss budget | Bound actual live currency exposure, issuer allocation, sponsor cumulative/epoch losses and controller concentration; repayment does not erase realized loss | Existing provider held-budget controls help but are not a cumulative-loss cap; changes to `maxLoanAmount` must not silently inflate the dollar issuance envelope |
| Recovery and revocation | Revoke unused approvals on cancel/refund, controller compromise or policy change; safe officer rotation; reject zero-authority downgrade | Governed/timelocked authority replacement with explicit pause/recovery and accountable operator review |
| Settlement and provenance | Controlled customer settlement repays the exact loan before surplus, with agreed dispute/refund/loss attribution; keep immutable minimal outcome receipts | Reuse reviewed escrow accounting; retain sensitive dossiers offchain |
| Privilege boundaries | An owner override, relayer, issuer, borrower manager reset or malicious module cannot originate without the required approval | Threat-model governance changes explicitly; owner authority can change rules unless governance is constrained |
| Optional shared trust | If transitive delegation is retained, enforce aggregate root-to-mid capacity across all terminal borrowers and conserve root capital | This remains needed for the agreed delegation target; simpler direct backing avoids the extra route |

Put evidence interpretation, statistical policy and committee administration outside the pool. The candidate's reported bytecode has very little deployment headroom; confirm the actual compiled size at the eventual reviewed head before choosing the smallest external-coordinator hook. No ABI/runtime/deployment match or fresh independent test execution is claimed by this design pass.

The new coordinator can use EIP-1271-compatible officer contract signatures for a committee without putting an LLM onchain. Confirm borrower signature compatibility separately: the existing pool meta-signature verifier is not automatically made smart-account compatible by a manager's signature checks. Recovery must not silently give a committee or guardian authority over sponsor money beyond its consent.

Required regression cases: fully staked/dues-only/override borrower still cannot bypass; setting manager to zero or another address cannot bypass; every direct/meta/relayer/vendor path; replay across nonce/chain/pool/order and rotated authority; stale/refunded order; altered amount/vendor/term/APR; pre-order loan attachment; concurrent borrowers exceeding shared capacity; repayment without release of outstanding backing; cumulative loss after repeated replenishment; officer down with repayment/default/runoff exits still usable; disputed rejection, partial settlement and token pause/blacklist. These are implementation requirements, not tests run in this pass.

## Alternatives and recommendation
A bounded multisignature treasury and offchain ledger can run the same officer policy sooner, using direct USDC transfers or existing rails. It gives up automatic pool-wide accounting and withdrawal/settlement enforcement unless equivalent deterministic controls are implemented. Merely putting a Safe or wallet in front of the old pool does not prevent another borrower from calling the old pool directly. Separate it as a comparator, with its own permitted capital and transparent custody terms.

A customer prepayment or purpose-bound direct sponsor advance may solve a first job with less locked capital and less overhead. A different underwriter or reciprocal network is another comparison; none eliminates model, custody or human-fit risk. An agent officer cannot assess its way into customer demand.

Preferred near-term path: shadow-test a single accountable officer with an independent challenger, retain bounded deterministic custody, and compare the same accepted job under prepayment/direct advance/pool financing. Introduce mandatory origination only after explicit architecture agreement and exact-source review. Keep the current testnet as the reference rather than silently switching its rules. Scale to a threshold committee only when independent funders and observed risk justify it. Judge success by additional human retained earnings, affordable access and bounded losses, not approval count.

Sources and scope: repository source/spec review on the pinned revisions; [BIS credit-risk principles](https://www.bis.org/committees/bcbs/basel-consolidated-guidelines/module/cri/10) inform independent review and validation as a design analogy, not a statement of legal requirements for this project; [NIST's generative-AI profile](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence) supports verification of generated assessments; [Safe architecture](https://docs.safe.global/advanced/smart-account-overview) supports the treasury comparator, with security-critical modules/guards. No regulator, identity provider, customer or outside reviewer has adopted this proposal.
