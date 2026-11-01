# Direction D7: self-service Omnequa borrower app with an embedded smart wallet

Claude Code (AI), 2026-11-01. **Status: PROPOSED, awaiting non-author review.** Not a decision, a mandate, a deployment, a solicitation or financial authority. Written at the operator's direction on November 1 (chat session; the operator's words are summarised, not quoted as a receipt) to record the direction in a reviewable form so that it can become a roadmap if it passes review, alongside other directions in [DIRECTIONS.md](../DIRECTIONS.md). Base inspected: testbed `main` d858448 (model 0.1.195). Checkable arithmetic: `experiments/self-service-borrower-app/steady_state.py`.

## What the operator proposed

1. Put about 100 USDC into the contract and advertise that Omnequa makes loans.
2. An agent assesses creditworthiness and assigns a reputation score in the contract; borrowers borrow against it, repay, and their reputation rises; borrowers can stake reputation on others.
3. A web-based Omnequa app that lets a borrower borrow USDC and send it, with an embedded smart wallet or an external wallet, so that anyone with the app can use it autonomously.
4. The concept is proven when the 100 USDC grows instead of shrinks; the numbers may be adjusted so that defaults do not wipe out the interest; the system must be self-sustaining (growing) in steady state. More capital follows proof.

## Outcome lane and the four questions

- **Outcome lane:** "a real lending scenario ready for funding" (operator's four outcomes, board 15 receipt [6561215518](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6561215518)). The smart-wallet half is also a candidate for "a new technical channel", because it can be exercised on testnet without money or a licence.
- **Measurable human outcome:** incremental spendable earnings caused by a loan, per sponsor dollar lost, under the canonical multiplier `M = B / sponsor money consumed` (NORTH_STAR.md). Pool growth is the reserve scorecard, necessary and not sufficient.
- **Cheapest evidence:** (a) the break-even arithmetic below, already done; (b) a testnet demonstration that a person with no wallet, no ETH and no key file can borrow, send and repay through a passkey smart wallet with gas paid in USDC; (c) five named people and the five people who would stake their own money on them.
- **Simpler competitors:** direct cash to the same people (about 87 cents to a dollar reaches them, with certainty); a licensed partner lending inside an existing group with the pool as ledger ([HUMAN_BORROWING_BOOTSTRAP_PLAN.md](../../docs/HUMAN_BORROWING_BOOTSTRAP_PLAN.md)); an employer-deducted wage advance; NO_LOAN.
- **Stop or change condition:** two defaults in the first 20 loans; nobody willing to stake on a borrower; counsel finds no lender of record; the break-even price exceeds what the borrower population can bear without harm; or the smart-wallet demonstration cannot be made to work for a non-technical user.

## What already exists

The deployed Base Sepolia pool already implements every mechanism in points 1 and 2. `stake` locks USDC as one's own credit; `back` commits it to another account (the operator's "stake reputation on others"); interest paid earns dues; an issuer line from the score reporter is the "agent assigns a reputation score" step (ONBOARDING.md; contract `CREDIT_MODEL.md`). Credit is conserved: backing moves credit and never creates it, proved and fuzzed in the contract repository. The only place credit is created from nothing is the agent-assigned line. Research in this repository ([ring attacks](../../research/ring-attacks-on-agent-trust-systems.md)) shows that every system that gave new identities trust from a neutral prior was broken by rings of free identities. A publicly advertised real-money pool with agent-assigned unsecured lines is that system.

The live deployment (`deployments/current.json`, source 1812e7d) is testnet and still carries the CI-30 sub-cent forgiveness defect; the fix is on contract `main` (claim `ci30-fixed-20261008`) and PR45 is merged, but no fixed pool is deployed anywhere. A Next.js client exists (release one, wallet-direct, GitHub Pages); a relayed gasless release two is proposed and unbuilt (claims `sepolia-release-two-custody`, `relayer-memory-measured-20261007`). Circle Paymaster lets an ERC-4337 account or EIP-7702 EOA pay gas in USDC on Base for 10% of the gas fee (claim `paymaster-meets-gas-need`); its testnet availability is unverified by this team.

## Steady-state arithmetic: can the numbers be adjusted so the pool grows?

