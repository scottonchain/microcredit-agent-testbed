# ETH gas-credit experiment: execution record

Codex (AI), 2026-10-08. Qualification in progress. No native loan, claim
transaction, swap, earned fee or repayment has executed.

## Actual observations

Hermes supplied read-only Base RPC observations at commit
77401503f995f37b6ef31888f5bf6bebc15673b9, evidence/ptv5-r1, with its receipt:
https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6049571854

It reports block52314628, hash
0xaa35ca53b7ee535f9639cdb01c317e238a8dbdc8f66ed261e4c6e09ba2cfbfa3,
draw841, seven tiers, deployed Claimer/PrizePool code and canonical Base WETH
as prizeToken. It obtained no current winner list or exact claim/fee/gas
simulation. A sampled500-block log window had no claim logs; this does not
establish absence of other claims or available jobs. No funds moved.

Codex independently downloaded the immutable public files and verified raw.json
(79,858 bytes) SHA256
b4f97e62c9691f3f4d265b31f0c62f38db267a1e34914e0eb088cf33a090e29e
and README SHA256
34585553b2bebc9216f4fa6f0015c2afc4dcd4697d1c495171fc31ec2560eb88
against Hermes's manifest. This verifies artifact identity, not independently
reading the chain.

Codex prepared read-only-winner-probe.mjs with official
@generationsoftware/js-winner-calc@1.3.1. Syntax, help and missing-RPC negative
control passed; it has not yet run against live RPC. The source-confirmed public
keyless GraphQL endpoint/schema is in KEYLESS_WINNER_DISCOVERY.md; availability
is unverified. The historical draw735 seed supplies1104 account addresses,
not current winners. The probe examines at most128 addresses and12 candidates,
forces contract reads to a recorded block, caps requests/runtime, refuses
signing/transaction methods and confirms eligibility, claim status, hooks,
claimer and quoted fee. An empty sample cannot prove global absence.

The exact probe/instructions were sent to Hermes and Claude via AgentMail,
work ID ETH-GAS-BOOTSTRAP-20261008-r6-probe, API acceptedHTTP200. This does not
prove execution. Their next result is due01:00Z. No duplicate automation or
change to the daily04:00 America/Denver sync was made.

An initial broad execution handoff was rejected by automatic approval review
because a concrete spending cap and already-qualified operation were not
established. It did not dispatch or move funds. Subsequent handoffs are read-only.
Exact transactions will be reviewed after a paying operation and complete costs
are concrete.

## Execution gates

Root controls borrower 0x62C4A163026feedB3eA1045d90bBa96d0C5d4F0B.
Hermes manages lender treasury 0xdb3dE88E9dba1B07A06D186DFbD86fae309043ad.
No private keys are included. Funding, claim, reward withdrawal, WETH unwrap
and ETH repayment require exact amounts/nonces, code/token fingerprints,
positive actual call simulation and complete L2/L1/operator fees.

Proposed ceilings: principal50,000,000,000,000wei and no more than$0.50;
gross experiment spend$1; bounded gas/loss$0.25. A fresh ETH/USD quote is needed
to apply both limits. These are ceilings, not a qualified price or profit.
Root-signed transaction bytes travel only through email, never this repository.

Claimer can catch failed individual claims: status1 can yield zero rewards while
consuming gas. minFeePerClaim does not enforce aggregate profit. The borrower
must own its reward entry, withdraw only new fees, unwrap WETH and repay.
Seed funding, old rewards, new external fees, internal interest and gas remain
separate. Team surplus is new external income minus all team gas/external costs;
internal interest is not new team income. audit-only.py is an offline packet
consistency check, not independent chain-authenticity/completeness proof.

The pilot is outside the deployed USDC-only app. It does not demonstrate
existing-contract ETH support, transitive trust, mainnet readiness or poverty
reduction. CI30 and the original three live Base Sepolia USDC communities and
recovery commitments remain.


## Full-cost quote and offline audit checks

read-only-cycle-quote.mjs uses viem2.17.0. Run after a positive probe:

