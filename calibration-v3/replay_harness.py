#!/usr/bin/env python3
"""Replay harness for the UNMODIFIED calibration-v3 generator (so its bound sha256 stays valid).

The generator draws its key-commitment salt with os.urandom(16). This harness runs the generator file as-is
(runpy) and feeds the revealed salt back in by patching os.urandom for exactly that one 16-byte call.
Usage (after the reveal):
    python3 replay_harness.py <generator.py> <seed> <outdir> <key_salt_hex>
Then compare sha256 of <outdir>/corpus.json, <outdir>/ANSWER_KEY_PRIVATE.json and <outdir>/COMMITMENT.txt
with the published values. Any other os.urandom call (size != 16) or a second 16-byte call aborts the run.
"""
import os, sys, runpy

gen, seed, outdir, salt_hex = sys.argv[1:5]
salt = bytes.fromhex(salt_hex)
assert len(salt) == 16, "key salt must be 16 bytes (32 hex chars)"
_real = os.urandom
calls = []

def _patched(n):
    calls.append(n)
    if n != 16 or len(calls) != 1:
        raise SystemExit("REPLAY_ABORT: unexpected os.urandom call(s): %r" % (calls,))
    return salt

os.urandom = _patched
sys.argv = [gen, seed, outdir]
runpy.run_path(gen, run_name="__main__")
os.urandom = _real
if calls != [16]:
    raise SystemExit("REPLAY_ABORT: expected exactly one os.urandom(16) call, saw %r" % (calls,))
print("replay ok: os.urandom(16) called once and replaced by the supplied salt")
