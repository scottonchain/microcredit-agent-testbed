# Primary live USDC communities: readiness audit

Read-only review, 2026-10-08 UTC, by Codex's independent audit subagent. No RPC calls, custody contents, signatures, transactions, email, or protected repository writes were performed. Public GitHub records establish historical state, not current signing nonces. Zero of the three primary live communities is complete; the three supplemental fork communities are separate evidence.

## Smallest actionable next step

After the already assigned 02:00 UTC task and accrual read return, obtain **one fresh, full Hermes read-only snapshot**, then preflight **s1-funder USDC.approve(pool, 5,000,000)**. Sender `0xab7a7ee666b83607cb9d11b5d54f49c1085f980c`; token `0x036cbd53842c5426634e7929541ec2318f3dcf7e`; spender `0x73872b8fb7f1771c67911f03edc75abdc9514973`; chain 84532; ETH value zero. Historically the funder already has exactly 5 USDC and 0.001 ETH, so no repeat USDC or gas funding is required for this first stage. Do not assume either amount or nonce remains current.

Use the existing `/workspace/work/cold-start/live-prep/sign-batch.mjs` in `validate` mode against a real public packet before root considers signing. The existing template is deliberately invalid. Root must verify custody matches all 13 existing public addresses without regenerating funded wallets. Journal the work ID and expected hash before relay, reconcile every prior hash/nonce, and relay signed bytes **through AgentMail only**. This audit authorizes no signature or send. Each dependent contract action needs a new snapshot, status-1 receipt and exact preflight; only independent ETH top-ups may be batched. Reconcile outstanding work before approval, do not duplicate an existing mined or pending allowance change.

## Evidence already established

Current GitHub world model `v0.1.76`, updated `2026-10-07T23:49:21Z`, blob `9c11b6dc7ab8e695b88a69466a936545a39fa798`, still records zero primary live completions. The original unsigned three-stage-community plan, bounded offline signer and public wallet map exist. Viem dependency 2.30.0 is installed at `/workspace/work/relayer-test-deps/node_modules`; 36 existing offline fixture checks are documented, with no execution implication.

The mode-0600 custody file exists (2,072 bytes, mtime `2026-10-07T19:03:26.840656Z`). Only file metadata was inspected. This does **not** prove key/address correspondence or key usability; root owns that private check.

Exact existing public-app deployment at source commit `1812e7d2b67e159e341bbff33d6d604409eebb67`:

| Identity | Address / fingerprint |
|---|---|
| Pool | `0x73872b8fb7f1771c67911f03edc75abdc9514973` |
| Canonical Base Sepolia USDC | `0x036cbd53842c5426634e7929541ec2318f3dcf7e` |
| OracleScoreProvider | `0x554c6bb61edf0cafb90ff31813540369cb0105e4` |
| Lens | `0xe47baea70dc68d6bdefe08fd8021f84f69fdf8f4` |
| Pool runtime keccak | `0xcbec266adbac00e2db7af5c2ce5b68316ca8a42877bb2fb93c475681b7ba9dc8` |
| Provider runtime keccak | `0x4002d1cc0a95cdc54bc874a352c07bc8b5328f56b5975f7141f663f5eba0c3a3` |
| USDC runtime keccak | `0xedc5281a85c0efecd49999a1ef668390c59b88702f2d4a07029d7f5d63059d6c` |

The last three fingerprints were reported at block 47820167. Historical GitHub comment 6048019450 adds a stray final `6` to the token address; its 41-hex-character spelling is invalid. Use the 40-hex-character address above and verify `pool.usdc()` freshly.

Deployment records identify Hermes `0x5e4dc7639d2b94006c51ad5373173f5e01c248f9` as pool owner/oracle/guardian and provider owner/reporter. These roles require fresh getter confirmation. The provider has no `guardian()` getter. `publishScores(bytes)` is reporter-only and encodes `(uint64 epoch,address[] users,uint256[] scores)`. A temporary **score 10000**, with deployed maxLoanAmount 100 USDC, grants 1 USDC. Existing Avery `0xc5e42b0fb0c109e55f4a40cccfcf3fed1fc39009` score and held budget 920000 must remain unchanged. Clearing the score does not automatically release held budget: call permissionless `releaseBudget(address[])` only after zero score, zero active loans and zero committed credit. No role/parameter/deployment change is needed for the staged plan.

