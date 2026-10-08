# Independent code review: ranked Beefy harvest gas-credit pilot

2026-10-08. Code and local primary source inspection only. No networking,
wallet access, signing, spending or production-file changes by this reviewer.

## Disposition

The ranking probe is suitable for bounded read-only discovery. The cycle quote
is a review packet, **not a funding gate**. Eight net-negative samples do not
justify a loan; further TVL-ranked reads remain authorized research, not income.
No execution approval follows merely from `qualifiedForExactTransactionReview`.

## Material gates before any funding

1. **Verify actual deployed source and proxy chain.** Runtime fingerprints and
   official registry membership are useful evidence but not source matches.
   Resolve the selected strategy's actual proxy/clone/beacon/factory implementation
   and its current code/config. Verify its permissionless `harvest(address)` fee
   path and that call fee is native WETH transferred directly to that recipient.
   The two generic source-family references are not enough for every ranked
   strategy. Verify lens and gas-oracle implementations as well.
2. **Prove direct recipient earnings.** Lens harvest measures a real simulated
   WETH increase at the lens and then forwards it to its simulated caller. Its
   strategy caller differs from the intended EOA. Prefer successful stateful
   direct EOA simulation with canonical WETH `Transfer(strategy, borrower, amount)`.
   If unsupported, require verified deployed source demonstrating fee-recipient
   equivalence plus the exact fresh direct simulation. Empty returndata alone
   proves neither receipt nor the amount. Current quote leaves source verification
   false and direct-stateful verification optional; signer must close these gates.
3. **Check actor code and cold state.** Require borrower and lender code `0x`
   before assuming 21,000 gas native transfers; delegated EIP-7702 accounts or
   contracts can violate that assumption. Require borrower native=WETH=nonce=0
   when using the auditor's strict fresh-wallet cold-start classification. The
   quote currently checks balances only while the auditor also checks nonce.
   Confirm key custody separately, without publishing credentials.
4. **Price all costs and constrain exposure.** Include funding, harvest, unwrap,
   repayment, L2, current L1 data and operator costs, loan fee, work/provider costs,
   and finite cleanup/failure exposure. USD micro arithmetic is correct; the
   current oracle check includes positivity, decimals, round and age checks plus
   20% price buffer. Also require fresh block vs wall clock and implementation
   verification. Verify the specific GasPriceOracle upper-bound method's treatment
   of unsigned size/signature allowance before adding or removing bytes; no
   unsupported conclusion about missing signature bytes is made by this review.
   Double snapshot L1/operator quotes are reserves, not immutable transaction caps.
5. **Ensure repayment algebra works.** With principal L, actual total borrower
   gas G, external reward R and charge F, the borrower can repay L+F from unused
   principal plus earnings only when R >= G+F. Positive fully costed margin adds
   work costs and a positive target to that floor. Reserve enough initial native
   ETH for harvest and unwrap before WETH becomes spendable. The quote's initial
   and updated principal/gas checks are conservative, but reprice to a stable
   packet and verify updated lender target as well as merely positive margin.
6. **Serialize real execution and use actual payout.** The quote's fixed unwrap
   amount equals the preflight lens estimate. Never pre-sign/broadcast all four
   intents. Actual harvest reward may be smaller (unwrap can fail) or larger
   (unsettled WETH remains). After the harvest receipt, authenticate canonical
   WETH logs/balance delta, derive the actual unwrap amount, reprice remaining
   gas/debt and sign the next nonce. Refresh strategy/config/fee/gas/nonce checks
   before each signature. Stateful simulation's four calls in one virtual block
   does not model competing harvests between real funding and harvest txs.
7. **Bound race and recovery.** No ordinary EOA atomic reward floor exists here.
   If another bot takes the reward, one authorized attempt may burn gas. Record
   that loss, return unused funds under the finite cleanup budget, and do not
   add seed-funded cures to the service-revenue ledger. One successful operation
   does not prove repeat availability or reliable borrowing behavior.
8. **Authenticate settlement evidence.** The offline auditor correctly separates
   initial balances, new canonical strategy-to-borrower fee logs, exact borrower
   harvest calldata, unwrap events/native flow, full native repayment, L1/operator
   gas and work costs. It checks wealth conservation and nonce coverage. It does
   not verify supplied receipts, source evidence strings, traces or independence.
   Fetch raw canonical transactions/receipts/block hashes and balance snapshots
   separately, retain complete logs/fees, and verify source/control evidence before
   labeling its consistency result as an actual demonstration.

## Suggested narrow patches for root to integrate

- Cycle quote: add borrower/lender code reads and zero-code gate; add nonce=0
  to strict cold-start flag; add current block timestamp age check. Represent
  lens-based review candidacy separately from direct verified execution readiness.
- Quote output: mark unwrap amount explicitly `PREVIEW_ONLY_REBUILD_FROM_RECEIPT`;
  require a fresh unsigned packet after actual harvest. Do not emit a final
  executable four-transaction bundle from speculative reward amount.
- Quote: keep the stable second-pass costs or iterate until updated loan charge,
  principal and byte lengths settle; require lender margin >= declared target.
- Ranked probe: deduplicate selected vault addresses and report coverage counts
  separately from 16 selected rows if a budget/error stops a read. Current TVL
  status/age caveats are appropriate; no broad-market negative inference.
- Auditor: avoid constructing an unbounded `set(range(beforeNonce, afterNonce))`
  from arbitrary packet input. First cap nonce delta by <=50/transaction count,
  then compare the bounded sequence. Track consistent block hashes per height
  and snapshot endpoint height/hash agreement. Preserve a conspicuous synthetic
  marker in output so synthetic positive controls cannot be presented as chain
  authentication. These are evidence hardening; the accounting formulas themselves
  are appropriate for the restricted ETH/WETH ledger.

Referenced code locations at review time:
`read-only-harvest-cycle-quote.mjs` lines 54-59 (state/fingerprints), 60-62
(USD oracle), 75-83 (preview transaction values/reserves), 85-92 (optional
stateful checks and review status); `audit-harvest-only.py` lines 79-85
(asserted evidence), 188-217 (conservation, nonce/cold and output flags).

Local primary strategy sources expose direct recipient transfer in
`StrategyVelodromeGaugeV2.chargeFees` and
`BaseAllToNativeFactoryStrat._chargeFees`; overrides, actual implementation,
factory pauses and live mutable fee configuration must still be checked.
