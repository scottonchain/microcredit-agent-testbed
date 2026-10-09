# Microcredit agent entrypoint

The shared [team operating guide](coordination/README.md) contains the repository
map, source ownership, communication, privacy and write rules. Read it once before
cross-repo work, then read the current [world model](world-model/model.json) at a
named `main` commit and follow its [update protocol](world-model/README.md).

This repo owns agent onboarding, test scenarios, operational checks, experiment
evidence and the team's planning index. Start with `README.md` for the code map,
`ONBOARDING.md` for a first testnet interaction, and `python tools/check.py` for
local verification. `deployments/current.json` records the live configuration;
query the chain to establish current state.

Coordinate material changes on board #15; use issue #17 for strategy. Ordinary
team communication uses TM2 on that board. Sensitive correspondence follows
`coordination/team-email.md`. Preserve frozen calibration terms, evidence and
outside commitments. Human poverty alleviation is the objective; agent activity
and testnet repayment are not evidence that it has been achieved.

The human-facing entrypoint is the [project blog](https://github.com/scottonchain/microcredit-vision).
Keep agent planning instructions out of human onboarding and public articles.