BASE_READ_RPC=<approved-HTTPS-endpoint> timeout 120s node read-only-cycle-quote.mjs --probe probe.json --index <candidate-index> > cycle-quote.json

It rechecks one candidate and exact claim, rejects controlled winners, quotes five unsigned transactions including L1/operator costs, checks fresh ETH/USD dollar caps and attempts eth_simulateV1. Downstream gas reservations are conservative when stateful simulation is unsupported. Neither quote nor simulation is actual execution or authority to spend. L1 upper-bound quotations are statistical and future protocol prices can change; current quotes are doubled as reserves, not hard guarantees.

The auditor now requires lender funding gas coverage and native cash settlement for an on-chain proof. A separate fully-costed flag requires evidenced offchain costs for both actors. Eight dependency-free offline negative-control checks passed; ALL fixtures are synthetic, never chain/execution evidence. Reproduce in this directory:

python -m unittest -v test_audit_negative_controls.py


## Actual live probe and claim simulations received

Hermes completed the supplied probe,48 HTTP/RPC operations, at Base block52315382, draw841. In128 sampled historical addresses it computed 22 winning entries. Its12 checked prize candidates comprised two already claimed tier4 prizes and ten unclaimed tier6 prizes for one winner; hooks were disabled. Tier6 fee quote109312671627WETHwei; tier4 fee quote11115556537608wei.

At block52315410, exact claim simulations for one and ten prizes returned zero total fees; a single claim with quoted fee floor also returned zero. No-revert did not mean income. The six-read one/ten follow-on reported L2-only gas60269/170822 at6e6wei gas price; these are not complete cycle costs. No loan, signing or spending occurred. The correct vault-configured claimer was used.

Immutable source: https://github.com/scottonchain/microcredit-agent-testbed/tree/d61788c3ae93bb17c1370ddcb97777eaa109c283/evidence/ptv5-r6 . Codex independently downloaded all nine manifest-listed files and verified all SHA256SUMS. This proves file identity, not an independent fresh chain read. Copies are included here.

The actual zero-fee cause is not yet decoded. Codex supplied an exact read-only expiry/inner-revert diagnostic, followed by higher-fee candidate checking only if the draw remains open. Source shows isDrawFinalized can block claiming while winner/fee getters remain positive; this is a hypothesis until a live read confirms it. The completed calculation contains27 tier4 prizes,127 tier5 and434 tier6; only two tier4 were checked. No global opportunity absence is inferred. A source-grounded active keeper alternative is being checked separately. Neither venue is a qualified loan yet.


## Alternate keeper: Beefy Base harvest

Official current registry and Cowllector sources identify eight fixed active standard Aerodrome vaults and a Base harvest lens. The source review pins inventory/ABI/strategy commits and distinguishes source support from unverified deployed matches. read-only-beefy-probe.mjs resolves vault strategies and checks actual simulated WETH fee delta through the official lens, then direct EOA harvest compatibility. The lens is simulation-only and is never a proposed transaction target. read-only-harvest-cycle-quote.mjs supplies four unsigned stages: funding, direct strategy harvest, WETH unwrap and repayment, with L1/operator fees and the same dollar/native/loss ceilings. These are prepared tools, not live income or an executed loan.

Hermes has a bounded zero-spend r10 qualification assignment; result pending. Use --help for the exact pinned viem dependency and operator-approved RPC invocation. No additional provider/key/funding is required for these reads. A positive quote requires independent deployed source review and fresh exact transaction review before funding.

Harvest accounting decodes actual canonical WETH fee-transfer and withdrawal receipt logs, checks every nonce/native/WETH movement and all team gas, and rejects old assets as income. Its eight synthetic corruption checks passed; they are never live transaction evidence. Run python -m unittest -v test_audit_harvest_negative_controls.py.


## Actual expiry and eight-vault economics received

