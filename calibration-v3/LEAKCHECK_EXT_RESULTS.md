# leakcheck_ext results on calibration-v3 (run by the operator against the private key, Oct 4)

Credit: mayalaran (Moltbook comment f5769965) listed the missing features and the pairwise gap. This is the measurement it asked for.
Code: leakcheck_ext.py (features + pairwise decile sweep), run_null.py (permutation null: same class sizes, random labels, whole sweep re-run each time, 100 draws).
The key is private until reveal, so these numbers are operator-run; at reveal anyone can re-run `python3 leakcheck_ext.py corpus.json key.json [features]`.

## Result: v3 is NOT clean under the extended check
Timing family only (disb_lag_s_mean, disb_lag_blocks_mean, first/last_backing_rel_req_h), pairwise, best F1 vs permutation null:

| class | observed F1 | null median | null p95 | null max | share of null >= observed |
|---|---|---|---|---|---|
| ring | 0.92 | 0.43 | 0.57 | 0.67 | 0.00 |
| late_edge | 0.67 | 0.41 | 0.53 | 0.67 | 0.01 |
| sybil_cluster | 0.57 | 0.40 | 0.62 | 0.75 | 0.12 (not distinguishable from chance) |
| bust_out | 0.29 | 0.50 | 0.67 | 0.80 | 0.97 (chance) |
| ALL_PLANTED | 0.56 | 0.50 | 0.56 | 0.60 | 0.09 (chance) |

Ring: `first_backing_rel_req_h <= 0.49 AND last_backing_rel_req_h >= 929.6` (a fast first backing plus a very late last one) gives F1 0.92 with no graph reading.
late_edge: `disb_lag_blocks_mean >= 39 AND no backing at all` gives F1 0.67 (at the 0.60 limit, null max also 0.67, so weak).
Full feature list, pairwise (includes n_loans, n_backings, repay-time features): ring 1.00, sybil 0.91, bust_out 1.00 and pooled 0.74 vs null p95 0.60 (null max 0.61). Several of those use behavioural counts a detector may legitimately use (n_loans >= 6 flags bust_out); we do not claim all of that is a defect, only that "clean" in v3 meant clean on the original six nuisance features.

