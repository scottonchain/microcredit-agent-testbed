# Three cold-start fork rehearsals

Status: prepared and checked offline. No scenario results are claimed by this code publication.

This helper exercises the existing public-app Base Sepolia pool, its score provider and canonical test USDC, copied into a fresh, isolated Anvil fork. It deploys nothing and changes no token balance, storage or runtime code through development overrides. It cannot target a public RPC: only `http://127.0.0.1:<port>`, Anvil, chain 31337, an unmodified pinned starting block, and independently recorded runtime fingerprints are accepted.

These are supplemental rehearsals, not the requested live testnet runs. On the live chain the scenario wallets remain controlled by Codex; private keys and signed transaction bytes are absent here. Local impersonation applies only to those public actor addresses and the existing Hermes reporter address inside the fork.

## Roles and cases

Each case has a distinct funder, two borrower roles and a controlled expense wallet. Separate subagents supplied conditional decisions before execution.

1. A worker borrows 1 USDC against an accepted simulated task invoice; the task payment comes from the controlled treasury.
2. A cash-poor borrower accepts only after a peer commits its entire 1-USDC endowment. That peer, with no loan of its own, repays directly.
3. A scripted pair attempts ordinary over-limit, repeated-request and onward-backing calls; expected rejection selectors are recorded through read-only calls. Proceeds are transferred to the second actor, which repays under supervisor control. Refusal is not an on-chain default.

Every funder deposits 5 USDC and receives a temporary 1-USDC line from the existing reporter, then backs one borrower. Deposits themselves grant no credit. Each ordinary loan repays its entire principal strictly inside the first-day grace window. The runner removes backing, withdraws all funder shares, clears and releases temporary issuance, and sweeps every actor's USDC to the treasury. Each boundary checks the exact initial aggregate USDC, original pool financial state, unrelated lender position and Avery's score/budget. ETH pays gas separately. Completed-loan counters change; earned dues remain zero.

The initial root aggregate may be 15 USDC or 20 USDC. The 20-USDC variant includes Hermes's temporary 5-USDC source contribution, with the original pool temporarily reduced from 20 to 15. Fork recovery does not return that live contribution or restore the live source position.

## Run on an authorized RPC host

First read a fresh canonical source block and record its hash plus the exact runtime bytes of all three contract addresses at that same block. Compute SHA-256 and Ethereum Keccak-256, using an independently trusted tool such as `cast keccak` for the latter. Save this public file:

```json
{
  "source_chain_id": 84532,
  "fork_block_number": 47819361,
  "fork_block_hash": "0x...actual source block hash...",
  "contracts": {
    "DecentralizedMicrocredit": {"address": "0x73872b8fb7f1771c67911f03edc75abdc9514973", "sha256": "...", "keccak256": "0x..."},
    "OracleScoreProvider": {"address": "0x554c6bb61edf0cafb90ff31813540369cb0105e4", "sha256": "...", "keccak256": "0x..."},
    "USDC": {"address": "0x036cbd53842c5426634e7929541ec2318f3dcf7e", "sha256": "...", "keccak256": "0x..."}
  }
}
```

Use the observed block, not the example above. Bind Anvil to loopback and assign chain 31337 explicitly:

```bash
anvil --host 127.0.0.1 --port 8547 --chain-id 31337 --fork-url https://sepolia.base.org --fork-block-number OBSERVED_BLOCK --disable-min-priority-fee
python3 run.py --self-test
python3 run.py --rpc http://127.0.0.1:8547 --fork-block OBSERVED_BLOCK --expected-code-hashes source-code-hashes.json --output NEW_EVIDENCE_DIRECTORY
```

On the executed Anvil 1.8.4 fork, the default minimum priority fee made `eth_gasPrice` exceed the one-gwei guard; `--disable-min-priority-fee` lets the helper use the copied chain's fee without relaxing that guard. This is a local-node setting, not a public-network workaround.

The fingerprint file is mandatory and its source block hash is checked even without the optional `--fork-block-hash` argument. The compiled-artifact comparison is supplementary: compiler metadata and constructor immutables can differ, so the independently pinned live fingerprints determine identity.

Do not put private keys, signed transactions, account data or credentials in the evidence directory. Return `evidence.json`, each boundary snapshot, runtime fingerprints, and the append-only `journal.jsonl` to the coordinator. Keep every result explicitly labelled `mode: fork`. On failure stop and inspect the journal; use a fresh isolated fork for a corrected run. Do not change the deployed contract or inject balances to force a pass. Shut down the local node after collecting evidence.

## Limits

Controlled payments and aid are subsidies, not observed outside income. Shared custody enables compulsory cleanup, so repayment is not evidence of independent honesty. No default, time travel, interest-earning repayment or short-payment write-off is executed. These three cases rehearse first-loan mechanics; they do not establish borrower demand, fraud equilibrium or an effect on poverty.
