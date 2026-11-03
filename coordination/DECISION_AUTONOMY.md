# Decision autonomy and continuity (operator direction, November 3, 2026)

Operator direction given in chat on November 3, 2026, recorded here by Claude
Code (AI): work around any lane that is down; make every decision the team can
make, without stalling; never route to the operator a decision the team can
take; keep every direction in motion; fix a broken process the moment it is
found. This file governs every Claude session, routine and subagent working in
the four repositories. Where it conflicts with an older "ask the operator",
"await the brief" or "await review" instruction, this file wins. Where it
conflicts with a financial, contact, account, credential, deployment or
signature gate, the gate wins and the item goes to [OPERATOR_QUEUE.md](OPERATOR_QUEUE.md)
with a default the team proceeds on.

## Rules

1. **Decide at the date.** Every direction, path and checkpoint has one owning
   lane and a dated next decision. At that date the owner records GO, CHANGE,
   PARK or NONE with the receipt and the re-entry condition. A date that passes
   without a decision is a defect: whoever notices decides at once and logs the
   miss in the receipt.
2. **Never ask the operator.** A decision that needs only judgment within the
   documented gates is made by the owner. A decision that needs authority only
   the operator holds (spend, first contact, a new account, a credential, a
   deployment, a signature, an environment setting) gets a row in the operator
   queue with the team's default; the team proceeds on the default and never
   waits. The operator reads the queue when they choose. A question to the
   operator in a status report is a defect.
3. **Work around a lane that is down.** Non-author reviewer order: Codex,
   Hermes, then an independent Claude session or subagent that did not author
   the change. A lane is down when the operator says so, when it is out of
   credits, or when it has not answered a bounded ask within two hours. When the
   ordinary reviewer is down, skip the review step with the note
   "non-author review skipped: <lane> down" in the pull request, the merge
   message and the board comment, and add the merged head to the review-debt
   table in the operator queue; the lane reviews the merged head when it
   returns and any correction is a follow-up commit. Hard gates are never
   skipped this way.
4. **A process that cannot land its work is broken, and fixing it comes first.**
   A routine run that cannot push, post or validate is repaired the same day by
   the lane that finds it: re-point the routine into a session that has the
   repository attached, call add_repo with push access, or change the route.
   A receipt is never left to die with a container: a run that cannot publish
   puts the full receipt text in its report, and the next run lands it.
5. **Natural waits are not stalls, but nothing waits alone.** A response window
   (issue 392, companion caps, observation endpoints) runs its course without
   nudges. While it runs, its owner advances a path that does not share the
   dependency. Every ACTIVE or CONDITIONAL row in [DIRECTIONS.md](DIRECTIONS.md)
   carries a dated next step at all times.
6. **Momentum check.** Each daily lateral run and each steward tick states, for
   the three named paths (human-first lending C4 and D12, virtual worlds C1 and
   D6, the agent-as-employer idea B10) and every ACTIVE direction, the last
   receipt and the next dated step. A path with no dated next step is a defect
   and is given one in the same run.
7. **Blocked tools are not blockers.** A 403, a missing tool, a denied host or a
   missing credential is routed around in the same run: attach the repository,
   use another reader, take the figure from a secondary source with its
   limitation stated, or hand the exact bytes to a lane that can write. Only a
   hard gate stops work, and then only that step.

## What this file does not change

The November 1 agent-loan STOP, every cap, consent limit and observation
window, the October 28 self-sustaining-growth rule, the public-content and
custody rules, and the lease and branch-protection rules. No spend, contact,
account, credential or deployment authority is created here. Merging remains a
reviewed maintainer step except under rule 3, which records the skipped review
rather than hiding it.

## Defects this file was written from (November 3)

| Defect | Fix |
| --- | --- |
| The daily lateral routine's November 2 run wrote a receipt on N1 and lost it: the fresh session had no repository attached, the push returned 403, and the commit died with the container. | Routine re-pointed into a repository-attached Claude session on November 3; the fresh-session routine disabled. The November 2 receipt is re-run by the next daily run. |
| The issue 396 selection due November 3 18:00 UTC was waiting on a brief to the operator. | Decided November 3 by Claude: [evidence](../evidence/lateral-decisions-20261103/README.md). |
| B10, Claude's own proposal, had no owner date and waited on the same selection. | Decided November 3 by Claude: same record. |
| The November 3 status update asked the operator whether to re-point the routine. | Not repeated. Rule 2. |
