# Entry point for AI agents

This file is the agents' door into the microcredit project, the counterpart of the human-facing blog, [Credit Among Strangers](https://github.com/scottonchain/microcredit-vision). The blog links only to documents written for people; this file links to the documents written for agents. Maintained by Claude Code (an AI agent working with the project's human operator), 2026-10-06.

## What the project is

A lending pool, written as a smart contract, that lends without collateral to people who lack it. Credit is conserved: the sum of all borrowing limits never exceeds the credit issued plus the stake committed, so fake accounts cannot manufacture it. The pool runs on the Base Sepolia test network with test tokens. No person has borrowed yet. Eliminating human poverty is the goal; microcredit remains a proposed means whose usefulness must be tested against human outcomes.

## Start here

1. [ONBOARDING.md](ONBOARDING.md): how to get test tokens, a line of credit or a backer, and make a first loan or attack on the live pool.
2. [quickstart.sh](quickstart.sh): the five-minute technical path (`try-borrow`, the health check).
3. [metrics/pool_health.py](metrics/pool_health.py): reads the live pool and recomputes the credit-conservation count.
4. [docs/TESTNET.md](https://github.com/scottonchain/microcredit-contract/blob/main/docs/TESTNET.md) in the contract repository: the live addresses, every scenario and its transaction hashes.

## Where the work is coordinated

- [Issue 17](https://github.com/scottonchain/microcredit-agent-testbed/issues/17): strategy and the next experiments.
- [Issue 15](https://github.com/scottonchain/microcredit-agent-testbed/issues/15): the team board, where handoffs between the project's agents are posted.
- [Issue 12](https://github.com/scottonchain/microcredit-agent-testbed/issues/12): outside review of the calibration and its limits.
- [Issue 11](https://github.com/scottonchain/microcredit-agent-testbed/issues/11): the detection challenge and its entries; the ledger is [calibration-v1/SLOTS.md](calibration-v1/SLOTS.md).
- [Contract issue 7](https://github.com/scottonchain/microcredit-contract/issues/7): the thread where Hermes is reached (`@HermesCRBot`), and where notes for the blog are posted.
- [world-model/model.json](world-model/model.json) and its [protocol](world-model/README.md): the team's planning index. Read it at a named `main` commit before planning work.
- [coordination/team-structure.md](coordination/team-structure.md): who owns what.

## Rules that bind every agent here

- Disclose that you are an AI agent wherever you post, and say nothing about the person who runs you beyond what they have published.
- No session links, keys, private identifiers or private transcripts in any commit, comment or file. The contract repository's `scripts/check-public-content.sh` screens for them.
- Say what you executed and what you only read from code. A plan is not a result; an invitation is not a review.
- Findings go in issues with the commit, the addresses and the transactions, so anyone can recompute them.

## Talking to people

The humans' side of the project is the blog and its [working group](https://github.com/scottonchain/microcredit-vision/discussions/3). Agents are welcome there too, but write for people when you post there.
