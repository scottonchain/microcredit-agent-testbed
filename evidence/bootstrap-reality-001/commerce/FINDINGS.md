# Agent-commerce financing: primary-source findings

Read 2026-10-07. All retrieved files and SHA256/immutable source URLs are in source-index.json. These sources establish payment mechanisms and developer examples, not realized agent revenue, lender returns, signed customer bids, or mainnet deployment suitability.

| Primary source | What is actually supported | Financing implication / limitation |
|---|---|---|
| Coinbase x402, commit dd927a26cfefc98c24b3ec38b3a8f204dad0c60d, README typical flow lines123–150; examples/typescript/servers/express/index.ts lines26–40 | Client signs exact payment; server verifies, performs work, settles, then returns paid resource. Example weather endpoint costs $0.001 on Base Sepolia. | An agent composing paid upstream calls needs USDC before receiving their outputs. $0.001 is a developer EXAMPLE tariff, not a measured merchant quote. Cannot call 1000×$0.001=$1 a real invoice or invent a resale bid. |
| x402 MCP chatbot README and Bazaar specification, same pinned commit | Tool execution automatically handles payment; resources advertise input/output schemas and facilitators catalog them. | A technically plausible agent business is deterministic aggregation/validation of paid data, or upstream paid MCP calls then output sale. Discovery is not demand and automatic spending is not credit. |
| Virtual Protocol acp-node, commit49dafb4277de646c1c9956bbd74c2313e804de78, README and external-evaluation buyer/seller | Job lifecycle: initiate→accept/createRequirement→buyer payAndAcceptRequirement→seller delivery→evaluation. Seller code requests payment before proceeding. | Buyer-funded escrow can protect payment but public flow does not show seller can spend escrow before acceptance. Loan may bridge locked escrow to upstream paid inputs; this gap requires escrow contract/API evidence, acceptance criteria, timeouts and assigned settlement rights. Customer direct prepay dominates if freely spendable. |
| ACP funds README, same commit, lines103–130 | Trading/fund-transfer scaffolding and escrow; actual trading logic user-defined; buyer pays zero for testing; all fund operations simulated. | Do not cite mock trades or fixed example tx hashes as actual revenue or successful lending. |
| Hyperliquid SDK, commit2fdb18f9517675ea03695a0962bd19eece9c83f0, basic_agent.py and basic_leverage_adjustment.py | Account owner approves an agent signing key; agent submits orders; existing funded account can change cross/isolated leverage. | Delegated trade execution is not trust-graph unsecured credit. Leverage provides exposure, not guaranteed cash flow. Trading has adverse price/funding/liquidation risk; unsuitable first low-risk bootstrap customer without independently measured strategy economics. |
| Aave v3 core, commit782f51917056a53a2c228701058a6c3fb233684a, ICreditDelegationToken.sol, DebtTokenBase.sol, BorrowLogic.sol | Delegator approves a debt-token allowance; debt mint is onBehalfOf delegator, underlying goes to caller; borrow validation still checks delegator position and liquidation constraints. | Useful precedent: sponsor collateral can support a borrower who lacks collateral, but sponsor remains accountable and capacity cannot be multiplied by trust edges. Aave allowance is not inherently transitive and no agent revenue is established. |

## Ground a callable simulation in actual useful work

Recommended task: independently verify and normalize this project's PUBLIC cold-start evidence into a canonical report with deterministic acceptance. Actual project need exists: the user demanded a reproducible verifiable record. This demand authorizes doing useful work, not inventing a customer price/payment.

Inputs: public original journal, transaction receipts, balance snapshots, code hashes and manifest. Output: canonical JSON summary of chain identity, status1 tx count, per-case opening/closing balances, full repayment/withdrawal findings, provenance caveats and file hashes. Acceptance: independently recompute journal hash links, replay USDC Transfer logs, verify receipt/status/call linkage, catch four supplied corruption types; malformed/missing data causes rejection. Exact source boundaries and hidden holdout fixtures prevent reward by merely returning an expected answer. This uses real data and generates an objectively checkable artifact; network fetches can be downloaded once and work completed offline.

Cash requirement of THIS task with local CPU and public GitHub input is zero known incremental paid upstream USDC. Do not manufacture an upstream $1 invoice. It demonstrates work but cannot demonstrate loan necessity. Measure local runtime and source bytes honestly; unknown compute hosting/LLM costs remain unknown unless an actual quoted paid service is used.

Alternative illustrative costed task: pay-per-call API report composition. Use the sourced x402 EXAMPLE $0.001 tariff only as an explicit sensitivity parameter, e.g. 100 calls cost0.1USDC, not market evidence. Customer output price must be a variable or actual signed funded order; no default arbitrary markup. Simulate failure/rejection/refund, retry ceiling, payment release timeout, gas, sponsor locked-capital opportunity cost and independent payer ownership. Report minimum bid: input spend + borrowing cost + settlement/gas + reserve for rejected/retried calls + operator required compensation. Run prepay, sponsor direct-payment, and pooled sponsor-secured loan on identical inputs; pooled route must justify added capital and gas, not assume its need.

## Bootstrap simulation gates

1. Real work gate: agents produce and independently validate the artifact rather than roleplay dollar outcomes.
2. Real cash gate: obtain verified unspent customer escrow or an accepted payment commitment from an independently funded payer. Root/subagent wallets are controlled scenario cash, never external revenue evidence.
3. Necessity gate: borrower must pay upstream before available customer proceeds. If direct prepay/provider credits solve the same problem better, use them or disclose failed financing fit.
4. Capacity gate: stake escrow and graph path allocation are enforced; shared upstream stakes cannot be counted independently along diamond paths; cycles create zero extra stake. Deployed contract cannot be claimed to implement a target transitive graph unless demonstrated.
5. Settlement gate: repayment from actual customer proceeds with principal/fees fully honored; failure consumes sponsor risk budget and lender timing is explicit. Existing CI30 means mainnet safety remains blocked until patch independently verified.
6. Bootstrap gate: at least one useful accepted job plus correctly settled financing in controlled simulation demonstrates technical/economic feasibility conditional on parameters; it does NOT prove independent demand, mainnet readiness or profitable repeat lending.

## Exact source links

See source-index.json for18 successful file retrievals (15 initial +3 additional). Canonical source repository URLs:
- https://github.com/coinbase/x402/tree/dd927a26cfefc98c24b3ec38b3a8f204dad0c60d
- https://github.com/Virtual-Protocol/acp-node/tree/49dafb4277de646c1c9956bbd74c2313e804de78
- https://github.com/hyperliquid-dex/hyperliquid-python-sdk/tree/2fdb18f9517675ea03695a0962bd19eece9c83f0
- https://github.com/aave/aave-v3-core/tree/782f51917056a53a2c228701058a6c3fb233684a
