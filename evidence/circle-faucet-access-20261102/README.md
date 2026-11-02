# Test USDC for sessions: Circle's faucet API is closed to a testnet-only account, and what works instead

Claude Code (AI), November 2, 2026. Operator request of November 2 (chat session, words summarised, not quoted as a receipt): make it possible for Claude Code sessions to obtain test USDC drips; if that is impossible, record it in the world model and work the path forward with the steward. Supports D7 gate 2 only ([directions/self-service-borrower-app.md](../../coordination/directions/self-service-borrower-app.md), GO for gates 1 to 3, zero money). Nothing here is money, a loan, a borrower, demand or human benefit. Credit is provisional. The revolving first-job payment guarantee ([NORTH_STAR.md](../../coordination/NORTH_STAR.md)) is unaffected: no exposure rule, scorecard or gate changes.

## The four questions

- **Measurable outcome or decision:** whether a Claude Code session can put a few test USDC into a tester's wallet without a person visiting a web faucet, so the desk on the steward's branch can grant a line and fund the interest buffer in one step. The decision is which route to use and what the operator must do, if anything.
- **Evidence sought:** an HTTP status and a balance change from each route, recorded with block number and time.
- **Competing simpler route:** the tester fetches test USDC from the web faucet by hand. The app and the tester guide on the steward's branch already do this. It costs nothing and needs no credential.
- **Stop or change condition:** any route that needs a mainnet-capable account, a new third-party account without the operator's explicit go, or a credential pasted into a message or a commit. Those stop the route, not the demonstration.

## What was measured

| When (UTC) | Who, where | Request | Result |
| --- | --- | --- | --- |
| 2026-11-02 about 15:30 | steward session, its container | `POST api.circle.com/v1/faucet/drips` with a Restricted testnet API key (products Webhooks, Wallets, Contracts, Swap Kit; faucet not selectable) | 403 |
| 2026-11-02 16:58:24 | steward session, its container | same request with a Standard testnet API key, address `0xfAF4a8e697800f459CCbACC790f8250430Dfe844`, `BASE-SEPOLIA`, usdc, balance before 0 at block 53584176 | 403 `{"code":3,"message":"Forbidden"}`; nothing dripped |
| 2026-11-02 after 16:58 | steward session | same endpoint with a bogus key and with no key; an authenticated entity read with the real key | 403 in both cases; the entity read returned 200 |
| 2026-11-02 about 16:30 | this session | Circle API reference, `request-testnet-tokens` page | "Calling the `/v1/faucet/drips` API requires upgrading to mainnet." |

Reading: the key reached Circle and authenticated. The refusal does not depend on the key or its type. It is the account gate Circle's reference states. **The faucet API is closed to a testnet-only Console account.** The key type was not the cause.

The upgrade is a business verification of the operator's entity with Circle. Circle's developer docs do not state the steps or the time for the Console path; for the wallet products they say mainnet access follows an approved eligibility application. It is a gate 5 action (mainnet readiness) and the operator's authority decision. Recommendation recorded here: not for a test faucet.

## Routes a session can use, compared

| Route | What it needs | Status today | Exposure |
| --- | --- | --- | --- |
| R1. Transfer from the team's test wallet `0x38e9845A1Df22c59Bfc693bf2CEAa3361158d6d1` | Nothing new. Its key exists only as the GitHub Actions secret the cold-start and real-agents workflows already use. A `workflow_dispatch` job sends a capped amount of test USDC to an allowlisted address and records the hash. A session triggers it through the GitHub API. | Built on branch `claude/sweet-hopper-a60ogd` with the steward's conditions (below); live only after a reviewed merge to main. The trust boundary does not change, because anyone who can push to this repository can already run a workflow that spends this wallet | Shared wallet: allowlist, per-run and balance caps per address, 100 test USDC per UTC day across runs, a 50 USDC floor, one wallet job at a time |
| R2. Circle agent-wallet CLI (`@circle-fin/cli`) | Operator allows `agentic-wallet.circle.com` in the environment's network access; one login email whose one-time passwords a session can read; `CIRCLE_ACCEPT_TERMS=1`, which accepts Circle's agent Terms of Use | Blocked: the host returns a proxy refusal from this container (checked 2026-11-02 about 17:00 UTC). Everything else is verified from the CLI source, below | A Circle-custodied testnet agent wallet under that email; faucet limits unknown; sessions last 28 days, then a new one-time password |
| R3. Web faucet `faucet.circle.com`, by the tester | A person and a browser | Already wired into the app and the tester guide on the steward's branch. The host is blocked from containers, and it is a human path | None for sessions. One measurement owed: the amount and the retry window, which the app copy and the sim docs state differently |
| R4. Circle faucet API after a mainnet upgrade | Business verification of the operator's entity | Not now (gate 5) | A mainnet-capable account before gates 4 and 5 |

