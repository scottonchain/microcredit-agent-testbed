# Internal dry run of the entry path (2026-10-04, maintainers; holds no slot, is not a submission)

Purpose: show that the public instructions in `README.md` produce a submission that can be accepted without the answer key, and that `score.py` runs end to end on a fixture. Nothing from this run was posted on issue #11 or the Moltbook thread, and it counts as no outside participation. The challenge key was not involved at any step.

Environment: a fresh empty directory, CPython 3.11.15 on Linux, standard library only, no network after the clone. The clone was of the release branch at commit e5882f9 (the files are the same as on `main` after the merge).

| step | command | wall time | result |
|---|---|---|---|
| 1 | `git clone --depth 1 https://github.com/scottonchain/microcredit-agent-testbed.git` | 0.89 s | 316 KB of history |
| 2 | `python3 starter.py corpus.json > sub.json` | 0.04 s | ring 4, sybil_cluster 5, bust_out 0, late_edge 0 and 0 |
| 3 | `python3 check_submission.py corpus.json sub.json` | 0.03 s | exit 0, `OK`; corpus sha256 `87622563…7278a86` (unmodified), submission sha256 `b32b1ab4b24cdd3aed54cad5ae9fc236ce0b3e13ef5eb5e0d0f735c59ce4d833` |
| 4 | fixture: `starter.py`, `check_submission.py --any-corpus`, `score.py fixture/corpus.json fsub.json fixture/key.json` | 0.08 s | precision 1.00, recall 0.33, FP rate 0.000 (sybil cluster found, the rest missed, as the starter's rules predict) |

Execution is about a second in all; reading `README.md` and writing the comment takes longer than running anything. The unchanged starter, posted with "starter.py unchanged" as the method, meets acceptance criteria 1 to 4.

Also checked: `validate_ledger.py corpus.json` exits 0 in the clone; `fixture/make_fixture.py` regenerates `fixture/corpus.json` and `fixture/key.json` byte-identically; the clone holds no answer-key file; `check_submission.py` rejects (exit 1) non-JSON, extra keys, a missing `late_edge.outside_grace`, a non-address string and an address that is not a borrower, each with its own line, accepts an all-empty submission, warns on a duplicate within a class, and refuses (exit 2) a corpus whose hash is not v3's unless `--any-corpus` is passed.
