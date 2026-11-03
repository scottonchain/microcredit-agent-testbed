# Trust ladder, November 3: practice desk disclosure, screening prototype, design, blog draft

Claude Code (AI), 2026-11-03. Receipt for [D17](../../coordination/directions/trust-ladder.md), written at the operator's direction of November 3 (chat; summarised, not quoted). Nothing here is a screened person, a loan, a credit decision or human benefit.

## What was found

- The practice app's credit officer (`experiments/d7-live/desk-daemon.mjs`, app branch `claude/d7-live-sim-app-20261101` at f455fe4) is a real agent (the model through the headless CLI, a rules officer as fallback) whose instructions grant the amount asked up to the desk's maximum and decline only for abuse, threats, a request not for the applicant, or a wallet with a past default. The structured request the app writes is decided by rules; the model phrases the answer. So the officer would not deny an ordinary request. Read from the source on 2026-11-03; no live transcript was needed.
- The only "screen" on `main` before this work was the parametric filter in `pool_stability.py` (an assumed sensitivity and false-rejection rate). It never looks at an applicant.

## What was done (branch `claude/laughing-davinci-k722xa`)

| Item | Where | Check |
| --- | --- | --- |
| The practice desk says, with its first grant, that this version approves every proper request and the real app will check the plan and evidence; a repaid practice loan counts there | `experiments/d7-live/desk-daemon.mjs` (TEST_NOTE appended once per applicant after either officer's reply), `app/src/main.js` (grant panel, How it works), `TESTER_GUIDE.md`; `app/dist/app.js` rebuilt with esbuild 0.24.2 | `node --check` on both files; the bundle contains the sentence. Not deployed: the `pages` branch is published by the steward's routine |
| Seven-tap interview with an evidence stage, validation, prohibited-field refusal, deterministic follow-ups | `experiments/self-service-borrower-app/screening/interview.py` | tests |
| Typed document intake, hashing, rule-based extractor, Claude extractor with measured cost, hash registry | `screening/documents.py` | tests with a stubbed client; not run against a live key |
| Dossier: stated, evidenced, verified; eleven coded contradictions | `screening/dossier.py` | tests |
| Policy `2026-11-03.1`: published weights, four hard rules, caps, adverse-action reasons, practice record at 5 of 100 | `screening/policy.py` | tests |
| Local private intake page and command line | `screening/server.py`, `screening/cli.py` | HTTP smoke test: GET 200, POST with two uploaded files approved the market-trader case at 10 USDC; records written under the data dir, the hash registry caught the same file on a second application |
| Chain reader for the pool record (borrower, backer, practice wallet) | `experiments/d7-live/pool-record.mjs` | run read-only against Base Sepolia on 2026-11-03 (reserve 35.000836 USDC, rate 933 bps) |
| Four worked examples | `screening/examples/` | `python3 -m screening --all-examples --today 2026-11-03`: market-trader approve 10 USDC (85/100); mismatch decline (39/100, name mismatch first); no-backer decline (17/100, backing rule first); practice-graduate approve 5 USDC (78/100) |
| Design: the four rungs, the signal table, the gates, the convergence to a stake-seeded graph score | `coordination/directions/trust-ladder.md`; register row D17 in `coordination/DIRECTIONS.md`; pointer in D16 | read |
| Blog draft for a general reader | [blog-2026-11-03-how-trust-can-grow-from-a-practice-loan.md](blog-2026-11-03-how-trust-can-grow-from-a-practice-loan.md) | drafted in the blog's post format; **not published**: the session could not attach `scottonchain/microcredit-vision` (two `add_repo` requests were denied by the session's permission classifier). To publish: copy it to `posts/`, make the image with `tools/make_images.py`, run `tools/build.py`, add a VERIFY row for the 1990s search-engine reference and the policy figures |

## Limits

- No applicant has been screened; the examples are synthetic and labelled.
- The policy weights are a first published version, not a validated model; the pilot's measurement replaces them (D7 screen rule 6: a randomised holdout is the only way to measure sensitivity and false rejection).
- The practice-record link is read from the chain but `linked` stays false until the intake verifies a passkey signature over a challenge; that check is the next build step.
- The Claude extractor's request follows the SDK's structured-output form and its cost arithmetic is unit-tested with a stub; it has not been run live.
- Rung 3 (the graph score) is a design with its required proofs listed in `docs/TRANSITIVE_TRUST_TARGET.md`, not an implementation.
