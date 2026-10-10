# Recorded deployments on Base Sepolia (chain 84532)

The current public deployment is the canonical test-USDC pool recorded in
[`current.json`](current.json). Both `quickstart.sh` and `metrics/pool_health.py`
read that descriptor and check the actual RPC chain and contract wiring. It is a
record of the October 6 deployment, not a new chain observation or permission to
deploy. Change it only with a reviewed deployment receipt. The source pin and
contract documentation are in the descriptor. `contract_commit` (`1812e7d`, on
contract `main`) is the deployed source. `contract_docs_commit` (`a23422a`) only
pins the documentation link; that commit is on the candidate branch, not `main`,
and its `docs/TESTNET.md` is identical to `main`'s (checked 2026-10-10).

| Current record | Pool | Asset | Source |
| --- | --- | --- | --- |
| October 6, 2026 | `0x73872B8fB7F1771C67911f03edc75aBdc9514973` | Circle Base Sepolia test USDC | [`base-sepolia-1812e7d-usdc001/`](base-sepolia-1812e7d-usdc001/) |

## Historical deployments

The records below remain reproducible and are not current application defaults.

All three run the same contract code (`9ab3729` and `main` `19b166e` differ only outside the contracts). The contract repo's history was rewritten on 2026-10-04 to remove private identifiers from commit messages, with file contents unchanged: the broadcast logs record the pre-rewrite ids `73cb3f6` (now `9ab3729`) and `19b166e` (now `19b166e`). The full record, with tx hashes and the scenario results, is `docs/TESTNET.md` in the contract repo.

| Deployment | Pool | Deployed by | Status | Broadcast logs |
| --- | --- | --- | --- | --- |
| Historical mock-token pool | `0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8` | Hermes, from `main` 19b166e, 2026-10-03 22:33 UTC | replaced by the canonical test-USDC pool on October 6; retained for existing positions and receipt reproduction | [`base-sepolia-19b166e-hermes/`](base-sepolia-19b166e-hermes/), also in the contract repo's `packages/foundry/broadcast/` |
| Reference run | `0xe3264D64cEF7C7675a548524D883b597e7894169` | Claude Code, from `73cb3f6`, 2026-10-03 21:00 UTC | not administered any more (its key is gone); kept as an independent run of the same scenarios | contract repo `packages/foundry/broadcast/*/84532/run-17910617…` and `run-17910621…` |
| Duplicate run | `0xad9dEA05FD0c63cf40e9D37da56B47AEFBB38973` | Hermes, from `main` 19b166e, 2026-10-04 00:21 UTC | complete and verified from chain state, but not the live pool | not captured: the files first published for it were copies of the reference run's logs and have been removed |

Hermes holds owner, oracle, score reporter and guardian on both of its deployments with `0x5e4dC7639D2b94006c51aD5373173f5e01c248F9`.
