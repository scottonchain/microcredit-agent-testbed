#!/usr/bin/env python3
"""Offline 409/key-switch regression; synthetic provider, NOT a provider test.

Credit: clawdbdc b85301b4 and merktop 92007d5d, recorded in retry-fixture
README/email-16. Source-case statuses and existing reference scripts are untouched.
Times are arbitrary simulated ticks, not a recommended retry/retention policy.
Only the evaluator reads provider effects; Client receives response dictionaries.
Run: python3 retry-fixture/reference/in_progress_409.py [--json]
"""
import json
import sys


class ToyProvider:
    """Atomic key lookup; completing work creates one effect and starts retention.

    The first request can remain pending forever. New keys create distinct work,
    even for the same logical intent. No real API, cancellation or status endpoint.
    """
    def __init__(self, first_completion=4, retention=10):
        self.first_completion = first_completion
        self.retention = retention
        self.records = []
        self.effects = []
        self.calls = 0
        self.now = 0

    def advance(self, now):
        if now < self.now:
            raise ValueError("clock cannot move backwards")
        self.now = now
        for r in self.records:
            if r["done_at"] is not None and now >= r["done_at"] and not r["done"]:
                r["done"] = True
                self.effects.append({"intent": r["intent"], "message_id": r["id"]})

    def request(self, now, key, intent, payload):
        self.advance(now)
        self.calls += 1
        for r in reversed(self.records):
            if r["key"] != key:
                continue
            if r["done"] and now >= r["done_at"] + self.retention:
                break  # This key's record is pruned; an identical retry is new work.
            if (intent, payload) != (r["intent"], r["payload"]):
                return {"status": 409, "kind": "payload_conflict", "key": key}
            if not r["done"]:
                return {"status": 409, "kind": "in_progress", "key": key}
            return {"status": 200, "kind": "replay", "key": key, "id": r["id"]}
        r = {"key": key, "intent": intent, "payload": payload,
             "id": "message-" + str(len(self.records) + 1), "done": False,
             "done_at": self.first_completion if not self.records else now + 1}
        self.records.append(r)
        return {"status": 202, "kind": "pending", "key": key}


class Client:
    """Worker state: no provider truth, no inferred failure from timeout or 409."""
    def __init__(self, request):
        self.request = request
        self.intent = "synthetic-intent"
        self.key = "original-key"
        self.payload = "synthetic-body"
        self.outcomes = {self.key: "unknown"}
        self.trace = []
        self.review_reason = None

    def dispatch(self, now, lose_response=False):
        response = self.request(now, self.key, self.intent, self.payload)
        if lose_response:
            response = None
        self.trace.append({"at": now, "key": self.key, "response": response})
        if response and response["status"] == 200 and response["key"] == self.key:
            self.outcomes[self.key] = "confirmed"
        elif response and response["kind"] == "payload_conflict":
            self.review_reason = "payload_conflict"
        # 202, lost response and in-progress 409 leave the outcome unknown.

    def retry(self, now, deadline=9, safe_retention=10,
              switch_key=False, ignore_retention=False):
        if self.review_reason or self.outcomes[self.key] == "confirmed":
            return
        if now >= deadline:
            self.review_reason = "deadline"
            return
        # First dispatch was at zero. This guard is conservative: real completion
        # may be later, but the worker does not know when that occurred.
        if now >= safe_retention and not ignore_retention:
            self.review_reason = "retention_uncertain"
            return
        if switch_key:  # Deliberately unsafe negative control, not the policy.
            self.key = "replacement-key"
            self.outcomes[self.key] = "unknown"
        self.dispatch(now)


def run(case):
    p = ToyProvider(first_completion=None if case == "deadline" else 4)
    c = Client(p.request)
    c.dispatch(0, lose_response=True)
    c.retry(1)  # Every scenario starts with the same in-progress 409 observation.
    after_409 = dict(c.outcomes)
    if case == "hold":
        c.retry(5)
        horizon = 5
    elif case == "switch_control":
        c.retry(2, switch_key=True)
        c.retry(5)
        horizon = 5
    elif case == "deadline":
        c.retry(5)
        c.retry(9)
        horizon = 9
    elif case in ("expiry_guard", "expiry_control"):
        c.retry(15, deadline=30, ignore_retention=case == "expiry_control")
        c.retry(17, deadline=30, ignore_retention=case == "expiry_control")
        horizon = 17
    elif case == "payload_conflict":
        c.payload = "changed-body"
        c.retry(2)
        c.retry(5)
        horizon = 5
    else:
        raise ValueError(case)
    p.advance(horizon)  # Evaluator only; never fed back to the worker.
    return {"case": case, "intent": c.intent, "after_409": after_409,
            "outcomes": c.outcomes, "review_reason": c.review_reason,
            "worker_trace": c.trace, "horizon": horizon,
            "evaluator": {"effects": len(p.effects),
                          "pending": sum(not r["done"] for r in p.records),
                          "provider_calls": p.calls}}


# Independent scenario expectations: effects, pending, calls, original outcome,
# active/replacement outcome if any, and review reason. Negative controls must
# reveal their duplicate rather than pass a no-duplicate safety criterion.
EXPECTED = {
    "hold": (1, 0, 3, "confirmed", None, None),
    "switch_control": (2, 0, 4, "unknown", "confirmed", None),
    "deadline": (0, 1, 3, "unknown", None, "deadline"),
    "expiry_guard": (1, 0, 2, "unknown", None, "retention_uncertain"),
    "expiry_control": (2, 0, 4, "confirmed", None, None),
    "payload_conflict": (1, 0, 3, "unknown", None, "payload_conflict"),
}


def check(result):
    e, o = result["evaluator"], result["outcomes"]
    got = (e["effects"], e["pending"], e["provider_calls"],
           o["original-key"], o.get("replacement-key"), result["review_reason"])
    trace = result["worker_trace"]
    return (got == EXPECTED[result["case"]]
            and result["after_409"] == {"original-key": "unknown"}
            and trace[1]["response"] ==
            {"status": 409, "kind": "in_progress", "key": "original-key"})


def main():
    rows = [run(name) for name in EXPECTED]
    for row in rows:
        row["matches_expected"] = check(row)
    if "--json" in sys.argv[1:]:
        print(json.dumps({"scope": "internal synthetic model only", "cells": rows}, indent=2))
    else:
        for r in rows:
            print(r["case"], r["evaluator"], r["outcomes"],
                  r["review_reason"], "OK" if r["matches_expected"] else "FAIL")
    return 0 if all(r["matches_expected"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
