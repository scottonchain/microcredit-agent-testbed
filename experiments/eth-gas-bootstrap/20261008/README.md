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
