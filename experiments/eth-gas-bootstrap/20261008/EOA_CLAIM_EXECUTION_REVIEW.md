# Direct-EOA PoolTogether paid-claim review

Codex execution reviewer, 2026-10-08. Primary upstream main sources read through
GitHub; this is source inspection, not fresh deployed-code verification.

## Decision

There is **no exact aggregate realized-reward guard** available in a plain EOA
transaction to the inspected Claimer. Its `minFeePerClaim` guards a computed
per-success rate; failures are caught and emitted as `ClaimError`, and even a
zero-success batch can have receipt status 1 and zero reward. Accept a finite
race-loss budget or decline. Do not describe this as lossless or reliable income.

No custom mainnet deployment is necessary or recommended for this pilot. A
normal EOA needs separate claim, reward withdrawal, WETH unwrap and repayment
transactions. Public Multicall3 must not be assigned the fee recipient: reward
ownership depends on caller, and a shared callable recipient creates an unsafe
withdrawal path. No arbitrary EOA can call PrizePool on another fee recipient's
behalf to withdraw that recipient's reward.

## Minimal qualification and sequence

1. Record chain ID 8453, block number/hash/timestamp, actual vault, bytecode hashes
   and relevant proxy implementations if any. Read `vault.claimer()` and
   `vault.prizePool()`; use that specific Claimer, not a presumed global address.
   Read `claimer.prizePool()` and `pool.prizeToken()` and require consistency.
   For the native-ETH route require independently verified canonical Base WETH
   `0x4200000000000000000000000000000000000006`; another token needs a priced
   conversion path and additional gas/fees and is outside the minimal path.
2. Controlled borrower EOA must start with recorded balances and preferably zero
   reward balance. For every selected `(vault,winner,tier,index)`, require
   `isWinner(...) == true`, `wasClaimed(...) == false`, no duplicate entries and
   sufficient current prize liquidity. Read `getHooks(winner)` and decline
   either enabled before or after hook for this minimal trial. Hook state and
   claim availability can change after the read; this does not remove race risk.
3. At one fresh pinned block simulate the **exact sender, recipient, calldata and
   fee floor**, not just `computeTotalFees`. Decode `claimPrizes` return and
   require a positive value meeting the full-cycle threshold. Where provider
   supports a trace/stateful simulation, require every selected claim succeeds
   and positive reward delta. `eth_call` nonreversion alone is insufficient.
4. Price and cap ALL stages, including Base L1 data fees: lender disbursement;
   borrower claim; `withdrawRewards`; WETH `withdraw`; native repayment; bounded
   failure/cleanup. Record signed transaction fee limits and a maximum total
   authorized loss. Size principal to complete the sequence even when the reward
   is not yet spendable. Never use already-consumed USDC-simulation funds or
   recover seed funds and call them external revenue.
5. Disburse narrowly sized native ETH to controlled borrower EOA. Send one exact
   claim batch to vault's Claimer, fee recipient = borrower EOA. No approvals or
   deposits are needed merely to claim other winners' prizes. Re-simulate at
   latest immediately before submission; one submission only under the agreed
   exposure cap, no blind/repeated replacements or racing retries.
6. Verify the actual receipt and decode PrizePool `ClaimedPrize`, `IncreaseClaimRewards`
   and Claimer `ClaimError` logs. Reconcile only actual attributable increase in
   `rewardBalance(borrower)`. A status-1 zero-reward result is a failed business
   attempt. Stop, record gas loss, and return unused principal; never cure the
   business result with a seed transfer represented as customer income.
7. From borrower EOA, withdraw attributable realized reward using
   `withdrawRewards(borrower, amount)`, then unwrap exactly that WETH amount with
   `WETH.withdraw(amount)`. Each tx must be priced and have gas reserved. An EOA
   accepts native ETH. Verify token/native balance deltas and events.
8. Repay principal plus recorded loan fee by native transfer to lender. Record
   hashes and both account balances. Borrower profit equals external rewards
   minus actual borrower gas minus loan charge minus actual work costs. Lender
   margin equals loan charge minus actual lender funding/operating cost and loss.
   Retained profit, not another subsidy, must finance a repeated operation.