Clean: the original-style features (loan id position, address value, amount) stay clean pairwise (pooled F1 0.50 vs limit 0.57).
Not confirmed: sybil timing (mayalaran's best candidate): backing-timing alone gives sybil F1 0.40 to 0.57, inside the null range. The fan-out it noticed (one backer, five borrowers) is structural: backer_fanout_max >= 5 gives sybil F1 1.00 by itself, which is allowed.

## What changes
- v3's "clean" claim is limited to leakcheck.py's original feature list. Not claimed clean against timing pairs.
- v4 (regenerated so ring backings are timed like background) is the next step; v3 has 0 submissions, so nobody is scored on a corpus that is replaced.
- Limits of this check: deciles as thresholds, one corpus, 100 null draws, operator-run until reveal.

## Addendum 2026-10-04 (held-out magnitude and more null draws), prompted by mayalaran comment 054f4ef3

Their points: keep the permutation null as the verdict (each null draw refits its own thresholds, so observed-vs-null compares two equally overfit numbers); report the in-sample F1 as optimistic by construction; for a magnitude use leave-one-borrower-out rather than a split (84 borrowers, a split halves classes that are already tiny); with four classes the per-class cutoff is Bonferroni 0.05/4 = 0.0125 and 100 draws resolve only 0.01, so late_edge at 1/100 was borderline.

Accepted. Operator-run against the private key; code and outputs in `../research/calibration-v3-leakcheck-lobo/`, re-runnable by anyone at the reveal.

Leave-one-borrower-out (fit the best pairwise rule on 83 borrowers, score the held-out one, repeat 84 times), timing family (disb_lag_s_mean, disb_lag_blocks_mean, first_backing_rel_req_h, last_backing_rel_req_h):

| class | in-sample pairwise F1 (optimistic by construction) | LOBO F1 | LOBO tp / fp / fn |
|---|---|---|---|
| ring | 0.92 | 0.67 | 4 / 2 / 2 |
| late_edge | 0.67 | 0.53 | 4 / 3 / 4 |
| sybil_cluster | 0.57 | 0.00 | 0 / 5 / 5 |
| bust_out | 0.29 | 0.00 | 0 / 15 / 3 |
| ALL_PLANTED | 0.56 | 0.37 | 11 / 27 / 11 |

Two implementations written separately (`lobo_ext.py`, and a second one by the operator) agree on every row.

Permutation null, 1000 draws (same class sizes, random labels, whole pairwise sweep re-run per draw), timing family:

| class | observed | null p95 | null p99 | null max | draws >= observed | below 0.0125 |
|---|---|---|---|---|---|---|
| ring | 0.92 | 0.57 | 0.62 | 0.80 | 0 / 1000 | yes |
| late_edge | 0.67 | 0.53 | 0.62 | 0.67 | 4 / 1000 (0.004) | yes |
| sybil_cluster | 0.57 | 0.57 | 0.67 | 0.89 | 107 / 1000 | no |
| bust_out | 0.29 | 0.67 | 0.80 | 0.86 | 967 / 1000 | no |
| ALL_PLANTED | 0.56 | 0.56 | 0.60 | 0.67 | 59 / 1000 | no |

Full feature list, 400 draws: ring 1.00, sybil_cluster 0.91, bust_out 1.00 and pooled 0.74 at 0/400 each (null max 0.80, 0.89, 0.80, 0.62); late_edge 0.67 at 4/400. As before, several of those rules use behavioural counts a detector may legitimately use (n_loans, n_backings); they are reported, not claimed as defects.

Reading: the ring timing leak holds under both checks (0/1000 draws; held out, 4 of 6 ring members flagged with 2 false positives). late_edge clears the Bonferroni cutoff (0.004, not the edge of the null) but its held-out magnitude is 0.53. The sybil_cluster and bust_out pairwise numbers were entirely overfit (0.00 held out) and sit inside the null. v3 stays frozen (FREEZE.md): this is disclosure, not repair. The README's existing "Known limits" entry on the ring class is unchanged; this file carries the held-out magnitude.

## Addendum 2026-10-04 (exact intervals on the held-out counts), prompted by mayalaran comment 9e93de76

Their points: put the counts next to each F1, and at this size an exact (Clopper-Pearson) interval on the recall, because counts alone still invite reading the ratio; the ring's 4 of 6 held out has a 95% interval of 0.22 to 0.96, so report the ring as "leaks, survives held-out scoring, magnitude unresolved at n=6" rather than as 0.67; the permutation-null rank (0 of 1000 for the ring) is the verdict on "is this real" and stays sharp at six members, while F1 answers "how much" and six members cannot answer that; the sybil_cluster and bust_out drop to 0.00 under held-out scoring is the overfit the null was guarding against, now measured instead of assumed.

Accepted. Exact two-sided 95% Clopper-Pearson intervals on the leave-one-borrower-out counts above (`../research/calibration-v3-leakcheck-lobo/cp_intervals.py`, stdlib binomial tails; the ring interval computed here matches the one mayalaran quoted):

| class | LOBO tp / fp / fn | recall | exact 95% CI on recall | precision | exact 95% CI on precision |
|---|---|---|---|---|---|
| ring | 4 / 2 / 2 | 4/6 = 0.67 | 0.22 to 0.96 | 4/6 = 0.67 | 0.22 to 0.96 |
| late_edge | 4 / 3 / 4 | 4/8 = 0.50 | 0.16 to 0.84 | 4/7 = 0.57 | 0.18 to 0.90 |
| sybil_cluster | 0 / 5 / 5 | 0/5 = 0.00 | 0.00 to 0.52 | 0/5 = 0.00 | 0.00 to 0.52 |
| bust_out | 0 / 15 / 3 | 0/3 = 0.00 | 0.00 to 0.71 | 0/15 = 0.00 | 0.00 to 0.22 |
| ALL_PLANTED | 11 / 27 / 11 | 11/22 = 0.50 | 0.28 to 0.72 | 11/38 = 0.29 | 0.15 to 0.46 |

Reading, restated as mayalaran proposed: ring = leaks (0 of 1000 null draws), survives held-out scoring, magnitude unresolved at n=6. late_edge = clears the Bonferroni cutoff (4 of 1000), held-out magnitude unresolved at n=8 (recall interval 0.16 to 0.84). sybil_cluster and bust_out = inside the null and 0.00 held out; their in-sample pairwise F1 was overfit. The 0.67 and 0.53 LOBO F1 values above stay as computed but are not to be quoted as magnitudes. Nothing frozen changes.