Yes, in three ways, and each has a cost that lands somewhere. Per loan of principal `P` for `T` days at annual rate `a`, with per-loan default `d`, loss given default `L` and per-loan cost `c`, expected net is `(1 - d)·P·a·T/365 - d·L·P - c`. Break-even annual rate:

`a* = (d·L·P + c) / ((1 - d)·P·T/365)`

Break-even rate for a 25 USDC loan, zero cost (`steady_state.py --table`):

| Per-loan default | Term | Full loss (`L` = 1) | 80% recovered from stake (`L` = 0.2) |
| --- | --- | --- | --- |
| 0.77% | 30 d | 9.4% (the live rate) | 1.9% |
| 1% | 30 d | 12.3% | 2.5% |
| 3% (partner and backer channel, low end) | 30 d | 37.6% | 7.5% |
| 5% | 30 d | 64.0% | 12.8% |
| 10% (unsecured digital first loans, low end) | 30 d | 135% | 27.0% |
| 20% (unsecured digital first loans, high end) | 30 d | 304% | 60.8% |
| 3% | 90 d | 12.5% | 2.5% |
| 10% | 90 d | 45.1% | 9.0% |

Per-loan cost matters as much as default: at 1% default and 30 days, a 2 cent cost adds one point to the break-even rate, 10 cents adds five points, and a 50 cent assessment adds about 25 points. An agent credit officer that spends 50 cents of inference per 25 USDC loan cannot be priced into a small loan.

The three levers, and where the cost lands:

1. **Raise the price.** At the unsecured digital benchmark (10% to 20% first-loan default, claim `first-loan-default-benchmarks`) the pool grows only at 135% to 304% a year. That is the digital-lender price band (90% to 219%, claim `human-price-gap`), which this project exists to undercut, and which the evidence links to higher default (Zidisha, CGAP). Growth bought this way fails the human-benefit scorecard.
2. **Lower loss given default with stake.** If backers' stake absorbs 80% of a loss, the pool grows at 27% even at 10% default. The loss has not gone away; it has moved to the backers, who then need to be paid for bearing it. Whether backers earn a share of interest is Design Question 2, still open. Done honestly this makes the pool a senior lender and backers junior risk-takers, which is the contract's structure already. The growth test must then count pool plus stakes together, or the stakers' losses hide behind a growing pool.
3. **Lower the default rate by choosing who borrows.** The only lever that does not move the cost onto the borrower or the backer. The evidence says default falls when someone who knows the borrower stands behind the loan (claim `intermediary-and-ties-cut-default`: partner channels 94% to 97% repayment, stranger-backed 18% write-off). A public advertisement selects the opposite population: wallet-capable strangers for whom a below-market unsecured loan is an arbitrage.

Longer terms help the ratio (interest scales with days, a per-borrower default does not), which is why the human plan uses 30 to 90 days.

**Finite pool.** Expected-value neutrality is not solvency. At 5% default priced exactly to break even, fixed 25 USDC loans from 100 USDC end the pool in 53% of seeded 500-loan runs; with the NORTH_STAR exposure rule (no loan above a fifth of the reserve) the same pool is never exhausted in 2,000 runs and its median ends at 58, so the rule trades ruin for shrinkage. A design that grows: 20 USDC loans, 0.5% per-loan default, 2 cent cost, live rate, half utilisation gives about 1% growth a year, median 113 after 100 loans, 10th percentile 74. **Growth at the live price is detectable only over a year or more, and one default of 20 USDC sets it back two to four years.** The pre-registered test therefore has to be a count of defaults in N loans, not a balance comparison.

## What the app would be

- **Web app, no install, no key file.** A passkey-backed smart account (ERC-4337 account or EIP-7702 delegated EOA) created in the browser; the team never holds a key. Gas paid in USDC through Circle Paymaster; the first transaction of a fresh account funded by the relayer (a subsidy to count in `c`). External wallet connection remains as the second path.
- **Three actions.** Borrow (against own stake, dues or backing, or an officer line), send (an ordinary USDC transfer, which the loan does not restrict), repay (permit-based pull). Stake and back for those who vouch for others.
- **One person, one line.** Enforced off-chain by a partner's KYC in a partner pilot, or behind a proof-of-personhood interface in any permissionless phase (claim text in the human plan). Without one of these, free identities farm every unsecured line.
- **Officer.** Deterministic policy code sets limits from recorded evidence; the agent extracts evidence and flags contradictions; it never invents a 0 to 100 trust number ([MANDATORY_CREDIT_OFFICER_COMPARISON.md](../../docs/MANDATORY_CREDIT_OFFICER_COMPARISON.md)). Cost per assessment is a measured input to `c`.
- **Cash-out.** Spendable means a usable payout. A USDC balance a borrower cannot convert is not a loan outcome; the ramp and its fees are part of every report (claim `cash-out-rail-required`).

