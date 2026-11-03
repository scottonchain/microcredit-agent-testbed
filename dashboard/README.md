# Lending dashboard: what the pool is doing, read from the chain

Claude Code (AI), 2026-11-03, at the operator's direction (chat, summarised): a funder
who puts USDC into the pool should be able to see how the money is lent, collected and
whom it reaches, from the public ledger, with anonymized borrower information recorded
on-chain. This is the funder-facing view of direction D16
([human-first-mainnet.md](../coordination/directions/human-first-mainnet.md)) and reads the
recorded Base Sepolia pool in [deployments/current.json](../deployments/current.json).

- **Measurable outcome or decision:** the funder's decision to keep money in the pool rests
  on what the pool did with it. The page shows the two NORTH_STAR scorecards (reserve
  survival; human benefit per sponsor dollar) from on-chain data, and says plainly when the
  second has no data.
- **Evidence sought:** every loan's disbursement and repayment with its transaction hash,
  interest actually kept by the pool, repayment and default counts, and consented borrower
  profiles attested on-chain.
- **Competing simpler route:** read Basescan by hand. It shows transfers, not loans; it
  cannot tell a repayment from a deposit or count interest, and it has no borrower view.
- **Stop or change condition:** if the steward cannot record profiles on-chain within the
  privacy rule below, the profile layer moves off-chain (hash on-chain, data with the
  steward) and the page says so; the ledger half stays as it is.

## Files

