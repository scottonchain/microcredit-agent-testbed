#!/usr/bin/env python3
"""Writes the conformance fixture: a tiny synthetic ledger in the calibration-v3 schema plus its answer key.
CONFORMANCE ONLY. It is hand-designed, not drawn from the challenge generator, and shares nothing with the challenge key.
Use it to see score.py run end to end before the reveal:
    python3 make_fixture.py                                   (rewrites corpus.json and key.json here, deterministic)
    python3 ../starter.py corpus.json > sub.json
    python3 ../check_submission.py corpus.json sub.json --any-corpus
    python3 ../score.py corpus.json sub.json key.json"""
import hashlib, json, os

DAY = 86400
T0 = 1790000000
HERE = os.path.dirname(os.path.abspath(__file__))

def addr(name):
    return "0x" + hashlib.sha256(("fixture:" + name).encode()).hexdigest()[:40]

events, loan_id, block = [], 0, 1000

def emit(event, ts, **args):
    global block
    block += 1
    events.append({"event": event, "ts": ts, "block": block, "args": args})

def loan(borrower, amount, t_req, outcome, t_end):
    """outcome: 'repaid' at t_end, or 'defaulted' at t_end (t_end must be > disburse + 30d term + 30d late period)."""
    global loan_id
    loan_id += 1
    lid = loan_id
    emit("LoanRequested", t_req, borrower=borrower, loanId=lid, amount=amount, interestRate=1000, repaymentPeriodDays=30)
    emit("LoanDisbursed", t_req + 3600, borrower=borrower, loanId=lid, amount=amount)
    if outcome == "repaid":
        emit("LoanRepaid", t_end, borrower=borrower, loanId=lid, amount=amount + amount // 20)
    else:
        emit("LoanDefaulted", t_end, borrower=borrower, loanId=lid, writtenOff=amount, recovered=0)
    return lid

emit("Deposited", T0, lender=addr("lender"), assets=2000_000000, shares=2000_000000)
r1, r2, r3 = addr("ring1"), addr("ring2"), addr("ring3")
s1, s2, s3, funder = addr("sybil1"), addr("sybil2"), addr("sybil3"), addr("funder")
bust, late_in, late_out = addr("bustout"), addr("late_inside"), addr("late_outside")
h1, h2, h3 = addr("honest1"), addr("honest2"), addr("honest3")

# ring: three accounts back each other in a cycle and repay on time
for backer, borrower in ((r1, r2), (r2, r3), (r3, r1)):
    emit("Backed", T0 + 1 * DAY, backer=backer, borrower=borrower, secured=0, unsecured=20_000000)
for i, b in enumerate((r1, r2, r3)):
    loan(b, 20_000000, T0 + 2 * DAY + i * 3600, "repaid", T0 + 25 * DAY + i * 3600)
# sybil cluster: one funder backs three accounts that all default
for i, b in enumerate((s1, s2, s3)):
    emit("Backed", T0 + 3 * DAY + i * 600, backer=funder, borrower=b, secured=10_000000, unsecured=0)
    loan(b, 10_000000, T0 + 4 * DAY + i * 3600, "defaulted", T0 + 4 * DAY + 61 * DAY + i * 3600)
# bust-out: two small loans repaid on time, then a large default
loan(bust, 5_000000, T0 + 5 * DAY, "repaid", T0 + 20 * DAY)
loan(bust, 5_000000, T0 + 21 * DAY, "repaid", T0 + 40 * DAY)
loan(bust, 60_000000, T0 + 41 * DAY, "defaulted", T0 + 41 * DAY + 62 * DAY)
# late edge: repaid inside the 30-day late period after the term, and defaulted just after it
loan(late_in, 15_000000, T0 + 6 * DAY, "repaid", T0 + 6 * DAY + 45 * DAY)
loan(late_out, 15_000000, T0 + 7 * DAY, "defaulted", T0 + 7 * DAY + 61 * DAY)
# honest background: two repay, one defaults on its own
loan(h1, 30_000000, T0 + 8 * DAY, "repaid", T0 + 30 * DAY)
loan(h2, 25_000000, T0 + 9 * DAY, "repaid", T0 + 35 * DAY)
loan(h3, 20_000000, T0 + 10 * DAY, "defaulted", T0 + 10 * DAY + 70 * DAY)

events.sort(key=lambda e: (e["ts"], e["block"]))
for i, e in enumerate(events):
    e["block"] = 1001 + i
corpus = {"name": "microcredit-calibration-v3-fixture", "synthetic": True, "seed_published": True,
          "schema": "same event names/args as calibration-v3/corpus.json; CONFORMANCE FIXTURE, not the challenge",
          "events": events}
key = {"note": "CONFORMANCE FIXTURE answer key for fixture/corpus.json; unrelated to the calibration-v3 answer key",
       "key": {"ring": [r1, r2, r3], "sybil_cluster": [s1, s2, s3], "bust_out": [bust],
               "late_edge": {"inside_grace": [late_in], "outside_grace": [late_out]}}}
json.dump(corpus, open(os.path.join(HERE, "corpus.json"), "w"), indent=1, sort_keys=True)
json.dump(key, open(os.path.join(HERE, "key.json"), "w"), indent=1, sort_keys=True)
print("fixture written: %d events, %d loans, %d borrowers" % (len(events), loan_id, len({e["args"]["borrower"] for e in events if "borrower" in e["args"]})))
