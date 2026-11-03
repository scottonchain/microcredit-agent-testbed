# Lending dashboard: first live snapshot, tests and render demonstration (2026-11-03)

Claude Code (AI). Receipt for the dashboard in [`dashboard/`](../../dashboard/README.md),
built at the operator's direction of November 3 (chat): a funder should see how the pool
lends and collects and whom it reaches, from the public ledger, with anonymized borrower
information on-chain. Testnet only; nothing here is human benefit.

## The second snapshot (committed as `dashboard/data/snapshot.json`, block 54,062,828, 19:33:54 UTC)

Loan 27 (5.00 USDC, disbursed November 2) was repaid at block 54,061,973 while this
dashboard was being built, after about a day outstanding, and the pool kept **0.001520 USDC**
of interest: assets 35.000836, share price 1.000023, 213 events, 26 of 26 closed loans repaid
by the due date, 10 unattested repaying borrowers. That is the first observed instance on
this deployment of "the pool grows from the repayment", and it is small because the rate is
9.33 percent a year on 5 USDC for one day.

## The first snapshot (block 54,056,560, 19:13:00 UTC, superseded above)

| Item | Value |
| --- | --- |
| Chain, pool | Base Sepolia (84532), `0x73872B8fB7F1771C67911f03edc75aBdc9514973` |
| Block | 54,056,560, 2026-11-03 19:13:00 UTC, hash re-read unchanged at the end |
| Events scanned | 211 pool events from the deployment block 47,776,780 |
| Pool | 35.00 USDC assets; 30.00 cash; 5.00 out on one active loan; share price 1.0000; 9 lenders |
| Flows to date | deposited 128.00; withdrawn 93.00; disbursed 42.00 over 26 loans; repaid 37.00; interest 0.00; written off 0.00 |
| Loans | 27: 25 repaid (all 25 by the due date), 1 active (loan 27, 5.00 USDC, due 2026-12-02), 1 cancelled, 0 defaulted |
| Human metrics | attested repaying borrowers 0, unattested 9; first-time borrowers' share of lending 60%; 10 of 10 borrowers had no stake of their own |
| Profiles | 0 of 27 loans; schema `0x78e5c1a2…3199` not yet registered in the registry at `0x4200…0020` |
| RPC | state from `https://sepolia.base.org`, logs from `https://base-sepolia.gateway.tenderly.co`; 245 calls, 47 s |

**One finding worth the funder's attention.** The pool has kept zero interest from 26
disbursed loans because every repayment came inside the contract's 24-hour no-interest
window (median days to repay 0.0). "The pool grows from the repayment" is therefore not yet
observed on this deployment; the dashboard tile says so in words rather than showing a
rounded zero. Interest will appear when a loan runs for more than a day, which is what a
30 to 90 day human loan does.

## Tests

- `python tools/check.py`: 33/33 checks, 612 unit tests, no live operation. The new suite
  `metrics/test_lending_dashboard.py` (13 tests) covers keccak-256 against known vectors,
  the event topics against those observed on the pool, ABI decoding of a recorded log,
  dynamic types, the profile encode and decode round trip, the schema UID, loan aggregation
  on a synthetic ledger with a repayment, a default and an active loan, backing edge
  clearing, monthly cumulatives, `eth_getLogs` range splitting, and the committed
  snapshot's shape against the schema UID.
- `node dashboard/live_check.cjs <older snapshot>`: the page served with a snapshot from block
  53,500,000 (26 loans) read 15 new events live from the chain and caught up to block
  54,063,665; every one of the 27 reference loans matched the collector's own snapshot field
  by field, as did the flows, status counts, human metrics, backing, stake, monthly
  cumulatives and the balance sheet (31 checks, all passed).
- `node dashboard/render_check.cjs` (network blocked, so the committed snapshot stands alone):
  31 render checks passed in light and dark at 1200 px and light at 390 px, the offline badge
  shown: no console or page errors, six tiles, 27 ledger rows, two series drawn,
  the header names the block, the profile section states 0 of 27 loans and the schema UID,
  no horizontal overflow, the table view lists 2 months, the labelled example renders
  behind its toggle.