| File | What it is |
| --- | --- |
| [`metrics/lending_dashboard.py`](../metrics/lending_dashboard.py) | Collector. Plain JSON-RPC, standard library only, no key, no transaction. Writes `data/snapshot.json` and `data/snapshot.js` at one block hash. |
| [`metrics/test_lending_dashboard.py`](../metrics/test_lending_dashboard.py) | Offline tests (keccak vectors, event topics, ABI decoding, aggregation, range splitting, the committed snapshot's shape). Run by `python tools/check.py`. |
| [`index.html`](index.html) | The page. No build step, no library, no network: it renders `data/snapshot.js`. Works from a file, GitHub Pages or omnequa.org. |
| [`render_check.cjs`](render_check.cjs) | Headless render check (Playwright, network blocked): every section renders from the committed snapshot alone, no console errors, no horizontal overflow at 390 px, light and dark screenshots. |
| [`live_check.cjs`](live_check.cjs) | Live-read check (Playwright, network): serves the page with an older snapshot, lets it catch up from the chain, and compares every loan and total with the collector's own later snapshot. |
| `data/` | The committed snapshot, the demonstrated state. Re-run the collector to refresh it. |

```bash
python metrics/lending_dashboard.py            # refresh data/ from Base Sepolia (about a minute)
python metrics/lending_dashboard.py --no-write # summary only
python metrics/lending_dashboard.py --schema-uid
node dashboard/render_check.cjs                # offline render check and screenshots
python metrics/lending_dashboard.py --block 53500000 --out /tmp/old && node dashboard/live_check.cjs /tmp/old
```

## How it stays current on its own

Three layers, each enough on its own:

1. **The page reads the chain when opened.** It renders the committed snapshot at once, then
   fetches every pool event since that snapshot's block from the logs RPC, the balance sheet
   and loan terms at the latest block from the state RPC, and any profile attestations, and
   re-renders. The topics and selectors come from the snapshot (`abi`), computed by the
   collector, so the page carries no hashing code. Both public RPCs answer browser requests
   (CORS). The header badge says "Live from the chain · block N · k new events since the
   snapshot". Where fetch is blocked (an offline file, a sandboxed copy) the badge says the
   committed snapshot is showing and the page stands as it was.
2. **A scheduled refresh.** A routine in the Claude session that owns this lane re-runs the
   collector every six hours, runs the checks, and when the ledger changed pushes the new
   snapshot to the hosted copy on the `pages` branch and republishes the shared artifact.
   The committed snapshot in this folder is refreshed with code changes.
3. **Hosting.** The page is served from this repository's GitHub Pages branch at
   `https://scottonchain.github.io/microcredit-agent-testbed/dashboard/`, beside the test
   wallet app. omnequa.org (served from the vision repository's `gh-pages` branch) can link
   to it or carry a copy.

The recorded RPC (`sepolia.base.org`) caps `eth_getLogs` at 200 blocks, so event history is
read from `https://base-sepolia.gateway.tenderly.co` (override with `--logs-rpc` or
`LOGS_RPC`); state is read from the recorded RPC at the same block, and the block hash is
re-read at the end so a reorg discards the snapshot. Cloudflare in front of
`sepolia.base.org` rejects Python's default user agent, so the collector sends its own.

## What the page shows

1. **The pool today:** assets, cash ready to lend, principal out, lent and repaid to date,
   interest kept by the pool.
2. **Lent out and paid back, cumulative:** a step chart from every disbursement and repayment,
   with a crosshair and a table view by month.
3. **Repayment outcomes:** loans by status, repayment rate, on-time count, median days to
   repay, first-time borrowers' share, borrowers with no stake of their own (METRICS.md 2, 3, 4).
4. **Who the money reaches:** consented profiles by country, occupation, purpose and income
   band; until the first attestation lands, the empty state names the schema and offers an
   example that is labelled as not on-chain.
5. **Scorecards:** reserve survival (net lender money in versus the pool today, share price,
   largest loan versus the one-fifth rule) and human benefit per sponsor dollar (attested
   versus unattested repaying borrowers, METRICS.md 1 and 8; "not measurable yet" until a
   consenting person borrows and the follow-up records what changed).
6. **The ledger:** every loan with its borrower address, principal, status, repaid, interest,
   closing date and explorer links.
7. **Backing, lenders and stakers; provenance and caveats.**

## Anonymized borrower profiles on-chain (the steward's part)

The pool contract has no profile field and is not changed. Profiles use the Ethereum
Attestation Service predeployed on Base Sepolia (and Base mainnet) at
`0x4200000000000000000000000000000000000021`, registry `0x…0020`, so nothing is deployed.

| Field | Type | Allowed values |
| --- | --- | --- |
| `loanId` | uint256 | the pool's loan id |
| `country` | string | ISO 3166-1 alpha-2, for example `GT` |
| `region` | string | first-level administrative area (a Guatemalan department, a US state) or empty; never a town, address or coordinates |
| `occupation` | string | one of a short published list of occupation groups (for example `market trader`, `smallholder farmer`, `tailor`, `food vendor`, `motorcycle taxi`), or empty |
| `purpose` | string | one of a short published list (`inventory`, `seed and fertiliser`, `equipment`, `repair`, `education`, `health`, `housing`, `other`) |
| `incomeBand` | uint8 | 0 not stated; 1 under 2.15 USD a day; 2 from 2.15 to 3.65; 3 from 3.65 to 6.85; 4 over 6.85 (World Bank poverty lines) |
| `consentVersion` | uint8 | version of the plain-language consent text the borrower agreed to |

Schema string, resolver `0x0` and `revocable = true` give the UID
`0x78e5c1a245b3903ea6b1bcb536e414ffe940b789941a4e9ec66d0afb28113199`
(`python metrics/lending_dashboard.py --schema-uid`; the registry computes the same hash,
so the page reads the right schema the moment it is registered). The attester is the
steward's credit-desk key, the recipient is the borrower's address, `refUID` is empty,
and the attestation is revocable: a borrower who withdraws consent has it revoked and the
page drops it.

**Privacy rule.** Values are coarse by construction and the steward attests nothing finer
than the table allows. A field is left empty when fewer than five borrowers in the pool
share its value, so no bucket identifies a person. The interview record itself stays with
the steward and never enters a repository or the chain. The data is permanent once
written, so coarsening happens before `attest`, never after.

**Recording procedure** (one transaction each, gas from the steward's testnet key):

1. Register the schema once: `SchemaRegistry.register(schema, 0x0, true)` with the schema
   string above.
2. At each credit check, with consent recorded, build the data with
   `encode_profile(loan_id, country, region, occupation, purpose, income_band, consent_version)`
   from the collector and call `EAS.attest({schema: uid, data: {recipient: borrower,
   expirationTime: 0, revocable: true, refUID: 0x0, data, value: 0}})`.
3. On withdrawal of consent, `EAS.revoke`.

Until step 1 happens the page shows "0 of N loans carry a profile" and the schema status
"not yet registered". That is the honest state, not an error.

## What this page is not

Base Sepolia, test USDC, no real funds, no real borrowers. Every loan so far was taken by an
AI agent or a team test account. A repaid testnet loan is evidence that the plumbing works,
not human benefit (NORTH_STAR.md). The dashboard counts attested human borrowers separately
and shows zero until there are some.
