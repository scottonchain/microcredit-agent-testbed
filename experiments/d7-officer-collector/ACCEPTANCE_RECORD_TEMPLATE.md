# Officer cutover acceptance record (TEMPLATE, every line NOT ACCEPTED)

This template creates no permission and records no decision. Each line is filled in by the person who holds the authority, with a
date and where the evidence lives. Deployment permission, spend and key custody are separate lines on purpose. Secrets, hostnames
and access details never go on a public board.

| Line | Question | Decision | By | Date | Evidence |
| --- | --- | --- | --- | --- | --- |
| a | Pinned runtime head and runbook accepted by the desk owners (pinned heads at the time: 9c181672 and ee8ceaf7) | NOT ACCEPTED | | | |
| b | Named operations owner and host (non-secret host report per `../d7-officer-observer/CUTOVER.md`) | NOT ACCEPTED | | | |
| c | DEPLOYMENT PERMISSION for that host | NOT ACCEPTED | | | |
| d | SPEND bounds for model calls and gas, approved separately from c | NOT ACCEPTED | | | |
| e | KEY CUSTODY: who holds the officer key on the host, separate service user, rotation, approved separately from c and d | NOT ACCEPTED | | | |
| f | Alert recipient and delivery path, and the watchdog's own host; the sender is wired so it receives only `serializeDelivery(...).message`; the local quarantine file (raw evidence from refused or altered items) has a stated location and is excluded from any log, board or sink that leaves the host | NOT ACCEPTED | | | |
| g | Cutover sequence S1 to S8 below completed in order, with the reconciliation table filled in | NOT ACCEPTED | | | |
| h | Delivered failure alert with recovery shown | NOT ACCEPTED | | | |
| i | Full synthetic journey passed (every stage), virtual and physical-device acceptance kept separate | NOT ACCEPTED | | | |
| j | Continuity across two old hourly boundaries without any steward relaunch | NOT ACCEPTED | | | |

## Cutover sequence (fence first; nothing here has been performed)

The old runtime keeps no durable journal, so its in-flight sends must be reconstructed from outside evidence. Comparing pending
requests with replies BEFORE the old runner is stopped leaves a race, and an empty desk queue does not prove that no transaction
is in flight. The order is therefore:

| Step | Action | Done by | Date | Evidence |
| --- | --- | --- | --- | --- |
| S1 | Fence new sends: remove the old runner's hourly relaunch (the line in the steward check-in) and stop the old process. | | | |
| S2 | Establish that the old runner cannot broadcast: no process holds the officer key, no relaunch path remains, and the key file is removed from the steward container or the key is rotated or revoked, as the owners decide. | | | |
| S3 | Record the freeze boundary: the time and block number F at which S1 and S2 both hold. | | | |
| S4 | Preserve evidence of old broadcast exposure up to F, kept restricted and off the public board: old log lines with reply transaction hashes, the officer account nonce at latest and at pending (before and after a settle interval), and receipts for every nonce from the first old-runner nonce to the pending nonce. | | | |
| S5 | Reconcile every known in-flight send and nonce through F and classify each (table below). A pending nonce above the latest nonce means something is in flight whatever the desk queue says. | | | |
| S6 | Compare pending desk requests with replies only now, after S1 to S3, and carry every UNKNOWN or pending item into the new journal as a held entry (nonce, hash if known, block) BEFORE the new signer is enabled. | | | |
| S7 | If old broadcast exposure cannot be reconstructed (missing log, RPC that cannot show nonce history, an unexplained nonce gap), remain STOPPED and HELD. Do not infer safety from absence and do not start a fresh empty journal. | | | |
| S8 | Only then enable the new signer under lines a to f. The new journal is never deleted once written. | | | |

Reconciliation record (one row per old send; request and hash columns are restricted evidence, never posted publicly):

| Request ref | Nonce | Transaction hash | Class | Evidence | Held in new journal |
| --- | --- | --- | --- | --- | --- |
| | | | SUCCESSFUL, REVERTED, REPLACED or UNKNOWN | | yes or no |

Classes, kept separate: SUCCESSFUL (mined, receipt status success); REVERTED (mined, receipt status reverted); REPLACED (the nonce was
consumed by a different transaction); UNKNOWN (no receipt, nonce unused or still pending, or the RPC cannot show it). Only
SUCCESSFUL is a delivered decision. UNKNOWN items stay held.
