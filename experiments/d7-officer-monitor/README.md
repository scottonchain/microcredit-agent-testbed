# Chain-only officer monitor (source only)

`reader.mjs` block-bound read of the CreditDesk pending queue (strict ABI decoding, hash recheck, per-provider snapshots);
`adapter.mjs` chain-only check, the one fixed-shape board message and its sender-side validator; `run-chain-monitor.mjs` and
`validate-comment.mjs` CLIs (print or check only, post nothing); `draft-workflow/officer-chain-monitor.yml` INACTIVE draft;
`dedup.mjs` the pure post/skip/halt decision and the read-back validator, `decide-post.mjs` its CLI (prints `post=` and `reason=` only), `DEDUP_DESIGN.md`;
`test-monitor.mjs` offline tests (`node test-monitor.mjs`, 256 checks) and `test-dedup.mjs` (`node test-dedup.mjs`, 198 checks); `fixtures/abi-samples.json` ABI result samples; `CHAIN_MONITOR.md` the
design, the scoped operating-owner acceptance request and the NOT covered list; `monitor-config.example.json`.
Needs `../d7-officer-collector/` (PR 473). No key, wallet, signer, workflow activation, deployment or live run. Not an officer runtime
acceptance and not a merge route.
