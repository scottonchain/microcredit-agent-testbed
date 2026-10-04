#!/usr/bin/env python3
"""Ledger invariants for the synthetic corpus. Usage: python3 validate_ledger.py corpus.json
Exit 0 only if every invariant holds. Invariants proposed by codexmainbizmac (Moltbook comment
fd7056ec, credit only); implemented and run by hermes-agent-909 (AI agent).
Contract rule for DEFAULT_TIME_STRICT: DecentralizedMicrocredit.sol line 658,
  require(block.timestamp > loan.disbursedAt + loan.term + LATE_PERIOD), LATE_PERIOD = 30 days."""
import json, sys, hashlib
path = sys.argv[1] if len(sys.argv) > 1 else "corpus.json"
raw = open(path, "rb").read()
ev = json.loads(raw)["events"]
DAY = 86400
viol = {"LOAN_TERMINAL_IMMUTABLE": [], "BORROWER_DEFAULT_LOCKOUT": [], "DEFAULT_TIME_STRICT": []}
state, disb, req, first_default = {}, {}, {}, {}
for i, e in enumerate(ev):
    a, t = e["args"], e["event"]
    lid = a.get("loanId")
    if t == "LoanRequested":
        req[lid] = e
        if a["borrower"] in first_default:
            viol["BORROWER_DEFAULT_LOCKOUT"].append(i)
        state[lid] = "Requested"
    elif t == "LoanDisbursed":
        disb[lid] = e
        state[lid] = "Active"
    elif t == "Backed":
        if a["borrower"] in first_default and a["secured"] + a["unsecured"] > 0:
            viol["BORROWER_DEFAULT_LOCKOUT"].append(i)
    elif t in ("LoanRepaid", "LoanDefaulted"):
        if state.get(lid) in ("Repaid", "Defaulted"):
            viol["LOAN_TERMINAL_IMMUTABLE"].append(i)
        if t == "LoanDefaulted":
            r, d = req[lid]["args"], disb[lid]
            if not e["ts"] > d["ts"] + r["repaymentPeriodDays"] * DAY + 30 * DAY:
                viol["DEFAULT_TIME_STRICT"].append(i)
            first_default.setdefault(a["borrower"], i)
        state[lid] = "Repaid" if t == "LoanRepaid" else "Defaulted"
print("corpus sha256", hashlib.sha256(raw).hexdigest())
bad = 0
for k, v in viol.items():
    print("%-26s %s  event indices %s" % (k, "PASS" if not v else "FAIL (%d)" % len(v), v))
    bad += len(v)
sys.exit(1 if bad else 0)
