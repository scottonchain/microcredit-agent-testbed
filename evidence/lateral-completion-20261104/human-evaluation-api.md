# Independent F9 source assessment — 2026-11-04

Independent reviewer; read-only source inspection. No account, credentials, study execution, funding, contact or deployment. This is a source critique for integration, not a final outcome claim.

## Changed assumption and terminal result

The November 3 packet left buyer-side automation unaddressed after reading participant anti-bot material and failing to reach researcher terms. A previously untested supplier primary source now establishes a concrete programmatic buyer-side workflow for paid human feedback on AI/agent outputs. It does **not** establish that an autonomous AI may be the contracting account holder, nor that independent external buyers will pay this team's humans.

The bounded source test is complete: **DEMONSTRATED_API_HUMAN_FEEDBACK; AUTONOMOUS_CONTRACTING_ELIGIBILITY_UNRESOLVED; NO_INDEPENDENT_BUYER_RECEIPT**. This narrows the feasibility gap without claiming a human employment outcome or market validation. It does not justify running the demo.

## Exact primary source

Repository https://github.com/prolific-oss/human-feedback-demo at commit `c162ba24800d97f444efd0504d02ae83500ca5bd` (commit date 2026-02-02T17:10:55Z). GitHub organization `prolific-oss` describes itself as the human data platform and links its blog field to www.prolific.com; treat this as supplier-published material, not independent verification of supplier claims.

| Path | Exact blob | Finding |
| --- | --- | --- |
| README.md | 74427b9222ed949c9a1da0fd1fe807b515befe08 | Live demonstration for preference ranking, red-teaming, evaluating agent outputs, post-training and multi-turn assessment; requires a Prolific account with API access, token, workspace and project. Explicit beta, educational, unmaintained, as-is notice. |
| config.yaml | 2e63183c5ec68ac55178512c7139617a87c773b9 | AI-generated image comparison, reward $2,50 participants, estimated1 minute/max5 minutes. Planned rewards $100 before fees; configuration is not proof of actual funding or payment. |
| prolific_helpers.py | 1b4f38b1b2d5069166543db6af95a830215d6ab9 | Concrete authenticated create/publish/export flow; reward converted to cents; completion-code auto-approval. |
| CatEval.ipynb | af50642feda0a6ba8da6402c8a6db521c3f738d9 | Retained output reports successful publication,50 submissions over5 minutes. Supplier-held notebook output, not independently verified ledger/payment receipt. |

Canonical pinned paths: https://github.com/prolific-oss/human-feedback-demo/blob/c162ba24800d97f444efd0504d02ae83500ca5bd/README.md ; same prefix for config.yaml, prolific_helpers.py and CatEval.ipynb.

## Supported API flow and payment boundary

1. Authenticated GET `/api/v1/users/me/` obtains researcher identity.
2. POST `/api/v1/surveys/` creates an internal survey, or an external survey URL can be supplied.
3. POST `/api/v1/studies/` creates a draft with project, description, privacy notice, device requirements, duration, places and `reward=int(dollars*100)`.
4. Completion-code action `AUTOMATICALLY_APPROVE` is included in study payload (helper lines131 and234). This is a requested approval rule, not evidence that a participant received spendable money.
5. POST `/api/v1/studies/{study_id}/transition/` with `action:PUBLISH` publishes the study (lines278–296).
6. GET study and export endpoints retrieve status, places and responses.

The helper contains no documented bank settlement, balance top-up or participant withdrawal receipt. Account creation/acceptance, account ownership and funding eligibility remain outside this source. The presence of a supported API addresses automation mechanics, not contracting authority. Copying this beta code into production would add technical risk and is unnecessary for the current test.

## Observed supplier execution trace

Notebook retained output reports study `69793d6bebf95a00047e1257`, publication HTTP200, ACTIVE,50 places and50 submissions, created January27 2026 at14:34 PST and latest response14:39 PST. This is a supplier-reported demonstration of human response collection. No independent buyer identity, budget source, actual participant payment or repeat purchase is established. Retain aggregate execution facts only; participant comments and researcher identity are unnecessary for this public-safe assessment.

## Strongest objection and final disposition

The strongest objection is that a supplier demonstrating its own product is not outside demand. A demo may be subsidized, and a saved notebook can show outputs without independent verification. Therefore this source cannot graduate B10 to a functioning employer, cannot turn internal verification needs into an external market, and cannot justify contacting or enrolling workers.

F9's exact API-feasibility test may close now with the above terminal result. Re-entry into an actual paid-human experiment requires an eligible existing account and lawful responsible buyer, authorized usable funding, consented participants with fair task terms, and concrete externally expressed demand if claiming a self-sustaining market. No new broad scan or unchanged repeat test is warranted. The November3 internal estimate (~$50/month) remains internal demand only. Existing C4/D12 no-nudge window and live-lending gates remain unaffected.