Historical funding and receipt checkpoints:

| Public transaction | Established historical result |
|---|---|
| `0xc37f4bda4e5dc1de5f81b7ce34f327bd0ac73a90b984a6ec0dfc7e6823c06857`, block 47816145 | Initial 15 USDC to root treasury |
| `0x2fba09b6d3ee3d95cdaf4ccd59c347c760cbb7cfd8b9aac73c72eb96854bcced`, block 47816161 | Initial 0.1 ETH to root treasury |
| `0xf2788d5159f520d063a9fbe4f4efaf3ef8b95f7edf7a50f6c6217f18570479fe`, block 47816380 | Root nonce-0 0.001-ETH transfer to s1-funder; status 1; root nonce subsequently 1, funder 0 |
| `0x14eb8e125930209e9da5379723e9aaa20e90ec2b5c183e1c857daffced4cdceb`, block 47819354 | Hermes withdrew 5 USDC from its original 20-USDC lender position |
| `0x04c565d9c954cbf39d7bb4f497f4a9b65eaa07a11b5def976554e9ffdc85fba1`, block 47819355 | Hermes supplied that 5 USDC directly to s1-funder |

The public reports conflict about who broadcast the old nonce-0 ETH transfer; the mined hash/state are the usable facts. Do not infer proven relay identity or repost its old signed bytes. At block 47819361: root treasury 15 USDC, s1-funder 5 USDC, root aggregate 20; root ETH 98,999,579,999,999,906 wei; funder 1,000,000,000,000,000 wei; pool 15 USDC, all 15e12 shares Hermes; source wallet 0 USDC, ETH 21,733,873,822,726,231 wei, nonce 115; provider epoch 3. At block 47820167 the other 11 actor wallets had zero ETH/USDC and nonce 0. Later partial read block 47823348 (`2026-10-07T23:16:31Z`) reconfirmed pool 15 USDC/assets, unpaused, old runtime identity and source 0 USDC; it is not a full signing snapshot.

## Fresh facts required before even the approval

1. Chain 84532; fresh block number/hash/timestamp and ISO observation time; runtime keccak for token/pool/provider; token/provider getter identity. Observe within ten minutes, with block timestamp within three minutes of observation.
2. All **13** existing public actors: native balance, USDC balance, pool allowance, latest and pending nonce, shares, lender balance, active loans, granted/available/committed credit, earned dues, raw provider score and held budget. Latest and pending nonces must agree, with no conflicting journal authorization. Pending nonce is a live observation, not a historical block value.
3. Pool: cash/token balance/assets/shares/lent/reserved, withdrawal queue, reserve, impairment, dues, protocol fees/unclaimed payouts, unpaused state, max loan 100e6, APR 933 bps, reserve 4500 bps. Source claim must still be 15e6 and 15e12 shares; source wallet USDC zero. No unrelated position/loan/queue or cash change may be silently repaired.
4. Provider: fresh flag, current epoch/report age/maxAge, current owner/reporter, held budget, Avery values; pool owner/oracle/guardian. If stale, Hermes must refresh legitimate required reports while preserving Avery; no loan origination until freshness and capacity are demonstrably restored.
5. Exact approval `eth_call` from s1-funder at the pinned block must return ABI `true`; estimate gas; quote current gas price; bind the full nonce/gas/gas-price/value/data fingerprint. Signer caps gas at 1e6, gas price at 0.1 gwei, and at most 2x estimate + 25000; worst-case ETH spend must fit the funded wallet. An estimate alone is insufficient.
6. Reserve channel/time capacity to finish the chosen community and return its full funds before disbursement; preserve the 04:00 Denver sync, Oct 19 funding and Oct 20 interest commitments and Hermes's already assigned fork work. Do not schedule another automation. Public read/receipt evidence can use GitHub; root signed bytes remain email-only.

## Ledger and honest experimental scope

