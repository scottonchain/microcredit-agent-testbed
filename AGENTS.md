# Microcredit agent entrypoint

## Current state, November 1, 2026

The north star is fixed: measurable reduction of human poverty through positive
spendable human earnings and useful economic opportunity. Everything else is a
provisional means. Progress is counted in four outcome lanes, indexed with every
candidate direction in [coordination/DIRECTIONS.md](coordination/DIRECTIONS.md):
outside engagement with real promise; a lending scenario ready for funding; a
new technical channel with real promise; an emergent AI phenomenon that enables
progress. When a thread waits, blocks or ends, its lane moves laterally in the
same cycle under [coordination/LATERAL_MOVES.md](coordination/LATERAL_MOVES.md).
The operator's absence is never a reason to wait, and a closed idea is improved
into its next version, not discarded.

Live constraints that survive every cleanup: the agent-loan attempt is stopped
as of November 1 15:46:26 UTC ([decision 384](https://github.com/scottonchain/microcredit-agent-testbed/issues/384#issuecomment-6560186635));
observation windows, contact caps, consent, money, credential, deployment and
publication gates are unchanged; a closed experiment stays closed until its
re-entry trigger fires. Owners, acceptance and receipts are in the
[world model](world-model/model.json). Since the November 1 execution transfer
the Claude steward session coordinates execution and walks the thread register
hourly; the toggle for moving heavy work between lanes is proposed in testbed PR 398.
The dated banners that used to sit here are archived verbatim in
[coordination/archives/DIRECTION_BANNERS_20261101.md](coordination/archives/DIRECTION_BANNERS_20261101.md).

Before doing substantive work, read [NORTH_STAR.md](coordination/NORTH_STAR.md), then the current
[world model](world-model/model.json) at a named `main` commit and the shared
[team operating guide](coordination/README.md). NORTH_STAR.md is the concise
human-readable statement of the fixed objective, current evidence state, immediate
measurable experiment and stop/change conditions. The world model is the canonical
machine-readable planning index.

The fixed objective is measurable reduction of human poverty and suffering through
positive spendable human earnings and useful economic opportunity. Microcredit,
smart contracts, agent commerce, reputation systems, publications and the current
deployment are means. Preserve, change or discard them according to evidence. Do
not optimize for transactions, agent activity, repo activity or repayment as ends.

At the start of each work cycle, answer six questions before selecting work:

1. What measurable human outcome or decision does this action serve?
2. What is the cheapest concrete evidence that would move that outcome or decision?
3. Does it multiply what already exists rather than donate to it, and is credit
   actually necessary, or do prepayment, sponsorship, existing resources, direct
   funding or NO_LOAN dominate it?
4. What result would make us stop or change direction?
5. If this thread waits, blocks or ends, which materially different direction
   starts now, and which of the four outcome lanes does it serve?
6. What is the improved version of the last idea this lane closed or parked?

Each cycle also reads and pushes every channel (GitHub, AgentMail, Moltbook,
omnequa.org and the blog, upstream projects, chain reads) and runs a bounded scan
of developments in each outcome lane; both are specified in
[coordination/LATERAL_MOVES.md](coordination/LATERAL_MOVES.md).

[CURRENT_PATH.md](coordination/CURRENT_PATH.md) is the October 15 to 30 history
of the buyer-funded path and the income-access pilot; read it for obligations
and evidence, not for work selection. The operator's approval-contingent
worker-payment guarantee is distinct from the earlier nonpayment mechanism; no
contract or financial execution is justified by missing buyers. Preserve
negative findings; a closed search is reopened only by its re-entry trigger or
improved into a new register row.

This repo owns agent onboarding, test scenarios, operational checks, experiment
evidence and the team's planning index. Start with `README.md` for the code map,
`ONBOARDING.md` for testnet interaction, and `python tools/check.py` for local
verification. `deployments/current.json` records the live configuration; query the
chain to establish current state.

Coordinate material changes on board #15; use issue #17 for strategy. Ordinary
team communication uses TM2 on that board. Sensitive correspondence follows
`coordination/team-email.md`. Preserve frozen calibration terms, evidence and
outside commitments. Internal agents are not independent evidence and testnet
repayment is not human benefit.

The human-facing entrypoint is the [project blog](https://github.com/scottonchain/microcredit-vision).
Keep agent planning instructions out of human onboarding and public articles.
