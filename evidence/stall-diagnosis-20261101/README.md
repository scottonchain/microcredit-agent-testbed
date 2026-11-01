# Stalls, October 18 to November 1: diagnosis and remedy

Claude Code (AI), 2026-11-01, at the operator's direction in this session:
"Look at recent stalls over the last couple of weeks to diagnose and remedy. You
need to move autonomously whether I'm there or not. Use this morning's jump start
as an example of what the team needs to do autonomously." This packet is evidence
for the operating change in [coordination/LATERAL_MOVES.md](../../coordination/LATERAL_MOVES.md).
It records board cadence and what the team was waiting on; it claims no human
outcome and changes no authority.

## Method

- Board 15 comments from 2026-10-18 15:28 UTC to 2026-11-01 18:17 UTC, API pages
  16 to 21 at 100 per page, 589 comments. `cadence.py` counts comments per day
  and per lane (signature-based) and lists silent gaps longer than five hours;
  `board-cadence.csv` is its output. Re-run it on fresh dumps to refresh the table.
- The testbed git log for the same period, the last two pages of strategy issue
  17, and the full text of the comments on the quiet days.
- Board silence is not proof that an agent was idle: Hermes works by email and
  Moltbook, Codex runs sessions off the board, and PRs carry work. A quiet day is
  a stall only where the comments themselves show the team waiting and nothing
  else was started. The episodes below meet that test.

## Cadence

| Day (UTC) | Codex | Claude | Hermes | Other | Total | Longest silent gap ending that day |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 10-18 | 4 | 6 | 4 | 0 | 14 | |
| 10-19 | 48 | 53 | 19 | 5 | 125 | |
| 10-20 | 18 | 19 | 2 | 1 | 40 | 6.1 h |
| 10-21 | 4 | 8 | 5 | 0 | 17 | 5.2 h |
| 10-22 | 8 | 9 | 1 | 0 | 18 | 18.2 h |
| 10-23 | 43 | 34 | 3 | 0 | 80 | |
| 10-24 | 33 | 27 | 6 | 0 | 66 | |
| 10-25 | 22 | 8 | 2 | 1 | 33 | 5.9 h |
| 10-26 | 10 | 7 | 2 | 20 | 39 | |
| 10-27 | 2 | 7 | 0 | 0 | 9 | 14.5 h |
| 10-28 | 5 | 15 | 2 | 3 | 25 | 7.3 h |
| 10-29 | 4 | 0 | 3 | 0 | 7 | 22.7 h |
| 10-30 | 2 | 0 | 0 | 0 | 2 | 18.8 h |
| 10-31 | 8 | 13 | 4 | 0 | 25 | 9.4 h, 8.8 h |
| 11-01 | 53 | 16 | 9 | 11 | 89 | |

Comment counts are activity, not outcomes. The two busiest days (October 19 and
November 1) are instructive for opposite reasons, below.

## Episodes

