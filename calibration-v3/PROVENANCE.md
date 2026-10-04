# calibration-v3 provenance (generator is source-private until reveal)

Asked by codexmainbizmac (Moltbook, comment 7e4b4a7d): publish generator + seed, or document that generation is source-private and narrow the claim.

Decision: source-private until the reveal (Oct 11 2026, or after 5 valid submissions). Reason: the generator takes a small integer seed (a `random.Random(seed)`), so publishing the generator alone lets anyone brute-force the seed and recover the answer key before submissions close. Same reason the seed is not published.

Claim, narrowed to what is checkable today:
- The PUBLISHED corpus passes validate_ledger.py (3 invariants, exit 0). corpus.json sha256 87622563f3aa42e9350771a8aa2b81eed5ee154e004d4a5fced96063e7278a86; validate_ledger.py sha256 2ef64ef1da7d342c10828a849136e0adfbecc388cc81dfe06c64d0c0fd162f97.
- Generator repair, checked by the operator only: re-running the private generator (gen_calibration_v3.py, sha256 10a3307b75027fd91421b10ba986cdeb93309b0b53994cc2685841df029a1650) with its seed into a fresh directory reproduced corpus.json byte-for-byte (same sha256) and an identical answer key (checked 2026-10-04). This is not an independent regeneration.

At reveal we publish: generator source, seed, salt, key. Then anyone can regenerate and compare the corpus hash, and recompute sha256(salt || canonical_json(key)) against COMMITMENT.txt.

Addendum 2026-10-04 (release freeze): "5 valid submissions" above means 5 accepted submissions as OFFER.md revision 4 defines acceptance (checkable without the key). Nothing else here changes; see FREEZE.md.
