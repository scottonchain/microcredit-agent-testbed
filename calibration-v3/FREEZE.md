# calibration-v3 release freeze (2026-10-04)

calibration-v3 is the one corpus the thank-you offer applies to (`../calibration-v1/OFFER.md`, revision 4), and it does not move again before the reveal. Research continues separately (a v4 with background-like ring timing is planned); a later corpus gets its own folder and holds no slot.

## Frozen until the reveal (sha256)

| file | sha256 | role |
|---|---|---|
| `corpus.json` | `87622563f3aa42e9350771a8aa2b81eed5ee154e004d4a5fced96063e7278a86` | the ledger entrants run on |
| `COMMITMENT.txt` | `00e51a80417238d03395c0d3319997bde8173d6096a587cc2d6872a771bf2c00` | sha256(salt \|\| canonical_json(key)) = `3c457dcd2ec45b4669e192d7bb2bf4f56f7c8b615fcf8906b06033417cd4acb4` |
| `score.py` | `7983a9006d6d0d1275b37175ceb4883e344258525767298dceb5e5115fec0fa7` | scorer and submission format (docstring) |
| `check_submission.py` | `0d21b2e3136f6c7e5340d89f9b0bb04d6ab876128b11af9534da649f754f4a42` | acceptance check, no key |
| `starter.py` | `b446d295a0e74cb43b09906a83c91e2aa61eabf0cd97f430d3584abe3a2e792e` | a valid submission in one command |
| `validate_ledger.py` | `2ef64ef1da7d342c10828a849136e0adfbecc388cc81dfe06c64d0c0fd162f97` | the three ledger invariants |

Also frozen: the submission format (`{"ring": [], "sybil_cluster": [], "bust_out": [], "late_edge": {"inside_grace": [], "outside_grace": []}}`), the five classes, the reveal date (2026-10-11, or earlier once 5 accepted submissions exist) and the terms in OFFER.md revision 4. The generator, seed, nonce, key and key-salt stay private until the reveal (`PRECOMMIT.md`).

## What may still change
- `../calibration-v1/SLOTS.md`: the ledger (submissions, decisions, scores, payments, revision hashes, the release commit id).
- `../calibration-v1/CONTRIBUTORS.md`: credits.
- `README.md` here: a "Known limits" entry may be added when a reviewer finds another limitation; nothing else in it.
- `DRYRUN.md`, `LEAKCHECK_EXT_RESULTS.md`, `PRECOMMIT.md`, `PROVENANCE.md`: measurements and receipts may be appended, never rewritten.
- At the reveal: the generator source, seed, nonce, key and salt are added, and nothing else changes.

## Defects versus limitations
A **defect that prevents fair scoring** is one of: (a) the revealed salt and key do not open `COMMITMENT.txt`; (b) `score.py` cannot run on a file that `check_submission.py` accepted; (c) the key names an address that is not a borrower of `corpus.json`, or lists one borrower in two classes. Handling: OFFER.md revision 4 pays accepted slots regardless, and the defect is recorded in `SLOTS.md`. None of these can be fixed by changing the corpus, and no such defect is known.

A **limitation** is anything that makes a high score less meaningful without making scoring unfair. Known ones are listed in `README.md` ("Known limits") and are disclosed, not fixed: a timing-pair leak on the ring class (`LEAKCHECK_EXT_RESULTS.md`), fixed 30-day terms and an exact 1.05 repayment ratio, a schema that carries `repaymentPeriodDays` on `LoanRequested` and omits `to` on `LoanDisbursed` where the chain's events differ, and an answer key that is operator-run until the reveal. A limitation found after this freeze is added to that list and credited; it does not change the corpus, the key, the scorer or the offer.

## Why freeze on v3 rather than repair it
Payment does not depend on the score (OFFER.md: "Score does not matter; honesty does"), so a leak lowers what a score proves but not whether an entrant is paid. v3 passes the public ledger invariants, has a committed key and a replay receipt, and had no submission when frozen. Every repair so far produced a new corpus, a new commitment and a new offer revision; that churn, not the leak, is what kept entrants away.
