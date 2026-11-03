# The trust interview (D16 prototype, shadow mode)

Claude Code (AI), the D16 lane, November 3, 2026. The agentic trust interview the operator asked for, built to the steward's seam in `desk-daemon.mjs`: `interview.mjs` exports `decide({ thread, facts, maxLine }) -> { reply, backing, score, cost, reasons, outcome, factors, dossier, version, ASSESS_US }`. With `MODE=interview` the daemon runs it in shadow: the rules officer still decides and replies, and the interview's score, outcome, recommended backing, reasons, cost and timing are logged in the `replied` line under `shadow`. Nothing it computes reaches the chain until the November 17 check compares its scores with the backers' judgment and with repayment outcomes. Testnet only; no real loan, no real money.

## Design (the reviewed officer rule, made concrete)

The agent extracts; code decides; every weight is published; every reason is a code from the adverse-action notice template ([compliance/adverse-action-notice-template.md](../../evidence/human-first-mainnet-20261103/compliance/adverse-action-notice-template.md)). This build extracts without a model call (the app's structured ask carries amount, purpose and term in one line; free text is parsed by patterns), so the cost per assessment is 0 dollars and the measured number is wall-clock microseconds (about 0.3 ms mean on the synthetic set). A model-assisted extraction can be added behind the same seam later and must report its dollar cost in the same field.

**Dossier** (from the applicant's messages and the chain facts only): amount, purpose (and whether it reads as a productive input), term, repayment source, each tagged `stated` or `none`; desk backing and loan history tagged `verified`; contradictions (two different amounts, or two template asks with different purposes); not-for-self. No name, address, age, language or any other prohibited-basis or proxy field exists in the dossier, and the scorecard never reads the transcript.

**Scorecard** (`WEIGHTS`, frozen): repayment source stated 25; purpose stated 15; purpose productive 10; amount within the desk's maximum 10; term stated 10; backer present 20; each prior loan repaid 10, up to 20; contradiction minus 20. Score is the clamped sum, 0 to 100.

**Hard rules before the score**: a defaulted loan (R09) and an open loan (R08) decline; "not for me" declines (R05); no backer at all declines (R03), because a score never creates an unbacked line (on the testnet desk the desk itself is the backer for the cohort; in the named cohort it is a person's deposit or the applicant's own).

**Cap** (`TIERS`): score 60 or more admits at the tier, 10 dollars for a first loan and 20 after a repayment, always bounded by the desk's `maxLine`; an ask above the tier is a counter-offer at the tier with R14; score 40 to 59 is a counter-offer at half the tier with the principal missing factors as reasons; below 40 declines with reasons; a contradiction caps the outcome at a counter-offer and is printed as R07.

**Conversation**: with fewer than three applicant messages and no hard rule, a missing purpose or repayment source is asked for, one thing at a time, and the current backing is kept, as the rules officer does. A decline prints the two principal reasons in plain words and never a score. Replies pass the daemon's `sanitizeReply` shape (under 420 characters, no links, no addresses).

## Shadow-scoring protocol (November 17 check)

1. Run the daemon with `MODE=interview` on the testnet desk. Each `replied` log line carries `shadow: { score, outcome, backing, reasons, cost, us, version }` beside the rules officer's actual backing.
2. For every applicant thread, record the triple (interview outcome and cap, rules officer's backing, the backer's own judgment where a named backer exists) and, after the term, the repayment outcome.
3. Report: agreement between the interview's cap and the backer's judgment; calibration of score against on-time repayment (binomial interval, the pilot's numbers are small); false approvals (interview admits, loan defaults); missed useful loans (interview declines, rules officer grants, loan repays); mean and maximum assessment time; cost. A randomised holdout of interview declines admitted with full backing is the only way to measure the screen's sensitivity (D7 screen rule 6); it needs the steward's consent and is not part of this build.
4. Stop condition from D16: if the shadow scores do not separate repayers from non-repayers, the interview stays an intake layer and the backer rule alone decides.

## Running it

```
cd experiments/d7-live
node --test test-interview.mjs              # 13 tests: schema bounds, outcomes, hard rules, reasons, injection, no prohibited fields
node interview.mjs interview-synthetic.json # shadow table over the 14 synthetic applicants, plus the summary line
MODE=interview RPC_URL=... DESK=... OFFICER_KEY_FILE=... node desk-daemon.mjs   # shadow mode on the testnet desk
```

The synthetic set is invented wording, no real person. Its expected outcomes are design assertions, not measurements; the measurement is the November 17 report.

## What this build does not claim

No validated model, no calibration, no human outcome. The weights are a published starting point for the shadow test, not fitted values. Reason codes R02, R04, R06, R10 to R13 are not evaluable in the app yet (no residence question, no income figure, no identity step, no sanctions screen on the testnet desk) and are not emitted.
