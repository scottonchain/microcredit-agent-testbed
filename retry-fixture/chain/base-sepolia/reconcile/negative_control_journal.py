#!/usr/bin/env python3
"""Negative controls for reconcile_journal.py: tampered or truncated copies of the journal must produce the stated verdicts.

    python3 negative_control_journal.py [JOURNAL_live_pool.jsonl] [RESULT.txt]

Each control is a journal the live run could have left behind (a crash between the intent row and the hash row; a lost row; a
row whose bytes the chain contradicts) and the verdict the fixture's rule assigns to it. The reconciler must print exactly that
verdict for the affected intent and exit as stated; everything else must stay as in the untampered run.
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
JOURNAL = sys.argv[1] if len(sys.argv) > 1 else "JOURNAL_live_pool.jsonl"
RESULT = sys.argv[2] if len(sys.argv) > 2 else "NEGATIVE_CONTROL_journal.txt"
rows = [json.loads(l) for l in open(os.path.join(HERE, JOURNAL)) if l.strip()]
out = []


def run(label, rows2, want_exit, want_lines):
    p = os.path.join(HERE, "tampered_%s.jsonl" % label)
    open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows2))
    r = subprocess.run([sys.executable, os.path.join(HERE, "reconcile_journal.py"), p], capture_output=True, text=True, timeout=600)
    os.remove(p)
    lines = r.stdout.splitlines()
    hits = []
    for want in want_lines:
        hit = [l for l in lines if all(w in l for w in want)]
        hits.append((want, hit[0] if hit else None))
    ok = r.returncode == want_exit and all(h for _, h in hits)
    out.append("%s: exit %d (want %d) | %s | %s" % (label, r.returncode, want_exit, "OK" if ok else "WRONG", lines[-1] if lines else r.stderr[-200:]))
    for want, hit in hits:
        out.append("    expected a line containing %s -> %s" % (want, ("found: " + hit.strip()) if hit else "MISSING"))
    return ok


def drop(rows_, pred):
    return [r for r in rows_ if not pred(r)]


oks = []
# 1. crash after broadcast of s3 (first repay, nonce 1) before its hash row was written: the intent landed on chain (nonce 1 consumed),
#    and s4 (the identical bytes, receipted, unmoved) does not explain the consumption -> LANDED by journal + nonces(signer), exit 0
oks.append(run("s3_hash_row_lost", drop(rows, lambda r: r.get("step") == "s3" and r["state"] == "broadcast"), 0,
               [["LANDED", "s3", "nonce 1", "(no hash)", "only unreceipted journal row carrying it"]]))
# 2. both s3 and s4 (same bytes, nonce 1) lost their hash rows: two unreceipted rows, byte-identical -> one intent resubmitted -> LANDED, exit 0
oks.append(run("s3_and_s4_hash_rows_lost", drop(rows, lambda r: r.get("step") in ("s3", "s4") and r["state"] == "broadcast"), 0,
               [["LANDED", "s3", "nonce 1", "byte-identical (one intent, resubmitted)"], ["LANDED", "s4", "nonce 1", "byte-identical (one intent, resubmitted)"]]))
# 3. s5 (re-signed repay, nonce 2, reverted) and s7 (borrow, nonce 2, landed) both lost their hash rows: same nonce, different bytes ->
#    AMBIGUOUS (nonces(signer) cannot say which of the two landed), exit 1
oks.append(run("s5_and_s7_hash_rows_lost", drop(rows, lambda r: r.get("step") in ("s5", "s7_borrow_loan_b") and r["state"] == "broadcast"), 1,
               [["AMBIGUOUS", "s5", "nonce 2", "2 unreceipted journal rows with different bytes"], ["AMBIGUOUS", "s7_borrow_loan_b", "nonce 2"]]))
# 4. the missing-journal-row case: s7's rows never written (intent and hash) while nonce 2 is consumed on chain and the only other row
#    carrying nonce 2 (s5) is receipted as unmoved -> UNKNOWN for nonce 2, exit 1
oks.append(run("s7_rows_missing", drop(rows, lambda r: r.get("step") == "s7_borrow_loan_b"), 1,
               [["UNKNOWN", "(no journal row)", "nonce 2", "no journal row landed it"]]))
# 5. the journal's calldata for s8 (the wrapper call) differs from the chain's tx input by one byte -> MISMATCH, exit 1
rows5 = json.loads(json.dumps(rows))
for r in rows5:
    if r.get("step") == "s8" and r["state"] == "intent":
        r["data"] = r["data"][:-1] + ("0" if r["data"][-1] != "0" else "1")
oks.append(run("s8_calldata_tampered", rows5, 1, [["MISMATCH", "s8", "chain tx input/to differ from the journal row"]]))
# 6. unreceipted row whose nonce is NOT consumed: an s13 repay of loan 17 at nonce 6 that never got a hash (intent row only) ->
#    NOT LANDED (latest nonces(signer) = 6 <= 6), exit 0; a resend could not double-execute
s12 = [r for r in rows if r.get("step") == "s12" and r["state"] == "intent"][0]
inner_nonce6 = None
# build a direct repayLoanMeta with nonce 6 by lifting batch[1] of s12 (that call is the expired nonce-6 intent)
a = s12["data"][10:]
arr = int(a[64:128], 16) * 2
n = int(a[arr:arr + 64], 16)
base = arr + 64
rel = int(a[base + 64:base + 128], 16) * 2
ln = int(a[base + rel:base + rel + 64], 16)
inner_nonce6 = "0x" + a[base + rel + 64:base + rel + 64 + 2 * ln]
assert inner_nonce6[:10] == "0x1d169fa9" and int(inner_nonce6[10:][64 * 3:64 * 4], 16) == 6
rows6 = rows + [{"step": "s13_never_broadcast", "state": "intent", "to": "0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8", "data": inner_nonce6, "gas_limit": None, "t": "2026-10-05T08:34:30Z"}]
oks.append(run("s13_intent_row_only_nonce_unconsumed", rows6, 0, [["NOT LANDED", "s13_never_broadcast", "nonce 6", "not consumed"]]))

hdr = "$ python3 negative_control_journal.py %s   (six journals the live run could have left behind; verdict and exit code per the fixture's rule)\n" % JOURNAL
print(hdr + "\n".join(out))
open(os.path.join(HERE, RESULT), "w").write(hdr + "\n".join(out) + "\n")
sys.exit(0 if all(oks) else 1)