Balances read by this session on 2026-11-02 at 17:10:59 UTC, block 53587951, Base Sepolia, read-only RPC `sepolia.base.org`:

| Address | Test USDC | Test ETH |
| --- | --- | --- |
| Team test wallet `0x38e9...d6d1` | 180.2 | 0.0248 |
| Steward's throwaway `0xfAF4...e844` | 0 | not read |

0.0248 ETH covers many USDC transfers at current Base Sepolia gas prices; the per-transfer cost is not measured here.

## R2 in detail: what the Circle CLI actually does (read from `@circle-fin/cli` 1.2.2, installed from npm into a scratch directory, 2026-11-02)

- **Hosts.** Agent-wallet operations go to `https://agentic-wallet.circle.com` under `/proxy/test` (testnet) or `/proxy/live`, authenticated with an `X-User-Token` header, not the Console API key. The same host serves the version policy at `/v1/cli/version`. The npm registry is read for the update notice (`CIRCLE_VERSION_CHECK=off` disables both checks). `api.circle.com` is used only by the x402 service discovery commands. Chain reads go to the public RPC of each chain (`sepolia.base.org` for Base Sepolia).
- **Login, non-interactive.** `circle wallet login <email> --type agent --testnet --init` sends the code and prints a request id; `circle wallet login --request <id> --otp <ABC-123456> --type agent --testnet` completes it. The code must be read from the inbox by whoever runs the second command. Interactive login prompts for the code on the terminal. A passkey method exists for interactive use only.
- **Terms.** First use prompts to accept Circle's agent Terms of Use (`https://agents.circle.com/terms-of-use`) and privacy policy. In a non-interactive shell the CLI refuses unless `CIRCLE_ACCEPT_TERMS=1` is set; `circle terms accept` records acceptance explicitly. Accepting is the operator's decision, not a session's.
- **Session storage.** `~/.circle-cli/profiles/agent/session.json` (file mode 0600), or under `CIRCLE_CLI_HOME`. Secrets go to the OS keychain when `secret-tool` exists, otherwise to the file. The session holds a user token (expiry read from the token, 28 days per Circle's docs), an encryption key and the encrypted user secret needed to sign; a fresh container has none of it, so every new session logs in again.
- **Faucet.** `circle wallet fund --address <agent wallet> --chain BASE-SEPOLIA --token usdc` posts to `<proxy>/fund` for one of the login's own agent wallets. It cannot fund an arbitrary address. Tokens `usdc`, `eurc`, `eth` and `native` are accepted. Rate limits are not documented; the service's error detail is printed on refusal.
- **Transfer out.** `circle wallet transfer <to> --amount 5 --token 0x036CbD53842c5426634e7929541eC2318f3dCF7e --address <agent wallet> --chain BASE-SEPOLIA`. Agent wallets are Circle smart accounts; the service submits the transaction and returns a transaction id.
- **Inbox for the code.** The team's agent inbox `claude-microcredit@agentmail.to` is readable from every session in this environment through the AgentMail API (`GET /v0/inboxes` returned 200 on 2026-11-02 at about 17:15 UTC, three inboxes listed). Using it as the login email would let a session complete the login without a person. Circle's own warning applies in reverse here: anyone who can read that inbox could take over the agent wallet, which would hold only faucet test tokens.

Nothing in R2 was executed. The host is blocked, so no login, no account, no terms acceptance and no drip happened.

## Live fallback on the steward's branch (verified 2026-11-02, 17:37 UTC)

The steward reports (cross-session message, 17:26 UTC) that the credit desk officer on branch `claude/d7-live-sim-app-20261101` (head 444d0a8 then, 1326dd7 at 17:36 UTC) tries one faucet drip and, when refused, sends 0.10 test USDC from its own balance to each newly backed wallet. Verified from the chain through `sepolia.base.org` at block 53595767:

| Transaction | Block | What it did |
| --- | --- | --- |
| `0x03b7cee64163f0288ae07e3de6a84b6c7919550d2ea9a233b07ab6acee8397d7` | 53585728 | Desk officer `0xb88DC88d538a754f57cAB344C1E09d02C129fcf2` to the CreditDesk `0x28e1d776d9f9f60b90cfb8075ebb9d0f07c82462`, status 1 (the grant) |
| `0xd250157d032a8ac3df79a79a0de37a3cc3aa9172ea58c8918e2522597c9bbc38` | 53585749 | 0.1 test USDC from the desk officer to `0x97bdfc59363f971ea96fd69783c8fde9d93ed458`, status 1 (the pre-fund) |

Balances at that block: sim treasury `0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212` 0 test USDC; desk officer 1.9 test USDC. The steward also reports today's liquidity as pool lendable 10, desk stake 10 free, officer pre-fund budget 2 and sponsor wallet 3 free (test USDC, not verified here), and relays the operator's statement that Codex is out of credits, so the expected 2,000 test USDC deposit will not come. Test USDC must then come from a faucet or from recycling. The steward asks for drips to the sim treasury and the desk officer once a session-side faucet works, with the per-drip amount, the observed rate limit and the host, and otherwise stays on the pre-fund route.

Answer recorded here: no session-side Circle drip is possible today. R2 is blocked by the network policy and waits on the operator's three decisions; R4 is not taken. R1 can fund both addresses from the team test wallet at 5 test USDC per dispatched run under the draft's caps; raising the cap for the treasury is a review decision, not a session's.

## Steward disposition and the conditions as implemented (2026-11-02, 17:40 UTC)

The steward accepted the team-wallet drip for review by cross-session message, with five conditions. How each is met on the branch:

| Condition | Implementation |
| --- | --- |
| Recipient allowlist: the sim treasury and the desk officer only, more addresses by a reviewed change | `scripts/drip_allowlist.json`, read by the script; an address not on it is refused before anything is signed |
| 5 per run by default, the treasury up to 25 per run, 100 per UTC day across runs, the 50 floor | `amount` input (default 5) checked against the entry's `max_per_run`; the daily total is read from this workflow's runs through the GitHub API, selecting today's runs by their creation time on the client (pages are read newest first until a run older than today appears, so many dry runs cannot hide live runs); successful and still-running runs count, dry runs do not, an unrecognisable run name counts as 25, so the run name must keep its form; floor unchanged |
| The balance refusal stays for the officer (5) but the treasury may receive while below 25 | `max_balance` per entry: officer 5, treasury 25 |
| One log line per run on board 15, or the run summary if a workflow cannot post | The workflow holds no issue-write permission on purpose (it holds the wallet secret); the run summary and a `drip-result` artifact carry amount, recipient and hash, and the steward posts the line |
| Same concurrency group, dry-run input kept | `codex-sepolia-test-wallet`; `dry_run` input runs a separate step with no secret loaded |

Read-only checks on 2026-11-02 at about 17:45 UTC, block 53598123 and following: treasury 25 would send; officer 5 would send (balance 1.9); officer 10 refused (per-run cap); an address off the list refused; treasury 25 with 80 already committed today refused (daily cap); a live run without a GitHub token refuses before any send. Six rule tests pass. No transaction was made.

The steward also reports, and this session verified on board 15 at about 17:50 UTC: the 403 is mirrored with the bogus-key and no-key controls (comment 6583257474, Claude steward, 17:06 UTC); Hermes tried `faucet.circle.com` from its host and answered no, stopped by reCAPTCHA (comment 6583862893, hermes-agent-909, 17:33 UTC); the operator's own visit today put 20 test USDC into each of two wallets, so the web faucet gives 20 per drip and its interval is still unknown. The Circle agent-wallet CLI route is recorded as the operator's decision; the steward will put it to the operator as one question once the team-wallet route is in place.

Opening the pull request is not this session's to do without the operator's word; the branch is ready for the steward to open it, or for the operator to say so.

## Recommendation

1. **Now:** the desk's 0.10 test USDC pre-fund is live on the steward's branch and the app links the web faucet; the steward records the 403 on board 15 as the measurement.
2. **Cheapest session-side drip:** R1, accepted by the steward for review on 2026-11-02 at 17:40 UTC with conditions, all folded in: `.github/workflows/drip-test-usdc.yml`, `scripts/drip_test_usdc.mjs`, `scripts/drip_rules.mjs` (pure rules, tested by `node --test scripts/test_drip_rules.mjs`) and `scripts/drip_allowlist.json`. It goes live through the ordinary reviewed PR and merge; the steward then triggers runs through the GitHub Actions API when the pool or the desk needs cash.
3. **If a Circle-side drip is still wanted:** R2, after the operator allows `agentic-wallet.circle.com`, chooses the login email and accepts the terms. First run measures the faucet's amount and limit with one drip to the agent wallet and one transfer out, recorded here.
4. **Not now:** R4.

## What this does not establish

Faucet limits for the agent wallet; whether Circle's agent-wallet faucet funds Base Sepolia in practice (its docs list `BASE-SEPOLIA` as supported); the per-transfer gas cost of R1; anything about testers, borrowers, demand or benefit.
