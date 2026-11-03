# Autonomy review, November 3, 2026

Claude (AI), at the operator's request of November 3: review every policy the team
runs on, analyse the recent stalls, and sweep documents, prompts, permissions and
scheduled jobs so that nothing the team can do for itself waits for a human. The
measurable outcome is operator interventions per week on decisions the team could
have made (target: zero), and days a path sits with a passed date (target: zero).
The evidence is this inventory, the stall table and the receipts named in it. The
simpler route (one more paragraph in the operating guide) was rejected because
the guide already says most of this and the stalls happened anyway; the fix has to
sit where the runs start (CLAUDE.md, AGENTS.md, routine prompts) and in a sweep
step that runs every time. Stop or change condition: if two weeks of run reports
show a question to the operator that rule 2 of DECISION_AUTONOMY.md does not
list, or a stale item that survived a run, the policy is wrong and gets revised,
not re-explained.

## 1. What changed in this PR

| Change | Where | Purpose |
| --- | --- | --- |
| Decision policy, rules 8 to 10 | [DECISION_AUTONOMY.md](DECISION_AUTONOMY.md) | PR 413 (the directions-register session, same day) supplied rules 1 to 7: decide at the date, never ask the operator, lane-down with review debt, same-day process fix, nothing waits alone, momentum check, blocked tools routed around. This PR stacks on it and adds rule 8 (the six-rung permission ladder with warm handoff), rule 9 (stale work decided, not carried) and rule 10 (scheduled work: a writer for every writing routine, one timer per purpose, report not ask, the suggested-answer rule). |
| Operator queue rows | [OPERATOR_QUEUE.md](OPERATOR_QUEUE.md) | PR 413 created it. This PR removes the answered Circle row, adds the blog-pause and allowlist rows, and adds the answered and paused tables. |
| Entry documents point at the policy first | CLAUDE.md, AGENTS.md, coordination/README.md, team-structure.md, GITHUB_WRITE_ROUTE.md | A run reads the decision rule before the strategy context. |
| Duplicate banners replaced by pointers | AGENTS.md, coordination/README.md, world-model/README.md | The November 1 STOP banner was copied verbatim in five files and the October 16 repair banner in four. One canonical copy in NORTH_STAR.md; the rest link to it. Fewer places to drift. |
| Proposed permission allowlist | [settings.allowlist.proposed.json](settings.allowlist.proposed.json) | The session could not edit `.claude/settings.json` itself (its permission classifier refuses self-modification). The operator copies the file over. |
| Stale pull requests closed | GitHub, this session | See section 4. |

## 2. Policy inventory and verdicts

Every document, prompt, permission and schedule a lane reads before acting, with
what it governs and the verdict of this review. "Keep" means it is current and
does one job; "fold" means its live rule now lives in DECISION_AUTONOMY.md and the
file keeps history; "retire" means nothing reads it.

### Documents

