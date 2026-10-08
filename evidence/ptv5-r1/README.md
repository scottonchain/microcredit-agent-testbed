# ETH-GAS-BOOTSTRAP-20261008-r2: PoolTogether v5 Base read-only qualification (Hermes, AI)

Read-only JSON-RPC (eth_getBlockByNumber/eth_getCode/eth_call/eth_getLogs) on Base mainnet, 2026-10-08 ~00:25-00:40Z.
No transfer, claim, approval, registration or purchase. No keys used. Public RPCs: mainnet.base.org, base-rpc.publicnode.com, 1rpc.io/base.
Pinned block 52314628 hash 0xaa35ca53b7ee535f9639cdb01c317e238a8dbdc8f66ed261e4c6e09ba2cfbfa3.

## Observed at that block
- Claimer 0xcdCE635b774DE77cdF791647601dba64a75547ba: code 7457 bytes; prizePool() = 0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb (matches docs).
- PrizePool 0x45b2010d...732cb: code 22984 bytes; prizeToken() = 0x4200000000000000000000000000000000000006 (WETH on Base, so the claim fee is paid in WETH, unwrap needed for ETH);
  getLastAwardedDrawId() = 841; numberOfTiers() = 7; drawPeriodSeconds() = 86400; getTotalShares() = 538; claimCount() = 283 (selector answers; meaning of the count not verified here).
- Claimer: timeToReachMaxFee() = 21600 s; maxFeePortionOfPrize() = 0.1e18 (10% of a prize at most).

## Not obtained (access gap, within the 15 minute / no paid key budget)
- Recent ClaimedPrize logs: eth_getLogs limits seen: mainnet.base.org rejects >500-block ranges (413); 1rpc.io limit 50 blocks; publicnode 403; drpc 400/500. In the 500-block window ending at the pinned block: 0 ClaimedPrize logs (and 0 logs of any kind from the pool in the last 200 blocks). A 500-block window is ~17 min, so this says nothing about daily claim volume.
- Winner list: winners are determined per vault/depositor off-chain (official bot / subgraph / prize API). No winner list was fetched, so no unclaimed winner, no computeTotalFees, no batch eth_call, no fee accrual check.
- No claim batch was simulated. No complete-cycle cost (L2 execution + L1 data fee, provider cost, failed-attempt exposure) was computed because there is no candidate call to price.

## Disposition: NO_LOAN, access gap
No positive-net unclaimed opportunity was identified. Smallest useful advance: undetermined. Next viable step (not started): a scan of recent claims via a provider that allows wider eth_getLogs ranges (paid or registered, which this task forbids), or the official bot's public winner endpoint if one exists without a key; otherwise stay NO_LOAN.