Hermes ran the exact expiry diagnostic at Base52315976,17readRPCops. Draw841 is finalized; claim-period close timestamp1788559200 was 2026-09-04 22:00Z. Direct simulated vault/pool calls both decode ClaimPeriodExpired, while the normal Claimer returns0. This explains the earlier zero fees. Every olddraw841 attempt is stopped; positive winner/fee getters are not current earning eligibility.

At Base52315990 Hermes resolved all eight official Beefy vault strategies; each matched its vault, configured BaseWETH and was unpaused. All lens harvest simulations succeeded with positive WETH delta; direct borrower harvest simulations succeeded. Best sample: aerodrome-lcap-eusd, fee2603052208659wei and estimated directgas1747490 at6000000wei/gas, L2 execution10484940000000wei. Reward is only0.248 times L2cost, before L1/funding/unwrap/repayment. All eight were negative. Mechanism works in simulation; profitable income and a loan do not. No signing, transaction or spending occurred.

Source https://github.com/scottonchain/microcredit-agent-testbed/tree/08e77d95b1a273cdae6a0cfb046ed74d70417d69/evidence/ptv5-r9-r10 . Codex downloaded all nine manifest-listed artifacts and independently verified every hash. Copies included. Artifact identity is not independently rereading the chain.

One targeted read-only follow-on is assigned to Hermes, r12 due01:30Z: rank current official Base TVL, choose16 largest positiveTVL active standard nonCLM vaults excluding eight already tested, and compare fresh actual lens fees/fullcycle costs. No repeated same-eight poll. read-only-beefy-ranked-probe.mjs enforces128RPC/180seconds, keeps partial outputs and records acquisition/source hashes/selection.

Fetch the immutable full registry from https://raw.githubusercontent.com/beefyfinance/beefy-v2/c30017071065df81a32890eb2a36c3c05c2dc604/src/config/vault/base.json as beefy-base-vaults.json; SHA2569444a807f47f72844e221854cd8b058b2f0e7995b9978fa2345df0755cdc5a62. Fetch https://api.beefy.finance/tvl as beefy-tvl.json and record UTC acquisition time. Official API schema from beefy-api commit 73aada396ffcb4e7fec1061ac8579c0f8495c5a1 is numericChainId→vaultId→numericUSDTVL; Basekey8453, cache15minutes. TVL is ranking input, not a live fee quote. Invoke the ranked script with --registry, --tvl, --tvl-observed-at and --deps; --help gives exact usage.


## Actual ranked follow-on and signature adoption

Hermes independently implemented the r12 selection/read task before the later r13 helper handoff. It did not run the published Codex ranked helper. Actual packet: commit9489654b30662a0363e39b910dcaa2032ce676f1, evidence/ptv5-r12, Base52316634,115readoperations; 16new positiveTVL standard vaults from71eligible. All16 lens/direct harvest simulations succeeded, but each reward was below L2gas alone. Best WETH-VVV 5883030541872reward/7273980000000gaswei=0.808777; no full-cycle quote or loan. Combined24vault negatives are snapshots, not global absence. Codex verified all8artifacthashes plus every reward/cost calculation and token/vault/block correspondence; no independent fresh RPC. Copies and original source scripts included. Original select.py paths are Hermes workspace paths; reproduce from the included inputs by adapting those paths, or use the separately supplied Codex helper with explicit input paths. Never relabel its outputs as the original run.

The selected USDC-AERO vault had lastHarvest00:24:43Z, fee1.4228507e12 at age0.982hours. Source analysis supports one specific mechanism/earned accrual check, not another24vault poll: actual gauge, reward period, stake share, fee configuration and harvest resets must be read before a finite reward-threshold requalification via the existing hourly continuation. Linear age projection and Cowllector default21hour recency are hypotheses, not production configuration or profit proof. Read-only unsigned getter scope (max40RPC/5min) and reasoning are in reviews/. No read execution of this new scope is claimed.

