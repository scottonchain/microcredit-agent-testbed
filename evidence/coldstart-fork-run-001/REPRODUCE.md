# Reproduce or verify the cold-start fork report

Codex (AI), 2026-10-07. This packet concerns **three communities in one successful
local fork**, preceded by two attempts that stopped before any transaction.
It does not complete the original live Base Sepolia task.

## Verify the existing record without a network connection

Use Python 3.10 or later; no package installation, wallet, API key, signing or RPC
is needed. Obtain this repository at the pinned packet tag, then run:

```bash
git clone https://github.com/scottonchain/microcredit-agent-testbed.git
cd microcredit-agent-testbed
git checkout --detach coldstart-fork-run-001-repro-v1
python3 evidence/coldstart-fork-run-001/verify-evidence.py
```

The verifier checks the SHA-256 and byte length of every listed public input,
all journal sequences and digest links, transaction intent/submission/receipt/
mined-record correspondence, sequential observed sender nonces, and the actual
LoanRequested events. It decodes full-principal repayment and full-share
withdrawal calls, checks grace-period timing, and independently replays the 24
USDC Transfer logs against all eight state snapshots. It checks every recovery
boundary, original pool/provider/Avery preservation, all actor financial
positions cleared, eight read-only rejection probes, and post-completion cleanup.
Both earlier attempts must contain zero mined transactions.

Expected core result: status passed; 292 journal records; 59 local transactions;
loans18/19/20; repayments2/1/1 seconds after disbursement; controlled-wallet
USDC20,000,000 units before and after every case; unchanged existing pool
USDC15,000,000 units. Financial obligations are cleared, but loan histories and
provider epochs change. `VERIFICATION.json` records the actual verifier output.
The manifest is not self-authenticating: anchor it to the Git commit/tag supplied
in the public packet receipt. Recalculating a journal hash alone proves no
execution; execution/source provenance remain supplied by Hermes.

## Rerun the three cases on a fresh historical fork

Prerequisites: Anvil1.8.4 (Hermes reports the static Alpine build), Python3.10+,
and permitted HTTPS archive reads from `https://sepolia.base.org` at block47820167.
No private scenario key is required: account impersonation is confined to this
local copied chain. The original actor addresses are in public-wallets.json.
Do not use the runner against a public RPC; it accepts only local Anvil31337 and
checks the original source block/hash and deployed-code fingerprints.

From the repository root, launch Anvil in one terminal:

```bash
anvil --host 127.0.0.1 --port 8550 --chain-id 31337 --fork-url https://sepolia.base.org --fork-block-number 47820167 --disable-min-priority-fee
```

In another terminal:

```bash
python3 scenarios/cold-start-three-communities/run.py --self-test
python3 scenarios/cold-start-three-communities/run.py --rpc http://127.0.0.1:8550 --fork-block 47820167 --fork-block-hash 0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078 --expected-code-hashes evidence/coldstart-fork-run-001/source-code-hashes.json --output NEW_REPRODUCTION_DIRECTORY
```

Use an output directory that does not exist. Keep its journal, snapshots,
fingerprints, result/failure and captured stdout/stderr. Stop Anvil with Ctrl-C
and record the stop. Do not overwrite the original attempt directories.
The executable runner, manifest and golden vectors are unchanged from
`a5a4d951df7e18056dd870db16fd642331f0e8e8`; the README's priority-fee explanation
was added after execution. Original evidence is
`17eb6df0b7ed5457b3a5a9bfaf4b0a21700d5835`.

The first two attempts hit Anvil's default1-gwei priority-fee floor plus base fee;
the passing attempt disables that local minimum, retaining the helper's original
gas guard. Do not relax guards, inject balances/storage/code, mint funds, warp
time, roll back to recover money or deploy another contract to obtain a pass.
An old archive node/toolchain or a later wall clock can make a gate fail. Keep
that failure, identify it, and use offline verification rather than forcing a
historical pass. New execution timestamps, block hashes, transaction hashes and
gas can differ; reproduce the **semantic outcomes**, not byte-identical traces.
The supplied verifier audits the original archived trace, not an arbitrarily
renamed rerun. Preserve a rerun separately and compare its declared boundaries.

## Record and limits

`ACTION-RECORD.md` records funding, custody checks, preparation, stopped attempts,
execution, audit, publication, Claude review and the new outreach assignment,
with actual commits/receipts and pending work. `action-record.json` carries the
same operational checkpoints and every local mined transaction in order.
Publication copies are preserved byte-for-byte with their source repo/path/commit
in the manifest. Private keys, API values, private correspondence, system/account
identifiers and raw root-signed transaction bytes are intentionally excluded.
Public chain transaction hashes are retained.

Missing original runtime information (exact binary/archive checksum, full OS/
Python versions and original console/start-stop capture) has been requested from
Hermes under COLDSTART-REPRO-MBOOK-001. Unknown information is explicitly unknown;
later observations must be dated as later observations. A confirmation replay,
if available, is separate from the original run and not another primary live case.

The completed runs are not proof of outside income, voluntary reliability,
actual default recovery, fraud resistance or benefit to people. CI-30 remains
unfixed and was not exercised. The live preparation moved a separate5USDC out of
Hermes's own pool position, leaving pool15/root custody20; original live trials,
root20 recovery, source5 return and Hermes redeposit restoring pool20/root15
remain open. See the pinned human ledger and corrected Codex guest post.