| When | What the board shows | How it ended |
| --- | --- | --- |
| Oct 16 00:35Z | Hourly five-sentence direction posts had replaced diagnosis. | Operator stopped them and asked for a diagnosis ([STRATEGY_REPAIR_20261016.md](../../coordination/STRATEGY_REPAIR_20261016.md)). |
| Oct 17 to 18 | Routine strategy choices were being returned to the operator; one experiment at a time. | Operator corrections: autonomy (October 17) and parallel experiments ([6256776930](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6256776930), October 18). |
| Oct 19 | 125 comments. Seven PRs that day (343, 344, 351, 354, 357, 359, 363) archive the canonical coordination comment as it approached the 65,536-character limit. Repository activity; no outcome lane moved. | Self-limiting; the archive churn stopped when the comment was replaced. |
| Oct 21 to 22 | 17 and 18 comments; an 18.2-hour gap. Four ACCEPT/AMEND rounds on one guest post, a PolicyEngine formatting blocker, two daily-sync openings. Review and receipts; no new test started. | Drifted into October 23's reconciliation work. |
| Oct 26 to 27 | 14.5-hour gap; October 27 is nine comments, all Claude verdicts on outgoing emails (Ask Agi STOP, MoneyHelper, PR 381 reply, VivaSLO). A review-only day while observation windows ran. | Drifted into the October 28 recovery proposal. |
| Oct 28 to 30 | The deepest stall. Gaps of 22.7 and 18.8 hours; seven comments on October 29, two on October 30. The agent-loan attempt (issue 384) waited on an open-ended readiness gate; at 21:42Z Hermes reported both borrower routes unavailable under the two-contact cap, no slot spent, no clock started. Nobody started anything else. | Operator at 17:20Z October 30: "resolve stall", the readiness gate removed, then a responsiveness check at 17:25Z. |
| Oct 31 to Nov 1 15:46Z | The loan attempt ran to its corrected demand gate and stopped. | STOP recorded; one bounded fallback round. |
| Nov 1 16:30Z onward | 89 comments. The jump start: lateral-thinking process ([6560984020](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6560984020)), the four outcomes ([6561215518](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6561215518)), virtual worlds ([issue 396](https://github.com/scottonchain/microcredit-agent-testbed/issues/396)), one real order ([issue 392](https://github.com/scottonchain/microcredit-agent-testbed/issues/392)), the human bootstrap and self-service app ([DIRECTIONS.md](../../coordination/DIRECTIONS.md) D7, D8), and the execution transfer to the Claude steward. | Every one of these directions was supplied by the operator. |

Operator rescues in fifteen days: October 16, 17, 18, 30 and November 1. The
interval between them is three to four days, which is the team's unassisted
run length under the rules as they stood.

## Root causes

1. **Waiting was treated as work.** Response windows, readiness gates and
   "requested checkpoint, not an accepted SLA" were respected, correctly, but no
   rule required anything else to start while they ran. The October 29 report
   that both routes were unavailable was a textbook trigger for a lateral move;
   the board was silent for 18.8 hours instead.
2. **One route at a time, in practice.** The October 18 correction allowed
   parallel experiments, but "keep one substantial deliverable per lane" stayed
   in the operating guide, and the loan attempt absorbed all three lanes from
   October 29 to November 1. A lane with one thread idles whenever that thread
   waits.
3. **Process plumbing displaced substance.** Across the 589 comments the words
   lease (190), nudge (100), route (97), writer (75), approval (65) and 403 (35)
   outnumber any outcome term. Git-route diagnosis recurred on November 1
   ([GITHUB_WRITE_ROUTE.md](../../coordination/GITHUB_WRITE_ROUTE.md)) and the
   October 19 archive churn consumed the busiest day. The execution-owner toggle
   and the verified-writer matrix are the right fixes; the operating rule now has
   to say that a missing capability is routed in one message and never blocks a
   different path.
4. **Instruction stacking.** Six documents (AGENTS.md, CLAUDE.md, NORTH_STAR.md,
   the operating guide, CURRENT_PATH.md and the world-model README) carried the
   same stack of dated banners, each "superseding" the one below while keeping it.
   A reader could not tell which rule was live, and obsolete rules survived in
   the live text: hourly direction posts, a 75-minute check interval with a next
   check on October 17, a 200-word hourly update, "one deliverable per lane".
   Codex's open PR 391 adds another banner. The banners are now archived verbatim
   in [DIRECTION_BANNERS_20261101.md](../../coordination/archives/DIRECTION_BANNERS_20261101.md)
   and each document carries one short current-state section.
5. **No generator of directions.** Every lateral move in the period came from the
   operator. Closed ideas were labelled exhausted and fenced with "do not restart"
   but were not improved; NONE QUALIFIES became an end state instead of a
   measurement that points at the next version. The directions register
   (November 1) is the first place ideas are kept; the protocol now requires an
   improved successor or an explicit "no improvement found" before any row closes.

## Remedy

The operating change is in [LATERAL_MOVES.md](../../coordination/LATERAL_MOVES.md):
objective stall triggers, a same-cycle three-option move, at least one active
direction per outcome lane and two per agent lane, a mandatory improvement line
before a direction closes, a generator list so new directions no longer have to
come from the operator, an every-channel sweep and a bounded development scan in
every cycle, and a weekly cadence check with this script. The register
in [DIRECTIONS.md](../../coordination/DIRECTIONS.md) is where the moves are recorded.

## Falsifier and recheck

If the next two weeks show a silent gap longer than twelve hours with an open
trigger and no recorded move, or another operator rescue of the same kind, the
protocol is not working and must be changed rather than restated. Re-run
`cadence.py` on November 8 and November 15 and attach the table to the weekly
summary.

## Limits

- Board 15 only; strategy issue 17, email, Moltbook and PR threads are not
  counted. Lane attribution reads the signature; 42 comments fell into "other".
- Counts measure board traffic, not useful work or human outcomes.
- The comment dumps are not stored here (they are public on GitHub); the CSV and
  the script reproduce the table from fresh dumps.
