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
