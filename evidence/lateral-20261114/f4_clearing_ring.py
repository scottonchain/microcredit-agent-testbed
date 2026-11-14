"""F4, mutual credit clearing ring for micro-businesses: how much trade settles without cash?

Analysis only, stdlib only, deterministic (fixed seed). Members invoice each other on a random
trading network; each period the ring (1) nets bilateral obligations, (2) nets multilateral
positions, and (3) lets a member carry a negative balance up to a credit line that is earned
from dues, the contract's rule for earned credit: the line is a fixed share r of the member's
cumulative settled turnover (plus a small floor), so credit follows evidence of trade rather
than a sponsor's capital. Cash is needed only for the net debt that exceeds a member's line.

Reported per (members, density): gross invoiced volume, share settled by bilateral netting,
by multilateral netting, with carried balances but no credit line (a member draws only on its own
past surplus), and with the earned line; cash needed per 100 of gross trade for each; and the share
of members who hit their line at least once. The sign of the absorbed-debt term and the zero-line
control follow Hermes's review of the first head (PR 477 comment 6883516407).

Run: python3 evidence/lateral-20261114/f4_clearing_ring.py
"""
import json
import random


def simulate(n, density, periods=24, r=0.10, floor=1.0, seed=7):
    rng = random.Random(seed)
    # a fixed trading network: i sells to j with probability density
    partners = {i: [j for j in range(n) if j != i and rng.random() < density] for i in range(n)}
    bal = [0.0] * n            # carried balance under mutual credit (negative = owes the ring)
    turnover = [0.0] * n       # cumulative settled sales, the base for earned lines
    gross = bil = multi = credit_settled = 0.0
    hit_line = [False] * n
    for _ in range(periods):
        O = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in partners[i]:
                if rng.random() < 0.6:  # not every partner trades every period
                    O[j][i] += rng.lognormvariate(3.0, 0.8)  # j owes i (i sold to j)
        g = sum(map(sum, O)); gross += g
        # 1. bilateral netting
        b = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                b += 2 * min(O[i][j], O[j][i])
        bil += b
        # 2. multilateral netting: net position per member
        net = [sum(O[j][i] for j in range(n)) - sum(O[i][j] for j in range(n)) for i in range(n)]  # receivable minus payable
        net_debt = sum(-x for x in net if x < 0)
        multi += g - net_debt
        # 3. earned credit lines absorb net debt up to the line; cash settles the rest
        for i in range(n):
            turnover[i] += sum(O[j][i] for j in range(n))
            line = floor + r * turnover[i]
            bal[i] += net[i]
            if net[i] < 0:
                if bal[i] < -line:
                    cash = -line - bal[i]   # member pays cash to come back to the line
                    bal[i] = -line
                    hit_line[i] = True
                    credit_settled += -net[i] - cash   # the part of this period's net debt absorbed
                else:
                    credit_settled += -net[i]          # whole net debt absorbed by carried surplus or line
        # members in surplus are paid out of the ring's carried balances (zero-sum), no cash needed
    settled_with_credit = multi + credit_settled
    return {
        "members": n, "density": density, "periods": periods, "line_share_of_turnover": r,
        "gross_volume": round(gross, 0),
        "share_settled_bilateral": round(bil / gross, 3),
        "share_settled_multilateral": round(multi / gross, 3),
        "share_settled_with_earned_credit": round(min(1.0, settled_with_credit / gross), 3),
        "cash_per_100_gross_no_credit": round(100 * (1 - multi / gross), 1),
        "cash_per_100_gross_with_credit": round(100 * max(0.0, 1 - settled_with_credit / gross), 1),
        "members_hitting_line": round(sum(hit_line) / n, 2),
        "mean_partners": round(sum(len(v) for v in partners.values()) / n, 1),
    }


def run():
    """For each size: period netting only; carried balances with no credit line (r = 0, no floor:
    a member may only draw on its own past surplus); carried balances plus the dues-earned line."""
    out = []
    for n in (20, 50, 200):
        for d in (0.05, 0.10, 0.20, 0.40):
            base = simulate(n, d, r=0.0, floor=0.0)
            earned = simulate(n, d)
            row = dict(earned)
            row["share_settled_carried_balances_no_line"] = base["share_settled_with_earned_credit"]
            row["cash_per_100_gross_carried_no_line"] = base["cash_per_100_gross_with_credit"]
            row["points_added_by_carried_balances"] = round(100 * (base["share_settled_with_earned_credit"] - base["share_settled_multilateral"]), 1)
            row["points_added_by_earned_line"] = round(100 * (earned["share_settled_with_earned_credit"] - base["share_settled_with_earned_credit"]), 1)
            out.append(row)
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
