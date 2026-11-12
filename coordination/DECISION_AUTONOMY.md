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

8. **The permission-failure ladder.** A permission, authentication or access
   failure is a routing problem, never a terminal state (operator standing rule
   of October 11, board 15 comment 6111721411, and this direction). Climb the
   whole ladder in the same run before reporting a blocker, and name each rung
   tried in the run report. Before rung 2, push the branch if any push works,
   otherwise put the complete artifact (patch, file, receipt text) in the run
   report, so no receipt dies with a container. No rung moves a token, key,
   endpoint or inbox from one runtime to another. Two failures of the same
   class in two runs is a defect in the process: the fix goes into the routine
   prompt or this file in the same pull request as the work.

   | Rung | Action | Done when |
   | --- | --- | --- |
   | 1. Classify | Name the class: missing authentication, missing repository attachment, a denied host, a missing secret, a missing tool, a lock, a policy refusal. Different rungs follow from different classes; never retry the same call blind. | The class is in the report. |
   | 2. Repair the session | Missing repository or 403 on push: `add_repo` with push access, then retry. Missing tool schema: load it. Stale clone: fetch and rebase. Denied host on a documented route: read the environment documentation for that topic and take the documented alternative. | The retry succeeds, or the class is confirmed. |
   | 3. Check the configuration | `python coordination/github_route_preflight.py --probe-remote`; check that a needed secret or variable exists by name, never by value; read the environment's settings pages. | The missing piece is named exactly, or nothing is missing. |
   | 4. Reuse a route that worked | Read the [capability matrix](GITHUB_WRITE_ROUTE.md#verified-capability-matrix), the last receipts on board 15 and the session list: which session or lane completed this exact operation most recently, and how. | The operation completes by the proven route, or no session can use it. |
   | 5. Warm handoff to a live lane | One TM2 request on board 15 to the lane with the capability, carrying the exact operation: repository, base SHA, patch blob or branch, file scope, checks already run, authority, receipt required. Also `send_message` to the live Claude session that holds the capability, or create a child session with the repository attached and the exact task. The sender keeps the artifact alive and verifies the receipt; a handoff unacknowledged within one check interval is escalated once on the board. | The receiver's receipt arrives, or no lane is live. |
   | 6. Record and re-route | Write the blocker once in [OPERATOR_QUEUE.md](OPERATOR_QUEUE.md) with the exact setting to change and the default; re-point the routine that hit it (rule 4); continue independent work. | The row exists and the routine is repointed. |

9. **Stale work is decided, not carried.** Every run sweeps its own scope. An
   open pull request older than one check cycle with no owner comment gets one
   of the three outcomes of the October 6 rule: merge from a checkout, request
   named changes with a dated recheck, or close with reasons. A draft untouched
   for seven days is closed with "closed as stale, branch kept, reopen when
   resumed"; an outside pull request that addresses no open task is closed with
   a courteous reason within one cycle. A world-model action whose `due_at`
   passed more than seven days ago is moved to `done` with its evidence,
   `cancelled` with the reason and re-entry condition in `stop_conditions`, or
   re-dated with an owner who accepted. "Dates becoming past never cancel a
   promise" holds for an accepted outside commitment; it does not hold for an
   internal agenda whose meeting has passed. A direction row whose next date
   passed is decided the same way (rule 1). The session that finds the stale
   item fixes it; an item of a down lane carries "decided without <lane>: down".
10. **Scheduled work that cannot stall.** A routine whose job includes a
   commit, push or pull request fires into a persistent session with the
   repository attached and push verified (`git push --dry-run`); a
   fresh-session routine may only read and report. Every routine prompt names
   its fallbacks: `add_repo` and retry on a 403, merge under review debt when
   no reviewer answers, the full receipt in the report when nothing can be
   pushed. One timer per purpose: a routine arms at most the follow-up its own
   merge needs, and a chain of one-shot wake-ups that re-arm each other is
   replaced by one cron routine when next touched, because a missed link stops
   a chain. The first step of every run is the list of dates passed or due
   today in its scope. A run ends with a report under 200 words and never with
   a question to the operator; if you would put a suggested answer in the
   operator's text box, that is the decision, so take it and record it.

11. **An offer is a stall.** A run that finds a job it could do (a rebuild, a
   reconciliation, a cleanup, a follow-up test, a page the live site has and the
   source does not) never ends by offering it. It does one of two things in the
   same run: does the job now when it is bounded (under about an hour, inside
   existing authority, no new contact or spend), or creates the owned, dated
   item itself (a world-model action with owner and `due_at`, a DIRECTIONS.md
   next step, or a rung 5 handoff to the lane that owns the files) and reports
   "scheduled: <owner>, <date>". The phrases "if you want it", "let me know",
   "a separate job", "happy to" and "shall I" in a report are defects: the
   reader of the report is not the decision maker for work inside existing
   authority. The operator decides only the items in rule 2. If the run truly
   cannot tell whether the job is wanted, the default is the cheaper of doing
   it and scheduling it, recorded with the assumption, never a question.

## What this file does not change

The November 1 agent-loan STOP, every cap, consent limit and observation
window, the October 28 self-sustaining-growth rule, the public-content and
custody rules, and the lease and branch-protection rules. A merge under
review debt (rule 3) is never used for contract source, frozen calibration
files, anything that moves funds, or a change to the privacy checks; those wait
for the reviewer, with the wait recorded. No spend, contact,
account, credential or deployment authority is created here. Merging remains a
reviewed maintainer step except under rule 3, which records the skipped review
rather than hiding it.

## Defects this file was written from (November 3)

| Defect | Fix |
| --- | --- |
| The daily lateral routine's November 2 run wrote a receipt on N1 and lost it: the fresh session had no repository attached, the push returned 403, and the commit died with the container. | Routine re-pointed into a repository-attached Claude session on November 3; the fresh-session routine disabled. The November 2 receipt is re-run by the next daily run. |
| Board 15 reached GitHub's 2,500-comment limit at 23:18 UTC on November 11; new comments returned 403; the steward reported it to the lateral lane by session message as a protocol decision for the operator or owners, and no successor existed. | Rule 7: the lateral lane opened [board 462](https://github.com/scottonchain/microcredit-agent-testbed/issues/462) within the hour, retitled board 15, re-pointed its own routine prompt, asked the D16, directions and steward sessions to re-point theirs (each confirmed by session message the same night), and landed the pointer PR for the coordination documents (November 11). Standing rule, now in the board's body: past 2,400 comments the first lane that notices opens the next board, posts the handover as its first comment, points the old board forward and lands the pointer PR. No operator decision. |
| The issue 396 selection due November 3 18:00 UTC was waiting on a brief to the operator. | Decided November 3 by Claude: [evidence](../evidence/lateral-decisions-20261103/README.md). |
| B10, Claude's own proposal, had no owner date and waited on the same selection. | Decided November 3 by Claude: same record. |
| The November 3 status update asked the operator whether to re-point the routine. | Not repeated. Rule 2. |
| The November 3 policy review found 16 pull requests open 8 to 15 days without an outcome, 23 world-model actions past due since October 7 to 19, and an hourly check-in run as a chain of one-shot timers. | Rules 8 to 10 and [AUTONOMY_REVIEW_20261103.md](AUTONOMY_REVIEW_20261103.md); the 16 pull requests were closed the same day. |
| The daily lateral routine's prompts of November 5 to 9 reached the maintainer session only on November 10 (the session's inbound queue was not delivered for five days); no run, receipt or Friday summary for those days. | Recorded and caught up in the November 10 run ([receipt](../evidence/lateral-20261110/README.md)); the steward's hourly tick is asked to post 'lateral run missed' when no run comment exists by 21:00 UTC, so a stalled queue is seen within hours. |
| A vision-lane report on November 3 ended: the omnequa theme source backup is the November 1 version, the live site is built files on gh-pages, "rebuilding from source would mean reconstructing the live-only pages, which is a separate job if you want it". The operator had to decide. | Rule 11. The job became a dated handoff to the steward the same hour (board 15 and session message): reconcile `omnequa/theme/` source with the gh-pages build so the site can be rebuilt from source, by November 5 18:00 UTC, with the limitation recorded if any page cannot be reconstructed. |
