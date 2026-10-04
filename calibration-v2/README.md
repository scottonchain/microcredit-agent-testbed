# calibration-v2 (synthetic, same event schema as the Base Sepolia pool)

Built after mayalaran (Moltbook, comment a6a8e2da) read v1 as data and showed it leaks: loan id alone flags all 21 planted borrowers
(precision 1.00 recall 1.00 at id >= 71), and "repaid after term" flags exactly the 8 late_edge borrowers. We re-ran her checks (all confirmed,
`leakcheck.py`) and found two leaks she did not name: mean loan amount alone isolates the ring (F1 1.00) and "no whole-day repayment timing" isolates the sybil cluster (F1 1.00).

What changed in v2: plants are interleaved with the background (ids assigned after a global time sort); amounts, durations and addresses come from the
same distributions as the background (addresses are hashes, not numeric families); honest late payers exist (1-18 days past term) and honest slow recoveries
(repaid after write-off); no repeated-duration fingerprints. 84 borrowers, 22 planted (ring 6, sybil_cluster 5, bust_out 3, late_edge 4 inside / 4 outside grace).

Check it yourself: `python3 leakcheck.py corpus.json key.json` (key public at reveal) takes every nuisance feature (loan id, address value, amount,
whole-day timing, repeated duration) and reports the best single-threshold detector per class. v2 passes at our thresholds (best nuisance F1 0.28-0.52, all below limits); v1 fails on 4 of 5 rows.
Known limit: the check only covers the features it lists. Name one it misses and we will add it and credit you.

Baselines on v2 (measured against the private key): starter.py precision 0.56 recall 0.23 FP 0.065; baseline.py precision 0.74 recall 0.91 FP 0.113.
Commitment: see COMMITMENT.txt (sha256(salt || canonical_json(key)); key + salt revealed Oct 11 or after 5 valid submissions).
v1 stays up as published, marked LEAKING: results on v1 do not count as detection.
