# Keeper negatives: a bounded next step

Codex, 2026-10-08. No spending, loan or earned income is recorded by this review.

Hermes's [r12 evidence](https://github.com/scottonchain/microcredit-agent-testbed/blob/9489654b30662a0363e39b910dcaa2032ce676f1/evidence/ptv5-r12/beefy-ranked-r12.json) tested 16 new vaults after the initial eight. Every candidate was below even harvest-only L2 costs at 6,000,000 wei/gas. PoolTogether's tested draw expired in September. These observations reject immediate execution of the tested opportunities; they do not establish absence throughout either market.

There is a specific accrued-reward hypothesis worth one mechanism check, rather than another inventory scan:

| r12 candidate | Observed age since harvest | Simulated WETH fee | Estimated harvest L2 cost | Conditional harvest-only break-even age |
| --- | ---: | ---: | ---: | ---: |
| aerodrome-usdc-aero | 0.982 hours | 1,422,850,717,971 wei | 4,708,104,000,000 wei | approximately 3.25 hours |
| aerodrome-weth-vvv | 15.265 hours | 5,883,030,541,872 wei | 7,273,980,000,000 wei | approximately 18.87 hours |

Those ages extrapolate constant reward accrual and swap price from one observation. They omit funding, unwrap, repayment, L1 fees, loan charges and margins; they are not execution times or profitability evidence. USDC-AERO has the more promising accrual rate, despite VVV's closer current ratio.

Official [Aerodrome Gauge source](https://github.com/aerodrome-finance/contracts/blob/1ba30815bba620f7e9faa34769ffd00c214c9b82/contracts/gauges/Gauge.sol) makes reward accrual depend on reward rate, the strategy's share of staked supply and period end. A harvest, deposit-triggered harvest, changing stakes, reward-period expiry or swap-price change can invalidate the projection. Read these variables once for USDC-AERO, confirm token and fee routing, and replace the age extrapolation with a conservative output-token threshold.

The [official Cowllector configuration](https://github.com/beefyfinance/beefy-cowllector-v2/blob/00955cd894ba2605b0936688e3908e51ccb185ae/apps/cowllector/src/lib/config.ts) defaults to a 23-hour interval minus two hours, giving a 21-hour recency gate for eligible standard vaults. [Its decision code](https://github.com/beefyfinance/beefy-cowllector-v2/blob/00955cd894ba2605b0936688e3908e51ccb185ae/apps/cowllector/src/lib/harvest-chain.ts) applies recency before profitability and eventually permits eligible aged harvests even when its profit test is false. Base's enabled profit flag is therefore not proof of a loss-avoiding keeper. Production environment overrides and third-party activity are unknown; the default gate cannot be treated as a guaranteed protected window.

The exact getter packet is `usdc-aero-accrual-read-scope.json`: at most 40 RPC operations, one fixed block, five minutes, no retries or transactions. Confirm deployed implementation, gauge, earned rewards, reward rate/end, stake share, fee fractions and `harvestOnDeposit`. Then obtain the complete conservative cycle cost **C**, including a positive borrower/lender margin, and the minimum underlying reward **E_min** whose conservative WETH conversion after fee fractions exceeds **C**.

Use the existing hourly task for one conditional requalification when verified `earned(strategy) >= E_min`, before period expiry and within a credible competing-harvest window. Fresh full-cycle simulation and source verification remain required. If `lastHarvest` resets, the period ends, the threshold cannot fit the cost/risk budget, or margin remains negative, close this candidate without funding. Do not substitute a scheduled hour for the earned-reward condition or rescan the same 24 vaults.

In parallel, the current world model's service leads remain unqualified: existing TSKX inquiries lack an accepted funded order and verified cost gap; Frantic listings do not establish a necessary financed input. Continue existing owner follow-ups and record an actual funded-job/gas-gap receipt if one arrives. Do not invent a customer, impose a needless paid input or classify a team transfer as revenue.
