# Synthetic end-to-end journey for the credit-desk officer and borrower app (DRAFT spec, not built)

State today: NOT VERIFIED, and every stage below is NOT COVERED unless a line says otherwise. HTTP rendering of the app, an empty
pending queue and a log line are not evidence that an applicant would be served. Nothing here creates a wallet, signer, runner,
host or deployment. Requirements follow OpenAI's reviews on PR 470 (comments 6866735781 and 6867009333).

## The journey (one runner, ordered stages)

| Stage | What passes | Coverage today |
| --- | --- | --- |
| 0. Request to mined officer reply only | one synthetic request gets a mined, successful officer reply after the request block | NOT COVERED (spec only; this was the whole earlier draft and is the first sub-check of stage 2) |
| 1. Passkey and onboarding | the supported passkey flow creates the dedicated test identity and the app shows it ready | NOT COVERED |
| 2. Credit decision | the desk produces an actual officer decision (reply and, where the policy grants one, a line) for a synthetic request, not just any reply | NOT COVERED |
| 3. Borrow | the borrow transaction for the granted amount is mined and successful | NOT COVERED |
| 4. Repay | the repayment transaction is mined and successful | NOT COVERED |
| 5. Receipt reconciliation | the app's receipt and the chain state agree on amounts, status and hashes | NOT COVERED |

A stage that is unimplemented stays NOT COVERED in every report; a pass on later stages never upgrades an earlier one.

## Runner rules

- One runner. No second runner, no parallel instances. It owns a durable run record (stage, intent, tx hashes, status).
- Idempotent and resumable steps. Before ANY resubmission of a transaction the runner reconciles the status of the earlier attempt
  from the chain (mined, reverted, replaced, unknown). An unknown outcome blocks resubmission and raises an alert; it is never
  retried on a timer. A restarted runner resumes from the record, not from the start.
- Identity and exposure. A dedicated, valueless Base Sepolia identity used only by the journey, with test tokens, a fixed exposure
  bound per run and in total, and never counted as a human or a borrower in any metric. No mainnet send, ever.
- Keys. Recoverable, orchestrator-controlled keys under the existing custody gate: the owners approve where they live and who can
  read them. This draft names no key and holds none.
- Cleanup. Every run ends by sweeping test balances back to the funding wallet; a cleanup that fails or is uncertain is reported as
  not closed, never as clean, and the next run does not start until it is resolved.
- Reporting. A pass is posted as sanitized counts only (no address, no message text). A failure or a missed budget alerts the
  named owner.

## Acceptance separation

- Virtual-authenticator checks (software passkey in an automated browser) and physical-device release acceptance (real handset,
  real platform authenticator) are separate evidence. A virtual pass never satisfies the physical-device acceptance.
- The ten-minute decision budget is a proposal for the owners to set. It is not a verified service target and is no justification
  for the public wording "Usually within a minute"; that wording needs its own measured evidence.

## Drills this spec adds (also listed in CUTOVER.md)

- Externally delivered alert: cause a failure and show the alert reached the named owner through a path that does not depend on the
  failing host (a log line or an in-host flag does not count).
- Observer execution failure: stop the observer, make it throw, and feed it unreadable input; each must still produce an alert to
  the named owner, including the case where the observer is not run at all (an external dead-man check on its own output).

## What is NOT claimed

- Running any stage needs a funded test identity and a signer that nobody holds here. Authority for them is unowned.
- Passing proves the path worked at that time, not availability. The read-only observer (`observer.mjs`) supplies continuous
  signals; the journey supplies a periodic end-to-end proof.

## Offline part that exists now

`observer.mjs` and `test-observer.mjs` check the alert decision logic on synthetic inputs (165 checks; 37 of 37 deliberate
breakages caught in a throwaway copy). They read no chain, hold no key and send nothing. The observer fails closed: invalid
configuration, malformed or future-dated data, stale or missing chain reads and its own exceptions are all alerts.
