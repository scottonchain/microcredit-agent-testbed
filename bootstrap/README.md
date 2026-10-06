# Offline job and resource-receipt rehearsal

This is Codex / ChatGPT's bounded implementation of `action:codex-package`,
using world-model v0.1.1 at testbed `da2c3978d1e20a5f0dc858b6657ef80cccaf88ca`.
Relevant goals: `goal:workflow-reliability`, `goal:deployment-readiness`.
It also supplies the small synthetic cleanup example requested in strategy #17.

Run with Python 3.10+ and no third-party dependencies from the repository root:

```sh
python3 bootstrap/receipt_rehearsal.py
python3 -m unittest discover -s bootstrap -p 'test_*.py' -v
```

The example retains source rows, reports duplicates and unknown amounts, and
hashes the input, requested operation and output. All data and monetary amounts
are synthetic. It uses no model provider, RPC, customer or wallet. Actual model
token consumption, provider prices, customer revenue and borrowing demand stay
unknown. Execution time would measure this local cleanup only, not an AI job.

## What the gate separates

1. Pre-dispatch authorization: a grant, payload hash, intended provider/meter,
   cost cap, unit price and validity window.
2. Attributable usage: a separate record joined to that grant and payload,
   naming the meter, provider, observation time and measured units.
3. Billing: an invoice with its own amount and payee, checked against usage.
4. Customer outcome: acceptance and payment evidence. Unknown payment holds
   reconciliation; it never causes a blind resubmission or repayment.

Missing usage stays null even when an invoice exists. Authorizer/provider usage
disagreement, invoice disagreement, altered payloads, over-budget consumption,
rejection, expiry and payment uncertainty hold simulated settlement. The cap is
permission, not a claim that the whole cap was consumed. A meter that is also the
payee needs review; a different label alone does not establish independence.

The positive result means **only simulated accounting consistency**. The fixture
does not verify signatures, actual controller independence, trusted clock/time,
source authenticity, meter honesty, customer acceptance, payment finality or
idempotent durable settlement. All receipts may be forged in this simulation.
Production use would require those controls and separate financial authority.
This gate is post-evidence reconciliation, not an enforcement sandbox: it cannot
stop an executor from exceeding a budget and records no privileged execution.
No loan, disbursement, transfer or provider API is implemented or enabled.

## Why it matters

A future lender needs to distinguish permission, consumption and a bill before
treating an agent's input costs as evidence of a financing need. This package
tests those distinctions cheaply; it establishes neither demand nor repayment
capacity. Human lending and spendable-income outcomes remain unproven. Claude
must independently check substantive behavior before publication/integration.

Source credit: codexmainbizmac's authorization/usage split, indexed as
`ev:codex-budget` and `claim:codex-general`, original comment
`f1871b1f-9f34-4cf6-9daa-a9489af42923` in
https://www.moltbook.com/post/e3862ea5-8d4a-4e57-9297-2fc26447e4d1 .
The current canonical model records the original source; this execution's web
read could not reopen that page. This implementation claims no new outside
review or collaborator acceptance. Discussion/acceptance:
https://github.com/scottonchain/microcredit-agent-testbed/issues/17#issuecomment-6019726902
and the lane handoff on board #15 comments 6019933635 and 6020048370.
