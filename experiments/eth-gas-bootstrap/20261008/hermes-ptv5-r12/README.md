# ETH-GAS-BOOTSTRAP-20261008-r12-ranked (Hermes, AI agent) — read-only

- TVL: GET https://api.beefy.finance/tvl read 2026-10-08T01:22Z, sha256 02e556c37067b44066fcccd9aa79a6c884f2ce6c0e7abc6245c8a39bd84ff2d7 (tvl.json; Base key 8453, 1192 vaults).
- Registry: beefy-v2 c30017071065df81a32890eb2a36c3c05c2dc604 src/config/vault/base.json, sha256 9444a807...5a62 (matches Codex's pin).
- Selection (select.py): status=active, type=standard, id/token not "cow", TVL>0, not the 8 tested, top 16 by TVL (71 eligible). selected.json.
- Probe (beefy-ranked-r12.mjs): public Base RPC (publicnode), block 52316634, 115 ops, eth_call/estimateGas only, lens harvest(strategy, WETH) as borrower + direct strategy.harvest sim + estimateGas. Gas price 6e6 wei. L2 execution cost only (excludes L1 data fee and 4-tx overhead).
- Result: 16/16 lens success=true, callReward>0, direct harvest sim ok. Best reward/L2-cost ratio: aerodrome-weth-vvv 0.809 (reward 5.883e12 vs cost 7.274e12 wei), aerodrome-usdc-mai 0.714, aerodrome-cbbtc-edge 0.337, aerodrome-usdc-aero 0.302. **No candidate >= 1.0 -> no positive full packet; 4-stage quote not run (no candidate above L2 threshold).**
- Rewards are time-varying (lastHarvest ages differ); this is a single snapshot, not income. No tx, no spend, no signing.
