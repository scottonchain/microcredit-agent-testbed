# r14 accrual packet: independent counterreview

2026-10-08. Read the local public r14 raw/analysis/code and current whole-cycle
quote helper. No network, wallet access, signatures, transactions or production
edits by reviewer.

## Supported findings

The fixed-block getter results are internally consistent with a working gauge
accrual model. At block 52317212, strategy gauge earnings are about 61.476 AERO
and the instantaneous stake-share model gives about 47.208 AERO/hour. Raw fee
configuration decodes total=0.095 and caller fraction of fees about
0.001052631578947368, giving approximately **0.0001 of gross reward value**
(0.01%). Harvest-on-deposit is enabled. These observations support the mechanism
hypothesis; they do not authenticate deployed source or demonstrate income.

The strategy is a canonical 45-byte EIP-1167 clone targeting implementation
`0x13ad51a6664973ebd0749a7c84939d973f247921`. The existing quote helper can call
its ABI transparently: all strategy reads and `harvest(borrower)` must target
the **clone** `0xede4dd6758634007eb1f4cf8a203bf237a44ea4c`, whose storage is used
by delegation. Fee transfer sender is likewise the clone, not the implementation.
Do not substitute implementation in intents or auditor strategy address.
The helper fingerprints clone code but does not itself extract/source-match the
implementation. The separate source gate remains open.

## Unsupported conclusions to correct

- A hypothetical $0.06-$0.09 spread does not establish that a loan stack cannot
  fit. Costs can be smaller or larger; obtain one concrete full-cycle quote.
- The default 21-hour keeper recency policy is neither a protocol earnings cap
  nor an assured competing harvest deadline. The projected result at that time
  is a conditional point, not a maximum single-harvest spread.
- 153.3 AERO is only a threshold using old harvest-only L2 gas and modeled
  conversion. 3x that threshold is a heuristic, not a full-cycle requirement.
- Sourcify HTTP 400 using `?fields=match,compilation` records a failed request.
  It does not establish absent verified source. Retry once with the documented
  supported default or `fields=all`, retain request/status/body/hash, and report
  the actual result. A future 404 would mean not found there, not globally
  unverifiable. Blockscout 403 is an access result, also not source absence.
- ACP escrow and lending-app mainnet deployment gates do not determine the
  economics of this separate bilateral ETH gas advance. The pilot cannot claim
  implementation of our deployed USDC pool's lending asset or trust graph.

## Exact debt algebra

Borrower starts with loan L; spends gas G_B; receives external fee R; repays
L+F. Ending borrower native wealth is:

`L - G_B + R - (L + F) = R - G_B - F`.

Unused principal therefore cancels. Adding L again as an expense is wrong.
Borrower fully costed margin is `R-G_B-F-C_B`; lender margin is
`F-G_L-C_L`. With loan charge `F=G_L+C_L+target_L`, the system's required reward
floor is `G_B+G_L+C_B+C_L+target_B+target_L`. Reserves, risk and funding size
remain separately bounded; zero profit is not a productive bootstrap.

## One concrete read-only quote now

Run the pinned current `read-only-harvest-cycle-quote.mjs` on this one candidate,
even if it returns NO_LOAN. If the old r12 packet uses `vaults` instead of
`candidates`, supply a minimal public adapter:

```json
{"candidates":[{"id":"aerodrome-usdc-aero","vault":"0xc005b9833debcf5fe6cc5bc9ba4fd74bb382ae55","strategy":"0xede4dd6758634007eb1f4cf8a203bf237a44ea4c"}]}
```

Helper re-reads its own fresh state; the adapter is not quote evidence. Obtain
all four unsigned intent gas reservations, actual current L1/operator quotes,
loan fee, oracle caps, current lens reward and direct call result. Negative
economics can be determined without spending and without deployed source being
fully verified; source remains required before positive execution.

At the same quote block, read gauge `earned(strategy)` plus AERO and WETH
balances of the strategy to identify existing balances that distort a simple
earnings ratio. With no material residual distortion, `q = simulated reward / E`
is only a conditional fee-per-AERO calibration. Derive `E_min = ceil(R_required/q)`
with an explicit conservative swap/price haircut. Keep `R_required` in wei as
the actual gate and the AERO amount/age as a projection. Refresh lens/direct
simulation before any funding; accrual, staking share, fees, price and competitors
can change. If residual balances matter, do not force the linear E_min model.

The present helper correctly includes nonce-zero cold state, empty-code actor
checks, block freshness, stable multi-pass fee pricing, and preview-only unwrap
intents that must be rebuilt from actual receipts. An optional stateful direct
simulation still does not eliminate race risk. There is no qualified income now.

## Reproducibility limitation

Published r14 `analyze.py` has absolute `/root/work/run_r14/` paths, depends on an
external `r12.json`, models its timestamp from a two-second block difference and
performs fresh Sourcify network requests. Retain original as provenance, but use
an offline parameterized reproduction that takes explicit r14/r12 file paths,
their hashes and exact recorded block timestamps; separate source HTTP evidence
from derived arithmetic. Do not rerun old network requests as if they were fixed
historical evidence.