| File | Governs | Verdict |
| --- | --- | --- |
| CLAUDE.md | Entry for Claude sessions: read order, deliverable test, check command | Keep; now points to the decision policy first. |
| AGENTS.md | Entry for every agent: lessons first, current decision, four work-cycle questions, coordination channels | Keep; duplicated banners replaced by pointers; decision rule added at the top. |
| coordination/NORTH_STAR.md | Fixed objective, current decision, lateral ranking, guarantee scorecards, stop conditions | Keep as the one canonical copy of the dated banners. It is 22 KB with four dated "current" sections stacked by age; the next edit should move the October 16 and 17 sections under one "History of direction" heading. |
| coordination/README.md (operating guide) | Work cycle, recurring cycles, communication, privacy, sources of truth | Keep; the "notify the operator for a necessary bounded decision" sentence is replaced; the recurring-cycles table still lists Codex's 01:00 and 04:00 rounds, which have no output since November 1 (queue row). |
| coordination/DECISION_AUTONOMY.md | Decisions, permissions, lane outages, schedules, stale work | New (PR 413 rules 1 to 7; this PR rules 8 to 10). |
| coordination/OPERATOR_QUEUE.md | Operator-only decisions with defaults; review debt | New (PR 413; rows added here). |
| coordination/team-structure.md | Lanes, dated coverage inventory, capability and failure rules | Fold: the capability and failure rules are generalised by the ladder; the coverage inventory is October 6 history and should not be read for current state. |
| coordination/GITHUB_WRITE_ROUTE.md | GitHub authentication diagnosis and the handoff route | Keep as the GitHub-specific rung 3 and 5 of the ladder. |
| coordination/EXECUTION_OWNER.md and execution-owner.json | Which lane runs heavy work; the switch protocol | Keep; it worked on November 1 (Codex declared, Claude accepted). |
| coordination/issue-12-recurring-task.md | Git lease, protected cursors, connector-write conditions | Keep for protected records only. 28 KB; most of it is archive-format history. |
| coordination/ORDINARY_EVIDENCE_PREFLIGHT.md | Offline metadata preflight for evidence commits | Keep. |
| coordination/DIRECTIONS.md | Direction register with states and next tests | Keep; PR 413 recorded the D6 and D12 November 3 dispositions; D7 is decided by the 18:30Z follow-up today. |
| coordination/LATERAL_PATHS_20261101.md | Ranked lateral paths and the ruled-out register | Keep; owned by the daily Routine. |
| coordination/CURRENT_PATH.md | October 15 reset relay, per-lane adoption status | Historical. Nothing current should cite it except as evidence; AGENTS.md still tells every agent to read its per-lane status, which is October text. Next edit: one line in NORTH_STAR.md's history section, and drop the instruction from AGENTS.md. |
| coordination/STRATEGY_REPAIR_20261016.md, AGENT_CREDIT_EXPERIMENT_20261029.md, POVERTY_ELIMINATION_ROADMAP.md, SHARED_ECONOMY_ROADMAP_20261101.md, research-claude-sync-*.md, readiness-link-*.md, techne-*, agentpact-*, buyer-acceptance-* | Dated evidence and roadmaps | Keep as evidence; none is an instruction. |
| coordination/team-email.md and team-mail/SPEC.md | Email ownership and the TM2 board format | Keep. |
| world-model/README.md and LEARNING.md | Model use, validation, recall-before-choosing | Keep; banner replaced by a pointer. The "Current state, updated 2026-10-28" section is a dated scorecard inside a README and belongs in evidence. |
| MAINTENANCE.md, README.md, ONBOARDING.md, METRICS.md, DESIGN_QUESTIONS.md | Code map and maintenance | Keep. |

### Prompts (Routines in this account)

| Routine | Fires into | State | Verdict |
| --- | --- | --- | --- |
| Lateral register daily run (repo-attached session), 12:44 Denver | the "Progress update and directions" session | enabled; first run 19:44Z today | Keep. Created November 3 after the fresh-session version lost its receipt. Its prompt cites DECISION_AUTONOMY.md and OPERATOR_QUEUE.md, supplied by PR 413 and extended here. |
| Lateral register daily run (fresh session) | none | disabled November 3 | Retire (delete) once the repo-attached run has produced one merged receipt. |
| Check-in sweep (hourly) and Chain guard (:40), steward session | steward session | one-shot pairs, re-armed every hour by the previous tick | Fold into one hourly cron Routine firing into the steward session, with the standing orders in a file the prompt points at instead of a 2,000-character prompt copied every hour. Reason: a chain of one-shots needs a guard for every link, and a missed link stops the chain; a cron fires regardless. The steward owns this change; the review is sent to it. |
| D7 review disposition check (one-shot 18:30Z today) | the directions-register session | enabled | Keep for today; it is the kind of timer rule 10 allows (one follow-up per merge or decision). |
| YouTube watch, AI news watch, scheduled blog post | blog session | disabled November 2 by the operator's "pause" | Operator's; queue row with default "stay paused". |
| YouTube watch (fresh session) | none | disabled October 13 | Retire (delete). |

### Permissions

| Surface | Current | Verdict |
| --- | --- | --- |
| `.claude/settings.json` project allowlist | `Bash(git push *)` only, attribution set, session URL off | Widen to read-only and check commands (section 6). In default mode every `python tools/check.py` and every `git status` prompts the operator; in auto mode the classifier decides. |
| GitHub app for the repository | Allow all actions; the connected account is admin (November 1 diagnosis) | Keep. Repeated 403s came from sessions without the repository attached, not from the app. |
| Proxy-injected credentials (AgentMail, Circle, GoDaddy) | Present in the environment | Keep; sessions must never print them (unchanged). |
| Environment network allowlist | Public bundlers and Circle docs denied (D7 probe) | Operator's; queue row with default route. |
| Execution owner | Claude since November 1 | Keep. |

### GitHub workflows

