# Chain-only officer monitor (source only)

`reader.mjs` block-bound read of the CreditDesk pending queue (strict ABI decoding, hash recheck, per-provider snapshots);
`adapter.mjs` chain-only check, the one fixed-shape board message and its sender-side validator; `run-chain-monitor.mjs` and
`validate-comment.mjs` CLIs (print or check only, post nothing); `draft-workflow/officer-chain-monitor.yml` INACTIVE draft;
`test-monitor.mjs` offline tests (`node test-monitor.mjs`, 244 checks); `fixtures/abi-samples.json` ABI result samples; `CHAIN_MONITOR.md` the
design, the scoped operating-owner acceptance request and the NOT covered list; `monitor-config.example.json`.
Needs `../d7-officer-collector/` (PR 473). No key, wallet, signer, workflow activation, deployment or live run. Not an officer runtime
acceptance and not a merge route.
