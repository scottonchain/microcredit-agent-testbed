Read-only supplement for HERMES-LIVE-COMMUNITIES-20261008-r1, both passes (loans 18-20 and 21-23). Hermes Agent (AI), hermes-agent-909.
Reconstructed 2026-10-08T16:16-16:18Z from Base Sepolia public RPC after the runs; nothing here was recorded at run time. No signed bytes, no state change.
- pass1_receipts.json / pass2_receipts.json: 66 txs each: public tx fields (from, to, nonce, input, value), receipt status, block, blockHash, gasUsed, effectiveGasPrice, l1Fee, decoded logs (USDC Transfer; Pool LoanRepaid, RepaymentApplied).
- fee_ledger.json: per pass funded wei, scenario-wallet balance at the pass's final block, fees (L2 + l1Fee), identity check.
- refusal_replay.json: each recorded refusal replayed with eth_call at explicit blocks. The original calls used the 'latest' tag (unpinned); the stored block was the case-start head.
- supplement.py, replay_refusals.py: the scripts.
