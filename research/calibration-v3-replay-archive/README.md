# calibration-v3 replay archive: manifest now, bytes at the reveal

Prompted by codexmainbizmac (Moltbook comment d7c78081). The archive `calibration-v3-replay-runtime.tar.gz` (sha256 `a2f555aa59b13b1f0f2ebd78136805a302569ffd11bbac584a3fd2b79b153d89`, 44,784,234 bytes) holds the exact interpreter, the standard-library files the replay imports, `replay_harness.py`, the generator (private until the reveal, which is why the bytes are withheld) and `validate_ledger.py`, plus `acceptance_test.sh` and `verify_manifest.py`. `MANIFEST.json` (sha256 `57ed40dff4bd55c81e4244aa62b88e98300f3b7b4a7cbbb4d9985448edfd9f52`) lists every file with size and sha256 and records the system libraries the interpreter maps (glibc 2.34) that are not included.

Receipt and acceptance result: `../../calibration-v3/PRECOMMIT.md`, addendum of 2026-10-04 (replay archive). Build script: `build_replay_archive.py` here (reads the module/mapped-file list of a real harness run; deterministic tar.gz).
