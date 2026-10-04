# Deployments of the redesigned pool on Base Sepolia (chain 84532)

All three run the same contract code (`73cb3f6` and `main` `489f01a` differ only outside the contracts). The full record, with tx hashes and the scenario results, is `docs/TESTNET.md` in the contract repo.

| Deployment | Pool | Deployed by | Status | Broadcast logs |
| --- | --- | --- | --- | --- |
| Live | `0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8` | Hermes, from `main` 489f01a, 2026-10-03 22:33 UTC | **the pool agents test**; every doc, config and issue points here | [`base-sepolia-489f01a-hermes/`](base-sepolia-489f01a-hermes/), also in the contract repo's `packages/foundry/broadcast/` |
| Reference run | `0xe3264D64cEF7C7675a548524D883b597e7894169` | Claude Code, from `73cb3f6`, 2026-10-03 21:00 UTC | not administered any more (its key is gone); kept as an independent run of the same scenarios | contract repo `packages/foundry/broadcast/*/84532/run-17910617…` and `run-17910621…` |
| Duplicate run | `0xad9dEA05FD0c63cf40e9D37da56B47AEFBB38973` | Hermes, from `main` 489f01a, 2026-10-04 00:21 UTC | complete and verified from chain state, but not the live pool | not captured: the files first published for it were copies of the reference run's logs and have been removed |

Hermes holds owner, oracle, score reporter and guardian on both of its deployments with `0x5e4dC7639D2b94006c51aD5373173f5e01c248F9`.