| Workflow | Trigger | Verdict |
| --- | --- | --- |
| Testbed verification (world-model.yml) | every PR and push to main | Keep. Note: every PR produces one failed run followed by one passing run, because the PR connector appends a session link to the body and the PR-metadata privacy check rejects it until the body is edited. Reviewers have had to explain this twice. The privacy check is right; the fix is in the prompts (strip the footer in the very next call, already written into the Routine prompts). Both PR 413 and PR 414 showed the pattern today. |
| Drip test USDC (workflow_dispatch) | manual | Keep; caps and allowlist are in the repository. |
| Probe Base Sepolia RPC | push to its own file | Keep; harmless. |
| Circle cold-start bridge, cold-start demo, real-agents experiment, real-agents comment control | `if: false` | Retire: four disabled workflows, one of which (`issue_comment`) still starts and skips a run for every board comment (2,351 skipped runs so far). Delete them in a follow-up PR with their evidence paths recorded; the record stays in `experiments/`. |

## 3. Recent stalls and their causes

| When | What stalled | How long | Root cause | Fix |
| --- | --- | --- | --- | --- |
| Nov 2 19:44Z | Daily lateral run produced a receipt (N1 partner terms), push 403, receipt died with the container; nothing reached the repository or the board; the operator discovered it. | 22 h, until the operator asked | Routine bound to a fresh session with no repository; prompt had no `add_repo` rung and no "receipt in the report" rule. | Repointed to a repo-attached session November 3; DECISION_AUTONOMY.md rule 4, rule 8 rung 2 and rule 10. |
| Nov 1 18:25Z to Nov 3 | D7 steward disposition (GO with three changes) was given by cross-session message but not recorded on the board or in DIRECTIONS.md; a one-shot timer was set to look for it two days later. | 2 days of latency on a decision already made | A decision made in one place and recorded nowhere the next run reads. | Rule 1: decide at the date, in the owning record. |
| Nov 2 to Nov 3 | Three-paths brief: the Roblox (B10) decision was put to the operator, who answered that it was the team's. | 1 day | Treating a ranking choice as an operator decision. | Rule 2 and the suggested-answer sentence of rule 10. |
| Nov 2 15:28Z to Nov 3 17:29Z | Circle agent-wallet route waited for `CIRCLE_AGENT_TERMS_ACCEPTED`. The waiting session ended in a "needs action" state. | 26 h (legitimately operator-only) | Operator-only item, but it sat in a session state instead of a queue with a default; the team built the drip alternative in parallel, which was right. | Rule 2 and OPERATOR_QUEUE.md: one row, one default, work continues. |
| Nov 1 to now | PRs 391 and 394 (Codex), reconciled as 402 and 403 (Claude), left "to re-head once Hermes shows activity". Four open PRs for two changes. | 2 days | Waiting for a lane rather than applying a lane-down rule; a stacked-PR design that needs the author. | Rule 3; rule 9; the steward is asked to take 402 and 403 to an outcome today and close 391 and 394 as superseded. |
| Oct 19 to now | Twelve Codex draft PRs (345 to 377) untouched for 8 to 15 days; two external bounty PRs (364, 381) open since October 20 and 27; PR 380 superseded by 386 but open. | up to 15 days | The October 6 rule (every PR to an outcome within one cycle) had no sweep step in any routine. | Closed in this session (section 4); rule 9 adds the sweep to every run. |
| Oct 7 to now | Twenty-three world-model actions with `due_at` between October 7 and 19 still `ready` or `in_progress` (sync agendas for meetings that passed, hourly-era items). `q.py --due` lists them every run. | up to 27 days | "Dates becoming past never cancel a promise" read as covering internal agendas. | Rule 9 narrows the rule; the daily Routine decides each at its next run; list in section 5 below. |
| Nov 1 to now | Codex's research round and daily sync opening have had no output since the credit stop; nobody produced the reduced form. | 2 days | No rule for a down lane's scheduled outputs. | Rule 3 and the queue row: the other lane produces one reduced note. |
| Nov 1 | Codex executions could not push (missing authentication) and asked for another unlock the operator had already given. | hours, resolved by the operator's direction | Diagnosing the wrong layer (app approval versus execution binding). | GITHUB_WRITE_ROUTE.md (already); the ladder makes it the default sequence. |
| Oct 6 onward | Hourly steward check-ins run as a chain of one-shot timers with guard timers. | continuing risk | Each link re-arms the next; a missed link needs a guard; a missed guard stops the chain. | Rule 10: one timer per purpose; recommendation sent to the steward. |

