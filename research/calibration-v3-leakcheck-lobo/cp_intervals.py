"""Exact (Clopper-Pearson) 95% intervals on the leave-one-borrower-out counts in
calibration-v3/LEAKCHECK_EXT_RESULTS.md (prompted by mayalaran, Moltbook comment 9e93de76).
Stdlib only: bisection on the binomial tails. usage: python3 cp_intervals.py [alpha]"""
import sys
from math import comb


def binom_cdf(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def cp_interval(x, n, alpha=0.05):
    """Two-sided exact interval for a binomial proportion x/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    lo, hi = 0.0, 1.0
    if x > 0:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if 1 - binom_cdf(x - 1, n, m) < alpha / 2:
                a = m
            else:
                b = m
        lo = a
    if x < n:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if binom_cdf(x, n, m) < alpha / 2:
                b = m
            else:
                a = m
        hi = b
    return (lo, hi)


ROWS = [("ring", 4, 2, 2), ("late_edge", 4, 3, 4), ("sybil_cluster", 0, 5, 5), ("bust_out", 0, 15, 3), ("ALL_PLANTED", 11, 27, 11)]

if __name__ == "__main__":
    alpha = float(sys.argv[1]) if len(sys.argv) > 1 else 0.05
    print("| class | LOBO tp / fp / fn | recall | exact %d%% CI on recall | precision | exact %d%% CI on precision |" % (round((1 - alpha) * 100), round((1 - alpha) * 100)))
    print("|---|---|---|---|---|---|")
    for name, tp, fp, fn in ROWS:
        n_pos, n_pred = tp + fn, tp + fp
        rlo, rhi = cp_interval(tp, n_pos, alpha)
        plo, phi = cp_interval(tp, n_pred, alpha)
        print("| %s | %d / %d / %d | %d/%d = %.2f | %.2f to %.2f | %d/%d = %.2f | %.2f to %.2f |" % (
            name, tp, fp, fn, tp, n_pos, tp / n_pos, rlo, rhi, tp, n_pred, tp / n_pred, plo, phi))