## Gates this direction must pass, in order

1. **Review** of this document by a non-author (the steward session or Codex): GO to a roadmap, CHANGE, or PARK with a re-entry trigger.
2. **Technical demonstration on testnet, zero money at risk:** a non-technical tester with no wallet borrows 5 test USDC through a passkey smart account, sends it to another address, repays, with gas paid in test USDC; every transaction hash recorded; paymaster testnet availability measured or a test paymaster substituted. This is the technical-channel evidence and needs no new authority.
3. **People before money:** five named prospective borrowers and five people willing to stake their own 5 to 20 USDC on them, with the stated purpose of each loan. If no one will stake on a borrower, no agent score should either, and the direction parks here.
4. **Legal:** counsel names the lender of record and the rules for the borrowers' jurisdiction (claim `lender-of-record-required`); consumer disclosure in plain words before acceptance.
5. **Mainnet readiness** as already recorded in `action:mainnet-readiness`: audit and bounty of the fixed source, a deployed fixed pool, a funded reserve, a measured cash-out round trip.
6. **Funding-ready packet** per the operator's definition (board 15, 6561215518): consenting accountable borrowers, the cash gap each loan fills, exact principal, rate, term and repayment route, full costs and downside, plausible human earnings, retained pool surplus, and NO_LOAN compared on the same cases. The operator's funding decision is separate from this packet.

## Pre-registered first pilot, if every gate passes

| Field | Value |
| --- | --- |
| Reserve | 100 USDC sponsor capital, recorded as `sponsorCapital`, separate from stakes |
| Loan cap | 20 USDC (a fifth of the reserve); one open loan per person; no new loan while reserve < 2 × cap |
| Backing | Each loan backed by a named person's own stake of at least 25% of principal |
| Term and price | 30 to 90 days; live rate unless the break-even table and measured `c` require a stated premium, disclosed in local currency before acceptance |
| N | 20 loans |
| Growth test | Pool + stakes + reserve at the end of 20 loans, against the start, with `c` itemised |
| Human test | For each loan, the purchase or activity it made possible and the earnings reported, with a NO_LOAN comparison |
| Stop | Two defaults in the first 20; any consumer-protection failure; any zero-purpose loan |

## Contingencies (three options at every block, per the November 1 lateral rule)

| Block | Another route to the outcome | Remove or reverse the requirement | Change payer, deliverable, channel or asset |
| --- | --- | --- | --- |
| No lender of record available | Licensed partner lends from its balance sheet; pool is ledger and liquidity (D8) | Savings-group ledger: the group's own money, no sponsor lending at all (D9) | Employer-deducted wage advance, where the employer is the payer and collector (D10) |
| No one will stake on a borrower | Park D7; test credible first-job references instead of money (D11) | Drop unsecured lending; stake-only pool, growth test on backers' returns | Direct cash comparator on the same people (D14), which needs no vouching |
| Paymaster unavailable on testnet | Relayer pays the first transaction; measure the subsidy | EOA with faucet ETH for the demonstration only, labelled | Test paymaster or another sponsor route; record cost |
| Defaults above budget in the first 20 | Publish the NO_LOAN finding with the measured `d` | Shorter terms or smaller caps only if the purpose evidence supports it | Shift to partner channel with group liability |

## Gate 2 feasibility probe, 2026-11-01 (executed, read-only)

From this session's cloud container: `https://sepolia.base.org` answers `eth_chainId` 0x14a34 and returns the pool's code (48,792 hex characters at `0x73872B8f...`). Denied by the environment's network policy (proxy 403 or no resolution): `api.pimlico.io`, `public.stackup.sh`, `bundler.candide.dev`, `api.candide.dev`, `base-sepolia-rpc.publicnode.com`, `developers.circle.com`. Foundry (`cast`, `forge`) is not installed here; Node 22 is. No funded testnet key is held by this session, by design.

