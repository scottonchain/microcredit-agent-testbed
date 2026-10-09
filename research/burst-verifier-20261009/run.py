#!/usr/bin/env python3
"""Offline, deterministic audit-capacity experiment. Python 3.10+, stdlib only.

Credit: specie suggested burst-mode falsification on Moltbook, 2026-10-04.
This is a new synthetic experiment, not a calibration challenge or chain test.
Policies see arrival order and immutable claims; only the verifier reads grants.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

ROOT = Path(__file__).resolve().parent
CONFIG = {
    "ticks": 300, "background_per_tick": 20, "injected_records": 1000,
    "burst_start": 40, "widths": [1, 5, 20, 100],
    "invalid_percentages": [0, 1, 25, 100], "budgets": [24, 40],
    "queue_capacity": 480, "deadline_ticks": 10, "seeds": list(range(32)),
    "policies": ["random_now", "bounded_fifo", "eventual_fifo"],
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class Claim:
    id: str
    tick: int
    grant: str
    version: int
    amount: int
    injected: bool


def make_stream(seed: int, width: int, invalid_pct: int,
                injected_count: int = 1000, one_bad: bool = False):
    """Changing invalid_pct preserves IDs, arrival order and total offered load.

    All claims are independent requests against separate fixed grants. They do
    not accumulate balances, execute loans or mutate authoritative state.
    """
    buckets = [[] for _ in range(CONFIG["ticks"])]
    grants = {}
    invalid_ids = set()
    bad_indices = set(sorted(range(injected_count),
                             key=lambda j: digest(f"{seed}/invalid/{j}"))
                      [:injected_count * invalid_pct // 100])
    for tick in range(CONFIG["ticks"]):
        for j in range(CONFIG["background_per_tick"]):
            cid = f"b{tick:03d}-{j:02d}"
            grants[cid] = {"version": 1, "limit": 100}
            bad = one_bad and tick == 10 and j == 0
            buckets[tick].append(Claim(cid, tick, cid, 1, 101 if bad else 50, False))
            if bad:
                invalid_ids.add(cid)
    for j in range(injected_count):
        tick = CONFIG["burst_start"] + j * width // injected_count
        cid = f"i{j:04d}"
        grants[cid] = {"version": 1, "limit": 100}
        grant, version, amount = cid, 1, 50
        if j in bad_indices:
            invalid_ids.add(cid)
            if j % 3 == 0:
                amount = 101                 # exceeds the fixed grant
            elif j % 3 == 1:
                version = 2                  # stale/wrong grant version
            else:
                grant = f"absent-{cid}"      # no such grant
        buckets[tick].append(Claim(cid, tick, grant, version, amount, True))
    for bucket in buckets:
        bucket.sort(key=lambda x: digest(f"{seed}/arrival/{x.id}"))
    return buckets, grants, invalid_ids


def verify_claim(claim: Claim, grants: dict) -> bool:
    """True means invalid; never reads generator labels or injected flag."""
    grant = grants.get(claim.grant)
    return (grant is None or claim.version != grant["version"]
            or type(claim.amount) is not int or claim.amount <= 0
            or claim.amount > grant["limit"])


def simulate(buckets, grants, policy, budget, seed,
             queue_capacity=None, deadline=None):
    """No quarantine effect after an alarm: continue to measure audit coverage.

    random_now: uniform sample without replacement of arrivals in each tick.
    bounded_fifo: expire age > deadline; append up to capacity; tail-drop the
    excess; serve oldest records. Capacity includes records served this tick.
    eventual_fifo: no expiry or memory bound; drain after arrivals stop. It is
    a latency/memory comparison, not an operationally safe recommendation.
    """
    capacity = CONFIG["queue_capacity"] if queue_capacity is None else queue_capacity
    ttl = CONFIG["deadline_ticks"] if deadline is None else deadline
    queue = deque()
    inspected = []
    dropped = []
    expired = []
    per_tick = []
    peak_queue = 0
    rng = random.Random(seed + 20261009)
    tick = 0
    while tick < len(buckets) or queue:
        arrivals = buckets[tick] if tick < len(buckets) else []
        if policy == "random_now":
            # Index selection depends on arrival order, never on validity.
            chosen = set(rng.sample(range(len(arrivals)), min(budget, len(arrivals))))
            work = [c for i, c in enumerate(arrivals) if i in chosen]
            dropped.extend(c for i, c in enumerate(arrivals) if i not in chosen)
        else:
            if policy == "bounded_fifo":
                while queue and tick - queue[0].tick > ttl:
                    expired.append(queue.popleft())
                for claim in arrivals:
                    if len(queue) < capacity:
                        queue.append(claim)
                    else:
                        dropped.append(claim)
            elif policy == "eventual_fifo":
                queue.extend(arrivals)
            else:
                raise ValueError(policy)
            peak_queue = max(peak_queue, len(queue))
            work = [queue.popleft() for _ in range(min(budget, len(queue)))]
        per_tick.append(len(work))
        inspected.extend((claim, tick, verify_claim(claim, grants)) for claim in work)
        tick += 1
    return {"inspected": inspected, "dropped": dropped, "expired": expired,
            "per_tick": per_tick, "peak_queue": peak_queue}


def quantile(values, p):
    return sorted(values)[max(0, math.ceil(len(values) * p) - 1)] if values else None


def score_run(buckets, grants, truth, run):
    all_claims = [c for bucket in buckets for c in bucket]
    inspected = run["inspected"]
    found = [(c, t) for c, t, bad in inspected if bad]
    deadline = CONFIG["deadline_ticks"]
    timely = [(c, t) for c, t in found if t - c.tick <= deadline]
    flagged = {c.id for c, _ in found}
    labels = {c.id for c in all_claims if verify_claim(c, grants)}
    if labels != truth:
        raise AssertionError("Full grant validator disagrees with planted labels")
    selected = [c.id for c, _, _ in inspected]
    rejected = [c.id for c in run["dropped"] + run["expired"]]
    if len(set(selected + rejected)) != len(all_claims) or len(selected + rejected) != len(all_claims):
        raise AssertionError("Each arrival must be inspected or explicitly unreviewed once")
    if not flagged <= truth:
        raise AssertionError("False positive from exact grant validator")
    delays = [t - c.tick for c, t in found]
    valid_delays = [t - c.tick for c, t, bad in inspected if not bad]
    first_bad_arrival = min((c.tick for c in all_claims if c.id in truth), default=None)
    return {
        "submitted": len(all_claims), "invalid": len(truth),
        "inspected": len(inspected), "detected": len(found),
        "timely_detected": len(timely), "false_positives": len(flagged - truth),
        "recall": len(found) / len(truth) if truth else None,
        "timely_recall": len(timely) / len(truth) if truth else None,
        "any_detection": bool(found),
        "first_alarm_delay": min((t for _, t in found), default=0) - first_bad_arrival if found else None,
        "invalid_delay_p95": quantile(delays, .95),
        "valid_delay_p95": quantile(valid_delays, .95),
        "valid_timely_reviewed": sum(not bad and t - c.tick <= deadline for c, t, bad in inspected),
        "valid_submitted": len(all_claims) - len(truth),
        "capacity_dropped": len(run["dropped"]), "expired": len(run["expired"]),
        "invalid_capacity_dropped": sum(c.id in truth for c in run["dropped"]),
        "invalid_expired": sum(c.id in truth for c in run["expired"]),
        "max_tick_work": max(run["per_tick"], default=0),
        "observed_ticks": len(run["per_tick"]),
        "post_arrival_drain_ticks": max(0, len(run["per_tick"]) - len(buckets)),
        "peak_queue": run["peak_queue"],
        "selection_sha256": digest("\n".join(selected)),
    }


def random_expectation(buckets, truth, budget):
    """Exact conditional hypergeometric mean/variance and probability of alarm.

    Conditions on each generated arrival bucket, independent uniform draws per
    tick. These calculations are separate from the scheduling implementation.
    """
    mean, variance, no_alarm = 0.0, 0.0, 1.0
    for arrivals in buckets:
        population = len(arrivals)
        bad = sum(c.id in truth for c in arrivals)
        n = min(budget, population)
        if not population:
            continue
        p = bad / population
        mean += n * p
        if population > 1:
            variance += n * p * (1-p) * (population-n) / (population-1)
        no_alarm *= (math.comb(population-bad, n) / math.comb(population, n)
                     if population-bad >= n else 0.0)
    return {"mean_detected": mean, "variance_detected": variance,
            "probability_any_detection": 1 - no_alarm}


def average(items, field):
    values = [x[field] for x in items if x[field] is not None]
    return statistics.mean(values) if values else None


def run_experiment():
    runs, summary, controls = [], [], []
    for width in CONFIG["widths"]:
        for invalid_pct in CONFIG["invalid_percentages"]:
            for seed in CONFIG["seeds"]:
                buckets, grants, truth = make_stream(seed, width, invalid_pct)
                for budget in CONFIG["budgets"]:
                    for policy in CONFIG["policies"]:
                        run = simulate(buckets, grants, policy, budget, seed)
                        scored = score_run(buckets, grants, truth, run)
                        assert scored["max_tick_work"] <= budget
                        if policy == "bounded_fifo":
                            assert scored["peak_queue"] <= CONFIG["queue_capacity"]
                        row = {"width": width, "invalid_pct": invalid_pct,
                               "seed": seed, "budget": budget, "policy": policy, **scored}
                        if policy == "random_now":
                            row["analytical"] = random_expectation(buckets, truth, budget)
                        runs.append(row)
            for budget in CONFIG["budgets"]:
                for policy in CONFIG["policies"]:
                    rows = [x for x in runs if (x["width"], x["invalid_pct"], x["budget"], x["policy"]) ==
                            (width, invalid_pct, budget, policy)]
                    s = {"width": width, "invalid_pct": invalid_pct, "budget": budget,
                         "policy": policy, "seeds": len(rows),
                         "peak_arrivals_per_tick": CONFIG["background_per_tick"] + CONFIG["injected_records"] // width,
                         "invalid_fraction_during_burst": invalid_pct/100 * CONFIG["injected_records"] /
                         (CONFIG["injected_records"] + width * CONFIG["background_per_tick"]),
                         "detected_seeds": sum(x["any_detection"] for x in rows)}
                    for field in ("recall", "timely_recall", "detected", "timely_detected", "first_alarm_delay",
                                  "invalid_delay_p95", "valid_delay_p95", "peak_queue", "inspected",
                                  "capacity_dropped", "expired", "valid_timely_reviewed", "valid_submitted",
                                  "observed_ticks", "post_arrival_drain_ticks"):
                        s["mean_" + field] = average(rows, field)
                    s["min_timely_recall"] = min((x["timely_recall"] for x in rows if x["timely_recall"] is not None), default=None)
                    s["max_timely_recall"] = max((x["timely_recall"] for x in rows if x["timely_recall"] is not None), default=None)
                    if policy == "random_now":
                        s["analytical_mean_detected"] = statistics.mean(x["analytical"]["mean_detected"] for x in rows)
                        s["analytical_mean_alarm_probability"] = statistics.mean(x["analytical"]["probability_any_detection"] for x in rows)
                        variance = sum(x["analytical"]["variance_detected"] for x in rows)
                        error = sum(x["detected"] - x["analytical"]["mean_detected"] for x in rows)
                        s["aggregate_sampling_z"] = error / math.sqrt(variance) if variance else 0.0
                        assert abs(s["aggregate_sampling_z"]) < 6, "Sampling does not match hypergeometric control"
                    summary.append(s)
    # A single bad claim at normal load must be seen; all-honest load must never
    # produce a false alarm. All primary all-valid burst rows are also controls.
    for bad in (False, True):
        buckets, grants, truth = make_stream(0, 1, 0, injected_count=0, one_bad=bad)
        for policy in CONFIG["policies"]:
            s = score_run(buckets, grants, truth, simulate(buckets, grants, policy, 24, 0))
            assert s["detected"] == int(bad) and s["false_positives"] == 0
            assert s["inspected"] == s["submitted"]
            controls.append({"name": "isolated_invalid" if bad else "benign_baseline", "policy": policy, **s})
    # Full-budget control: every invalid claim is recognizable immediately,
    # independent of concentration. The primary failures are audit selection.
    for width in CONFIG["widths"]:
        buckets, grants, truth = make_stream(0, width, 100)
        max_arrivals = max(map(len, buckets))
        s = score_run(buckets, grants, truth, simulate(buckets, grants, "random_now", max_arrivals, 0))
        assert s["timely_recall"] == 1 and s["first_alarm_delay"] == 0
        controls.append({"name": "full_budget", "width": width, "budget": max_arrivals, **s})
    # The schedules cannot peek at validity. On identical arrival schedules,
    # selection must be byte-identical when only payload validity changes.
    by_schedule = {}
    for row in runs:
        key = row["width"], row["seed"], row["budget"], row["policy"]
        if key in by_schedule:
            assert by_schedule[key] == row["selection_sha256"], "Policy used validity to select work"
        else:
            by_schedule[key] = row["selection_sha256"]
    return {"config": CONFIG, "runs": runs, "summary": summary, "controls": controls,
            "verification": {"mass_balance": True, "budget_bounds": True,
                             "queue_bound": True, "plant_labels_recomputed": True,
                             "validity_blind_selection": True, "hypergeometric_control": True,
                             "isolated_invalid_and_benign_controls": True, "full_budget_controls": True}}


def canonical(data):
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "results.json")
    parser.add_argument("--check", action="store_true", help="recompute and compare without writing")
    args = parser.parse_args()
    result = run_experiment()
    data = canonical(result)
    if args.check:
        if args.out.read_bytes() != data:
            raise SystemExit("FAIL: stored result differs from deterministic recomputation")
    else:
        args.out.write_bytes(data)
    print(json.dumps({"ok": True, "runs": len(result["runs"]), "controls": len(result["controls"]),
                      "sha256": hashlib.sha256(data).hexdigest(), "mode": "check" if args.check else "write"}))


if __name__ == "__main__":
    main()
