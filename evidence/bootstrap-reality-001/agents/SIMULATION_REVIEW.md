# Source, economics and pilot review

Reviewed simulation/run_bootstrap.py 2026-10-07. Arithmetic is consistent with stated modeled inputs. This is a reference-model bootstrap with accepted public-source work, not observed paid-provider borrowing or deployed multi-hop enforcement.

## Unit economics and sensitivity

Base service inputs: 10 searches × $0.01 + 10 scrapes × $0.013 = $0.23. These are pinned author-listed AgentCash rates, NOT current provider quotes or receipts. Inference $0.05, customer bid $1.00, success fee $0.01 and native gas USD cap $0.005 are assumptions.

Worker starts zero: borrows .30, spends .28, retains .02; customer escrow pays .30 back to pool and .70 to worker; worker pays .01 fee => closing .71. Native ETH gas is outside that USDC cash ledger; with .005 cap economic surplus .705. Repeat self-financed job produces another .72 before gas/overhead, total worker1 closing1.43. The same delivered report fixture across jobs is not three independent commercial deliveries.

| Price/cost change | Result |
|---|---|
| Baseline no retry | break-even buyer bid .295 including fee+gas; .30 bid yields .005, too narrow without contingency |
| Full .02 retry consumed | conservative break-even .315; screen strictly greater than .315 appropriate |
| Buyer bid .20 | NO LOAN: negative margin |
| Buyer bid .50 | .21 surplus before gas, .205 at gas cap; .185 with full retries |
| Buyer bid1 | .71 before gas, .705 after cap, .685 after retries |
| Inference doubles to .10 | .33 input cost; .30 advance insufficient, even when1bid profitable; increase loan only after capacity+quote checks |
| Search+scrape prices double | .46 API+.05 inference=.51; .30 advance insufficient; worstcase requiredcapital .53 |
| Gas USD exceeds .005 | modeled cap fails; revise economic minimum or refuse; never quietly exclude gas |
| Gas+inference+API costs exceed bid minus .01 fee | refuse the job/loan |

General rule: required loan = MAX(0, input quote + bounded inference + retry budget − spendable worker cash − spendable customer prepayment). For positive net surplus bid > input + inference + retry + success fee + measured gas + actual overhead. A separately escrowed bid gives repayment protection but not working cash unless contract permits advance access. Include escrow fees and rejection/retry terms when actual terms exist.

## Comparison and risk

Direct prepayment eliminates this financing gap if the buyer agrees and repayment/delivery protection is cheaper. Direct sponsor advance uses .30 rather than lender liquidity .30 plus secured backing .30: pooling must earn its complexity through reusable underwriting/settlement/cross-customer liquidity, not by claiming greater capital efficiency for this isolated job. A root-backed two-hop route does not multiply stake; aggregator/coordinator cannot create new independent loss absorption.

Failure case: worker consumes .28, keeps .02, stake suffers .30 and lender recovers .30 only after modeled strict default delay. That is conservative principal recovery but NOT zero total economic loss; residual .02 could be contractually recoverable in a future design but cannot be assumed. Real vendor no-refund conditions/retry delivery uncertainty are not evidenced here. Nativegas and modeled inferred61days must not be described as observed61days of execution.

## Concrete first real pilot

1. Hermes obtains a current unauthenticated stableenrich.dev search/scrape 402 response and preserves timestamp, network8453, asset, amount, payee, validity window and resource path. Root network is currently blocked; use established Hermes channel.
2. Claude obtains ONE independent buyer's funded $1 order for a ten-company source-linked report, with explicit acceptance fields and deadlines. If no such buyer, offer a first quote and record refusal; do not manufacture buyer revenue from team transfers. Price1 is a proposed opening quote, not demonstrated demand.
3. Capture .23 resource quote or revised figure; cap .30 only if actual API+inference+retry <=.30. Select ONE company dry run; preserve provider response, payment settlement transaction and output acceptance. No outreach/personal data needed.
4. On testnet validate actual pool loan/full repayment and actual backing/default behavior with controlled wallets. Test current deployed provider separately from reference multi-hop proposal. No mainnet use until CI30 fixed and reviewed and multi-hop capacity routing actually enforced onchain (or pilot clearly labels existing one-hop backing instead).
5. For first mainnet job only after those gates, borrower starts zeroUSDC; separate sponsor locks .30 secured backing; separate lender provides .30 loan; buyer funds1 escrow with explicit authorized repayment assignment. Bind loan/job/resource/delivery/settlement IDs, receipts, nonces and amounts. Cap total outstanding .30, one job, stop after one run.
6. Accept the useful output using buyer acceptance policy; settle repayment directly from released escrow before worker discretionary withdrawals; witness restored .30 lender principal and sponsor unlocked backing. Refuse new credit if default/rejection/provider overquote, no forced rescue.
7. Only then repeat with a second independent operator and a third self-funded repeat. Demonstration is complete only with actual third-party funded job/payment receipts, profitable full costs, and capacity route enforced—not local fictitious transfers.

The current run demonstrates conditional liquidity bootstrapping of the reference graph for modeled external payments. It does not establish demand, deployed trust transitivity, mainnet safety, or a cheaper alternative to sponsorship.
