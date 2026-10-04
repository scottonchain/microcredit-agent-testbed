# retry-fixture (DRAFT)

Test cases for retry safety after an unknown outcome (a call that may or may not have taken effect).
Off-chain cases 1-4 are from merktop's public description of a real incident (21 duplicate emails); chain cases come from the microcredit contract's relayer tests. Expected states for off-chain cases are merktop's words, not ours. Cases we did not run are marked `tested_by_us: false`.

Corrections and additions welcome by issue or PR; contributors are credited by name in this file.

Contributors (credit only):
- forgeloop (Moltbook, independent agent): proposed email-5 (per-recipient DSN) and email-6 (unknown stays unknown past the read budget) in public comments on merktop post 117ae039; not asked by us, not reviewed by it.
- merktop (Moltbook, independent agent): source and expected states for email-1..4; confirmed expected states for email-5/6 in its own replies.
