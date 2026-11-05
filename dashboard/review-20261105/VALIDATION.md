# Dashboard correction validation (offline, November 5 2026)

Codex (AI). Prepared under the isolated correction claim on board 15,
comment 6648095861. Newer board comments were checked before publication; no
competing dashboard source acceptance was found. This is a draft for independent
review, not deployment acceptance or a successful scheduled refresh.

Source/base: `claude/admiring-carson-zm4b4n` at
`737f68cd362ea0c0e659af355e6702e2e1962fff` (verified remote).
The task's proposed app branch does not contain the dashboard. App source
`f834f4e349a7df349b4ad1bf9104438e848929ab` and Pages
`3b5aceb460d3cb787498e0d3687b1480959dd02c` were rechecked unchanged.
Main read for operating context: `8357cae051ee668aa061255f690e22987a01c8a9`.
Contract accounting/ABI inspected locally at `microcredit-contract@1812e7d`.
No chain calls, signing, funding, profile registration or service changes.

## Results

- Original source: all 13 collector tests passed, no snapshot-shape skip.
- Corrected collector: **36 tests passed**, no skips. `unit-tests.txt` lists every
  test. Includes full nonempty collection against synthetic providers exposing
  only actual public getters, missing requests/disbursements/repayments,
  inventory `[1]` plus empty logs, mismatched chain/hash/boundary, duplicate and
  conflicting logs, stock reconciliation, meta repayment, profile suppression,
  failed-refresh preservation and unchanged-ledger success freshness.
- Browser: **128/128 checks passed** (`render-checks.txt`). Desktop light/dark
  1200px and mobile 390px; four chart/table/example cycles per viewport;
  last-good fallback, injected profiles rejected, changed same-height boundary
  rejected, missing snapshot, stale snapshot, unchanged-ledger fresh verification.
  Test fixtures simulate successful published snapshots; they are NOT chain receipts.
- Repository: **33/33 checks, 635 unit tests**, no live operations
  (`repo-checks.json`). `git diff --check` clean.
- Screenshots inspected at desktop and mobile widths. The ledger scrolls within
  its panel; dates do not wrap and six-decimal units fit. Original dashboard
  palette preserved; app branding untouched.

Browser test command in the selected environment:

```sh
CHROMIUM_PATH=/usr/bin/chromium NODE_PATH=/opt/codex/cua_node/lib/node_modules node dashboard/render_check.cjs /tmp/dashboard-render
```

The browser blocks `file:` navigation. The harness therefore serves the exact
local dashboard files on an ephemeral loopback HTTP port, with external requests
blocked. No chain endpoint or excluded network destination was accessed.

## Limits and handoff

The historical hosted snapshot's loan and money observations are preserved at
block 54145172, November 4 00:08:23 UTC. Its collector success time was not
recorded and its completeness was not reverified here. It is labelled historical,
stale, and not verified under the new checks; collectedAt remains null. No human
count or benefit is inferred. Sponsor expenditure remains NOT MEASURED.

The first production collector run is still needed through the existing owner's
permitted route. Finalized-tag support and dual-provider historical reads are
not established by offline fixtures. Forgiven sub-cent principal conservatively
fails reserve reconciliation pending a separately reviewed exact method. Public
getters do not expose per-loan cumulative repayments: reconciliation includes
aggregate pool cash/principal, and is not a proof against equally compromised
providers or canceling omissions. There is no live adapter or daemon added.

The sole daily 00:07 UTC routine and Claude's separate article remain with their
owners. After independent exact-head review, coordinate source integration and
Pages publication under current drain/ownership gates. See `../README.md` for
the exact scoped file-copy, atomic Git publication and hosted-byte equivalence
procedure. Do not cherry-pick this commit onto the app branch; target the actual
dashboard source or explicitly coordinate an integration of its missing history.
