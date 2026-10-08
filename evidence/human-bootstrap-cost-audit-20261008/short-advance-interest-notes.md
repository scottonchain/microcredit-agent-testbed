# Short-advance interest: exact current-source arithmetic

Codex, 2026-10-08; offline source inspection and integer arithmetic only. No chain, keys, signing, contact or protected-repository edits.

**933 bps (9.33%) is the local documented testnet APR**, EFFR433 + premium500. **1833 bps (18.33%) is a calibrated scenario**, EFFR433 + premium1400; deployment guidance associates1400 with10% annual default-probability calibration. Neither rate was freshly verified by RPC in this task. Existing loans retain their origination rate when the settings change.

Inspected local checkout `460875c897241d6b9d09877ca36da9fb696f2bf9`, contract Git blob `d06ebd2d8397d62840269314e87710d3c43bb89b`. Formula in `_interestAccrued`, lines1412–1416:

```
annual_micro = floor(principal_micro * loan_apr_bps / 10000)
interest_micro = 0                              if elapsed_seconds < 86400
interest_micro = floor(annual_micro * elapsed_seconds / 31536000) otherwise
```

`disbursedAt==0` also returns zero. Exactly one day triggers interest for the **whole elapsed day**; the grace day is not subtracted. Simple interest uses original principal until closure, even after partial principal repayments. The selected1/5/25USDC principals divide exactly at the first floor; arbitrary smaller principals may not. The lens preview uses a differently ordered division and does not apply this first-day branch, so core source is authoritative here.

The JSON contains24 exact rows:1/5/25USDC ×0/1/7/30elapsed days ×933/1833bps, including debt, interest, full-payment dues and principal-only payment allocation. USDC amounts have six decimals; no cent rounding is applied to these accrued-interest rows. Reserve45% and protocolfee0% are explicit allocation assumptions matching the documented pilot, not fresh state reads.

**CI30 matters:** `_repay` applies cash to interest first. On5USDC at7days and933bps, accrued interest is8946micro-USDC. A5,000,000-unit payment allocates8946 to interest and4,991,054 to principal, credits4025 dues, then closes because8946 remains below10,000—writing off8946 **principal**. With initially zero reserve, the newly credited4025 reserve cash is consumed at closure, while dues remain recorded. Total cash above borrowed principal is zero; that differs from saying no cash was allocated to interest. A fully paid5,008,946-unit debt would instead repay all principal, retain4025 reserve and deliver4921 units of lender interest. Principal-only cases are diagnostic arithmetic, not a suggested repayment policy or earned-history proof.

The one-cent thresholds use exact rational arithmetic: `days = 0.01 * 365 / (principal_USDC * APR_fraction)`, with ceiling seconds and a check of the source result one second before/at that threshold. A borrower should not delay a paid job just to generate interest or dues.

A hypothetical **one-cent fee on a one-dollar one-day advance** is1% for the day, or **365% simple nominal annualization**. Rolling and compounding the same1% cost every day yields approximately3678.3434% effective annual cost, `((1.01)^365 − 1) ×100`; this is a hypothetical compounding assumption, not the pool's APR or a legal disclosure calculation. The current source does not implement that flat fee.

Sources inspected locally: [pool source](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol), [TESTNET.md](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/docs/TESTNET.md), [deployment calibration](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/docs/DEPLOYMENT.md). Links identify sources; no network fetch occurred in this task. Reproduce with `python3 work/claude-support-20261008/reproduce-short-advance-interest.py` from `/workspace`.