Consequences, with the three options the lateral rule requires:

| Blocked prerequisite | Another route | Remove the requirement | Change channel |
| --- | --- | --- | --- |
| External ERC-4337 bundler | Hermes runs the demonstration from its host with its existing throwaway testnet key (bounded board assignment, no new key) | The team relayer calls `EntryPoint.handleOps` itself; any EOA may bundle, so no third-party bundler is needed | Operator allows one bundler host in the environment's network settings |
| Circle Paymaster testnet address and terms (docs unreachable) | Read the address from the contract repository's pinned research (`ev:circle-paymaster-usdc-gas`) if recorded there | The relayer pays gas for the demonstration and the subsidy is itemised; USDC-paid gas is measured in a later step | Operator allows `developers.circle.com` |
| Funded testnet account | Existing Hermes wallet, under its custody rules | Fork rehearsal first (the repository's fork runner), labelled as not live | Circle faucet to a fresh throwaway key held by whoever runs the demonstration, never committed |

A passkey can be exercised headlessly with the preinstalled Playwright browser through the WebAuthn virtual authenticator, so the "no wallet, no key file" claim is testable without a person present; a person is still needed for the usability half.

### Gate 2 probe, second pass (2026-11-01, after the operator allowed `developers.circle.com` and `api.pimlico.io`)

Verified from Circle's documentation (fetched through the session proxy, HTTP 200, pages `paymaster` and `paymaster/addresses-and-events`) and the Base Sepolia RPC:

| Item | Finding | Check |
| --- | --- | --- |
| Circle Paymaster on Base Sepolia, EntryPoint v0.7 | `0x31BE08D380A21fc740883c0BC434FcFc88740b58` | 144 bytes of code at that address (proxy) |
| Circle Paymaster on Base Sepolia, EntryPoint v0.8 | `0x3BA9A96eE3eFf3A69E2B18886AcF52027EFF8966` | 141 bytes of code |
| EntryPoint v0.7 `0x0000000071727De22E5E9d8BAf0edAc6f37da032` | present | 16,035 bytes |
| EntryPoint v0.8 `0x4337084D9E255Ff0702461CF8895CE9E3b5Ff108` | present | 21,738 bytes |
| Fee | 10% surcharge on gas, Arbitrum and Base and their testnets; USDC only | Circle overview page |
| Account types | ERC-4337 v0.7 and v0.8 accounts; EIP-7702 EOA through the v0.8 quickstart (`toSimple7702SmartAccount`); Circle Modular Wallets add passkeys (WebAuthn) but need a Circle Console client key and a registered passkey domain | Circle quickstart and the `circlefin/skills` modular-wallets skill |
| Bundler in Circle's quickstart | `https://public.pimlico.io/v2/<chainId>/rpc`, no API key | quickstart code |
| Reachability from this container | `api.pimlico.io` answers but requires an `apikey` query parameter; `public.pimlico.io` still denied (proxy 403) | curl, 2026-11-01 18:2x UTC |

So the demonstration is buildable with viem's account-abstraction module, the v0.8 paymaster and either the keyless public Pimlico endpoint (needs `public.pimlico.io` allowed) or the relayer calling `EntryPoint.handleOps` directly. The passkey half has two routes: Circle Modular Wallets (a Console key and domain, no payment for testnet) or a plain WebAuthn P-256 signer validated by an ERC-4337 account that supports it. A funded throwaway testnet key remains the one input this session does not hold.

## Proposed checkpoints (owner estimates, not accepted SLAs)

- **2026-11-03 18:00 UTC:** review disposition (GO, CHANGE, PARK) recorded on board 15 next to the issue 396 matrix, so the two technical-channel candidates are compared at once.
- **2026-11-08 18:00 UTC:** if GO, the testnet smart-wallet demonstration result (gate 2) and whether five borrowers and five backers exist (gate 3).
- **After both:** the legal and mainnet gates are the operator's spending and authority decisions and have no date here.

## What this document does not claim

No borrower, backer, partner, jurisdiction or buyer is identified. No demand is established; the November 1 stop found no case where credit rather than prepayment was the binding constraint for agents, and no human case has been qualified. No pool growth, human earnings or poverty reduction is claimed. Internal agreement is not demand; a repaid testnet loan is not human benefit.
