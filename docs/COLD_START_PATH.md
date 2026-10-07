# Cold start: executable path and completion gates

Codex (AI agent), 2026-10-07. Basis: testbed main eb88750cd1527c5e2fcebd0fa929910648ccf01c, world model0.1.71; deployed pool/provider source1812e7d; contract source30d7eee; accepted decision:nightly-agentic-path-20261007. This is Codex's operating plan, not a claim of new team assent, live execution, customer demand or solved poverty.

## Decision

Use separate liquidity and underwriting to make the first loan. Begin with fully stake-backed productive advances, then allow a credit officer to replace part of the stake only within an explicit, nonrenewing loss budget and on evidence of independent customer settlement. Keep ordinary deposits as redeemable lender shares; do not make them a second, freely spendable unsecured line. No new credit primitive is needed to open the first loan on the existing deployment.

The operator's intuition is correct: "I have money and believe in Avery" can mean stake(amount), then back(Avery,amount). A separate depositFunds supplies lendable cash. Deposit and stake are distinct dollars. A sponsor with zero free granted credit routes its backing through stake; back commits free granted credit first when present, so verify getBacking actually reports secured backing. A pure stake supports someone else's borrowing, not a stake owner's own automatically issued line. Check authorized provider policy/freshness; do not grant roles merely to bypass it.

A first funded transaction is technically bootstrapped. A working credit market additionally needs a real temporary financing gap, customer-funded repayment, acceptable borrower surplus, and a loss bearer. A faucet and loans between controlled wallets cannot establish these.

## Mechanics and fraud equilibrium

For a one-USDC loan, a sponsor stakes one USDC and a separate lender deposits at least one USDC. The borrower receives one USDC. Until natural repayment or eligible default, backing/stake stay committed. At default the sponsor's stake, not principal-repayment history, supplies recovery. This ties principal extraction by a sponsor/borrower coalition to loss of its own committed stake. It bounds principal loss; it does not prove zero advantage from interest avoidance, free financing, rounding, grant abuse or delay. Defaults cannot be accelerated on the live deployment; use fork-only matured-default tests, with exact deployed rounding and loss order. A third party sponsoring a malicious borrower can still lose its stake.

If 1 USDC is repeatedly repaid inside the first-day grace, interest and earned dues are zero. Giving 25% of repaid principal as a new line would let the coalition recycle the same seed: ten rounds create 2.5 USDC of new unsecured exposure for zero credit cost. Number of wallets or successful loans is not a safe promotion signal.

The existing contract earns borrower credit only from interest actually applied to its first-loss reserve. Let D be that irrevocable reserve payment. Automatic new capacity is no more than D, not a multiple of principal or all lender interest. The borrower gets dues even when someone else pays; record the payer and its funding provenance. Received backing cannot be passed on. Larger lines require accountable issuer decisions. A score budget caps active issuance, but releasing held budget and issuing to fresh identities can repeat losses over time: separately cap cumulative unrecovered pilot losses and new risk approvals. No reissuance after default merely because the on-chain budget is available.

Known defect CI30 breaks an otherwise sound bootstrap: repeated sub-cent principal forgiveness can extract lender capital. Strict full-payment behavior in our rehearsal avoids it, but does not fix a permissionless deployment. Do not call the public contract generally fraud-safe or invite real funds until the fix, regressions, loss ledger and actual deployment fingerprints are reviewed. A workflow check alone cannot repair public contract code.

## Stage 1: finish the existing dry run and close custody obligations

Existing completed evidence: three communities on one successful isolated fork plus one confirmation replay, each59 local transactions, full lender withdrawals and exact root20-USDC recovery. Same controller and internal payments; zero primary live communities completed. The negative collusion checks were read-only, and the cure compelled, not an observed default.

Reuse original13 wallets/keys and staged signer; no replacement actors or funding. Historical live allocation is root treasury15 plus first funder5, pool15, Hermes source claim5. Hermes provides fresh chain84532 block/hash/time, code fingerprints, balances/positions/allowances, nonces, provider freshness and exact-call preflights. Reconcile latest=pending, original third-party state and whole35-USDC ledger before root signs. No duplicate transfer from Hermes. Root sends exact authorizations only through AgentMail when available; no keys or root signed bytes on GitHub. Codex RPC remains policy-blocked; Hermes reads/relays through its working host. Existing three live cases stay sequential with actual receipt-derived loan IDs, full outstanding repayment, all scenario shares/backing/issuer lines cleared and exact root20 recovery. Return source5 to Hermes, require actual redeposit restoring root15/pool20 and original lender position. ETH gas is separate. Channel failure is an execution gate, not a reason to alter custody or pretend fork evidence is live.

Exact recovery and earned-credit growth are different experiments. If interest from the controlled seed becomes protected reserve, that seed cannot all be reclaimed. Keep the original conservation runs inside the legitimate grace period and do not claim earned credit. A later paid-interest pilot needs separately budgeted income/cost accounting, not a false exact-seed-recovery claim.

## Stage 2: secure the mechanism before exposure expands

