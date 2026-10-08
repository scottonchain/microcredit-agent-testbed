# ETH-GAS-BOOTSTRAP-20261008-r14-accrual (Hermes AI, read-only)

Scope: Codex scope JSON f95dac64 (sha256 f48404d3f5f563f88e30d6b294369d15647a73ec532f2c68392711c03efc27a4, verified on fetch). Quote helper not run. No keys, signatures, spend, paid data.

Read: Base 8453 (chainId 0x2105), public RPC base-rpc.publicnode.com, fixed block 52317212 (hash 0x9c77cf74...fac7, ts 1791423771 = 2026-10-08T01:42:51Z), 34 RPC requests (<=40), 0 retries, ~3 s. Raw responses: r14_raw.json. Derived numbers: r14_analysis.json (analyze.py).

## Deployment
- vault 0xc005B983...ae55 -> strategy() 0xedE4Dd67...ea4C; strategy.vault() matches; paused=false; harvestOnDeposit=TRUE; native=WETH 0x4200...0006; output=AERO 0x940181a9...8631; want=0x6cdcb1c4...971d (= gauge stakingToken); gauge=0x4f09bab2...8360 (rewardToken = AERO = output; rewardPool/rewards/swapper/beefySwapper/stratName getters revert, recorded, not guessed); unirouter 0xcf77a3ba...4e43; factory 0x420dd381...40da; feeConfig 0xfc69704c...61eb.
- Strategy runtime is a 45-byte EIP-1167 clone (len 45) -> implementation 0x13ad51a6664973ebd0749a7c84939d973f247921 (15088 bytes). keccak(runtime): clone 0x70ed0474...b39b, impl 0x7dafca48...b2bf. Source match NOT verified: Sourcify v2 lookup HTTP 400 and Blockscout 403 for both impl and gauge (2 attempts each, stopped). Fingerprints are not source verification.

## Gauge accrual (block 52317212)
- earned(strategy)=61.4758 AERO; strategy stake 2.6172% of totalSupply; rewardRate 0.501034 AERO/s (total, 1e18-scaled); periodFinish 2026-10-15T00:00:00Z (166.3 h remaining); lastUpdateTime 1791423555; userRewardPerTokenPaid vs rewardPerToken consistent.
- Strategy accrual 47.21 AERO/h. Cross-check: rate x age since lastHarvest (1791419083, age 1.302 h) = 61.475 AERO vs earned() 61.476 -> accrual is linear and matches the gauge, so far.
- Fees (getFees): total 9.5%; call share 0.1053% of that => caller gets 0.01% of reward value (9.99e-5); beefy 94.6%, strategist 5.3%.

## Threshold (conditional, NOT a profit claim)
Calibration: r12 lens callReward 1.42285e12 wei at block 52316634 (model age 0.981 h, 46.32 AERO accrued) => 3.072e10 wei callReward per AERO earned (implies ~3.07e14 wei = 0.000307 ETH per AERO swap value, from the lens simulation, not a quote).
Harvest-only L2 cost C from r12 (784,684 gas x 6e6 wei) = 4.708e12 wei.
| C multiple | C wei | E_min AERO | age from lastHarvest (constant rate) |
|---|---|---|---|
| 1.0 (break-even) | 4.708e12 | 153.3 | 3.25 h |
| 1.5 | 7.062e12 | 229.9 | 4.87 h |
| 2.0 | 9.416e12 | 306.5 | 6.49 h |
| 3.0 | 1.412e13 | 459.8 | 9.74 h |
All reachable before periodFinish (166 h) IF nobody harvests first.

Best case (21 h, Cowllector default recency gate, constant rate/price): spread = +2.57e13 wei L2-only, about USD 0.06 to 0.09 at an assumed ETH price of 2,500 to 3,500 (price assumption stated, not read). That is the ceiling for one harvest: it must also cover 4-tx overhead, L1 data fee, unwrap, loan charges, borrower/lender margin. A 0.10-USD-class surplus does not clear the stack, and the loan is only needed for ETH gas the borrower does not have.

## Exposures (not eliminated)
- harvestOnDeposit=TRUE: any deposit into the vault triggers a harvest and resets lastHarvest/earned (any depositor can reset the threshold).
- A competing Cowllector harvest after the recency gate (default 21 h; production overrides unknown) takes the reward at or above break-even age; 3.25 h is far inside the window where others may harvest.
- Constant-rate and constant-price assumptions; AERO swap price can move; stake share changes dilute rate; weekly epoch emission change at 2026-10-15T00:00Z.
- Source verification still missing (see above).

## Disposition
Mechanism qualified (accrual matches gauge). Income NOT qualified: finite trigger exists (earned(strategy) >= E_min, E_min = 153.3 AERO at break-even, ~307 AERO at 2x cost, before 2026-10-15T00:00Z and before a competing harvest), but the maximum single-harvest spread is on the order of USD 0.1, not enough for a loan stack. Recommend: NO_LOAN stands; no timer-based poll. One conditional requalification only if earned() >= ~460 AERO (3x C) is observed by the existing hourly carry, with a fresh full-cycle quote and source verification first. No execution authorized or performed.
