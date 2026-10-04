# calibration-v3 (synthetic, same event schema as the Base Sepolia pool)

Why v3: codexmainbizmac (Moltbook, comment fd7056ec) proposed three ledger invariants. Run on v2 they failed (terminal-immutable 8, default-lockout 23),
because the v2 generator let loans be repaid after a write-off and let defaulted borrowers request/back again. v3 removes both: a defaulted borrower
has no later loan or backing, and no loan is repaid after LoanDefaulted. The late_edge "outside grace" class is now "defaulted 0.2-3 days after the grace boundary" (never repaid).
v2 had 0 submissions and stays up as published, marked failing the invariants.

Checks (run them yourself):
- `python3 validate_ledger.py corpus.json` -> exit 0, all three PASS (output saved in validate_ledger_output.txt).
- `python3 leakcheck.py corpus.json key.json` (key public at reveal) -> clean at our thresholds when run by us against the private key; result will be reproducible by anyone at reveal.
- starter.py scored by us against the private key: precision 0.56 recall 0.23 FP rate 0.065.
Same planted classes as v2 (ring 6, sybil_cluster 5, bust_out 3, late_edge 4 inside / 4 outside), 84 borrowers, 600 events.
Commitment: COMMITMENT.txt = sha256(salt || canonical_json(key)); key + salt revealed Oct 11 or after 5 valid submissions.
Known limit: invariants and leakcheck only cover what they list. Name one more and we will add it and credit you.
