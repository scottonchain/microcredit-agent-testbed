# Omnequa contributor lending ledger

This dashboard reports dated Base Sepolia test-USDC loan accounting. It does not
establish human borrowers, sponsor expenditure, incremental earnings or poverty
reduction. Those outcomes are **NOT MEASURED**. No real-person profiles are fetched,
derived or published, regardless of claimed consent, attester, expiry or loan ID.
Wallet-linked chain data is pseudonymous and permanent; revocation or removing a
public display cannot erase history. No registration or attestation is requested.
The optional example is entirely synthetic, has no wallet/loan links and never
enters ledger totals. Legacy encoding helpers remain only for fixture compatibility.

## Source and hosting

The actual source branch is `claude/admiring-carson-zm4b4n`, verified at
`737f68cd362ea0c0e659af355e6702e2e1962fff`. The app branch
`claude/d7-live-sim-app-20261101` at `f834f4e349a7df349b4ad1bf9104438e848929ab`
does not contain the dashboard. Its branding, code and service are separate.
The hosted copy is `pages:dashboard/`; its HTML at
`3b5aceb460d3cb787498e0d3687b1480959dd02c` matched source byte for byte before
this patch. Only the hosted snapshot was newer. This patch preserves those dated
ledger amounts at block **54145172**, November 4 2026 00:08:23 UTC, while removing
misleading derived fields and marking it `historical-not-reverified`. There is no
invented collection timestamp or new chain observation.

## Accounting

Contract source: `microcredit-contract@1812e7d`,
`packages/foundry/contracts/DecentralizedMicrocredit.sol`.

- `flows.interest` is **gross interest collected**. Repayment fees and reserve
  allocations are distinct; current fee and reserve balances are stocks.
- Lender NAV is `max(0, lenderCash + totalLentOut - max(firstLossReserve, totalImpaired))`.
  The dated snapshot has gross interest 0.001520, reserve allocations 0.000684,
  fees 0.000000 and NAV above net lender deposits 0.000836 test USDC. Six decimal
  places keep these differences visible. This difference is not a return rate
  or proof of reserve sustainability; funding, releases, losses and fees matter.
- Unreserved pool cash means `lenderCash - reservedLiquidity`, including reserve
  cash. It is not available borrowing capacity: queued withdrawals, liquidity
  buffer, threshold, utilisation and borrower limits also apply.
- Write-offs are not sponsor expenditure. Historical largest-loan/current-NAV
  ratios do not establish origination-limit compliance. Current stake and first
  request proxies do not establish first-time or financially excluded humans.
- Historical backing edges are not shown as current capacity: the contract can
  release/consume them without a new `Backed` event.

## One existing daily refresh writer

The existing owner reports the original routine changed to **daily 00:07 UTC**,
with the first run under that cadence due November 6. This patch neither modifies
nor creates a schedule. A schedule report is not a successful collection receipt.

After exact-head review and coordinated integration, that owner runs:

```sh
python metrics/lending_dashboard.py
python -m unittest metrics.test_lending_dashboard metrics.test_lending_dashboard_safety
node dashboard/render_check.cjs /tmp/dashboard-render
```

The collector uses the configured canonical state endpoint and existing log
endpoint only where permitted. No key or transaction is involved. It requires:

1. Matching expected chain IDs on both providers; the lower finalized height;
   matching deployment/boundary numbers, hashes and timestamps on both providers.
   Explicit older blocks must also be finalized. No latest-head fallback.
2. Full history from deployment block 47776780, chunked ranges with bounded
   timeouts, retries and a ten-minute provider budget. Duplicate logs are counted
   once; conflicting duplicates, wrong addresses, removed/out-of-range logs fail.
   Each event block hash must match both providers.
3. Exact `getAllLoanIds` reconciliation, independent `getLoan/getLoanTerms`
   principal, borrower, rate, lifecycle and timestamp checks; per-transaction
   repayment/application matching, including meta repayments. Active outstanding
   includes the contract's fixed-principal interest calculation. Pool cash,
   outstanding principal, reserved liquidity, shares, stake, impairment, reserve
   and NAV must reconcile. The ABI exposes no per-loan cumulative repayment
   getter: repayment completeness therefore also depends on aggregate cash and
   principal reconciliation, not a fabricated private-storage getter.
4. Rechecking both boundary hashes after all reads. Only then is `collectedAt`
   advanced, even if amounts did not change. Provider URLs/errors are not emitted
   into published output. Finality/provider claims are not independent consensus
   proofs; equally compromised providers are outside this trust model.

Conservative limitation: a repaid loan with forgiven sub-cent principal fails
closed because the ABI does not expose the historical reserve allocation needed
for exact reserve replay. Preserve the last good snapshot and report this to the
owner; never silently treat the forgiveness as cash or sponsor spending.

`refresh-status.json` records attemptedAt and success/failed, independently of
source block/time and last successful collection. Failed collection does not
write either snapshot. Each file is atomically replaced locally; publish matching
JSON and JS **together in one Git commit** after checking their equivalence.
A failed attempt may publish only the status file while retaining the last-good
snapshot. Never gate successful publication only on changed ledger amounts.

The browser never performs RPC replay, so it cannot combine an old base with
inconsistent new state. It reloads only published snapshot JSON with an eight-second
timeout, retains its dated snapshot on failure, and distinguishes browser fetch
attempts from collector attempts and success. More than 30 hours since verified
collection is stale. Historical snapshots without a verified collection timestamp
are always labelled stale/unverified. Missing data is unavailable, not zero.
`live_check.cjs` now directs callers to offline checks and performs no live calls.

## Coordinated delivery, not deployment

This draft only changes dashboard source, collector/tests and its documentation.
It does not advance app, main or pages; PR443, PR441, the article and the daily
routine remain separate. Source integration requires independent exact-head
review and the current ownership/drain gates.

For later approved Pages publication, refresh and preserve its current head, acquire
the project lease, and copy only `dashboard/index.html`, `dashboard/README.md`,
`dashboard/data/snapshot.json`, `dashboard/data/snapshot.js` and the optional
`dashboard/data/refresh-status.json` from the accepted source/collector output.
Never replace the Pages root or app assets. Verify SHA256 equality for each copied
file and JSON/JS payload equivalence before the conditional push; re-read remote
bytes and rendered results afterward. Record source commit, collector commit,
source block/hash/time, collection/attempt times, Pages commit and hosted URL.
The first live refresh and hosted readback are still required, not supplied here.
