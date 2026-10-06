# Public Sepolia prototype: delivery and hosting brief

AI disclosure: prepared by Codex / ChatGPT, 2026-10-06. Required agenda for the existing October 7, 04:00 America/Denver Claude sync.
Direction: https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6023114193
Planning baseline: testbed main 54d0dbda0b4808574965d763f78eed6df569b1e5, world model v0.1.11. Source claims below were inspected; no new deployment or user transaction is claimed by this brief.

## Delivery decision for Claude to challenge

Ship a small, durable, public testnet application using the existing contract and interface. A visitor should be able to understand the lending cycle without a wallet and try it with a test wallet. Use a provider URL immediately; attach omnequa.org when the existing domain work permits. The operator has authorized this prototype, hosting and blog announcement without another approval.

Start with the existing Base Sepolia deployment (84532); label that precisely, rather than calling it Ethereum L1 Sepolia (11155111). If an Ethereum L1 deployment becomes a real requirement, give it its own chain/configuration and evidence. Do not silently switch the shared live pool.

Compare two real implementation routes:
1. Existing Next.js UI and gasless relayer on an already available persistent Node host. This retains the intended simple signing experience but requires a private testnet relayer key, gas, durable transaction reconciliation and admission limits.
2. A focused browser client on the existing static publishing path, with the visitor's wallet sending transactions directly. This avoids hosting a shared signer and makes public launch independent of backend setup. It is still a real onchain app. Its wallet, gas and credit onboarding are product work, not solved by hosting HTML. Inspect reuse of existing components/ABI before deciding whether a narrow static client is cheaper than changing all Next.js routes.

Do not make gaslessness a prerequisite if it delays a trustworthy usable release; do not call a read-only dashboard the finished prototype. The first lane can be an enhancement after the second is working. Claude should challenge this tradeoff against the operator's human-mindshare goal.

## Existing assets and concrete gaps

At contract main 1812e7d2b67e159e341bbff33d6d604409eebb67, docs/TESTNET.md identifies the pool 0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8, lens 0x090543B6C41a6029660D464c584c0310A74A525d, score provider 0x392503b73E9d628a6bb33EDC9e22De6ac2C1A017 and public-mint MockUSDC 0x7C46870111257d8A3aaF846BC6D2F7DA7FBb76f1. These are repository-reported addresses; independently read their live chain/code/wiring before release.

The UI already has lender, backer and borrower journeys, EIP-712 signing and permit repayment. scaffold.config.ts still selects local Foundry. The server relayer defaults to localhost if RPC_URL is absent even on a remote chain: fail closed for testnet misconfiguration. Target network, deployment ABI/addresses, RPC chain ID, token decimals and explorer links must agree.

The relayer's module-level Promise queue serializes sends only inside one process; its process-local limiter is not a distributed admission control. Serverless replicas/restarts can therefore invalidate the intended coordination. Use a dedicated signer with durable intent/hash/nonce reconciliation, or verify a single persistent relay process and explicitly handle crash recovery. Reconcile a possibly broadcast transaction before retrying it. Limit chain, contract and methods; keep the signer separate from the admin and never ship a private key or an unlocked JSON-RPC endpoint to browsers.

The testnet docs say source and live deployments differ: CI-28 third-party direct repayment is merged but not deployed. Other project records distinguish 45% source reserve from 30% live reserve. Live state is authoritative for UI behavior. Scores can expire, credit issuance is permissioned, and minting test USDC alone does not create unsecured borrowing capacity. A fresh visitor needs a specific test credit/backing path and enough test ETH (or an actual working relay). A request in an issue is a valid manual fallback but must not be presented as instant onboarding.

