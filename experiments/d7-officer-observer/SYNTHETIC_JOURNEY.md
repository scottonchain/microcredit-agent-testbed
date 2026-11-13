# Synthetic end-to-end journey for the credit-desk officer (DRAFT spec, not built live)

State today: NOT VERIFIED. No synthetic journey exists. HTTP rendering of the app, an empty pending queue and a log line are not
evidence that an applicant would be served.

## The journey

1. A dedicated synthetic applicant (a throwaway test wallet with test tokens, labeled as synthetic in the desk) writes one request
   on the test desk.
2. The officer is expected to mine a reply to that applicant's request inside the agreed budget (initial proposal: 10 minutes at the
   desk's poll interval; the owners set the number).
3. The check passes only if a mined, successful officer reply transaction to that applicant exists after the request block. A reverted
   or missing reply, or a reply that is the UNAVAILABLE text, is a recorded failure of the journey.
4. A failure or a missed budget alerts the named owner. A pass is posted as a sanitized count only (no address, no message text).

## What is NOT claimed

- Running the journey needs a funded synthetic wallet and a signer. Neither is created or used by this draft; authority is unowned.
- The synthetic applicant must never be counted as a human or as a borrower in any metric.
- Passing proves the path worked once at that time, not availability. The read-only observer (`observer.mjs`) supplies continuous
  signals; the journey supplies a periodic end-to-end proof.

## Offline part that exists now

`observer.mjs` and `test-observer.mjs` check the alert decision logic on synthetic signal inputs (20 checks; 12 of 12 deliberate
breakages caught in a throwaway copy). They read no chain, hold no key and send nothing.
