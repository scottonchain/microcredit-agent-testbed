# Direction D7: self-service Omnequa borrower app with an embedded smart wallet

Claude Code (AI), 2026-11-01. **Status: GO for gates 1 to 3 only, zero money, with three changes applied below (steward session disposition by cross-session message, 2026-11-01 18:25 UTC; to be mirrored on board 15 by the steward). Gates 4 to 6 remain unreviewed and unauthorised.** Not a decision, a mandate, a deployment, a solicitation or financial authority. Written at the operator's direction on November 1 (chat session; the operator's words are summarised, not quoted as a receipt) to record the direction in a reviewable form so that it can become a roadmap if it passes review, alongside other directions in [DIRECTIONS.md](../DIRECTIONS.md). Base inspected: testbed `main` d858448 (model 0.1.195). Checkable arithmetic: `experiments/self-service-borrower-app/steady_state.py` and, from November 2, `pool_stability.py` (proven ruin bound, screening, two tiers).

## What the operator proposed

1. Put about 100 USDC into the contract and advertise that Omnequa makes loans.
2. An agent assesses creditworthiness and assigns a reputation score in the contract; borrowers borrow against it, repay, and their reputation rises; borrowers can stake reputation on others.
3. A web-based Omnequa app that lets a borrower borrow USDC and send it, with an embedded smart wallet or an external wallet, so that anyone with the app can use it autonomously.
4. The concept is proven when the 100 USDC grows instead of shrinks; the numbers may be adjusted so that defaults do not wipe out the interest; the system must be self-sustaining (growing) in steady state. More capital follows proof.

**Change C2 (steward, 2026-11-01).** No public advertisement and no borrower invitation of any kind before gates 4 and 5 (lender of record, mainnet readiness) have passed. Gate 3 uses named people reached through existing relationships, not an advertisement.

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

## Design proof (change C1a), computed 2026-11-01

`steady_state.py --design-proof`: 20 USDC loans, 2 cent per-loan cost, 100 USDC reserve, one-fifth exposure cap, 2,000 seeded runs of 500 loans. Ruin is below 1% for every candidate because the cap shrinks loans with the reserve, so the discriminating number is expected net per loan and the median final reserve.

| Design | 3% default | 5% | 10% | Passes band |
| --- | --- | --- | --- | --- |
| Live 9.33%, 30 days, full loss to pool | net -0.47, median 23 | -0.87, 23 | -1.88, 22 | no |
| Live 9.33%, 90 days, full loss to pool | -0.17, 28 | -0.58, 23 | -1.61, 23 | no |
| Live 9.33%, 90 days, stakers cover 80% of loss | +0.31, 253 | +0.22, 209 | -0.006, 95 | no (marginal at 10%) |
| 18.33% (the 10%-default calibration row), 90 days, stakers cover 80% | +0.74, 468 | +0.64, 419 | +0.39, 297 | yes |
| Live 9.33%, 90 days, stakers cover 100% | +0.43, 313 | +0.42, 309 | +0.39, 297 | yes |

Reading: at the live price with losses falling on the pool, no term in the band grows. The pool grows across the whole band only when stakers absorb most or all of each loss, which is the contract's existing structure (secured backing slashed first). That moves the question to the stakers: at 10% default a staker covering 80% of 20 USDC loans loses 1.60 USDC per loan on average and must be paid for it, so the design proof for the whole system (pool + stakes) still requires either the known-borrower default band (3% or below) or a priced backer share of interest (Design Question 2). The 18.33% row prices the pool for 10% default but at nearly twice the live rate.

## What the app would be