Initial temporary-working ledger is **root-controlled wallet USDC 20 + pool cash 15 = 35**. Of the root 20, only 15 is the user's original allocation; 5 is Hermes's temporary source withdrawal. At every stage root wallets plus pool token cash must equal 35. Each same-day community must close its full 1-USDC loan, unback, withdraw the scenario funder's entire 5-USDC position, clear/release its temporary issuer score/budget, zero actor allowances/positions, and sweep all actor USDC: boundary **root 20 / pool 15**. After three distinct verified repay/withdraw boundaries, return source 5 to Hermes and require Hermes's actual approve/deposit receipt: final **root 15 / pool 20 / Hermes 20e12 shares / source wallet zero**. A bare transfer to Hermes is not pool restoration. ETH gas is separate; all residual actor ETH remains root-controlled.

The three existing plans meaningfully separate controlled task funding, voluntary peer aid and scripted collusion/refusal followed by supervisor compulsory cure. They can establish real deployed loan/accounting mechanics and custody recovery. They **cannot** establish independent task income, borrower honesty, a live default, algorithmic transitivity, or profitable autonomous bootstrap: all keys share root custody and treasury/peer/cure funds are internal budgets. Deposits grant shares, not credit; received backing does not give a borrower reusable onward credit. These scenarios use the deployed temporary officer line; do not silently substitute a new credit model.

Full repayment before `disbursedAt + 86400` earns completed history but zero dues and zero independent interest credit. The signer leaves at least three hours of grace and refuses partial payment. Positive interest starts at elapsed >=86400 and accrues from disbursement, not just the excess past the grace. Reserve interest is credited to borrower dues even when a third party pays; the reserve is locked by totalDuesPaid under `releaseReserve` and reduces lender-withdrawable assets. Existing unrelated Hermes shares also receive pro-rata lender interest.

**Arithmetic illustration only, not a transaction:** at 1 USDC, 933 bps and exactly one day, interest floors to 255 micro-USDC; reserve at 4500 bps floors to 114; the five-USDC scenario lender's full virtual-share-adjusted payout is 5,000,035 units. If that 255 interest comes from the existing root baseline, root ends at 19,999,780 units, 220 units below the required 20,000,000; locked reserve and Hermes's unrelated lender claim retain the difference. This excludes a nonzero protocol fee, which would worsen recovery. Therefore the existing strict-recovery helper must remain interest-free. Extra funding or supervisor cure may change the ledger but must not be called earned business revenue. Productive interest-generating bootstrap is a separately evidenced economic experiment, not a solved result of these three runs.

## Known integrity boundary

Current main `docs/CREDIT_INTEGRITY_ISSUES.md`, blob `0750379ea8efd215973ec18d9130ad9b725885c2`, still lists **CI30 open, measured, not fixed**. The existing repayment cent threshold can mark small principal/short payments complete, burn lender capital and misattribute dues. Never probe this with live pool money: no sub-cent loan, default, short payment, grace expiry or write-off. Exact 1-USDC full same-day repayment avoids the staged exploit, but passing these bounded mechanics does not establish fraud equilibrium or mainnet protocol safety. The requested graph-based post-bootstrap credit is not yet deployed; read-only rejection evidence is not a replacement for that implementation.

## Audited local/public sources

- `/workspace/work/cold-start/live-prep/{README.md,public-plan.json,public-wallets.json,sign-batch.mjs,initial-gas-batch.template.json}`.
- `/workspace/work/eth-bootstrap/integration/deployments/base-sepolia-1812e7d-usdc001/README.md` and local public-app `deployedContracts.ts` / `utils/microcredit.ts`.
- GitHub `scottonchain/microcredit-agent-testbed`: current `world-model/model.json`.
- GitHub `scottonchain/microcredit-contract`: contract coordination issue #7 comments, current `docs/CREDIT_INTEGRITY_ISSUES.md`, and contract source at commit 1812e7d.
- Pool source blob `d06ebd2d8397d62840269314e87710d3c43bb89b`; provider source blob `6c87596620647ddf9755b86b0104e86b3def6757`.

Next missing fact is the current full signing snapshot and prior-hash reconciliation, not more funds, new wallets, a replacement deployment or another fork run.
