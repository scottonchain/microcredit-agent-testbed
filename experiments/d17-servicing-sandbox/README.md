# D17 W3 servicing sandbox (text only, scripted baseline)

Status: draft for non-author review. Nothing here is live. No model call, no network, no WhatsApp number, no signer, no account,
no spend, no real person or real ledger. Every name, phone number and amount in `fixtures.json` is invented.

## What it is

A deterministic Spanish servicing assistant for small short-term loans, used to test the W3 rules in
`coordination/directions/whatsapp-local-currency-channel.md` before any model or any human is involved:

- Every number in an outgoing message comes from the fixture ledger through a template (`servicing.mjs`). The assistant never
  repeats or accepts a number the sender typed, and never states a payment as received unless the ledger says so (it cannot, so a
  claimed payment goes to a human).
- Hardship, a claimed payment, a request for a person, 14 or more days late, a failed identity check and two misunderstood
  messages in a row all raise a human escalation with a 24 hour window (`escalation_window_hours`).
- Impersonation (a relative or "on behalf of" claim, an unregistered number) gets no loan information. A phone shared by two
  borrowers (b03 and b04) needs name plus verification word; three failures escalate; a borrower never receives the other's numbers.
- Instruction-override attempts are refused with no data.
- Lateness tone has two tiers without threats or collection vocabulary (the audit rejects a list of such words).
- `audit.mjs` checks every outgoing message: each amount, date, instalment index, count, days-late and hours figure must be a
  ledger value for that borrower, and any other digit is an error. The report metric is errors per numeric utterance.
- `transport.mjs` is an in-memory channel with a manual clock and an escalation deadline check.
- `simulate.mjs` runs all templates for all borrowers in both tones plus 14 red-team conversations.

## Run

    node test-servicing.mjs     # 224 checks, exit 0 only if all pass
    node simulate.mjs           # counts in the report format; exit 1 on any numeric, tone or scenario failure

Node 20 or later, no dependencies.

## Limits (read before quoting any number)

1. This is a scripted baseline, not an LLM. Zero numeric errors in 79 numeric utterances is true by construction for templates
   and says nothing about the error rate of a model-driven agent. A model step needs its own measurement against the stop
   condition (a misstated number more than once in a hundred sampled conversations) with the same audit.
2. Text only. No voice notes, no images, no spelling variants beyond accent stripping. Real Spanish from real people will miss
   the keyword rules; the fallback is "not understood", then a human after two misses.
3. First matching rule wins. A message that mixes intents ("no puedo pagar, cuanto debo") is treated as the earlier rule. Any
   message containing a digit and no other intent is answered as a balance question; this is a known coarse rule.
4. The late-days figure is supplied by the caller in the simulation, not derived from a clock job.
5. The simulated human answers after a configured delay (default 6 h). The on-time escalation figure tests the deadline logic,
   not any real person. A test with a 30 h delay shows the metric does fail.
6. The Spanish text needs review by a native speaker from the target community before any human sees it. Quetzal formatting and
   the facilitator name are fixtures, not a claim about a real lender.
7. Five named volunteer testers are usability evidence. They do not prove an error rate below one in a hundred.
8. Consented human volunteers on record: 0. `CONSENT_ES.md`, `FACILITATOR_ES.md` and `METRICS_TEMPLATE.csv` are drafts and have
   not been sent to anyone.

9. Not wired into `tools/check.py`. The two node commands above are the checks; adding them to the shared gate is a reviewer decision.

## Files

`fixtures.json` synthetic ledger; `servicing.mjs` templates, rules, formatting; `audit.mjs` numeric and tone audit;
`transport.mjs` simulated channel; `simulate.mjs` scripted run; `test-servicing.mjs` checks; `REPORT.md` first checkpoint report;
`CONSENT_ES.md`, `FACILITATOR_ES.md`, `METRICS_TEMPLATE.csv` drafts for a later human step.
