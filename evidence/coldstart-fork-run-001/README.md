# COLDSTART-FORK-RUN-001 evidence (fork, chain 31337)

Executed by hermes-agent-909 (AI) on the Hermes host, 2026-10-07 ~21:30-21:34 UTC.
Helper: testbed commit a5a4d951df7e18056dd870db16fd642331f0e8e8 (PR #34), `scenarios/cold-start-three-communities/run.py` unmodified.
Mode for every result: **fork, chain 31337** (local Anvil 1.8.4 static alpine build, bound to 127.0.0.1, forked from https://sepolia.base.org). No live fund moves, no key, no signed bytes, no faucet. Node shut down afterwards.

## Pinned source (Base Sepolia 84532), read before the run
- fork block 47820167, hash 0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078, timestamp 1791408622 (2026-10-07T21:30:22Z)
- code hashes: `source-code-hashes.json` (sha256 + keccak256 via `cast keccak`, read at that block): pool keccak 0xcbec266a...a9dc8, provider 0x4002d1cc...0c3a3, USDC 0xedc5281a...59d6c. Fork runtime hashes in attempt-3-passed/runtime-code-hashes.json match.
- root wallets at that block (`roots_at_block.json`): treasury 0x5225...1575 = 15 USDC, nonce 1; funder 0xab7a...980c = 5 USDC, nonce 0; every other scenario wallet 0 USDC, 0 ETH, nonce 0. Root aggregate 20 USDC (the 20-USDC variant; pool original 15 USDC).

## Attempts (3, same block, three fresh forks)
1. Stopped by the helper's own gate: `Gas price above one gwei; stop for bounded gas review`. Anvil's fork `eth_gasPrice` returned 0x3be6cc82 (1.005 gwei) because the base fee at the block is 0.005 gwei and Anvil adds a 1 gwei minimum priority fee. Journal shows only fork_guard, snapshot, impersonation, failure. No scenario transaction mined. (attempt-1-stopped-gas-guard/)
2. Same stop with `--gas-price 6000000` (that flag does not change eth_gasPrice). (attempt-2-stopped-gas-guard/)
3. Passed with Anvil flag `--disable-min-priority-fee` (eth_gasPrice 0x4c0282 = 0.005 gwei). Helper code unchanged, gate not relaxed. (attempt-3-passed/)

Command for attempt 3: `anvil --host 127.0.0.1 --port 8550 --chain-id 31337 --fork-url https://sepolia.base.org --fork-block-number 47820167 --disable-min-priority-fee --silent`, then `run.py --rpc http://127.0.0.1:8550 --fork-block 47820167 --fork-block-hash 0x2189...2078 --expected-code-hashes source-code-hashes.json --output <dir>`.
Suggested helper note: README's anvil command should include `--disable-min-priority-fee` (or the gate should read base fee).

## Result of attempt 3 (evidence.json)
status passed, 3 scenarios, 59 mined local txs, initial and final root aggregate both 20,000,000 units (20 USDC), no_live_fund_moves true, journal tip sha256 5c24b450739181a596ebd5a848b1a9d5dd62ef695c95b4d44bb2b262eb48961a. Loan ids from mined receipts: scenario 1 = 18, scenario 2 = 19, scenario 3 = 20. Scenario 3 negative checks (read-only eth_call) matched expected selectors: 0x8ac4bc73 (second hop), 0x5d615d32 (over-limit, reservation), 0x315b0e14 (no credit), 0x9917947d (backing removal with open reservation). Gas topups from treasury 0.011 ETH (fork only), gas spent 2.59e13 wei.

Limits as stated by the helper: one operator controls all actors, subsidies are internal transfers, no default/time travel/short payment. Fork results; they say nothing about live Base Sepolia state, which was not changed.
