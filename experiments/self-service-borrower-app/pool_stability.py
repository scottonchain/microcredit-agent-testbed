#!/usr/bin/env python3
"""Pool stability with a proven ruin bound, and first-borrower screening.

Operator request, 2026-11-02: give mathematical assurance that the pool is stable,
adjust the numbers, algorithms and assumptions so that the pool grows, and let an
agent filter first-time borrowers to establish trust. This module extends
`steady_state.py` (expected net, break-even, seeded ruin estimate) in three ways.

1. A proven upper bound on the probability of ruin, not only a simulation.
   Let the reserve be R and each loan be s = min(P, e * R) (the NORTH_STAR exposure
   rule, e = 1/5). On repayment the reserve gains s * rate - c, on default it loses
   s * L + c, where L is the share of the loan the pool itself loses after the
   backers' stake is slashed, and c is the per-loan cost. Write the relative change
   as X = lambda * X', where lambda = s / (e * R) is in (0, 1] and X' is the change
   that would occur if every loan were exactly e * R:

       X' = e * (rate - k)  with probability 1 - d,
       X' = e * (-L - k)    with probability d,

   with k = max(c / P, c / (e * pause)) an upper bound on cost as a share of the
   loan while the reserve is above the pause level (lending pauses below it, so the
   smallest loan ever made is e * pause). Because (1 + lambda x) ** -theta is
   convex in lambda and equals 1 at lambda = 0, and because the cost bound makes
   X >= lambda * X' pathwise, M_n = R_n ** -theta is a supermartingale whenever
   theta solves E[(1 + X') ** -theta] = 1 (the Lundberg equation). Optional
   stopping then gives, for a reserve starting at R0,

       P(reserve ever falls below pause) <= (pause / R0) ** theta.

   theta exists and is positive exactly when E[log(1 + X')] > 0, the condition for
   the pool to grow almost surely rather than merely in expectation. The bound is
   conservative: it charges every loan the worst-case cost share and it ignores the
   fact that large reserves make fixed-size loans and therefore smaller relative
   swings. A seeded simulation with the same inputs is reported beside it; the bound
   must dominate the simulation, and the tests check that it does.

2. Screening of first-time borrowers by an agent. An applicant population with raw
   per-loan default d0 is filtered with sensitivity s (share of would-be defaulters
   rejected) and false-rejection rate f (share of good applicants rejected). The
   admitted default rate is

       d1 = d0 (1 - s) / (d0 (1 - s) + (1 - d0)(1 - f)),

   the admission rate is d0 (1 - s) + (1 - d0)(1 - f), and the screening cost per
   funded first loan is the cost per applicant divided by the admission rate.
   Screening is claimed only against honest-but-risky applicants. Against free
   identities (research/ring-attacks-on-agent-trust-systems.md) a filter has no
   power: an attacker creates identities until one passes. The only defence is
   that passing costs something the attacker cannot recover, which here is a named
   backer's slashable stake covering the first loan (backing share b1 >= 1 means
   the pool loses nothing on a first-loan default, whoever the borrower is). A
   design with b1 < 1 therefore passes only under the additional assumption that
   one person holds one line (partner KYC or proof of personhood).

3. Two tiers. First loans (screened, small cap, backing share b1) and repeat loans
   (borrowers who repaid, larger cap, backing share b2, default d_r = rho * d1).
   In steady state with n repeat loans per surviving borrower, the share of first
   loans among all loans is m = 1 / (1 + n (1 - d1)).

Two scorecards, never mixed (NORTH_STAR.md). The pool scorecard counts the pool
alone: it keeps (1 - beta) of interest and loses (1 - b) of a defaulted loan. The
system scorecard counts pool plus backers' stakes: all interest, all losses. A
design that grows the pool by moving losses onto backers must show what the
backers earn for it; the system drift is that number per loan.

Every input is a labelled assumption. Nothing here measures a live default rate,
screening accuracy or cost. Standard library only; deterministic for a seed.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, asdict

DAYS_IN_YEAR = 365


# ----------------------------------------------------------------------------
# Screening
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Screen:
    """An agent filter on first-time applicants. Rates are per applicant."""
    sensitivity: float = 0.0       # share of would-be defaulters rejected
    false_rejection: float = 0.0   # share of good applicants rejected
    cost_per_applicant: float = 0.0  # inference, evidence checks, support, per applicant
    label: str = "no screen"

    def validate(self) -> None:
        for name in ("sensitivity", "false_rejection"):
            v = getattr(self, name)
            if not 0 <= v <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.cost_per_applicant < 0:
            raise ValueError("cost_per_applicant must be non-negative")


def screened_default(raw_default: float, screen: Screen) -> dict:
    """Admitted default rate, admission rate and screening cost per funded first loan."""
    screen.validate()
    if not 0 <= raw_default < 1:
        raise ValueError("raw_default must be in [0, 1)")
    bad = raw_default * (1 - screen.sensitivity)
    good = (1 - raw_default) * (1 - screen.false_rejection)
    admitted = bad + good
    if admitted <= 0:
        return {"admitted_default": 0.0, "admission_rate": 0.0, "screen_cost_per_loan": math.inf}
    return {
        "admitted_default": bad / admitted,
        "admission_rate": admitted,
        "screen_cost_per_loan": screen.cost_per_applicant / admitted,
    }


# ----------------------------------------------------------------------------
# Design and its per-loan outcome distribution
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Design:
    term_days: int = 90
    apr: float = 0.0933            # live testnet rate
    first_cap: float = 10.0        # first-loan cap, USDC
    repeat_cap: float = 20.0       # repeat-loan cap, USDC (a fifth of a 100 USDC reserve)
    backing_first: float = 1.0     # named backer's stake as a share of a first loan
    backing_repeat: float = 0.5    # backer stake share on repeat loans
    backer_interest_share: float = 0.0  # share of interest paid to backers (Design Question 2)
    cost_per_loan: float = 0.02    # gas subsidy, paymaster surcharge, support, per loan
    repeat_loans_per_borrower: float = 4.0  # n: repeat loans a surviving borrower takes
    repeat_default_ratio: float = 0.5       # rho: repeat default = rho * admitted first default
    screen: Screen = Screen()
    label: str = ""

    def validate(self) -> None:
        if self.term_days <= 0 or self.first_cap <= 0 or self.repeat_cap <= 0:
            raise ValueError("term and caps must be positive")
        if self.apr < 0 or self.cost_per_loan < 0 or self.repeat_loans_per_borrower < 0:
            raise ValueError("apr, cost and repeat count must be non-negative")
        for name in ("backing_first", "backing_repeat"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if not 0 <= self.backer_interest_share <= 1:
            raise ValueError("backer_interest_share must be in [0, 1]")
        if not 0 <= self.repeat_default_ratio <= 1:
            raise ValueError("repeat_default_ratio must be in [0, 1]")
        self.screen.validate()

    @property
    def rate(self) -> float:
        """Interest as a share of principal over one term."""
        return self.apr * self.term_days / DAYS_IN_YEAR


@dataclass(frozen=True)
class Outcome:
    prob: float
    cap: float        # loan cap for this tier, USDC
    pool_gain: float  # pool result as a share of the loan (positive on repay, negative on default)
    system_gain: float  # pool plus backers, as a share of the loan
    cost: float       # fixed cost per loan, USDC (charged to the pool)
    tier: str
    event: str


def outcomes(design: Design, raw_default: float) -> list[Outcome]:
    """Per-loan outcome distribution for a steady-state mix of first and repeat loans."""
    design.validate()
    sc = screened_default(raw_default, design.screen)
    d1 = sc["admitted_default"]
    dr = design.repeat_default_ratio * d1
    n = design.repeat_loans_per_borrower
    m = 1.0 / (1.0 + n * (1 - d1))  # share of loans that are first loans
    rate = design.rate
    pool_rate = (1 - design.backer_interest_share) * rate
    rows = []
    for tier, share, d, cap, b, extra_cost in (
        ("first", m, d1, design.first_cap, design.backing_first, sc["screen_cost_per_loan"]),
        ("repeat", 1 - m, dr, design.repeat_cap, design.backing_repeat, 0.0),
    ):
        if share <= 0:
            continue
        pool_lgd = max(0.0, 1.0 - b)
        cost = design.cost_per_loan + extra_cost
        rows.append(Outcome(share * (1 - d), cap, pool_rate, rate, cost, tier, "repaid"))
        if d > 0:
            rows.append(Outcome(share * d, cap, -pool_lgd, -1.0, cost, tier, "defaulted"))
    return rows


def expected_net_per_loan(design: Design, raw_default: float) -> dict:
    """Expected USDC change per loan at the caps, for the pool and for the system."""
    pool = system = 0.0
    for o in outcomes(design, raw_default):
        pool += o.prob * (o.cap * o.pool_gain - o.cost)
        system += o.prob * (o.cap * o.system_gain - o.cost)
    sc = screened_default(raw_default, design.screen)
    return {"pool": pool, "system": system, "admitted_first_default": sc["admitted_default"],
            "admission_rate": sc["admission_rate"]}


# ----------------------------------------------------------------------------
# Lundberg bound
# ----------------------------------------------------------------------------

def _relative_outcomes(design: Design, raw_default: float, exposure_share: float, pause: float) -> list[tuple[float, float]]:
    """(probability, X') pairs: the relative reserve change if every loan were e * R, cost at its bound."""
    rows = []
    for o in outcomes(design, raw_default):
        k = max(o.cost / o.cap, o.cost / (exposure_share * pause))
        rows.append((o.prob, exposure_share * (o.pool_gain - k)))
    return rows


def log_drift(design: Design, raw_default: float, exposure_share: float = 0.2, pause: float = 25.0) -> float:
    """E[log(1 + X')]: positive means the reserve grows almost surely (strong law), at the cost bound."""
    total = 0.0
    for p, x in _relative_outcomes(design, raw_default, exposure_share, pause):
        if 1 + x <= 0:
            return -math.inf
        total += p * math.log1p(x)
    return total


def lundberg_exponent(design: Design, raw_default: float, exposure_share: float = 0.2, pause: float = 25.0,
                      tol: float = 1e-10) -> float | None:
    """theta > 0 with E[(1 + X') ** -theta] = 1, or None if the drift condition fails.

    Returns math.inf when no outcome is negative (ruin is impossible).
    """
    rows = _relative_outcomes(design, raw_default, exposure_share, pause)
    if any(1 + x <= 0 for _, x in rows):
        return None
    if log_drift(design, raw_default, exposure_share, pause) <= 0:
        return None
    if all(x >= 0 for _, x in rows):
        return math.inf

    def phi(theta: float) -> float:
        return sum(p * (1 + x) ** (-theta) for p, x in rows) - 1.0

    # phi(0) = 0, phi decreasing just after 0 (positive drift), convex, -> +inf. Find the second root.
    lo, hi = 0.0, 1.0
    while phi(hi) < 0:
        hi *= 2
        if hi > 1e6:
            return math.inf
    # phi(lo) is 0 at lo = 0; move lo to a point where phi < 0 so bisection brackets the positive root.
    lo = hi / 2
    while phi(lo) >= 0 and lo > tol:
        lo /= 2
    if phi(lo) >= 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if phi(mid) < 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return (lo + hi) / 2


def ruin_bound(design: Design, raw_default: float, reserve: float = 100.0, pause: float = 25.0,
               exposure_share: float = 0.2) -> dict:
    """Proven upper bound on P(reserve ever falls below `pause`), starting from `reserve`."""
    if reserve <= pause or pause <= 0:
        raise ValueError("reserve must exceed pause, and pause must be positive")
    theta = lundberg_exponent(design, raw_default, exposure_share, pause)
    drift = log_drift(design, raw_default, exposure_share, pause)
    if theta is None:
        bound = 1.0
    elif theta == math.inf:
        bound = 0.0
    else:
        bound = (pause / reserve) ** theta
    return {"theta": theta, "log_drift_per_loan": drift, "ruin_bound": bound,
            "reserve": reserve, "pause": pause, "exposure_share": exposure_share}


# ----------------------------------------------------------------------------
# Seeded simulation (cross-check; must sit under the bound)
# ----------------------------------------------------------------------------

def simulate(design: Design, raw_default: float, reserve: float = 100.0, pause: float = 25.0, loans: int = 500,
             runs: int = 2000, seed: int = 11, exposure_share: float = 0.2) -> dict:
    """Share of seeded runs in which the reserve falls below `pause` within `loans` loans.

    Loans are drawn from the steady-state tier mix at the tier cap, capped at e * R. Stakes
    slashed from backers and interest paid to backers are tracked for the system scorecard.
    """
    design.validate()
    rows = outcomes(design, raw_default)
    probs = [o.prob for o in rows]
    cum = []
    acc = 0.0
    for p in probs:
        acc += p
        cum.append(acc)
    rng = random.Random(seed)
    ruined = 0
    finals, systems = [], []
    for _ in range(runs):
        r = reserve
        stakes_lost = backer_interest = 0.0
        paused = False
        for _ in range(loans):
            u = rng.random() * cum[-1]
            o = rows[next(i for i, c in enumerate(cum) if u <= c)]
            size = min(o.cap, exposure_share * r)
            if o.event == "repaid":
                r += size * o.pool_gain
                backer_interest += size * (o.system_gain - o.pool_gain)
            else:
                r += size * o.pool_gain  # pool_gain is -(1 - b): the pool's share of the loss
                stakes_lost += size * (1.0 + o.pool_gain)  # the backers' share of the loss, at most the loan
            r -= o.cost
            if r < pause:
                paused = True
                break
        if paused:
            ruined += 1
        finals.append(r)
        systems.append(r + backer_interest - stakes_lost)
    finals.sort()
    systems.sort()
    return {"runs": runs, "loans": loans, "ruin_probability": ruined / runs,
            "median_final_reserve": finals[len(finals) // 2], "p10_final_reserve": finals[len(finals) // 10],
            "median_final_system": systems[len(systems) // 2], "p10_final_system": systems[len(systems) // 10]}


# ----------------------------------------------------------------------------
# Assessment and search
# ----------------------------------------------------------------------------

RAW_BAND = (0.03, 0.05, 0.10, 0.20)  # per-loan default of the unscreened first-loan population

# Operator design constraint, 2026-11-02: the agent filter is built and measured so that the raw per-loan
# default of the population it admits is at most this. It is the system scorecard's growth ceiling at the
# live rate for the open-access design (both tiers fully backed, evidence-plus-backer screen). It is an
# assumption to be measured, not a measurement: the pilot's binomial interval on observed defaults tests it.
FILTER_DEFAULT_CEILING = 0.11


def assess(design: Design, raw_default: float, reserve: float = 100.0, pause: float = 25.0, runs: int = 0,
           loans: int = 500, seed: int = 11, ruin_threshold: float = 0.01) -> dict:
    """One design at one raw default rate: drifts, bound, optional simulation, pass flags."""
    net = expected_net_per_loan(design, raw_default)
    bound = ruin_bound(design, raw_default, reserve, pause)
    row = {
        "raw_default": raw_default,
        "admitted_first_default": round(net["admitted_first_default"], 4),
        "admission_rate": round(net["admission_rate"], 4),
        "pool_net_per_loan": round(net["pool"], 4),
        "system_net_per_loan": round(net["system"], 4),
        "log_drift_per_loan": None if bound["log_drift_per_loan"] == -math.inf else round(bound["log_drift_per_loan"], 6),
        "theta": None if bound["theta"] in (None, math.inf) else round(bound["theta"], 3),
        "ruin_bound": round(bound["ruin_bound"], 6),
    }
    if runs:
        sim = simulate(design, raw_default, reserve, pause, loans, runs, seed)
        row.update({"ruin_simulated": sim["ruin_probability"],
                    "median_final_reserve": round(sim["median_final_reserve"], 1),
                    "p10_final_reserve": round(sim["p10_final_reserve"], 1),
                    "median_final_system": round(sim["median_final_system"], 1)})
    row["pool_grows"] = net["pool"] > 0 and bound["ruin_bound"] <= ruin_threshold
    row["system_grows"] = net["system"] > 0
    row["within_filter_ceiling"] = raw_default <= FILTER_DEFAULT_CEILING
    return row


def max_raw_default_passing(design: Design, reserve: float = 100.0, pause: float = 25.0, ruin_threshold: float = 0.01,
                            step: float = 0.01, limit: float = 0.5) -> dict:
    """Largest raw default rate (to `step`) at which the pool passes, and at which the system passes."""
    pool_max = system_max = None
    d = 0.0
    while d <= limit + 1e-12:
        row = assess(design, d, reserve, pause, ruin_threshold=ruin_threshold)
        if row["pool_grows"]:
            pool_max = round(d, 4)
        if row["system_grows"]:
            system_max = round(d, 4)
        d += step
    return {"pool_max_raw_default": pool_max, "system_max_raw_default": system_max}


SCREENS = {
    "none": Screen(0.0, 0.0, 0.0, "no screen"),
    "evidence": Screen(0.6, 0.2, 0.05, "agent evidence review: rejects 60% of would-be defaulters, 20% of good applicants, 5 cents"),
    "evidence+backer": Screen(0.8, 0.3, 0.10, "evidence review plus a named backer's record: 80% / 30%, 10 cents"),
}


def candidate_designs() -> list[Design]:
    """A small labelled grid; the search reports which members pass across the raw band."""
    out = []
    for term in (30, 90):
        for apr in (0.0933, 0.1833):
            for b1, b2 in ((0.0, 0.0), (0.5, 0.25), (1.0, 0.5), (1.0, 1.0)):
                for key in ("none", "evidence", "evidence+backer"):
                    label = f"{term}d, {apr:.2%}, first backing {b1:.0%}, repeat backing {b2:.0%}, screen {key}"
                    out.append(Design(term_days=term, apr=apr, backing_first=b1, backing_repeat=b2,
                                      screen=SCREENS[key], label=label))
    return out


def search(reserve: float = 100.0, pause: float = 25.0, ruin_threshold: float = 0.01, band=RAW_BAND,
           designs: list[Design] | None = None) -> list[dict]:
    rows = []
    for design in designs or candidate_designs():
        points = [assess(design, d, reserve, pause, ruin_threshold=ruin_threshold) for d in band]
        limits = max_raw_default_passing(design, reserve, pause, ruin_threshold)
        rows.append({
            "design": design.label,
            "pool_passes_band": all(p["pool_grows"] for p in points),
            "system_passes_band": all(p["system_grows"] for p in points),
            **limits,
            "points": points,
        })
    rows.sort(key=lambda r: (r["pool_passes_band"], r["system_passes_band"], r["pool_max_raw_default"] or 0,
                             r["system_max_raw_default"] or 0), reverse=True)
    return rows


# ----------------------------------------------------------------------------
# Pilot stop rule
# ----------------------------------------------------------------------------

def binomial_tail(n: int, k: int, p: float) -> float:
    """P(at least k defaults in n loans) at per-loan default p."""
    if not 0 <= p <= 1 or n < 0 or k < 0:
        raise ValueError("bad arguments")
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def stop_rule_power(n: int = 20, k: int = 2, rates=(0.01, 0.03, 0.05, 0.10, 0.20)) -> list[dict]:
    """How often the pilot stop rule (k defaults in n loans) fires at each true default rate."""
    return [{"true_default": p, "stop_probability": round(binomial_tail(n, k, p), 4)} for p in rates]


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def recommended_design() -> Design:
    """Open-access design: anyone with the app. Both tiers fully backed, so the pool never loses principal.

    With free identities a half-backed repeat loan is farmable: a two-identity ring repays one 10 USDC
    first loan, borrows 20 against a 10 USDC stake from its second identity, defaults and keeps 10.
    Full backing on both tiers removes that take; the pool is then a senior lender and the backers
    carry the credit risk, which the system scorecard shows.
    """
    return Design(term_days=90, apr=0.0933, first_cap=10.0, repeat_cap=20.0, backing_first=1.0, backing_repeat=1.0,
                  backer_interest_share=0.0, cost_per_loan=0.02, repeat_loans_per_borrower=4.0,
                  repeat_default_ratio=0.5, screen=SCREENS["evidence+backer"],
                  label="open access: 90d, live rate, both tiers fully backed, screened first loans")


def named_cohort_design() -> Design:
    """Named-cohort variant: one person holds one line (partner KYC), so repeat loans can be half backed.

    Doubles the loans a backer's dollar can support; valid only where identities are not free.
    """
    return Design(term_days=90, apr=0.0933, first_cap=10.0, repeat_cap=20.0, backing_first=1.0, backing_repeat=0.5,
                  backer_interest_share=0.0, cost_per_loan=0.02, repeat_loans_per_borrower=4.0,
                  repeat_default_ratio=0.5, screen=SCREENS["evidence+backer"],
                  label="named cohort: 90d, live rate, first loans fully backed, repeat half backed, one line per person")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--search", action="store_true", help="assess the candidate grid across the raw default band")
    parser.add_argument("--recommended", action="store_true", help="assess the recommended design with simulation")
    parser.add_argument("--stop-rule", action="store_true", help="power of the k-in-n pilot stop rule")
    parser.add_argument("--raw-default", type=float, default=0.10)
    parser.add_argument("--reserve", type=float, default=100.0)
    parser.add_argument("--pause", type=float, default=25.0)
    parser.add_argument("--runs", type=int, default=2000)
    parser.add_argument("--loans", type=int, default=500)
    args = parser.parse_args(argv)
    if args.search:
        print(json.dumps(search(args.reserve, args.pause), indent=1))
        return 0
    if args.stop_rule:
        print(json.dumps(stop_rule_power(), indent=1))
        return 0
    out = {"note": "Assumptions, not measurements. Pool growth is the reserve scorecard; human benefit is scored separately."}
    for design in (recommended_design(), named_cohort_design()):
        out[design.label] = {
            "design": asdict(design),
            "limits": max_raw_default_passing(design, args.reserve, args.pause),
            "filter_default_ceiling": FILTER_DEFAULT_CEILING,
            "at_ceiling": assess(design, FILTER_DEFAULT_CEILING, args.reserve, args.pause),
            "points": [assess(design, d, args.reserve, args.pause, runs=args.runs if args.recommended else 0,
                              loans=args.loans) for d in (RAW_BAND if args.recommended else (args.raw_default,))],
        }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
