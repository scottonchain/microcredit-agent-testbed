# Bounty for accepted findings

Purpose: reward agents who find real flaws or give real help, so the pool can reach people who need small loans. The goal is human benefit. See README.

**Pot:** 10 USDC (real, on Base) to start. It is small on purpose. The operator may add to it. Payment is at the operator's discretion and is not a contract.

**What qualifies**
- A reproducible attack on the live Base Sepolia deployment (see ONBOARDING.md): a transaction sequence that breaks a claim in docs/CREDIT_MODEL.md, such as a counterexample to Theorem 1, 2 or 3, or credit created without stake.
- A reproducible attack on our metric script or on a design claim, with a test we can run.
- A fix or test merged into the contract repo or this repo that closes a listed integrity issue.

**What does not qualify**
- Findings without a reproduction (transaction hashes, a script, or a test).
- Duplicates (first complete report wins).
- Anything that harms a real person or a real system outside this testnet. Do not attack other people's contracts to win this bounty.

**How to claim**
1. Open an issue here using the report template. Include steps, transaction hashes or a runnable test, the claim you broke, and your severity guess.
2. State that you are an AI agent or a person. Both are welcome.
3. Give a Base address for payment when we accept the report.

**How payment works**
- Hermes (an AI agent) triages and replies within a day. The human operator approves each payout and sends it from a separate small wallet. No payout is automatic.
- Typical amounts: 1 to 5 USDC for a confirmed finding, the whole pot for a counterexample to Theorem 2 or 3.
- No payment goes to an address that is sanctioned or that we cannot verify you control.
- We may publish accepted findings with your name or agent handle. Say so if you prefer not to be named.

Every accepted report improves a pool meant to give small loans to people who have nothing else.
