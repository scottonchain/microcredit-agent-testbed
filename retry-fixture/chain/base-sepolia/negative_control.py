#!/usr/bin/env python3
"""Negative control for verify_live_run.py: three tampered copies of EVIDENCE.json must each make the verifier exit 1."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = sys.argv[1] if len(sys.argv) > 1 else "EVIDENCE.json"          # e.g. EVIDENCE_live_pool.json
RESULT = sys.argv[2] if len(sys.argv) > 2 else "NEGATIVE_CONTROL.txt"
ev = json.load(open(os.path.join(HERE, EVIDENCE)))
out = []
def run(label, mutate):
    e = json.loads(json.dumps(ev))
    mutate(e)
    p = os.path.join(HERE, "tampered_%s.json" % label)
    json.dump(e, open(p, "w"))
    r = subprocess.run([sys.executable, os.path.join(HERE, "verify_live_run.py"), p], capture_output=True, text=True, timeout=300)
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
    summary = [l for l in r.stdout.splitlines() if l.endswith("skipped")]
    out.append("%s: exit %d | %s | first FAIL: %s" % (label, r.returncode, summary[-1] if summary else "?", fails[0] if fails else "none"))
    os.remove(p)
# 1. the replay step points at the FIRST submission's tx (a run that never actually resubmitted)
run("replay_is_first_tx", lambda e: e["steps"]["s4_chain1_replay_same_calldata"].update({"tx": e["steps"]["s3_chain1_first_submission"]["tx"], "block": e["steps"]["s3_chain1_first_submission"]["block"]}))
# 2. the recorded signed nonce of the first repay is off by one
run("wrong_signed_nonce", lambda e: e["steps"]["s3_chain1_first_submission"].update({"signed_nonce": e["steps"]["s3_chain1_first_submission"]["signed_nonce"] + 1}))
# 3. chain-7a points at the successful envelope of 7b (an envelope in which an intent DID land)
run("7a_points_at_7b", lambda e: e["steps"]["s11_chain7a_envelope_with_expired_intent"].update({"tx": e["steps"]["s12_chain7b_two_intents_one_lands"]["tx"], "block": e["steps"]["s12_chain7b_two_intents_one_lands"]["block"]}))
print("\n".join(out))
open(os.path.join(HERE, RESULT), "w").write("$ python3 negative_control.py %s   (three tampered copies of %s; each must exit 1)\n" % (EVIDENCE, EVIDENCE) + "\n".join(out) + "\n")
