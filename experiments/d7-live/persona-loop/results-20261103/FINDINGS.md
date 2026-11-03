# Usability test of the practice lending app, 2026-11-03

Thirty-two usability runs (p001 to p032) of the practice lending app, each by a separate AI agent playing one ordinary person with no knowledge of crypto, on a headless phone with a virtual passkey authenticator against a private copy of the live test pool with its own AI credit officer. These are simulated people: they find confusing wording and broken flows; they are not real borrowers and say nothing about real lending outcomes. Three further runs (p033 to p035) were stopped mid-way and are not counted.

| Item | Count |
| --- | --- |
| Runs counted | 32 (p001 to p032) |
| Findings logged in LOG.md (F1 to F96) | 77 numbered findings, plus harness notes H1, H5, H6, H7, H8, H9 |
| Fixes shipped | one per finding, in eight app commits on this branch |
| Officer model calls with cost logged (officer-calls.csv) | 31 calls, 1.73 US dollars in total, 0.03 to 0.14 dollars each |

Files: `LOG.md` (findings and the fix for each, by batch), `reports/pNNN.md` (each tester's own six-section report), `officer-calls.csv` (one row per logged officer reply: time, world, models, tokens, cost; applicant addresses omitted). Per-tester screenshots are not published. The cost figures are the Claude CLI's own reported cost per call (`total_cost_usd`), for calls the daemon logged; calls before the cost logging was added on 2026-11-03 are not in the file.

Reading the result honestly: from batch 3 (p006) every run ended with the loan taken and repaid, and from batch 6 no run was blocked inside the app; the first five runs found real blockers. Several testers needed real money (a meter, a bus pass, a uniform, a work tool) and the practice app cannot give it, so those testers left with their real need unmet.
