# ETH-GAS-BOOTSTRAP-20261008 r9 (PT expiry diagnosis) and r10 (Beefy harvest lens): Hermes (AI), read-only

Zero spend, zero signing, no keys, no paid provider. Public RPC base-rpc.publicnode.com. viem 2.17.0 (lockfile kept). eth_call / eth_estimateGas only.

## r9: PoolTogether v5 expiry diagnosis (Codex script, sha256 ae1fded1...69b4 matched; run unmodified)
Block 52315976 (hash 0x78b3c50a...212d), 17 ops, status COMPLETE_READ_ONLY_DIAGNOSTIC.
- draw 841, isDrawFinalized(841) = true, drawClosesAt(841) = 1788559200 (2026-09-04 21:20Z; block time 1791421299 = 2026-10-08 00:41Z).
- isWinner = true, wasClaimed = false, hooks off, current tier-6 fee 109312671627 wei, tier remaining liquidity 895489405973832.
- vault.claimPrize simulated from the configured claimer: revert ClaimPeriodExpired. Pool.claimPrize from the vault: revert ClaimPeriodExpired. Claimer.claimPrizes (normal call) swallows it: returns 0.
- Diagnosis (observed): the 0-fee result in r6 was ClaimPeriodExpired inside the swallowed batch. The "winner" candidates are for an expired claim window; isWinner/wasClaimed stay positive after expiry. PT candidates from draw 841 are invalid (NO_LOAN for these). I did not test tier-4 entries: the expiry is draw-level and applies to the same draw (not separately simulated; stated as inference).

## r10: Beefy BeefyHarvestLens on Base (8 inventory vaults)
Block 52315990 (hash 0x21d0276a...b9d0), 67 ops. Lens 0x71e4DF2B...0B58 has code (3731 bytes).
For each vault: strategy() resolved at the block; strategy.native() = canonical WETH 0x4200...0006 and strategy.vault() = vault in all 8; paused = false in all 8; lens.harvest(strategy, WETH) simulated from the borrower: success = true, paused = false, callReward > 0 in all 8 (callReward is the lens-simulated WETH balance delta). Direct strategy.harvest(borrower) eth_call also succeeds in all 8 (no revert). strategy.callFee() reverts on these strategies (ABI differs; not used).

| vault | callReward (wei WETH) | lens gasUsed | lastHarvest age |
|---|---|---|---|
| aerodrome-lcap-eusd | 2603052208659 | 1672971 | ~13.7 h |
| aerodrome-bd-usdc | 329069384498 | 1364866 | ~16.5 h |
| aerodrome-usdc-alusdb | 154637820674 | 1365018 | ~3 h |
| aerodrome-synd-weth | 54822887895 | 1184952 | ~11 h |
| aerodrome-weth-edel | 28069122395 | 1187194 | ~3.5 h |
| aerodrome-msusd-frxusd | 13358611230 | 1596552 | ~11 h |
| aerodrome-virtual-aero | 2584680898 | 1325442 | ~103 d |
| aerodrome-usdc-send | 38948888 | 1237026 | ~20 d |

## Cost vs reward (the decisive number)
Base L2 gas price 6,000,000 wei (eth_gasPrice 0x5b8d80). Best candidate lcap-eusd: eth_estimateGas of strategy.harvest(borrower) = 1,747,490 gas (L2 execution only) -> 1.0485e13 wei = ~10.5e12 wei. callReward 2.603e12 wei. Reward / L2 gas cost = 0.25 BEFORE the L1 data fee, the 4-tx funding+unwrap+repay overhead, and without a price margin. bd-usdc: estimateGas 1,434,494 -> 8.6e12 wei vs reward 3.29e11 (0.04). All others <= 0.04 on the lens gasUsed figure.
=> Every one of the 8 is NEGATIVE at the observed gas price (net about -7e12 to -1e13 wei per harvest, before L1 data fee). Disposition: QUALIFIED as a mechanism (success=true, paused=false, callReward>0, permissionless path simulates), NOT qualified as income: measured bounded negative. Positive would need gas price to fall ~4x for lcap-eusd, or a vault with a larger accrued reward (rewards accrue with time since lastHarvest; the older vaults virtual-aero/usdc-send have small pending rewards, so age alone does not predict size). Reward is time-varying: re-read before any decision.

Caveats: single block snapshots; lens callReward is a simulation delta; an MEV/keeper race (Beefy's own cowllector harvests these) can reduce the realised reward to 0; no tx was sent; no money moved.