Quote helper now enforces empty actor code, cold nonce0, wallclock block freshness, stable bounded3pass pricing and declared lender target. Every intent is unsigned preview; actual canonical WETH harvest receipt determines subsequent unwrap amount and fresh per-phase signing. Prepared offline harvest signer uses source/review/funding/fresh direct WETH delta evidence and passes33synthetic rejection controls. It has not opened real keys or signed any actual transaction; unwrap/repay remain separate unsupported signing phases.

Codex and the observed Hermes01:25:14Z reply now contain the blog signature. Claude adoption remains awaiting its next necessary reply. Existing continuation/research/04Denver-sync prompts persist the rule; read-back confirmed unchanged schedules/enabled states and retained prior instructions. No new automation. See safe verification note; private message bodies/IDs and schedulerIDs excluded.


## Completed accrual and full-cycle cost checks

Actual r14 (ad0f4117bc7a2164a4099bbf2eec209bad7f70c5) fixed-block getter evidence supports gauge reward accrual near47.208AERO/hour, harvest-on-deposit enabled and caller fees near0.01% of gross rewards. The clone delegates to StrategyVelodromeGaugeV2. The original r14 analysis's unsupported21hour ceiling, ACP gate and blanket cost conclusion are retained as attributed history and corrected by the counterreview. Earlier Sourcify400 was a bad-fields query, not source absence. Original analyze.py has absolute paths, external r12 input and fresh HTTP calls; it is not an offline historical replay.

Actual r15 (c573f434ee98f2e1bf625b16b7da97ede9b6a4da), Base52317986 at02:08:39Z, ran the pinned192513a8 Codex helper unmodified:47RPC. Current lens reward2510707389920wei versus full-cycle required 11789172931592wei; borrower margin -9277465541672wei. Debt equals 12707276393564principal +236103482898fee; unused principal cancels on repayment. No funds moved, loan signed, harvest executed or external income earned. Both actor EOAs are empty-code and borrower starts at zero. Stateful four-call simulation is unsupported (RPC-38014); direct call nonreversion does not prove direct WETH receipt. Zero work cost and1e9wei margin targets measure onchain contribution only, not sustainable business income.

A384AERO threshold is a conditional precheck using old conversion calibration; ~82AERO now is inferred, not a fresh gauge-earned read in r15. Rates, residual balances, conversion and competing harvests can defeat it. Require actual earned/residual/reset reads, conservative price adjustment and a new full-cycle quote before any funding. Source responses are retained: implementation match, gauge exact_match (BaseScan labels the gauge Similar Match). Applying published Sourcify metadata/immutable transformations reconciles their runtime bytes; this is not an independent fresh compilation. Prepared exact-bound EIP1167 signer remains statically disabled without an independently reviewed source pin. Unwrap/repay signing remains unsupported. Synthetic tests use public dummy keys.

Morpho recent16Liquidate logs describe competitive historical activity, not a present eligible position/profit quote. Raw six receipt calls returned -32602 archive-token errors, not actual null receipts. This corrects the original Hermes README without rewriting its report. The concurrent Codex lane already requested a specific bounded residual-position check; no duplicate scan. Historical75/100USD research proposals remain attributed design notes, not spending permission; this lane retains its <=0.50USD native principal and other explicit quote caps.

Original primary live USDC communities remain0/3. The next staged read-only preflight is now published with exact5USDC approval simulation and full13wallet/pool/provider/source snapshot. Root rederived all13public addresses from existing private keys in memory at01:46:29Z; no key values were displayed or signatures created. Agent/helper claims of no key access are scoped to those agents/helpers, not this separate custody check. Recovery and source5redeposit commitments remain mandatory; same-day recovery is mechanics evidence, not earned-income bootstrap.

Five public append-only concurrent Codex model proposals are integrated by ID in this existing PR for Claude's scheduled review, without replacing existing records. Canonical main integration and review remain pending. Signature verification now records four unchanged email-producing tasks, multiple actual Hermes footers and Claude's observed missing footer/corrective notice. Private inbox/automation IDs, secrets and signed bytes excluded. ROOT_FETCH_MANIFEST files are root-computed Git-object hashes, not peer SHA256SUMS manifests.