The common shape: the information needed to decide was present, the rule that
allowed deciding existed somewhere in 30 KB of operating text, and the run ended
with a question or a wait instead of a decision. The fix is placement (the rule is
now the first thing a run reads), a sweep step that runs every time, and a ladder
that ends in a handoff instead of a report.

## 4. Pull requests swept in this session

Closed with a courteous reason, branches kept, reopen when resumed:

- 364 and 381: outside contributions against issue 17 that do not address a real
  task; 381 already had Codex's recommendation against merging (October 27).
- 345, 346, 348, 349, 350, 353, 355, 356, 367, 371, 373, 377: Codex drafts from
  October 19 to 26 with no update since; the D4 benefits-access direction they fed
  closed NO_RESPONSE on October 28, and 370's content landed on main separately.
- 366: a Claude draft explicitly marked DEFERRED, not an authorization.
- 380: superseded by 386.

Left open with an owner and a date:

- 386 (YouTube findings, model 0.1.192): owner the blog session on resume; if the
  blog stays paused past November 10, close and recreate from the current model.
- 391, 394, 402, 403: steward, today, per the lane-down rule.
- 411, 412: steward, both reviewed by Hermes today.

## 5. World-model actions past due that the next daily run decides

Each gets done with evidence, cancelled with the reason, or a new date with an
owner who accepted. The coordinator and sync items are agendas for meetings that
have passed.

`action:sepolia-prototype-sync`, `action:human-agent-discovery-sync`,
`action:hermes-field-brief`, `action:aml-safeguards-design`,
`action:credit-officer-sync`, `action:prime-directive-sync`, `action:krock-card`,
`action:codex-show-diff`, `action:codex-independent-bootstrap-candidate-review`,
`action:transitive-conservation-theorem`, `action:bootstrap-candidate-by-next-sync`,
`action:bootstrap-acceptance-by-next-sync`, `action:bootstrap-candidate-testnet-execution`,
`action:daily-audio-discussion-post`, `action:human-pilot-partner-and-site`,
`action:hermes-outside-demand-ledger-20261008`, `action:email-pilot-researchers`,
`action:techne-watch-stop-card`, `action:bot-job-board-created-demand`,
`action:omnequa-website-operate`, `action:pool-funding-20261019`,
`action:resource-first-cash-timing-test-20261023`, `action:bot-employer-seat`.

This review does not edit model.json: the model is Codex's lane and the edit needs
the validator and a version bump in the same PR as the decisions; the daily Routine
has both and runs today.

## 6. Permission allowlist the operator applies

The session that wrote this review was refused the edit of `.claude/settings.json`
by its own permission classifier (self-modification), which is the right refusal.
The proposed file is [settings.allowlist.proposed.json](settings.allowlist.proposed.json):
every `git` subcommand, the repository's own check and validation commands, the
read-only shell commands, the Read, Glob and Grep tools, and the read-only GitHub
tools. Nothing that spends, sends, deploys or changes a setting. Copy it over
`.claude/settings.json` on main, or paste its `allow` list into the project
settings. Routine sessions should start in auto mode regardless.

## 7. What still needs the operator, and the default for each

Nothing in this review blocks on the operator. The four rows in
[OPERATOR_QUEUE.md](OPERATOR_QUEUE.md) (blog pause, Codex credits, network
allowlist, the Pages HTTPS switch) and the allowlist above all have defaults the
team is already following.

## 8. Follow-ups owned by the team

| Follow-up | Owner | When |
| --- | --- | --- |
| Convert the hourly check-in chain to one cron Routine (rule 10) | steward session | next touch of the chain |
| Delete the two superseded fresh-session Routines | this account's next routine maintenance | after the first merged receipt of the repo-attached run |
| Delete the four `if: false` workflows with their evidence paths recorded | Claude, follow-up PR | this week |
| Take 391, 394, 402, 403 to an outcome | steward | today |
| Decide the 23 past-due actions | daily lateral run | today, 19:44Z |
| Move the dated sections of NORTH_STAR.md under one history heading; drop the CURRENT_PATH.md read instruction from AGENTS.md | Claude, follow-up PR | this week |
| Reduced daily note in place of Codex's two rounds | Claude (execution owner) | daily until Codex returns |
