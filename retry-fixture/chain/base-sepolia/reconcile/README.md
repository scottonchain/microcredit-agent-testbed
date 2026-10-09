# Maintained journal reconciliation

The current checker requires transaction-level evidence for a landed verdict.
A whole-block nonce change cannot make a reverted transaction land; wrapped
requests need a unique matching pool event. A consumed nonce with no receipt
remains ambiguous unless the identical signed bytes are established by an
existing receipt. A local journal cannot prove that no other signed intent
exists. `--json` creates a new sidecar and refuses to overwrite an existing one.

```bash
python -m unittest discover -s retry-fixture/chain/base-sepolia/reconcile -p 'test_*.py'
```

These regressions use published calldata and mocked reads. They do not read the
chain or send transactions. The historical record below describes the original
nonce-only checker and its run; its saved verdicts have not been rewritten.
`negative_control_journal.py` uses the maintained stricter verdicts for new runs.

## Historical record

# Journal reconciliation: the recovery rule as code, run over the live runs' own journals

Date: 2026-10-05 ~09:30 UTC (ours). Network: Base Sepolia (chain id 84532), fake money. No key is needed by anything here.

`cases.json` says, for chain-4, "check the nonce, not the loan; if it moved, find the transaction; do not resubmit or re-sign", and
for chain-7 (merktop's words, comment 2ba3808e) "settled by journal plus nonces(signer) ... 'unknown' strictly for the missing-journal-row
case". Until now that rule was a sentence and a forge test. `reconcile_journal.py` is the sentence as a program, and the two files
`JOURNAL_*.jsonl` are the intent journals the two live runs in `..` actually left behind (`lib.py` writes an `intent` row before every
broadcast and a `broadcast` row with the tx hash after it; `estimate_gas_failed` rows are diagnostics). They were not published with
the runs; they are now, unedited.

## What is here

- `reconcile_journal.py`: standard-library Python, JSON-RPC only. `python3 reconcile_journal.py JOURNAL_live_pool.jsonl [--pool ADDR]
  [--rpc URL]`. Pairs each `intent` row with the `broadcast` row that completes it (same destination, most recent unreceipted row), then
  settles every signed intent the calldata carries (direct `repayLoanMeta` / `borrowAndDisburseMeta`, or one level down inside
  `forward(address,bytes)` and `batch(address,bytes[])`) by `nonces(signer)` read from the chain: at the receipt's block for a receipted row
  (`[before, after)` names the landed nonce), at `latest` plus elimination over the other journal rows for a row that has no hash. It trusts
  nothing in the journal: a receipted row's calldata is compared with the chain's `tx.input`. Verdicts: `landed`, `not landed`, `ambiguous`
  (several unreceipted rows with different bytes carry one consumed nonce: a re-signed intent after a revert reuses the nonce the revert
  gave back, and `nonces(signer)` alone cannot say which landed), `mismatch` (journal bytes differ from the chain), `unknown` (a consumed
  nonce that no journal row landed: the missing-journal-row case). Rows without a signed intent (owner call, mint, contract creation) are
  settled by receipt only and listed. Exit 0 only if nothing is ambiguous, mismatched or unknown.
- `JOURNAL_live_pool.jsonl` (second run, live pool `0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8`): 28 rows = 13 intent, 13 broadcast,
  2 `estimate_gas_failed`. `RECONCILE_OUTPUT_live_pool.txt` (CPython 3.14.7) and `RECONCILE_OUTPUT_live_pool_cpython39.txt` (CPython
  3.9.25): 10 signed intents, landed 6, not landed 4, ambiguous 0, mismatch 0, unknown 0; exit 0; outputs identical apart from the header.
  The four `not landed` are chain-1's replay (reverted, nonce 1 unmoved), chain-2's fresh signature (reverted, nonce 2 unmoved), chain-7a's
  wrapped intent (envelope status 1, nonce 5 unmoved) and chain-7b's second intent (nonce 6 unmoved while nonce 5 moved). Each verdict is
  the expected state of its case, derived from the journal and `nonces(signer)` alone; the verifier in `..` is not consulted.
- `JOURNAL_first_run.jsonl` (first run, pool `0x09d9D1fd4Ed5EC5d9e8ceB9275D864D9c8d99A1f`): 18 rows, no step names. Its first row (the
  s5 intent) is at 07:38:05Z, between step s4 (recorded 07:38:04Z in `../EVIDENCE.json`) and step s5 (07:38:09Z): the journal did not exist
  yet when steps s0-s4 were sent (`lib.py` was being changed during that run, see `../README.md`), so those five transactions have no
  rows. `RECONCILE_OUTPUT_first_run.txt`: landed 4, not landed 4, `UNKNOWN` for nonces 0 and 1 (consumed on chain by the unjournaled
  borrow and first repay; no journal row landed them), exit 1. That is the missing-journal-row branch of chain-7's expected state, which
  `../README.md` listed as not run live: it is exercised here by our own incomplete journal, not by a constructed one, and the program says
  `unknown` rather than guessing. The same file also shows the wrapper call's first attempt, whose gas estimation failed and which was never
  broadcast (an intent row with no hash, then the intent re-signed and receipted as the next row): the unreceipted row is settled
  `not landed` because the receipted row landed that nonce, and the contract consumes a nonce exactly once.
- `negative_control_journal.py` / `NEGATIVE_CONTROL_journal.txt`: six journals the second run could have left behind, each with the verdict
  the rule assigns: s3's hash row lost (crash after broadcast) -> `landed` by elimination, exit 0; s3 and s4 (identical bytes) both without
  hash -> one intent resubmitted, `landed`, exit 0; s5 and s7 (different bytes, both nonce 2) both without hash -> `ambiguous`, exit 1; s7's
  rows missing entirely -> `unknown` for nonce 2, exit 1; one byte of s8's journaled calldata changed -> `mismatch`, exit 1; an intent row
  at nonce 6 that was never broadcast -> `not landed` (nonce not consumed; a resend could not double-execute), exit 0.

## What it adds to the cases, and what it does not

- chain-4 / chain-7: the recovery rule is executable and was run over real journals of real transactions, with the outcomes above. Status
  stays `tested by us` (the runs and the journals are ours).
- One refinement of the chain-side reading (ours, not merktop's words, so the `expected` text is unchanged): "journal plus nonces(signer)"
  settles an unreceipted row only when the journal keeps the calldata (or its digest) as well as (signer, nonce). After a revert the next
  intent legitimately reuses the nonce (chain-2's fresh signature and the following borrow both carry nonce 2 in the second run); two such
  rows without receipts are `ambiguous` by nonce alone and need the transaction (input or logs) to settle. A journal keyed by (signer, nonce)
  only would mis-settle that case.
- Limits: one signer, one relayer, our own journals; the test-helper envelopes (`forward`, `batch`) are the only wrappers decoded; a reorg
  between the journal write and the read is not covered; `latest` reads are not pinned to a block (a verdict for an unreceipted row is as of
  the node's head). Public nodes may prune the historical state the receipt-block reads need; then the script fails loudly, it does not guess.
