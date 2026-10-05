#!/usr/bin/env python3
"""calibration-v3 generator (v2 + ledger invariants from codexmainbizmac fd7056ec: no repay after default, no new loan/backing after default) (PRIVATE: the seed reproduces the key).
Fixes the leaks mayalaran found in v1 (comment a6a8e2da): plants appended as contiguous loan-id blocks,
constant timing (29.0 / 31.0 days), plant-only amounts, address-numeric families, and zero honest late payers.
Method: every loan is an independent episode with its own start time; ids/blocks assigned AFTER a global time sort;
all amounts, durations and addresses drawn from the same distributions as the background."""
import json, random, hashlib, sys, os, collections
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 7741
OUT = sys.argv[2] if len(sys.argv) > 2 else "/root/work/agents/calibration_v3"
rnd = random.Random(SEED); DAY = 86400; T0 = 1_790_000_000; WINDOW = 170 * DAY
def addr(role, i): return "0x" + hashlib.sha256(("%d|%s|%d" % (SEED, role, i)).encode()).hexdigest()[:40]
AMTS = [10, 20, 20, 30, 40, 40, 50, 60, 60, 80, 100]
def amt(): return rnd.choice(AMTS) * 10**6
eps = []   # list of (ts, event, args) with args['_L'] = local loan key
nloan = [0]
def loan(b, start, amount, backers, outcome, days=None, after_default=None, late=0.0):
    """outcome: full(days after disburse) | default | default_then_repay(after_default days)"""
    nloan[0] += 1; k = nloan[0]
    s = start; term = 30
    eps.append((s, "LoanRequested", dict(borrower=b, _L=k, amount=amount, interestRate=1000, repaymentPeriodDays=term)))
    for j, bk in enumerate(backers):
        eps.append((s + 60 * (j + 1) + rnd.randint(0, 3000), "Backed", dict(backer=bk, borrower=b, secured=amount // max(1, len(backers)), unsecured=0)))
    d = s + rnd.randint(3600, 3 * 3600) + rnd.randint(0, 3599)
    eps.append((d, "LoanDisbursed", dict(borrower=b, _L=k, amount=amount)))
    end = d
    if outcome == "full":
        end = d + int(days * DAY) + rnd.randint(0, DAY - 1) if days == int(days) else d + int(days * DAY)
        eps.append((end, "LoanRepaid", dict(borrower=b, _L=k, amount=int(amount * 1.05))))
    else:
        dd = d + (term + 30) * DAY + (int(late * DAY) if late else rnd.randint(1, 2 * DAY))
        eps.append((dd, "LoanDefaulted", dict(borrower=b, _L=k, writtenOff=amount, recovered=0)))
        end = dd
        if outcome == "default_then_repay":
            end = dd + int(after_default * DAY)
            eps.append((end, "LoanRepaid", dict(borrower=b, _L=k, amount=int(amount * 1.05))))
    return end
def rtime(lo=0, hi=None): return T0 + rnd.randint(int(lo * DAY), int((hi or 150) * DAY))
key = {"seed": SEED, "ring": [], "sybil_cluster": [], "bust_out": [], "late_edge": {"inside_grace": [], "outside_grace": []}}
lenders = [addr("lender", i) for i in range(6)]
for i, l in enumerate(lenders): eps.append((T0 + i * 600, "Deposited", dict(lender=l, assets=5_000_000_000, shares=5_000_000_000)))
# honest background: 62 borrowers, 1-4 sequential loans; mostly on time, some late (day 31-48 = 1-18 days past term), some defaults,
# a few default-then-recover (repay 8-25 days AFTER write-off)
honest = [addr("h", i) for i in range(62)]
for b in honest:
    t = rtime(2, 100)
    for _ in range(rnd.choice([1, 1, 2, 2, 3, 4])):
        r = rnd.random()
        backers = [rnd.choice(honest)] if rnd.random() < .45 else []
        if r < .72: e = loan(b, t, amt(), backers, "full", days=rnd.uniform(3, 28))
        elif r < .88: e = loan(b, t, amt(), backers, "full", days=rnd.uniform(31, 48))          # honest late payers
        else:
            e = loan(b, t, amt(), backers, "default"); break   # defaulted borrowers are locked out: no later loan or backing
        t = e + rnd.randint(1, 12) * DAY
# A) ring of 6, circular backing, 3 rounds, every loan repaid fast
ring = [addr("ring", i) for i in range(6)]; key["ring"] = sorted(ring); rs = rtime(5, 60)
for rd in range(3):
    for i, b in enumerate(ring):
        loan(b, rs + rd * rnd.randint(18, 28) * DAY + rnd.randint(0, 3 * DAY), amt(), [ring[(i + 1) % 6]], "full", days=rnd.uniform(2, 7))
# B) sybil cluster: one funder backs 5 borrowers, each defaults
cl = [addr("syb", i) for i in range(5)]; key["sybil_cluster"] = sorted(cl); funder = addr("syb_funder", 0); ss = rtime(30, 110)
for b in cl: loan(b, ss + rnd.randint(0, 18 * DAY), amt(), [funder], "default")
# C) bust-out: 3 borrowers, 4-5 small repaid loans, then one large default
bo = [addr("bo", i) for i in range(3)]; key["bust_out"] = sorted(bo)
for b in bo:
    t = rtime(2, 70)
    for _ in range(rnd.choice([4, 5])):
        t = loan(b, t, rnd.choice([10, 20, 20, 30]) * 10**6, [], "full", days=rnd.uniform(3, 12)) + rnd.randint(1, 6) * DAY
    loan(b, t + DAY, rnd.choice([80, 100]) * 10**6, [], "default")
# D) late_edge: label = repays within 3 days of the grace boundary (term+30). inside: 27.0-29.9 days past term; outside: written off at term+30, repaid 0.2-3 days later
ins = [addr("late_in", i) for i in range(4)]; out = [addr("late_out", i) for i in range(4)]
key["late_edge"]["inside_grace"] = sorted(ins); key["late_edge"]["outside_grace"] = sorted(out)
for b in ins: loan(b, rtime(5, 120), amt(), [], "full", days=30 + rnd.uniform(27.0, 29.9))
for b in out: loan(b, rtime(5, 120), amt(), [], "default", late=rnd.uniform(0.2, 3))
# assemble: global time sort, ids by request order, blocks monotone
eps.sort(key=lambda e: (e[0], e[1]))
reqorder = {}
for ts, ev, a in eps:
    if ev == "LoanRequested": reqorder[a["_L"]] = len(reqorder) + 1
events = []; blk = 1000
for ts, ev, a in eps:
    a = dict(a)
    if "_L" in a: a["loanId"] = reqorder[a.pop("_L")]
    blk += rnd.randint(1, 40)
    events.append({"block": blk, "ts": ts, "event": ev, "args": a})
corpus = {"name": "microcredit-calibration-v3", "synthetic": True, "schema": "same event names/args as DecentralizedMicrocredit.sol on Base Sepolia",
          "seed_published": False, "events": events}
os.makedirs(OUT, exist_ok=True)
json.dump(corpus, open(OUT + "/corpus.json", "w"), indent=0, sort_keys=True)
salt = os.urandom(16).hex()
commit = hashlib.sha256(salt.encode() + json.dumps(key, sort_keys=True).encode()).hexdigest()
json.dump({"key": key, "salt": salt}, open(OUT + "/ANSWER_KEY_PRIVATE.json", "w"))
open(OUT + "/COMMITMENT.txt", "w").write("sha256(salt || canonical_json(answer_key)) = " + commit + "\n")
print("seed", SEED, "events", len(events), dict(collections.Counter(e["event"] for e in events)), "borrowers", len({e["args"].get("borrower") for e in events if "borrower" in e["args"]}))
print("commitment", commit)