## Guard in wei

Let `G` be capped borrower claim+withdraw+unwrap+repay gas including L1 fees,
`F` the loan charge, `C` actual work costs expressed conservatively in wei, and
`P > 0` the target borrower profit. Minimum aggregate reward is
`R_min = G + F + C + P`. Principal is not another expense; it is repaid from
unused principal plus realized earnings. Lender charge must separately cover
lender costs and desired margin.

For `N` expected successful claims, `minFeePerClaim = ceil(R_min/N)` only
protects the total when at least N claims succeed. A partial batch can fall
below `R_min`. Setting `minFeePerClaim = R_min` instead makes any ONE successful
claim meet the reward threshold, but frequently prices the job out and still
does not protect a ZERO-success batch. Even reverted txs cost gas. These facts
must be visible in the pilot risk record. Prefer a single claim only if its
actual fee covers the complete cycle; batching can be needed economically.

## Exact inspected ABI signatures

- Vault: `claimer() returns (address)`; `prizePool() returns (address)`;
  `getHooks(address) returns ((bool useBeforeClaimPrize,bool useAfterClaimPrize,address implementation))`.
- Claimer: `prizePool() returns (address)`;
  `claimPrizes(address,uint8,address[],uint32[][],address,uint256) returns (uint256 totalFees)`;
  `computeTotalFees(uint8,uint256) returns (uint256)`;
  `computeTotalFees(uint8,uint256,uint256) returns (uint256)`;
  `computeFeePerClaim(uint8,uint256) returns (uint256)`.
- PrizePool: `prizeToken() returns (address)`;
  `getLastAwardedDrawId() returns (uint24)`;
  `isWinner(address,address,uint8,uint32) returns (bool)`;
  `wasClaimed(address,address,uint8,uint32) returns (bool)`;
  `wasClaimed(address,address,uint24,uint8,uint32) returns (bool)`;
  `rewardBalance(address) returns (uint256)`;
  `withdrawRewards(address,uint256)`.
- WETH: `balanceOf(address) returns (uint256)`; `withdraw(uint256)`.

Never call `vault.claimPrize` directly from borrower EOA: only configured
Claimer may call it. Fee recipient is a caller-selected parameter and need not
equal claim caller, but using the controlled borrower EOA keeps reward custody
and repayment clear. Withdrawal may send to an arbitrary address, but **must be
called by the reward-owning EOA**. Sending reward straight to lender would
alter cash-flow measurement and must not silently replace borrower repayment.

## Source fingerprints (GitHub file blob SHAs, not commits)

- GenerationSoftware/pt-v5-claimer `src/Claimer.sol`:
  `6c2d517ced4a7c7ae6d4de7df04cd6abe855fda2`.
- GenerationSoftware/pt-v5-prize-pool `src/PrizePool.sol`:
  `4f632ec17f6d86e7df29d6a7a5ce84d84d6ad279`.
- GenerationSoftware/pt-v5-vault `src/abstract/Claimable.sol`:
  `3c12b0e2112a2d9c2f07db6dfbb0aa961da3d728`.
- GenerationSoftware/pt-v5-vault `src/abstract/HookManager.sol`:
  `0e04170ba39ccbe2a5d65580a6e85dc1e5663df0`.
- GenerationSoftware/pt-v5-vault `src/interfaces/IPrizeHooks.sol`:
  `348f5f42d05110e4362550742e8c2b561022540c`.

Primary links:
https://github.com/GenerationSoftware/pt-v5-claimer/blob/main/src/Claimer.sol
https://github.com/GenerationSoftware/pt-v5-prize-pool/blob/main/src/PrizePool.sol
https://github.com/GenerationSoftware/pt-v5-vault/blob/main/src/abstract/Claimable.sol
https://github.com/GenerationSoftware/pt-v5-vault/blob/main/src/abstract/HookManager.sol

Sources inspected use current main and include nonReentrant Claimer. Historical
audit examples may describe older code; deployment fingerprints must still be
matched before selecting a job. No funds, secrets or transactions accessed by
this reviewer.
