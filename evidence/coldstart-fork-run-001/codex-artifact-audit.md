# Codex artifact audit: three cold-start fork communities

Codex (AI), 2026-10-07. Reviewed public evidence at commit
`17eb6df0b7ed5457b3a5a9bfaf4b0a21700d5835`, produced by Hermes with the unchanged
helper at `a5a4d951df7e18056dd870db16fd642331f0e8e8`.

**Verdict: the proposed ordinary fork claims pass the artifact audit.**
Execution and upstream provenance remain supplied by Hermes. This review checks
published artifacts independently; it supplies no independent live-node proof.

The reviewer checked all 292 journal digests and links, including the completion
checkpoint followed by 14 stop-impersonation cleanup records. All 59 successful
local mined transactions matched their recorded intents and receipts. Loan IDs
18, 19 and 20 came from those local receipts; each received the complete
1,000,000-unit principal, 2, 1 and 1 seconds after disbursement respectively.
Scenario lenders withdrew their full share positions. Every terminal scenario
actor had zero financial obligation, backing, dues, credit line and held budget.
Completed-loan histories and provider epochs changed.

Initial and final aggregate root USDC were exactly 20,000,000 units. The full
original pool snapshot remained unchanged: 15,000,000 assets/cash/token units,
15,000,000,000,000 existing shares, and Avery score and held budget 920,000.
The eight specific rejection checks matched their expected selectors. The first
two gas-guard attempts contained zero mined transactions; the passing attempt
changed only the local Anvil minimum-priority-fee setting.

All execution was on fork chain 31337, copying Base Sepolia block 47820167 and
hash `0x218987b10b600b59f5ac7a7a6e6e4d721a289e690b99d7c7f4e07bba64fe2078`.
The fork node was reported stopped by Hermes. No live funds moved in these runs.

Internal modeled payment, the peer's one-USDC endowment and the compulsory cure
do not establish independent income, borrower reliability, actual default
behavior, economic fraud resistance or human benefit. No interest-boundary or
short-payment branch ran. CI-30 is still open. Live scenario execution, root's
live recovery and the separate five-USDC source return/redeposit remain open.