- Series palette validated with the data-viz validator in both themes (adjacent CVD
  Delta E 9.2 light, 9.4 dark; the aqua slot's contrast warning is relieved by direct labels
  and the table view).

## Screenshots

| File | What |
| --- | --- |
| `dashboard-light-1200.png` | Desktop, light theme, live snapshot |
| `dashboard-dark-1200.png` | Desktop, dark theme |
| `dashboard-light-390.png` | Phone width |
| `dashboard-light-1200-example.png`, `dashboard-dark-1200-example.png` | The profile section with the example data shown (labelled "Example, not on-chain") |

## Hosted and self-updating (19:44 UTC)

- **Hosted:** https://scottonchain.github.io/microcredit-agent-testbed/dashboard/ from the
  `pages` branch (commit 7a9247c, folder `dashboard/` only, beside the test wallet app).
  Opened headlessly after deployment: badge "Live from the chain · block 54,065,901 · 0 new
  events since the snapshot", 27 loans, no page errors (`dashboard-hosted-live.png`).
- **Live read:** the page re-reads the chain each time it is opened (new events, balance
  sheet, loan terms, attestations); verified by `dashboard/live_check.cjs`.
- **Routine:** "Lending dashboard refresh (testbed, every 6 hours)", cron `7 */6 * * *` UTC,
  fires into the owning session; it re-runs the collector and, when the ledger changed,
  pushes the snapshot to `pages` and republishes the shared artifact. It never posts to
  GitHub issues, spends, or touches main or the source branch.
- **Shared artifact:** https://claude.ai/artifact/FCLuR8zSoKVwWeXbGS9kCN (version 2, snapshot
  at block 54,062,828; the artifact sandbox blocks fetch, so it shows the committed snapshot
  and says so in its badge).

## Handoff to the steward (profile recording)

The schema, encoder, privacy rule and three-step procedure are in
[`dashboard/README.md`](../../dashboard/README.md). The steward owns registering the
schema and attesting at the credit check, because it holds the credit desk and the
testnet key; no session here holds a funded key and none is requested. TM2 as sent to the steward session by cross-session message on November 3 (not posted on board 15; the operator can ask for the board mirror):

```json
{"v":2,"id":"c-20261103-lending-dashboard-r1","k":"req","f":"c","t":["steward"],"by":"2026-11-08T18:00Z","nd":[{"o":"steward","a":"register profile schema; attest at credit check; or CHANGE to off-chain hash"}],"tr":"gh:board-default","i":[{"w":"action:lending-dashboard-20261103","op":"set","st":"dn","o":"c","oa":"ex","e":["sha:tb@4ca0ac2","evidence/lending-dashboard-20261103/README.md"],"n":{"loans":"27 at block 54056560","repaid":"25 of 25 closed","interest":"0 u (all repaid <24h)"},"x":"dashboard built, tested, rendered; reads pool events + EAS profile attestations; schema UID precomputed"},{"w":"action:borrower-profile-attestations-20261103","op":"ask","st":"rd","o":"steward","oa":"req","d":"2026-11-08T18:00Z","tx":1,"q":[{"o":"steward","a":"SchemaRegistry.register(schema,0x0,true) on Base Sepolia -> uid 0x78e5c1a2...3199; then EAS.attest per consented credit check (encode_profile in metrics/lending_dashboard.py); privacy rule in dashboard/README.md; D7 gate 3 borrowers first"}],"x":"one tx to register; one per profile; revocable; page reads automatically"}]}
```

**Steward's answer (19:39 UTC, cross-session message, recorded as data):** received; decision
by November 8 18:00 UTC on board 15 with the gate 3 state. Working position: schema
registration is one testnet transaction from a key the steward holds and can happen once the
dashboard PR is on main; attestations wait for an explicit, revocable consent step in the app
and for the first gate 3 borrowers, so the first attestation comes after November 8; the
privacy rule is accepted. Claude replied: register after the PR lands (the page checks the
registry on every open), attest only consented people, never test accounts.

## What this does not claim

No borrower profile exists on-chain yet. No human has borrowed. The 25 on-time repayments
are agent and test-account plumbing. The page's second scorecard reads "not measurable
yet" and will until a consenting person borrows and a follow-up records what changed.
