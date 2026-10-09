# PR28 clean rerun at frozen head 3efdb6f (Hermes, AI) - preserved original outputs

AI disclosure: Hermes Agent (hermes-agent-909). This directory preserves the ORIGINAL, UNMODIFIED output of one run of
`scripts/candidate_evidence.sh` at contract repo head `3efdb6f2ed93bfdd19e8fd7f0a379868ca2e81b3`.
**It is NOT an acceptance packet.** The script's evidence gate failed (exit 1), so no gate-written `README.md` / `SHA256SUMS` exists.
Disposition belongs to Codex / Claude / the designated reviewer. HOLD unchanged.

Receipt: https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6076655696
Request: Codex https://github.com/scottonchain/microcredit-contract/pull/28#issuecomment-6076923762

## What ran
- Fresh clean git worktree of 3efdb6f (HEAD verified by `run_clean_3efdb6f.sh` before start; `logs/tree-status.txt` is empty = clean after).
- Script unmodified. forge 1.8.4 / cast 1.8.4 / anvil 1.8.4-dev (commit 50af4efe189dc64bad2b75ed6990b835de66c4ae), solc 0.8.33, via_ir, optimizer 200 (`logs/toolchain.txt`).
- Local Anvil forks of Base Sepolia only. No transaction to any public chain. Spend $0.
- START 2026-10-09T06:20:17Z, END 2026-10-09T07:38:55Z (`run_clean_3efdb6f.log`). Script exit 1.

## Files (original bytes; verified identical to the preserved local copies by sha256 before commit)
- `FAILED.txt` - original gate output, verbatim: `invariant-deep: 0 PASS lines, not all at runs 512 and calls 76800`
- `logs/exit-codes.txt` - per-stage exit codes: forge-test-local 0, forge-test-fork-routers 0, invariant-deep 0, mutants 0, python-tests 0, rehearsal-normal 0, rehearsal-with-default 0
- `logs/fork-block.txt` - full pinned fork block: `47881599 0xbdd034c324acf0d6095186f96a30c92b26cd86b947472b9a47de1ac5a909458c`
- `logs/verifier.json` - full verifier output including full masked hashes and ABI hashes
- `logs/invariant-deep.txt` - the log the gate could not parse (forge 1.8.4 prints `[PASS] invariant_X` with no counts, and the counts on a separate suite line)
- `logs/forge-test-local.txt`, `logs/forge-test-fork-routers.txt`, `logs/mutants.txt`, `logs/python-tests.txt`, `logs/rehearsal-normal.txt`, `logs/rehearsal-with-default.txt`, `logs/build-sizes.txt`, `logs/toolchain.txt`, `logs/tree-status.txt`
- `HERMES_SHA256SUMS.txt` - MY OWN checksum index over the logs and FAILED.txt (labelled Hermes; not the gate's SHA256SUMS and carries no acceptance meaning)
- `run_clean_3efdb6f.sh`, `run_clean_3efdb6f.log` - wrapper (head check, PATH to the pinned binaries) and its transcript; host paths replaced by <WORK>, <ANVIL_DIR>, <FOUNDRY_1.8.4>, <PATH> (the only sanitized files)

## Sanitization
Log files and FAILED.txt were copied byte-for-byte (no host paths, keys or wallet files were present in them; checked by grep for `/root/`, private-key and mnemonic markers). Rehearsal tx hashes are Anvil-fork local.

## Preservation
The original local directory (/root/work/repro28/out-3efdb6f on the runner host) is untouched and will not be rerun over. Any parser-only re-evaluation should use a separate copy.
