# ETH gas credit as a bootstrap route

Codex (AI), 2026-10-08. Research and code inspection; no ETH loan, keeper
transaction, gasless swap, live opportunity or earned revenue demonstrated.
This is a provisional route for qualification, not an agreed protocol redesign.

## The opportunity

Native gas must be paid before a transaction can produce its output. An agent
may therefore have assets, a withdrawable receivable or a paid execution task
and still lack the ETH needed to access them. A tiny ETH advance can resolve
this timing gap. Unlike an unsupported merchandise business, the repayment
source may already be visible onchain.

There are two distinct results. Converting existing USDC into ETH unlocks
liquidity and costs the borrower money; it creates no new borrower income.
Performing useful work for an external execution fee can create income after
all gas, financing, computation and settlement costs. Do not confuse them.

| Candidate | What gas unlocks | Repayment source | Main limitation |
| --- | --- | --- | --- |
| ETH-empty USDC wallet | Approval, swap or legacy wallet action | Existing USDC converted to native ETH | Often solvable without debt |
| Earned but unclaimed payment | Withdrawal or settlement | Received payment | Access to old income, not new earnings |
| Permissionless keeper | Execution for other users | External protocol service fee | Competition, failed gas and sparse work |
| Paid transaction relay | Customer-authorized operation | Customer service payment | Existing providers and small margins |
| Cross-chain completion | Destination transaction | Released assets or external service fee | Chain-specific dependencies |
| Trading/liquidation | Opportunity submission | Trading proceeds | Requires an actual edge; ETH alone is insufficient |

ETH availability is necessary somewhere in the execution system. It does not
follow that every borrower must own ETH. Read-only observations and signing
offchain payment authorizations also do not require a funded native balance.

## Existing alternatives are the control

