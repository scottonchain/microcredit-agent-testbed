# r15 full-cycle counterreview

**Decision: NO_LOAN at the recorded snapshot.** The packet supplies a genuine negative, read-only quote, not a funded bootstrap or earned revenue. Reviewed offline; no network calls, signatures, wallet access, or transactions.

Evidence: commit `c573f434ee98f2e1bf625b16b7da97ede9b6a4da`, `evidence/ptv5-r15`. All 13 local files match the byte lengths and SHA-256 values in `ROOT_FETCH_MANIFEST.json`; these are root fetch fingerprints, not a peer-issued execution attestation. Quote block **52317986**, hash `0xf2fa561df0703e15ebe39a5ee3f7d4a076ec8bec6d53404aeeab064ee9bfb0df`, timestamp **2026-10-08 02:08:39 UTC**.

## Accounting and threshold

Every reported debt, gas-total, target, and margin identity checks out with integer arithmetic:

| Quantity | Wei |
|---|---:|
| Principal L | 12,707,276,393,564 |
| Loan fee F | 236,103,482,898 |
| Borrower gas reserve G_B | 11,552,069,448,694 |
| Lender funding gas reserve G_L | 235,103,482,898 |
| Required external reward C | 11,789,172,931,592 |
| Simulated lens WETH delta R | 2,510,707,389,920 |
| Borrower margin R − G_B − F | **−9,277,465,541,672** |
| Lender margin F − G_L | 1,000,000,000 |

Principal cancels upon full repayment: `L − G_B + R − (L + F) = R − G_B − F`. The floor is `C = G_B + G_L + target_B + target_L`, with both targets 1,000,000,000 wei and declared work cost zero. Unused principal is neither profit nor an extra cost. The four transaction reserves sum correctly; current L1 quotes are doubled and operator quotes are zero. These are conservative snapshot reservations, not actual receipts or guaranteed future fee ceilings.

Using the **historical modeled** conversion 30,720,000,000 wei/AERO gives `C/q = 383.7621397003 AERO`; the unrounded r14 calibration gives 383.7564661491. Thus **384 AERO is a conditional precheck level**, not an execution guarantee. `C/R = 4.6955583032`. At unchanged 47.21 AERO/hour, the modeled threshold takes about 8.13 hours after last harvest. Competitors, vault deposits (`harvestOnDeposit=true`), reward-rate changes, routing prices, inventory and gas can invalidate this projection. The claimed ~82 AERO “now” is a model, not a fresh gauge-earned getter in this quote. Zero work cost establishes only an on-chain contribution-margin test; the tiny target margins do not demonstrate a sustainable agent business.

## Execution and source evidence

The direct EOA `harvest(address)` eth_call succeeds with empty returndata. That does not measure the borrower's WETH receipt. The lens records an actual **simulated** WETH delta for its own call path. `eth_simulateV1` fails with `RpcError_-38014`; all-four-call success and exact-cycle demonstration are false. There is no atomic plain-EOA net-profit guard: a competing harvest between simulation and inclusion can consume the reward while this borrower still pays gas. Never submit the lens intent or presign the four previews; unwrap and repayment must be rebuilt from actual receipts, balances, fees, and nonces.

Offline Sourcify reconciliation materially strengthens the source evidence:

- Implementation `0x13ad51a6664973ebd0749a7c84939d973f247921`: `match`, not `exact_match`. Applying its **one 53-byte CBOR metadata replacement at byte 15035** to the supplied recompiled runtime reproduces **all 15,088 on-chain bytes exactly**. There are no immutable replacements; the original 32 differing bytes are confined to metadata.
- Gauge `0x4f09bab2f0e15e2a078a227fe1537665f55b8360`: `exact_match`. Applying its **25 supplied 32-byte immutable replacements** reproduces **all 6,236 on-chain bytes exactly**. Different raw runtime hashes are therefore expected. BaseScan's “Similar Match” label and Sourcify's label describe different verification workflows; the raw hash difference alone is not a contradiction.

This compares saved compiler/deployment artifacts; it is not an independent compiler rerun or a new chain-code read. The saved implementation source's `harvest(address)` passes the explicit recipient through `_harvest` to `chargeFees`, which transfers `native` to that recipient without a caller whitelist. Calls must target the configured **clone**, not the implementation. This supports recipient routing equivalence while retaining the absence of a stateful direct-recipient balance measurement and actual income.

## Next finite gate

On the existing scheduled team task, perform one capped, block-pinned read of `earned(strategy)`, `lastHarvest`, vault strategy, clone/implementation fingerprints and pause state. If reset or materially below the conditional level, record NO_LOAN and stop that pass. If plausible, obtain **one new full-cycle quote**, using fresh lens delta/native costs and current dollar caps; require `R_fresh >= C_fresh` plus any explicit work-cost/race margin. Reconcile deployed source and direct recipient behavior before a signer considers funding. A positive quote remains a bounded execution opportunity, not a claim of bootstrap success; success requires actual harvest WETH, native unwrap, full repayment and both parties' fee-adjusted balance reconciliation. Preserve this lane's $0.50 principal and tighter native/exposure caps; another lane's $50 scope does not apply. Do not create another automation or broaden scans.

Correction to the Morpho README: all six saved receipt requests returned **RPC -32602, “Archive requests require a personal token”**, not successful `result:null`. Net liquidation profit remains unestablished. The already assigned residual-position reads in the other Codex lane should proceed without duplication.