- **Web app, no install, no key file.** A passkey-backed smart account (ERC-4337 account or EIP-7702 delegated EOA) created in the browser; the team never holds a key. Gas paid in USDC through Circle Paymaster; the first transaction of a fresh account funded by the relayer (a subsidy to count in `c`). External wallet connection remains as the second path.
- **Three actions.** Borrow (against own stake, dues or backing, or an officer line), send (an ordinary USDC transfer, which the loan does not restrict), repay (permit-based pull). Stake and back for those who vouch for others.
- **One person, one line.** Enforced off-chain by a partner's KYC in a partner pilot, or behind a proof-of-personhood interface in any permissionless phase (claim text in the human plan). Without one of these, free identities farm every unsecured line.
- **Officer.** Deterministic policy code sets limits from recorded evidence; the agent extracts evidence and flags contradictions; it never invents a 0 to 100 trust number ([MANDATORY_CREDIT_OFFICER_COMPARISON.md](../../docs/MANDATORY_CREDIT_OFFICER_COMPARISON.md)). Cost per assessment is a measured input to `c`.
- **Cash-out.** Spendable means a usable payout. A USDC balance a borrower cannot convert is not a loan outcome; the ramp and its fees are part of every report (claim `cash-out-rail-required`).

## Gates this direction must pass, in order