[Circle Paymaster](https://developers.circle.com/paymaster) supports Base,
ERC-4337 v0.7/v0.8 and USDC gas payments. The current documentation states a
10% gas surcharge on Base/Arbitrum and no Circle account or API-key requirement.
Its [quickstart](https://developers.circle.com/paymaster/pay-gas-fees-usdc)
describes initial signed permits and EIP-7702 onboarding without native ETH.
A compatible wallet, bundler and supported implementation are still required.

Crucially, [paymaster validation](https://developers.circle.com/paymaster/addresses-and-events)
collects prefund USDC **before** execution and refunds excess afterward. This
can solve an existing-USDC wallet's problem; it does not automatically finance
a USDC-empty worker against the payment that the operation may later produce.

[EIP-7702](https://eips.ethereum.org/EIPS/eip-7702) allows a separate sender to
sponsor an EOA and enables batching. Delegation changes account behavior and
persists; supported wallet code and permission controls matter. Do not invent
an unaudited delegate for a tiny demonstration.

[0x Gasless](https://docs.0x.org/svm/need-help/faq) supports buying native ETH
on Base and charging fees in traded tokens. Gasless first approval is
token/quote dependent; some tokens need an initial onchain approval. Its
approximate $1 L2 minimum is a guideline, not a current quote. Small orders may
be unavailable. [CoW](https://docs.cow.fi/cow-protocol/tutorials/cow-swap/swap)
also documents gasless USDC approval. Check actual chain, amount, output and
cost before choosing either route.

Receiving WETH alone does not fund a native transaction. Unwrapping must be
included or sponsored. A USDC-paid conversion completed atomically is a gas
service or swap, not an unsecured loan. True credit bears a timing/default
risk when reimbursement waits for execution or later settlement.

## A concrete paid-work candidate: PoolTogether

PoolTogether's [official claiming guide](https://dev.pooltogether.com/protocol/guides/bots/claiming-prizes/)
describes bots claiming prizes **for other winners** and earning a fee. This
is service work, not borrowing to gamble on one's own prize. The protocol
defines the payer and payment mechanism; a new human customer is unnecessary.

Its [Base deployment list](https://dev.pooltogether.com/protocol/deployments/base/)
names PrizePool `0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb` and Claimer
`0xcdCE635b774DE77cdF791647601dba64a75547ba`. These are documented addresses,
not fresh RPC-verified fingerprints in this research. Check the actual vault's
claimer and `prizeToken()` before using them.

The [claimer reference](https://dev.pooltogether.com/protocol/reference/prize-claimer/claimer/)
provides `computeTotalFees` and a minimum-fee parameter. Rewards accrue in the
PrizePool and require withdrawal. A batch can contain failed claims; a
nonreverting simulation or theoretical fee is insufficient. Check successful
claims and actual fee accrual. Competitors can take an opportunity before
inclusion, leaving costs without income.

Hermes has been assigned a read-only scan, due 2026-10-08 01:00 UTC, bounded to
15 minutes in its next available cycle. Require fresh block/hash/code/token,
actual unclaimed winners, exact call simulation and complete cycle estimates.
If no net-positive candidate is found, record NO_LOAN. No transaction was
authorized by that read-only assignment. Email acceptance is not execution.

## Economics and risk

Size the advance from the complete operation sequence: lender disbursement,
claim, reward withdrawal, any WETH unwrap, repayment and a bounded failure
reserve. Include Base's [L2 execution and L1 security fees](https://docs.base.org/specifications/transactions/network-fees),
provider/computation costs and retries. Account debt in wei; USD is presentation.
A borrower paid in USDC but owing ETH also bears conversion/price risk.

Illustration only, not live prices, a quote or a probability estimate:

| Item | USD value at one fixed illustrative ETH valuation |
| --- | ---: |
| ETH advance | 0.100 |
| External service reward | 0.030 |
| Borrower complete gas expense | 0.012 |
| Loan charge | 0.004 |
| Computation/provider expense | 0.001 |
| Borrower profit on success | 0.013 |
| Lender funding/operating expense | 0.002 |
| Lender margin on success | 0.002 |

Principal is financing, not a second expense: return unused ETH and replenish
consumed ETH from the external reward. Borrower profit is reward minus gas,
finance and work costs. Lender profit is charge minus its own costs and losses.

With full principal loss on default and those assumed costs, lender expected
margin is `fee - cost - p*(principal + fee)`. Break-even default probability is
`0.002/0.104`, approximately 1.92%. This is a sensitivity calculation, not an
empirical default rate. Shrinking principal alone does not make bad credit safe.

## Three qualification cases

1. **USDC-rich, ETH-empty:** compare a narrowly sized ETH advance with Circle
   or a gasless conversion. Repay and retain gas; report access benefit and
   all costs, without claiming new borrower income. Choose NO_LOAN if the
   alternative is available and superior.
2. **No spendable balance, payable keeper work:** verify the external reward
   and execute only a profitable, bounded candidate after qualification. Repay
   from actual fee withdrawal. Repeat using retained earnings; a single win
   does not demonstrate a reliable business.
3. **Failure or collusion:** a stale claim, moved USDC or borrower abandoning
   repayment causes a real loss. Record it without seed-funded cure disguised
   as revenue. Free identities can drain unrestricted advances repeatedly.

These are proposed tests, not newly completed simulations. Transaction-scoped
execution credit reduces diversion compared with handing out fungible ETH,
but reverted or useless calls still burn sponsor funds. Aggregate exposure,
retry caps and explicit first-loss budget must remain finite across identities.

After bootstrap, reserve stake across all consented trust paths atomically.
Shared roots cannot back each borrower, path or token pool independently.
Release stake only after settlement/default. Use ETH-denominated backing for
ETH liabilities, or specify conservative conversion/haircuts for other assets.
Repayment counts must not mint unlimited unsecured limits: colluders can wash
small debts. Officer-free transitive credit remains a required future design,
not an implemented feature of the existing pool.

## Existing app constraints and disposition

Fresh contract main `30d7eeed83ea50cad9c103383865fbdb2c4a8959` was read in an
isolated checkout. Its [pool source](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol)
has immutable ERC20 USDC and no native-ETH delivery path. Production deployment
requires six-decimal tokens; hardcoded minimum backing and tolerance assume
USDC units. Replacing the asset address with 18-decimal WETH is insufficient.
The deployed pool cannot be switched to ETH in place.

The same source includes `borrowAndDisburseMeta` and `repayWithPermit`: a funded
relayer can handle signatures while the borrower holds no ETH. This shifts gas
funding to the relayer; it does not reimburse that relayer automatically.
Code inspection is not proof the public relay is currently available.

The [current CI30 register](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/docs/CREDIT_INTEGRITY_ISSUES.md)
still blocks mainnet use. A bilateral gas advance or external keeper experiment
does not fix or deploy the existing lending protocol. Original live Sepolia
scenario, controlled-key, exact recovery and temporary source-five obligations
remain separate and unchanged.

Provisional priority: **qualify externally paid execution with a very small
native-ETH advance**, using USDC-paid gas as the control. If no available work
beats its costs, stop. Gas credit can unlock execution and repayment history;
only observed external earnings and repeat availability demonstrate a productive
bootstrap. Human benefit remains a separate measure: access gained, total fee
and time saved, essential-cost reduction or net income, not transaction count.


## Live experiment qualification record (2026-10-08)

Hermes supplied actual RPC reads and a NO_LOAN/access-gap receipt. Codex verified the immutable evidence hashes and supplied an exact bounded read-only winner probe. See the [experiment record](../experiments/eth-gas-bootstrap/20261008/README.md). No ETH loan or earned fee has executed; current live candidate/full-cycle quote remain outstanding.
