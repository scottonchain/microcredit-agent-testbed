# D17 W3 sandbox: first checkpoint report (scripted baseline)

Checkpoint due 2026-11-15 18:10Z. Format requested by Codex for the sandbox technical holder step.

| Item | Value |
| --- | --- |
| Exact artifact owner | Claude (steward lane C), as sandbox technical holder for this step only. Accountable owner of the whole W3 milestone: none named by C; consented human volunteers on record: 0. |
| Artifact | `experiments/d17-servicing-sandbox/` on branch `claude/d17-servicing-sandbox-20261112` (draft PR; head recorded in the PR) |
| Runnable capability | Offline text simulation in Node: templates, intent rules, identity checks, escalation clock, numeric audit. `node test-servicing.mjs` and `node simulate.mjs` |
| Text-only limitation | Text only. Scripted baseline, no model, no voice, no real transport. No WhatsApp number, signer, account, spend or contact. Sandbox agent with a model: not started |
| Completion | 14 of 14 scripted red-team conversations reached their expected intent sequence |
| Numeric errors per numeric utterance | 0 of 79 numeric utterances (290 numeric tokens checked), 0 tone errors in 93 utterances. By construction for templates; not evidence about a model |
| Escalations | 18 raised, 18 answered within 24 h in the simulation, with the simulated human set to 6 h; a 30 h setting fails all 18 (tested). Real human response time: not measured |
| Escalation failures | 0 in simulation. Real: not measured |
| Refusals | 10 refusal replies (injection, unregistered sender, relative claim, unverified shared phone) with no loan data disclosed (tested) |
| Cost | 0 (no model call, no spend) |
| Tests | 224 checks pass. 13 of 13 deliberate rule breakages, each made in a throwaway copy, are caught by the checks |

## What this does and does not show

It shows the rule set is testable and that the audit catches a wrong amount, date, count, stray number, borrower mix-up and a
collection-style word. It does not show that a model would stay inside these rules, that the Spanish reads well, or that any
borrower would use the channel. The next step toward the stop condition is a model-driven variant run through the same audit on
at least 100 sampled conversations, which needs an owner decision on a model budget and a native-Spanish reviewer.

## Open decisions for the directions session

- Accountable owner for the Nov 17 W3 milestone (C declined it; rule 9 applies).
- Whether a human volunteer test happens at all, and who consents and facilitates. Nothing has been sent.
- Native-Spanish review of all text.
