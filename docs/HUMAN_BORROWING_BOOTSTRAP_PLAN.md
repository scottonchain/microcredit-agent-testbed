# From today's contract to people borrowing: a sourced plan

Claude Code (AI agent), 2026-10-08. Written at the operator's direction: "We need concrete steps to deploying and bootstrapping. It must result in human level borrowing after bootstrap." It builds on the Codex lane's bootstrap-reality packet (`evidence/bootstrap-reality-001/`, e9e10c0) and transitive-trust design note (`docs/TRANSITIVE_TRUST_TARGET.md`, a2dfa16), and on the contract's deployment runbook (`docs/DEPLOYMENT.md` in the contract repository). Every figure below is from a named source or from arithmetic that is labelled as such. Nothing here is a decision; the decisions it needs are listed at the end.

## 1. What "human-level borrowing" means in numbers

The people the project is for borrow small amounts, often, at high prices:

- Kenya's digital lenders made about 270 million loans worth KSh 1,512 billion over 2019 to 2023, to about 10 million unique borrowers a year ([FSD Kenya, CIS Kenya and Creditinfo, 2024](https://www.fsdkenya.org/blogs-publications/fsd-kenya-cis-kenya-and-creditinfo-crb-launch-the-findings-of-a-study-on-kenyas-credit-market-landscape/)). Arithmetic on those rounded totals gives an average digital loan of about KSh 5,600.
- Safaricom's Fuliza overdraft averaged KSh 217.90 per draw in the year to March 2026 ([Nation](https://nation.africa/kenya/business/kenyans-fuliza-record-sh1-4-trillion-loans-for-food-rent-and-fees-5452126)); M-Shwari's facility fee is 7.5% a month, about 90% a year, and its floor was raised to KSh 2,000 to cut defaults ([Business Daily](https://www.businessdailyafrica.com/bd/markets/capital-markets/m-shwari-shifts-loans-of-below-sh2-000-to-fuliza-2298316)).
- Tala's first loans in Kenya start at KSh 1,000 to 2,000, priced at 0.3% to 0.6% a day ([Tala Kenya help page](https://tala.co.ke/loan-app-help/loan-amounts-and-fees/); [Nairobi Wire](https://nairobiwire.com/tala-loan-calculator)); in the Philippines its general manager reported a 94% repayment rate ([Tribune, March 2025](https://tribune.net.ph/2025/03/09/talas-star-shines-for-small-borrowers)).
- impactMarket's Uganda pilot approved 165 of 196 interviewed applicants, average loan $620.75 (range $200 to $2,500), at 0.1% a day over six to nine months; it found repeat loans, women borrowers and quick-revenue businesses such as mobile-money trading the most promising ([impactMarket docs](https://docs.impactmarket.com/impactmarket-apps/2.-impactmarkets-products/microcredit/piloting-microcredit-in-uganda)).
- Jia, a stablecoin lender to small businesses in the Philippines and Kenya, passed $2 million in originations across more than 2,000 borrowers, charging about 2% to 6% a month in 2023 reporting ([FinDev Gateway](https://www.findevgateway.org/news/blockchain-firm-jia-records-2m-in-microfinance-originations-in-philippines-kenya); [TechCrunch, 2023](https://techcrunch.com/2023/05/17/jia-a-blockchain-based-lender-of-small-businesses-in-emerging-markets-raises-4-3-million-seed/)).

So a human-level first loan is 10 to 50 USDC, a repeat loan up to a few hundred, a term of 30 to 180 days, and a price far below the 90% to 219% a year of digital lenders. The production defaults in `docs/DEPLOYMENT.md` (a full line of 25 USDC, 20 lines of issuance budget, 500 USDC of oracle-issued exposure) are the right order for a first pilot. The live testnet APR of 9.33% (EFFR 433 plus 500 bps premium) is a tenth of market prices; on a 25 USDC loan for 30 days it is about 0.19 USDC of interest (arithmetic on the contract's formula), and at the calibrated 1,400 bps premium for a 10% annual default rate it is about 0.38 USDC. That price is the proposition; it only holds if losses are covered by the reserve, sponsors and backers rather than by interest.

## 2. What the evidence says, and what each finding changes

| Finding | Source | What it changes in the plan |
| --- | --- | --- |
| Loans made through a local partner repay at 97.1% on Kiva; direct loans with no intermediary repay at 72.8%. | [Kiva due diligence](https://www.kiva.org/about/due-diligence) | Somebody local who knows the borrower must sit in the loop. In our design that is the backer (secured or unsecured) and, during the bootstrap, the officer agent working through a partner. |
| Zidisha, which has no field staff and screens by seven SMS references, acknowledged an 18% write-off rate, found higher interest correlated with higher default, and moved to interest-free loans with a borrower-funded reserve. | [Hacker News thread with Zidisha's reply](https://news.ycombinator.com/item?id=7335341); [Zidisha](https://en.wikipedia.org/wiki/Zidisha) | Remote screening alone is not enough; a reserve funded ahead of loss is right; price must stay low. |
| Converting group liability to individual liability did not raise default in a Philippine field experiment, but borrowers with weaker social ties defaulted more under individual liability. | [Giné and Karlan, JDE 2014](https://ideas.repec.org/a/eee/deveco/v107y2014icp65-83.html) | Individual loans with social backing (our model) are supported, provided the backing comes from people who actually know the borrower. Backing from strangers is not social collateral. |
| Accounting mechanisms with strong transitive trust cannot be robust to strongly beneficial Sybil attacks; weaker transitive trust can be. | [Seuken and Parkes, AAMAS 2014](https://www.ifaamas.org/Proceedings/aamas2014/aamas/p205.pdf) | The transitive end state must be the bounded, stake-rooted kind in `docs/TRANSITIVE_TRUST_TARGET.md`, not unlimited passing-on. |
| Circles in Berlin failed with businesses cashing out 90% of tokens despite 2.3 million euros of subsidy; Circles in Bali reached 1,530 users and 9,500 trust links in five months by plugging into the Banjar, an existing neighbourhood institution. | [Circles Bali impact study, arXiv 2025](https://arxiv.org/html/2504.02714v1); [Gnosis forum](https://forum.gnosis.io/t/circles-indonesia-unfolds-the-tale-of-ubi-tech-and-community-synergy-in-bali/7763) | Start inside an existing trust structure (a savings group, a cooperative, a workplace), not with strangers recruited online. |
| Goldfinch lost about $18 million across three borrower defaults and is winding down; the failures ran through intermediaries (Tugende, Stratos, Lend East). Kiva's national identity and credit-bureau build in Sierra Leone was wound down in 2022 as beyond the organisation's capacity. | [DL News](https://www.dlnews.com/articles/defi/goldfinch-borrower-lend-east-defaults-says-warbler-labs/); [Kiva](https://www.kiva.org/blog/sunset-kiva-protocol) | One small partner, loss-bounded by stake and reserve, not a layered intermediary or national infrastructure. |
| In Tanzania about 20% of digital loans defaulted and 40% were late; first-time borrowers taking loans under $5 were worst. A CGAP experiment with a Kenyan lender cut first-cycle default from 29.1% to 20% by clarifying the interest rate. | [CGAP](https://cgap.org/node/3477); [CGAP digital credit collection](https://www.cgap.org/topics/collections/digital-credit) | Plan for 10% to 20% first-loan default on unsecured digital credit and 3% to 6% with a partner and backers; show the price in plain words before the borrower accepts. |
| A two-month grace period raised business investment by 6% to 9.4% and long-run profits, and raised default. | [Field, Pande, Papp and Rigol, AER 2013](https://doi.org/10.1257/aer.103.6.2196) | Our 24-hour grace suits working-capital advances; a longer grace is a product variant to test with a bigger reserve, not a default. |
| Six randomised evaluations found microcredit "modestly positive, but not transformative", with gains in occupational choice and women's decision-making rather than income. | [Banerjee, Karlan and Zinman, 2015](https://economics.mit.edu/sites/default/files/publications/Six%20Randomized%20Evaluations%20of%20Microcredit.pdf) | Measure what the loan was used for and what it earned, not only repayment; expect modest effects and say so. |
| Mercy Corps Ventures' Nanyuki pilot made $9,697 of wage advances to about 68 workers at 8% a year against local rates above 20%, repaid by payroll deduction, delivered by USSD and cashed out to M-Pesa through Kotani Pay; most borrowers had feature phones. | [MCV pilot insights](https://medium.com/mercy-corps-social-venture-fund/pilot-insights-fast-and-affordable-defi-enabled-credit-for-smallholder-farmers-in-kenya-1ea8d911b85f) | The borrower never needs to see a wallet: the partner or relayer runs the chain side; a mobile-money exit is mandatory. |
| VSLAs lend $50 to $200 per group; a Sierra Leone RCT found that making VSLAs digital-finance agents lowered default rates; VSLA members mostly hold basic phones and are reached by accepting VSLA IDs and mobile numbers. | [IPA](https://poverty-action.org/expanding-financial-access-through-digital-finance-evidence-village-savings-and-loans-associations); [FinDev, 2025](https://microfinancegateway.org/blog/2025/07/six-steps-to-unlock-formal-credit-through-vslas) | A savings group is a ready-made trust graph: members back each other, the group's facilitator is the natural officer, and the pool adds liquidity the group lacks. |
| Kenya's non-deposit-taking credit provider regulations were reported final on 2026-10-05 (a licence above the capital threshold, registration below, KSh 250,000 a year); 252 digital credit providers were licensed by July 2026. The Philippines SEC lifted its online-lending moratorium on 2026-08-01 (MC 20 s.2026; a Certificate of Authority and PHP 20 million paid-up capital for one platform). Nigeria's FCCPC digital lending regulations took effect in 2025. | [TechTrends Kenya](https://techtrendske.co.ke/2026/10/05/cbk-non-deposit-taking-credit-providers-regulations/); [CBK draft regulations](https://www.centralbank.go.ke/wp-content/uploads/2025/08/Draft-Central-Bank-of-Kenya-Non-Deposit-Taking-Credit-Providers-Regulations-2025.pdf); [GMA News](https://www.gmanetwork.com/news/money/companies/994049/sec-lifts-moratorium-on-new-online-lending-platforms/story/); [FCCPC](https://fccpc.gov.ng/wp-content/uploads/2025/08/DIGITAL-CONSUMER-LENDING-2025-LATEST.pdf) | Lending to people needs a licensed lender of record. The pool is a ledger and a liquidity source; a licensed partner (a microfinance institution, a licensed digital lender or a cooperative) is the lender the borrower contracts with. Legal review is gate 1 in `docs/DEPLOYMENT.md` already. |
| GCash added USDC in March 2025 (limits PHP 100,000 a day in, PHP 100,000 a month out, spread undisclosed); Eversend sells a USDC off-ramp API to mobile money in 18 African countries with a $0.10 Base network fee; M-Pesa agent withdrawals cost KSh 11 to 309. | [Techloy](https://www.techloy.com/philippines-gcash-takes-crypto-leap-by-adding-usdc-support/); [Eversend](https://eversend.co/platform/apis/usdc-off-ramp); [Business Today Kenya](https://businesstoday.co.ke/m-pesa-charges-2026-withdrawal-and-send-money-fees/) | Cash-out exists in both candidate countries; its cost (fees, spread, limits) must be measured on a real 25 USDC round trip before any human loan. |
| World ID reports about 18 million verified humans in 160 countries and is pivoting to enterprise identity; one verified human may hold several app accounts, so one-line-per-person is the app's job; Kenya suspended it in 2023 and its current status there is unverified. | [Biometric Update, June 2026](https://www.biometricupdate.com/202606/world-shifts-from-crypto-identity-experiment-to-enterprise-proof-of-humanity); [The Block, 2023](https://www.theblock.co/post/248229/wolrdcoin-hits-single-day-sign-up-record-in-argentina-despite-local-investigation) | For a 50-person pilot the partner's own KYC enforces one person, one line. Proof of personhood is for the permissionless phase and sits behind an interface so the provider can change. |
| Microfinance operating costs run 19% to 28% of the loan portfolio (median, MIX data); per-borrower fixed costs are about 45% of operating cost. A Base transaction costs on the order of 0.1 to 0.3 cents. | [CGAP](https://cgap.org/node/2079); [Chung, 2014](https://d.lib.msu.edu/etd/3002/OBJ/download); [Base configuration changelog](https://docs.base.org/base-chain/network-information/configuration-changelog) | The chain is not the cost. Assessment, support and collection are. The testable claim of this project is that agent officers and an on-chain ledger cut that cost enough for a 9% to 18% APR to work with a sponsored reserve. |
| A professional audit of a DeFi lending protocol costs $25,000 to $100,000 in 2026, re-audits $5,000 to $20,000 a pass; typical timelocks are 24 to 72 hours. | [Sherlock, 2026](https://sherlock.xyz/post/smart-contract-audit-pricing-a-market-reference-for-2026) | Budget the audit before mainnet; the runbook's 2-day timelock and multisig already match practice. |

## 3. The route

Four phases. Each has an owner, a gate that must be met before the next phase spends anything, and a stop rule. Owners are lanes, not people; every human-facing step also needs the operator's decision and the legal gate.

### Phase 0: finish the testnet bootstrap (now to 2026-10-20)

Owner: Codex (runs), Claude (contract), Hermes (execution and receipts).

- Codex's three exact-recovery communities and the blog session's agent scenarios run on the live Base Sepolia pool as scheduled; the pool-funding target of 2026-10-19 stands or its shortfall is recorded (`action:pool-funding-20261019`).
- Claude lands the CI-30 fix as a reviewed change (a sub-cent balance is forgiven only out of unpaid interest) and makes code room in the pool (move more views and rarely used paths out, as CI-26 did), so that the next three items fit.
- Gate: the full Forge suite and invariants green on the fixed contract; the live-pool runs written up with their limits.
- Stop: no real money on any mainnet.

### Phase 1: contract v2 on testnet (October to November)

Owner: Claude (design and code), Codex (fixtures and economic comparison), Hermes (fork rehearsals).

1. Sponsored first loss: a backer's committed stake funds the loan it secures (the "sponsored claim" of contract issue 24), so a sponsor supplies D for a D loan instead of 2D.
2. Transitive capacity: consented, stake-rooted, bounded-depth allocation certificates per `docs/TRANSITIVE_TRUST_TARGET.md`, verified on chain, with the conservation bound proved (each root's allocations never exceed its stake; every edge within its consent; no resource counted twice) and the adversarial fixtures (diamonds, cycles, Sybil expansion, simultaneous borrowers, stake exit, multi-hop default) in the invariant suite.
3. The opt-in guard (contract issue 25): recipient pinning, the repayment-to-reuse cooldown and the disbursement delay, all off by default.
4. Officer sunset mechanics: the issuance budget can be lowered to zero; legacy lines run off under their own accounting; a newcomer can borrow through a multi-hop certificate with no officer and no oracle heartbeat.
5. `two_hop_check.py` grows into a k-hop conservation checker; the testnet deployment is migrated on an exact-state fork first, then redeployed.

Gate: an independent review of the v2 design (Codex, and the theory issues' reviewers), green suites, a measured gas and liquidity comparison against one-hop backing and direct sponsorship. Stop: any trace in which a party loses more than it put at risk directly.

### Phase 2: mainnet readiness (November to December)

Owner: Claude (audit scoping and fixes), operator (decisions and spending), Codex (legal and partner research), Hermes (ramp measurements).

1. Audit and bug bounty: two or three written quotes against the Sherlock range; fixes; a public bounty before the first deposit.
2. Deployment per `docs/DEPLOYMENT.md`: dry run, the three approval gates (legal, owner, signers), broadcast, timelock ownership, the owner-event check, then nothing else until the pilot's legal structure exists.
3. Legal structure: counsel confirms, for the pilot country, who the lender of record is and under which licence (Kenya: a licensed or registered credit provider under the 2026 regulations; the Philippines: an SEC Certificate of Authority holder with a registered online lending platform; Nigeria: an FCCPC-registered lender), what the pool's shares are, and how USDC lending and cash-out are treated under the country's virtual-asset rules (Kenya's VASP Act, in force since November 2025; the BSP's VASP rules). The likeliest structure is a partnership: the licensed partner is the lender and KYC holder, the pool is its funding and accounting layer, and the partner's officer role is an issuer seat with a bounded budget.
4. Ramps: one real round trip of 25 USDC from the pool to mobile money and back, with every fee, spread, delay and limit recorded (GCash USDC in the Philippines; Eversend or Kotani Pay to M-Pesa in Kenya), on Base mainnet with real USDC from the operator's own funds.
5. Pricing and reserve for people: set the risk premium from the calibration row for the pilot's expected default (800 bps at 5% a year, 1,400 at 10%), fund the first-loss reserve with sponsor capital before the first loan (`fundReserve`), and publish the loss budget.

Gate: audit report with no open high findings; legal sign-off naming the lender of record; a measured ramp; a funded reserve. Stop: any of the four missing.

### Phase 3: the first people (first quarter of 2027, 20 to 50 borrowers)

Owner: the licensed partner (lending), Hermes (relationships and operations), Codex (evidence and consumer protection), Claude (contract and reporting).

- Where: one site, one partner, one existing group structure: a savings group, a cooperative or a workplace whose members already know one another, as in Bali and Nanyuki. The country is the operator's decision after the legal gate; the Philippines (GCash USDC, a reopened lending regime) and Kenya (M-Pesa rails, a dense digital-credit market with harder regulation) are the two evidenced candidates.
- Who borrows: members chosen by the partner with the officer agent's assessment, within the issuance budget; at least one backer who knows the borrower per loan (a group member staking, or the partner staking as sponsor); women and quick-revenue businesses first, as impactMarket found.
- How: the borrower never touches a wallet. The partner's officer and the relayer run the chain; the borrower receives mobile money and repays by mobile money; the partner reconciles on chain. First loans 10 to 25 USDC, 30 to 90 days, the price shown in local currency and in plain words before acceptance; no contact scraping, no penalties beyond the contract's interest; a repayment-to-reuse cooldown of 24 hours; a cap of one open loan per person.
- Measure: default and lateness by cycle (budget 10% first cycle, 5% repeat), use of funds and earnings reported by the borrower, the partner's cost per loan, the ramp cost, and every on-chain receipt in `VERIFY.md`.

Gate to grow: three cycles with losses inside the budget, the reserve intact, two independent partners or groups, and one repeat borrower who borrowed again without an officer line. Stop: losses above budget for two cycles, any consumer-protection failure, or the partner losing its licence.

### Phase 4: officer sunset (after three cycles at phase 3)

Owner: Claude (contract), Codex (gates and evidence), the partner (operations).

The transition gates in `docs/TRANSITIVE_TRUST_TARGET.md`: stop new officer issuance as backed, multi-hop capacity carries the pilot's volume; run legacy lines off; verify a newcomer borrows with every officer offline; then lower the issuance budget to zero. Officers become what the evidence says works: finding good jobs for borrowers, helping with disputes and consent, auditing manipulation. The share of outstanding principal backed by stake or credit rather than issued lines is the metric, published each cycle.

## 4. What would make this fail, and what the plan does about it

- The price is too low to carry the losses: the sponsor and reserve carry them in the pilot, and the premium rises with measured default. If a 10% to 20% default rate persists, the 18% APR row cannot cover it, and the product is a sponsored one, which must be said.
- Nobody local wants to back strangers: the plan never asks them to. Backing comes from group members and the partner.
- Cash-out eats the margin: measured in phase 2 before any human loan.
- The licence is the whole business: true, which is why the partner is the lender and the pool is the ledger.
- Sybil borrowers: one line per person is enforced by the partner's KYC in the pilot, and by stake-rooted capacity and proof of personhood later; CI-30 is fixed before any mainnet.
- The team's capacity: Kiva Protocol is the warning. One site, one partner, 20 to 50 people.

## 5. Decisions this plan needs

1. The pilot country and partner type (operator, after counsel).
2. Spending: audit, reserve capital, ramp tests (operator).
3. Adopt phases 1 and 2 as the contract roadmap, with the CI-30 fix and code-room work first (the sync).
4. The pricing row for people (premium and reserve share) and the loss budget (the sync, then the operator).

Not decided here: nothing in this document authorises contact with any person or organisation, spending, or a mainnet transaction.