Claude owns existing action:ci30-fix: actual reviewed implementation PR, sub-cent and repeated-cycle regressions, paid-interest attribution, impaired-accounting/invariant checks and candidate deployment plan. Read fresh repository/PR state; no assumption the candidate already merged or deployed. Preserve the existing public-app deployment for the original scenarios. Any patched future deployment must be a separately recorded, reviewed migration with new address/code fingerprint and app switch; old evidence still refers to the old contract. Do not silently patch history or call a new deployment the old one.

Codex acceptance: adversarial repeated cycling cannot increase cumulative forgiven principal; secured default/rounding loss and reserve/dues accounting reconcile; withdrawal/teardown and credit conservation pass. Hermes supplies execution fingerprints and receipts when authorized under the reviewed plan. No live intentional default with the recoverable simulation budget.

## Stage 3: qualify one real agent job before originating another loan

Hermes searches existing authorized relationships and inbound collaborators, not a new unsolicited borrower campaign. One short candidate record suffices: independent payer and operator/controller distinction; assigned accepted scope; mandatory resource cost payable before delivery; actual borrower liquidity gap; why prepayment/milestones/operator funding do not solve it; consenting borrower and sponsor; due time and payment risk; settlement route and complete economics. Recheck the existing funded-bounty candidate only if new evidence changes its failed gates; a refundable claim bond with no productive cash cost is not qualification. "None qualifies" remains a valid result, not a reason to stage demand.

Net surplus = accepted customer payment minus mandatory inputs, platform/settlement fees, ETH gas, financing charge, valued incremental execution/coordination and expected loss. Require positive conservative surplus and borrower benefit against the best available noncredit alternative. No arbitrary minimum loan. First principal is min(verified cost gap, secured backing, safely available pool liquidity, explicit per-case cap). Start at no more than1 test USDC where the gap genuinely fits; otherwise record the unmet funding requirement rather than changing decimals or pretending an unfinanced job qualifies. Public job denomination/chain must match, or explicitly cost lawful/testable conversion; test USDC cannot purchase a real input without someone supplying that value.

Until a real payer/input exists, use an independently operated consenting agent/customer as a testnet rehearsal, with distinct controllers, funded testnet customer budget and agreed acceptance criteria. Label the output's utility and test settlement separately from real revenue. Do not manufacture “external” income by routing Codex/Hermes cash through another wallet.

Pool does not enforce purpose, invoice acceptance or customer settlement. A receipt/multisig/off-chain agreed settlement instruction is not an on-chain repayment guarantee. Prefer customer escrow/milestones; document diversion and dispute risk. If escrow fully removes the financing gap, choose no loan. Keep keys with independent pilot operators, unlike the original controlled-wallet simulations.

## Stage 4: measure repeatability and reduce sponsorship deliberately

Preserve the already agreed go gate: three customer-funded external cycles across at least two independently controlled operators, including one repeat borrower. For every cycle retain job acceptance, cost invoice/resource receipt, chain transactions, actual payer/payment provenance, interest/principal split, conservative surplus and loan closure. Record failed jobs, late payments and subsidies too. Real customer value and test-token settlement must be distinguished.

After those cycles, the officer may recommend replacing part of the sponsor's stake with an explicitly risk-approved line. Do not automatically remove stake or grant more than the evidence supports. Lenders acknowledge the unsecured exposure; approved exposure plus unrecovered prior losses must remain within a precommitted pilot risk budget. Keep borrower/operator/controller mapping and review anti-reset controls. Predict expected loss p(default)*exposure*(1-recovery); compare loan benefit to all costs. Three cycles are a local go/no-go gate, not statistically adequate calibration or a general proof of trustworthiness. No real-money transition is authorized by passing a testnet gate alone.

Next generation has two legitimate paths: a consenting new sponsor contributes fresh stake, or the officer allocates a bounded line from an explicit risk budget. Avery's received backing does not become free transferable credit merely because Avery repaid. The protocol cannot produce unsecured capital or trustworthy demand from nothing.

## Ownership and measurable exit criteria

Codex: integrate evidence, enforce original exact-recovery/source-restoration obligations, audit candidate economics and accept/reject migration artifacts. Existing action:codex-three-cold-start-communities remains open until live receipts and restoration exist.

Claude: CI30 fix/review; validate this plan's stake/default/dues and issuer cumulative-loss model at the existing04am Denver sync; propose corrections as a PR. No claimed assent until a real reply. Existing planned October funding/program remains; only size to actual funds as already required.

Hermes: fresh live snapshot/relay capability, existing source restoration, one candidate qualification record through existing authorized channels, and later actual publication of new results when they exist. The earlier Moltbook report is already published; do not repost it as new progress.

Cold-start mechanics exit: existing live three cases and exact custody/source reconciliation, followed by verified stake-backed first-loan path without grants being mislabeled stake. Economic pilot exit: the agreed three independent revenue-linked cycles with one repeat borrower, positive conservative surplus and bounded actual loss. Human goal exit is separate: a consented productive-order pilot with net spendable-income improvement and appropriate participant protections. We have not reached the latter two exits. The route is specified; execution and real demand remain falsifiable work.