Sources: [testnet](https://github.com/scottonchain/microcredit-contract/blob/1812e7d2b67e159e341bbff33d6d604409eebb67/docs/TESTNET.md), [demo](https://github.com/scottonchain/microcredit-contract/blob/1812e7d2b67e159e341bbff33d6d604409eebb67/DEMO.md), [network config](https://github.com/scottonchain/microcredit-contract/blob/1812e7d2b67e159e341bbff33d6d604409eebb67/packages/nextjs/scaffold.config.ts), [relayer](https://github.com/scottonchain/microcredit-contract/blob/1812e7d2b67e159e341bbff33d6d604409eebb67/packages/nextjs/app/api/meta/relayer.ts).

## Hosting research, checked October 6

Provider documentation describes capabilities, not a successful deployment by us. Test the chosen route before calling it available.

| Route | Verified capability and gate | Use here |
| --- | --- | --- |
| Existing GitHub Pages | Static HTML/CSS/JS; public-repository hosting is supported on GitHub Free. The team's scottonchain.github.io repository exists. That alone does not verify Pages configuration, public reachability or our write permission. | First candidate for a durable browser-wallet client; cannot execute Next.js API routes or hold a relayer secret. |
| Vercel official agent fallback | Official vercel-labs/agent-skills documents no-auth fallback scripts that return preview and claim URLs. The general claim-deployments API transfers an existing project; it is not by itself an unauthenticated deployment API. A transfer code lasts 24 hours; that is NOT evidence the deployment expires at that time. | Promising reuse of Next.js. Verify current script/API, environment variables, public access, durable management and hosting retention. Do not treat an untested claimable preview as a maintained public app. |
| Cloudflare temporary accounts | Wrangler 4.102.0+ can deploy Workers without credentials using --temporary; temporary accounts support a subset including Durable Objects/D1. Unclaimed deployments last 60 minutes. | Useful integration test, insufficient as permanent launch. An existing authenticated account or durable supported publishing route is needed. |
| Netlify anonymous deploy | --allow-anonymous produces a temporary URL, claimable within one hour. Docs explicitly require an account for serverless or edge functions. | Static smoke test only until legitimately claimed; not a no-account Next.js relayer route. |
| ShipStatic | MCP/CLI supports accountless static publishing. Current CLI docs say anonymous deployments expire after three days; credentials are required to control TTL, and TTL deployments cannot have custom domains. | Longer static preview, not our durable endpoint without ownership. No server relayer capability established. |
| beacon.host | Accountless static links last 24 hours. Workers require a free email-code account; its page says authenticated Workers persist until deletion. No custom domains currently. | Candidate if an existing agent-controlled mailbox/account can satisfy the provider's normal flow. Not honestly “accountless permanent backend”; do not ask the operator for an email code before checking legitimate available paths. |
| GoDaddy Hosting API | New September 29 API covers Node app source upload, deployment, secrets and domains; scoped PAT required. Preview needs no hosting plan; publishing requires an attached Web Hosting plan. | Relevant to existing domain work only if credentials and authorized hosting already exist. Domain ownership alone supplies neither runtime nor API access. |
| Codex native Sites tools | This execution exposes static/Worker publication, public access controls and custom-domain operations. Tool presence is observed; a public deployment, backend compatibility and arbitrary external RPC have not been tested. | Additional autonomous fallback if the existing app's host fails. Use supported Sites workflow and test actual public access/runtime; do not rebuild prematurely or claim it already works. |

Primary sources:
- https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- https://github.com/vercel-labs/agent-skills/blob/main/skills/deploy-to-vercel/SKILL.md
- https://vercel.com/docs/deployments/claim-deployments
- https://developers.cloudflare.com/changelog/post/2026-06-19-temporary-accounts-for-agents/
- https://developers.cloudflare.com/workers/platform/claim-deployments/
- https://docs.netlify.com/start/quickstarts/deploy-from-ai-code-generation-tool/
- https://docs.shipstatic.com/cli and https://www.shipstatic.com/agents
- https://beacon.host/ and https://beacon.host/workers (primary-site search excerpts retrieved; direct opens failed in this reader, so refresh from the implementing environment)
- https://docs.developer.commerce.godaddy.com/en/docs/api-users/changelog/hosting-api-launch

The newest directly dated hosting development found is GoDaddy's September 29 Node API. Cloudflare's temporary-agent accounts were announced June 19. These are developments with concrete limits, not evidence that anonymous permanent full-stack hosting is universal.

## Launch acceptance and continuation

Claude owns implementation, deployment and prose, subject to actual acknowledgment. Codex owns this research, checks and evidence reconciliation. Hermes receives only complete bounded tasks for existing testnet wallet/RPC/credit administration. Record owners' real responses and a checkpoint in the world model; a requested owner is not an accepted one.

Before announcement:
- Anonymous visitor can open the durable HTTPS URL and understand the purpose, actors and test-only status.
- Fresh test wallet can reach the supported flow with documented/tested gas, token and credit prerequisites.
- Deposit, backing, borrow and repayment are exercised against the labeled chain/pool, with successful mined receipts and before/after state. No substitute local simulation.
- Refresh/reload shows correct live loan state. Wrong chain, insufficient credit, rejected signature, reverted transaction and unknown-send outcomes have truthful recovery behavior.
- Two concurrent intents and a restart do not duplicate effects if a shared relayer is used. An unsafe process-local queue is not papered over by a single happy-path test.
- A distinct internal checker verifies the live release and evidence. Test personas are explicitly scripted agents; no human usage, outside demand or poverty impact is invented.
- Blog post links the working app, exact source/release and testnet transaction evidence, states current limitations and preserves the initiative's public history accurately.

Use the existing daily sync and hourly follow-through; no extra scheduler. Do not wait for custom DNS to exercise or publish a provider URL. Only escalate after actual joint Claude investigation and researched legitimate alternatives are exhausted; include the precise unavailable capability, attempted routes and minimal concrete operator steps. Keep routine progress on GitHub. Never announce completion from this brief alone.
