# Working in the testbed

Read [AGENTS.md](AGENTS.md) and the shared [team operating guide](coordination/README.md).
They are the canonical repo map, planning, communication, privacy and write rules;
do not maintain another copy here.

Run `python tools/check.py` before submitting changes. It covers maintained
code and schema checks without importing live experiments or rewriting evidence.
Frozen calibration and historical reproduction files keep their original hashes.
