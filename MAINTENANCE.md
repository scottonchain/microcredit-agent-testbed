# Maintained code and recorded evidence

Run the maintained checks from the repository root with Python 3.10 or newer:

```bash
python -m pip install -r world-model/requirements.txt
python tools/check.py
```

`tools/check.py --list` lists the checks. `--json` returns their results and test
counts. GitHub Actions runs the same command for every pull request and push to
main. Every listed suite is required; a missing directory or an empty suite fails
the gate. The command has no live sends, wallet access, RPC reads or privileged
archive execution. Individual suites run in separate processes so the older
flat modules named `model`, `lib` and `q` cannot shadow one another.

## Where maintained behavior belongs

| Need | Maintained source | Verification |
| --- | --- | --- |
| Current recorded deployment | [`deployments/current.json`](deployments/current.json) | Descriptor validation; workspace address checks in `coordination/`; runtime chain, token, provider and lens checks |
| Pool quickstart | [`scripts/quickstart.py`](scripts/quickstart.py), reached through `quickstart.sh` | Exact amounts, keyless reads, receipt-derived loan IDs and failed-send controls in `scripts/test_*.py` |
| Shared Foundry calls and token amounts | [`scripts/deployment.py`](scripts/deployment.py) | No automatic resend after an unknown outcome; no floating-point transaction amounts |
| Pool health | [`metrics/pool_health.py`](metrics/pool_health.py) | One block for all reads, recorded block identity, reorg rejection and nonzero exit on a conservation violation |
| Planning and coordination | [`world-model/`](world-model/README.md), [`coordination/`](coordination/team-structure.md) | Schema, relationship and ownership checks; coordination unit tests |
| Compact team messages | [`team-mail/tm2.py`](team-mail/tm2.py) and [`team-mail/SPEC.md`](team-mail/SPEC.md) | Published examples and malformed-input controls |
| Offline accounting rehearsal | [`bootstrap/`](bootstrap/README.md) | Provenance, unknown usage, malformed receipts and simulated settlement controls |
| Retry behavior | [`retry-fixture/reference/`](retry-fixture/README.md), `validate_cases.py` | Reference/mutant scenarios and the case-ledger validator |
| Historical chain verification | `retry-fixture/chain/base-sepolia/chain_read.py`, `verify_live_run.py`, `reconcile/reconcile_journal.py` | Shared read-only RPC and bounded ABI decoding; published calldata plus outcome-attribution controls |
| Replay verification tools | [`research/calibration-v3-replay-archive/`](research/calibration-v3-replay-archive/README.md) | Offline release identity/digest controls and stubbed isolation gates |
| Bounded fork scenario | [`scenarios/cold-start-three-communities/`](scenarios/cold-start-three-communities/README.md) | `run.py --self-test` checks ABI vectors, local-only routing, exact shares and the journal without RPC |

New operational helpers should use these modules instead of copying addresses,
amount parsing, RPC retries or validators. The deployment descriptor is a record
of deployed code; it does not mean the current contract source has been deployed.

Retry effect scripts share their S1–S4 setup and score labels in
`retry-fixture/reference/gate_readings.py`. Each effect's `evaluate()` supplies its
CLI and the scorecard with the same cells and expected-table checks. The scorecard
runs those evaluators directly, so it needs no child-process/JSON bridge. Existing
CLI paths and published results remain usable; each effect keeps its own policy
and horizon.

## Sources retained for reproduction

The repository also contains immutable or dated material. It is intentionally
kept separate from current runtime defaults:

- `calibration-v1/`, `calibration-v2/` and `calibration-v3/` preserve their published
  corpus, generator, scorer, commitments and offer terms. Some scorer and leak
  checker files are byte-identical. Sharing an implementation now would break
  the original hashes and independent reproduction, so they stay pinned. The
  check command verifies v3's ledger and conformance fixture in a temporary
  directory; it never regenerates a committed corpus.
- `evidence/` preserves source captures, exact-run implementations, outputs,
  receipts and transaction hashes. Code copied there is evidence of what ran,
  not another supported implementation to edit in place.
- `deployments/<deployment>/` and the dated `experiments/` tree are recorded runs.
  The source can be inspected, but live execution must use its own reviewed
  run-specific instructions. Cleanup does not rerun or republish it.
- `retry-fixture/live/` holds historical provider probes and their records. The
  three `check_*.py` commands recompute those observations offline and are in the
  check command. The other scripts send or read from the external provider and
  are outside ordinary verification.
- Historical chain send/probe scripts retain the October 3 MockUSDC deployment
  because that is what their receipts describe. They are not the current public
  quickstart. Their shared sender now makes only one broadcast attempt and
  records ambiguous outcomes for reconciliation.
- Other calibration research scripts reproduce specific published analyses;
  their archived numbers are not recalculated as current product metrics. The
  replay archive builder is a reproduction source, not a release-building path
  for changing the published archive.

All tracked Python and shell sources, including these historical copies, are
syntax-checked without imports. An offline test pass establishes those tests'
results; it does not establish a fresh chain observation, a new deployment,
external revenue or human benefit.

## Changes to outcome reporting

The maintained journal reconciler no longer treats a whole-block nonce change
as proof that every transaction in that block landed. A reverted transaction
stays not landed. A wrapped request needs a unique matching pool event as well
as its consumed nonce. A missing transaction receipt leaves consumed signed
bytes ambiguous unless identical bytes have already been established by a
receipted intent. The local journal cannot prove its own completeness. Historical
reports retain their original results and source pins; new runs use the stricter
verdicts. No automatic retry follows an ambiguous result.
