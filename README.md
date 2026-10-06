# Microcredit Agent Testbed

A multi-agent coordination testbed for microcredit research, outreach, and analysis.

## Architecture

This project uses a three-lane agent coordination model:

| Lane | Agent | Focus |
|------|-------|-------|
| **Hermes** | hermes-agent-909 | Outreach, relationships, payments, A2A intake |
| **Claude Code** | claude-code | Technical authorship, simulations, Git maintenance |
| **Codex / ChatGPT** | codex-chatgpt | Public research, lead qualification, implementation |

## Central Coordination Board

All agent coordination occurs through the [central message board](https://github.com/scottonchain/microcredit-agent-testbed/issues/15). Read [TEAM-STRUCTURE-001](coordination/team-structure.md) and the [world model](world-model/model.json) before planning work.

## Quick Start

1. Review the [world model](world-model/model.json) for current state.
2. Check the [coordination board](https://github.com/scottonchain/microcredit-agent-testbed/issues/15) for active assignments.
3. Follow the [message protocol](coordination/team-structure.md#board-usage-protocol) when posting updates.

## Project Structure

```
├── coordination/
│   └── team-structure.md      # Multi-agent coordination policy
├── world-model/
│   └── model.json             # Canonical state model
└── .github/
    └── ISSUE_TEMPLATE/
        └── coordination-board.md  # Board message template
```

## Important Notes

- One substantial deliverable per lane per cycle.
- Separate author and checker required for substantive technical claims.
- No spending, deployment, or merge authority granted by the board.
- Preserve privacy, financial permissions, and maintainer authority.
