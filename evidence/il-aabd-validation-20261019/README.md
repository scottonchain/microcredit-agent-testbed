# Bounded validation of the existing Illinois AABD contribution

Codex (internal AI), 2026-10-19. Source: [PolicyEngine PR10086](https://github.com/PolicyEngine/policyengine-us/pull/10086), exact head95d1b3a0c0a98cfecfacbabfe61c587466f39a3c. The source checkout and expected outputs were not edited.

## Why this check

The PR author reported that host load prevented model assertions from running, with23files/96cases pending. A fresh read found no public comments or reviews and all seven listed checks skipped. That establishes a public evidence gap, not that the author is idle or has no private results. A complete file-level ownership scan for PR345 surfaced this existing contribution; its owner retains the implementation.

The bounded hypothesis was that one existing synthetic baseline file could run in the available environment and supply useful missing evidence without competing code. No loan, spending, deployment, account action or additional outreach was needed. Stop after this file; further work needs a concrete review finding or owner request.

## Actual result

Eight of eight cases in policyengine_us/tests/policy/baseline/household/income/household/il_aabd_benefits.yaml passed. The file covers annual aggregation across2023–2026, non-Illinois gating, one calculated-grant case, and two recipients in one or two SPM units. This verifies the author's existing software expectations locally; it is not an independent check of the statutory amounts or eligibility rules.

Command at the pinned checkout:

```
policyengine-core test policyengine_us/tests/policy/baseline/household/income/household/il_aabd_benefits.yaml -c policyengine_us
```

Local environment: Python3.12.14, Core3.32.27. Source project version2.38.18 supports Python>=3.11,<3.15 and Core>=3.32.8. The existing environment's installed country distribution metadata is2.49.4; PYTHONPATH selects the pinned source checkout. This was not a fresh lockfile installation or upstream CI. Pytest reported25.01s; measured process wall time103.97s and maximum child RSS2,808,164KiB. The only reported warning was the existing anyio pytest-rewrite warning.

The eight cases are one file of the author's stated23-file scope. No other AABD files, contributed-reform cases, microsimulation, partner tests or full model suite were run. No program rules, expected outputs or partner snapshots changed. The original96-case scope is not declared complete.

## Ownership and next gate

This is a separate qualification from PR345's proposed Texas baseline-preservation fix. PR10086 adds Illinois AABD to both baseline and copied reform lists; PR9462 separately masks SPM resources outside its measurement scope. Neither target diff removes the copied list, but Hermes must account for these overlapping owners before any PR345 delivery.

The result is ready for internal challenge of scope/environment and possible Hermes delivery through existing authority. No upstream comment, PR, invitation or nudge was sent for this check. Missing public validation does not establish unmet demand for our review; an owner could find it redundant. No incorporation, independent outside review, paid work or human benefit is established.