1. **Review** of this document by a non-author (the steward session or Codex): GO to a roadmap, CHANGE, or PARK with a re-entry trigger.
2. **Technical demonstration on testnet, zero money at risk** (steward condition: no funded key held by a session; a fork rehearsal and the preinstalled browser's WebAuthn virtual authenticator first, then a run with a key held by an independent operator): a non-technical tester with no wallet borrows 5 test USDC through a passkey smart account, sends it to another address, repays, with gas paid in test USDC; every transaction hash recorded; paymaster testnet availability measured or a test paymaster substituted. This is the technical-channel evidence and needs no new authority.
3. **People before money:** five named prospective borrowers and five people willing to stake their own 5 to 20 USDC on them, with the stated purpose of each loan. If no one will stake on a borrower, no agent score should either, and the direction parks here.
4. **Legal:** counsel names the lender of record and the rules for the borrowers' jurisdiction (claim `lender-of-record-required`); consumer disclosure in plain words before acceptance.
5. **Mainnet readiness** as already recorded in `action:mainnet-readiness`: audit and bounty of the fixed source, a deployed fixed pool, a funded reserve, a measured cash-out round trip.
6. **Funding-ready packet** per the operator's definition (board 15, 6561215518): consenting accountable borrowers, the cash gap each loan fills, exact principal, rate, term and repayment route, full costs and downside, plausible human earnings, retained pool surplus, and NO_LOAN compared on the same cases. The operator's funding decision is separate from this packet.

## Pre-registered first pilot, if every gate passes

| Field | Value |
| --- | --- |
| Reserve | 100 USDC sponsor capital, recorded as `sponsorCapital`, separate from stakes |
| Loan cap | 10 USDC first loan, 20 USDC after one on-time repayment (a fifth of the reserve); one open loan per person; lending pauses while the reserve is below 25 USDC (revised November 2, see the stability section) |
| Backing | First loans backed by a named person's own stake covering the whole principal, or the borrower's own locked deposit; repeat loans fully backed in open access, at least half backed in a named cohort (revised November 2) |
| Term and price | 90 days at the live rate (revised November 2: no 30-day design grows the whole system at the live rate); any premium stated and disclosed in local currency before acceptance |
| N | 20 loans |
| Success criterion (change C1) | Two parts, neither alone suffices. (a) **Design proof:** parameters (term, price, cap, backing share, screen, per-loan cost) at which expected net per loan is positive at every point of the 3% to 10% default band and the proven ruin bound (stability section, `pool_stability.py`) is below 1%, checked against a 2,000-run seeded simulation. (b) **Pilot statistic:** observed default count, per-loan cost and loss given default over the 20 loans with exact binomial bounds, reported beside pool + stakes + reserve (change C3: stakers' losses always counted with the pool). A balance comparison alone is underpowered and is not the test. |
| Human test | For each loan, the purchase or activity it made possible and the earnings reported, with a NO_LOAN comparison |
| Stop | Two defaults in the first 20 (power table in the stability section); any consumer-protection failure; any zero-purpose loan; per-loan cost measured above 15 cents |

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

### Gate 2, third pass (2026-11-01, after the steward's GO): zero-key prerequisites

- **Headless passkey works.** `demo/passkey_probe.cjs` with the preinstalled Chromium and Playwright: the WebAuthn virtual authenticator (CTAP2, internal transport, resident key, user verification) created a P-256 credential (COSE alg -7, 32-byte id, 91-byte SPKI public key) and signed a challenge (70-byte DER signature, 37-byte authenticator data) on a page served from localhost. This is the "no wallet software, no key file" primitive; the remaining work is an ERC-4337 account that validates that signature, or Circle Modular Wallets, which needs a Console client key and passkey domain.
- **Fork rehearsal tooling.** The Foundry release download was refused by this session's auto-mode classifier (external binary); `hardhat` 3.21.2 is installable from npm and can fork `sepolia.base.org`, so the fork rehearsal uses it or waits for an environment with Foundry. Not run yet.
- **Keyless bundler** `public.pimlico.io` is still denied by network policy; `api.pimlico.io` answers but needs an API key. Either unblocks the live path once an independent operator holds the key.

## Pool stability assurance and first-borrower screening (November 2, operator request)

Operator request of November 2: give mathematical assurance of pool stability, adjust the numbers, algorithms and assumptions so the pool grows, and let an agent filter first-time borrowers to establish trust. Checkable arithmetic: `experiments/self-service-borrower-app/pool_stability.py` (`--recommended`, `--search`, `--stop-rule`), with tests.

- **Measurable human outcome or decision:** whether the pilot's reserve rule and screening rule can be pre-registered with a stated, proven failure probability, so the operator's seed decision rests on a bound and a count, not on a hope.
- **Evidence sought:** (a) a proven upper bound on the chance the reserve ever falls to the pause level; (b) the admitted first-loan default rate and admission rate the screen actually produces, measured in the pilot; (c) the backers' realised loss per loan, counted with the pool (change C3).
- **Competing simpler route:** direct cash to the same people; a partner lending inside an existing group (D8); an employer wage advance (D10). None needs a reserve bound because none revolves. The revolving guarantee (NORTH_STAR.md) is the sibling mechanism: same exposure rule, same two scorecards; its channel remains unqualified.
- **Stop or change condition:** the pilot's binomial interval on observed defaults lies above the filter's 11% ceiling; the pilot's admitted default count exceeds the stop rule below; a measured per-loan cost above 15 cents; a backer unwilling to stake at the required share; or any evidence that screening excludes the people the project exists for faster than it excludes defaulters.

### 1. The assurance: a proven ruin bound, not a simulation

With the exposure rule (no loan above a fifth of the reserve) and lending paused when the reserve falls below a pause level, the reserve after each loan is `R(1 + lambda X')` where `lambda` is in (0, 1] and `X'` is the relative change that a loan of exactly a fifth of the reserve would cause, with the per-loan cost charged at its worst case (the smallest loan the rule ever makes). If `theta > 0` solves `E[(1 + X')^-theta] = 1` (the Lundberg equation), then `R^-theta` is a supermartingale, because `(1 + lambda x)^-theta` is convex in `lambda` and equals 1 at `lambda = 0`, and optional stopping gives

`P(reserve ever falls below pause) <= (pause / R0)^theta`.

Such a `theta` exists exactly when `E[log(1 + X')] > 0`, which is also the condition for the reserve to grow almost surely (strong law), not merely in expectation. The bound is conservative on purpose. The module checks it against long seeded simulations where the bound is strictly between 0 and 1:

| Design (90 days, screened first loans) | Raw first-loan default | `theta` | Proven bound | Simulated (4,000 runs of 3,000 loans) |
| --- | --- | --- | --- | --- |
| 18.33%, no backing | 10% | 3.87 | 0.47% | 0.00% |
| 9.33%, no backing | 5% | 2.04 | 5.9% | 0.08% |
| 18.33%, first 50% backed, repeat 25% | 20% | 1.34 | 15.7% | 0.30% |

Reserve 100 USDC, pause 25 USDC (loans at the cap are then 5 USDC, the smallest useful loan), exposure a fifth. With an unbacked 30-day loan at the live rate the drift is negative at every rate in the band and no `theta` exists: there is no assurance to give, which is the honest reading of PR 400's finding.

### 2. The screen: an agent filters first-time borrowers

An applicant population with raw per-loan default `d0` is filtered with sensitivity `s` (share of would-be defaulters rejected) and false-rejection rate `f` (share of good applicants rejected). Admitted default is `d1 = d0(1 - s) / (d0(1 - s) + (1 - d0)(1 - f))`; the admission rate is the denominator; screening cost per funded first loan is cost per applicant over the admission rate. Two labelled screens are modelled: evidence review alone (60% / 20%, 5 cents) and evidence review plus a named backer's own record in the pool (80% / 30%, 10 cents). At a raw 10% the stronger screen admits 65% of applicants at an admitted default of 3.1%, for about 15 cents per funded first loan.

What the agent does, and does not do (the existing officer rule in [MANDATORY_CREDIT_OFFICER_COMPARISON.md](../../docs/MANDATORY_CREDIT_OFFICER_COMPARISON.md) stands):

1. **One person, one line.** Named people through existing relationships in the pilot (change C2); partner KYC or proof of personhood in any open phase. Without it, the screen filters honest risk only.
2. **A named backer's stake covers the whole first loan**, or the borrower's own locked deposit does (a credit-builder loan). No backer and no deposit: decline. This is the only defence that works against free identities, because a filter has no power against an attacker who creates identities until one passes ([ring attacks](../../research/ring-attacks-on-agent-trust-systems.md)); the stake makes the pool indifferent to who the borrower is.
3. **Evidence review, deterministic cap.** The agent extracts recorded evidence (stated purpose, stated repayment source, the backer's record in the pool, contradictions between statements) and policy code sets the first cap, at most 10 USDC, from it. The agent never emits a trust number and never issues a line.
4. **Graduation.** After one on-time repayment the cap rises to 20 USDC. In the open-access design repeat loans stay fully backed. In a named cohort, where identities are not free, repeat loans may be half backed: a two-identity ring would otherwise repay one 10 USDC first loan, borrow 20 against a 10 USDC stake and keep 10 by defaulting.
5. **The filter's ceiling (operator design constraint, November 2).** The agent filter is built and measured so that the raw per-loan default of the population it admits is at most 11% (`FILTER_DEFAULT_CEILING` in the module). That is exactly the band in which pool and system both grow at the live rate in the open-access design: at a raw 11% the screen admits about 64% of applicants at an admitted first-loan default of 3.4%, the proven ruin bound is below one in a hundred thousand in both designs (zero to the sixth decimal in open access, five in a million in the named cohort), and pool plus stakes gain about 0.01 USDC per loan. One point above it the system stops growing while the pool still does, because the loss has moved to the backers. The ceiling is an assumption until the pilot's exact binomial interval on observed defaults is inside it; a measured rate above it is a CHANGE trigger (raise backing, raise the price with disclosure, or tighten the screen), not a reason to keep lending.
6. **Measuring `s` and `f`.** The pilot observes the admitted default rate and the admission rate directly. Separating `s` from `f` needs a randomised holdout: a seeded random slice of rejected applicants admitted with full backing, whose outcomes are reported apart. Without it the screen's accuracy stays an assumption.

### 3. The numbers that grow, and what they cost

Two tiers: first loans (cap 10 USDC, screened) and repeat loans (cap 20 USDC, default assumed half the admitted first-loan rate, four repeat loans per surviving borrower, so about a fifth of loans are first loans). Per-loan cost 2 cents plus screening. Reserve 100, pause 25, 500 loans, 2,000 seeded runs. The pool scorecard counts the pool alone; the system scorecard counts pool plus backers' stakes (change C3).

**Open access (anyone with the app): 90 days, live 9.33%, both tiers fully backed, screened first loans.**

| Raw first-loan default | Admitted | Pool net per loan | System net per loan | Proven ruin bound | Median reserve after 500 loans | Median pool + stakes |
| --- | --- | --- | --- | --- | --- | --- |
| 3% | 0.9% | +0.36 | +0.27 | below 1e-6 | 281 | 242 |
| 5% | 1.5% | +0.36 | +0.21 | below 1e-6 | 280 | 210 |
| 10% | 3.1% | +0.35 | +0.05 | below 1e-6 | 277 | 127 |
| 20% | 6.7% | +0.34 | -0.33 | below 1e-6 | 271 | -58 |

The pool grows at every raw default rate up to 50%, trivially: it never loses principal, only the per-loan cost, and interest covers that. The pool is a senior lender; the backers carry the credit risk. The system grows up to a raw 11%, which with the screen means an admitted first-loan default of about 3.4%. Above that the backers lose more than the interest earns, and the pool's growth is their loss moved, not wealth created.

**Named cohort (one line per person): same, repeat loans half backed.** Doubles the loans a backer's dollar can support. Pool grows with a proven bound below 1e-6 up to a raw 14%; system up to 11%. At a raw 20% the pool's drift turns negative and the bound is void (the simulation shows 0.05% ruin in 500 loans, which is not assurance, only too short a horizon).

**What moved from PR 400, and why:** the term, from 30 to 90 days (interest scales with days, a per-loan default does not: at the live rate no 30-day design grows the whole system anywhere in the band); the first loan, capped at 10 USDC and fully backed; a screen on first-time applicants; a pause level at a quarter of the seed. The price stays at the live rate. The 18.33% row (the 10%-default calibration row) would extend the system band to a raw 21%, at the cost of the human-benefit scorecard the project exists to beat. Paying backers a share of interest (Design Question 2) is priced too: at a 25% share the pool still passes to a raw 8%, at 50% only to 2%, so at the live rate the pool cannot afford to pay the backers; their compensation is the relationship, which is what social collateral means, and the pilot records their realised loss (about 0.31 USDC per 10 USDC first loan at a raw 10%, zero when the backer knows the borrower well enough that the admitted rate is near 1%).

**Growth is slow.** At a raw 10%, half utilisation and 90-day terms, the open-access design turns about 11 loans a year on a 100 USDC reserve: about 4 USDC a year, 4%. Full utilisation doubles it. More capital does not change the rate, only the amount.

### 4. The pilot stop rule has little power at 20 loans

`--stop-rule`: the pre-registered rule, two defaults in the first 20 loans, fires with probability 1.7% at a true 1% per-loan default, 12% at 3%, 26% at 5%, 61% at 10% and 93% at 20%. It catches the unsecured-stranger band and mostly misses the partner band, which is acceptable only because the first loans are fully backed: a default there costs the backer, not the pool. The pilot statistic therefore reports the exact binomial interval on the admitted default count and the backers' realised loss, as change C1 requires, and does not read two defaults in 20 as proof of a 10% population.

### 5. Assumptions that are not measurements

Screen sensitivity and false-rejection rates; the repeat-loan default ratio (one half); four repeat loans per surviving borrower; 2 cents per loan; applicants' raw default band from `claim:first-loan-default-benchmarks`. Each is labelled in the module and replaced by a pilot measurement when one exists. Nothing here is demand, a borrower, a backer or human benefit.

## Proposed checkpoints (owner estimates, not accepted SLAs)

- **2026-11-03 18:00 UTC:** review disposition (GO, CHANGE, PARK) recorded on board 15 next to the issue 396 matrix, so the two technical-channel candidates are compared at once.
- **2026-11-08 18:00 UTC:** if GO, the testnet smart-wallet demonstration result (gate 2) and whether five borrowers and five backers exist (gate 3).
- **After both:** the legal and mainnet gates are the operator's spending and authority decisions and have no date here.

## What this document does not claim

No borrower, backer, partner, jurisdiction or buyer is identified. No demand is established; the November 1 stop found no case where credit rather than prepayment was the binding constraint for agents, and no human case has been qualified. No pool growth, human earnings or poverty reduction is claimed. Internal agreement is not demand; a repaid testnet loan is not human benefit.
