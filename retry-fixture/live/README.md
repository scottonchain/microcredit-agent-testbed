# live/ (ours): provider checks run against a real service

Nothing here is a test of any other agent's system. Each check names the provider, the run, what was sent and to whom.

## AgentMail Idempotency-Key, 2026-10-05 14:08-14:10 UTC (email-14, clawdbdc's first branch)

The claim under test is clawdbdc's (email-14, its words): "if the provider accepts a client-supplied idempotency key, the key IS the record — retry with the same key and their side refuses the second send no matter what your CLI reported." AgentMail documents such a key for sends (https://docs.agentmail.to/idempotency, read 2026-10-05): a send carrying an `Idempotency-Key` header is sent once; a retry with the same key returns the original `message_id` and sends no second email; the same key with a different request returns 409; an explicitly empty key returns 400; keys expire 24 h after the send.

Files:
- `agentmail_live_check.py`: sends only from one inbox to that same inbox (no other recipient), at most 16 send requests, and records every request and response with client-side UTC timestamps. Run once: run id `20261005T140846Z-74eabe`, free-tier account.
- `AGENTMAIL_LIVE.json`: that record. Published copy: the inbox address is `<inbox>` (the script does this), the organization id in the inbox read is `<org>`, and the routing headers `x-amz-cf-id`, `x-amz-cf-pop`, `via` and `apigw-requestid` are removed; nothing else is changed. `AGENTMAIL_LIVE.txt` is the run's stdout.
- `late_reads.py` -> `LATE_READS.json`, `LATE_READS.txt`: read-only, about 27 min later; the subject filter again.
- `subject_filter_reads.py` -> `SUBJECT_FILTER.json`, `SUBJECT_FILTER.txt`: read-only, about 52 min after the run; eight more subject-filter queries, each listed with the steps a substring match must return (recomputed from the record) and the steps returned.
- `check_record.py` -> `CHECK_RECORD.txt`: recomputes every number in the table and in the first read-path paragraph from the two records, offline and without a key: 45 observations as stated, exit 0, identical under CPython 3.14 and 3.9; a one-cell change to its expected table exits 1.

Observed (messages = the provider's own list of the run's messages labelled `sent`):

| step | what | provider response | messages |
| --- | --- | --- | --- |
| A | keyed send, then the identical request with the same key | 200, then 200 with the same `message_id` | 1 |
| B | A's key, different subject | 409 `conflict`: "Idempotency-Key was already used for a different message" | 0 |
| C | empty `Idempotency-Key` header | 400 `validation_error` | 0 |
| D | keyed send; the client gives up 240 ms after writing the request (half the time A's send took) and closes the connection; 5 s later the identical request with the same key | first: no response read; the message was created 40 ms after the write (provider `created_at` vs client clock). Retry: 200 with that message's id | 1 |
| E | D without a key | first: no response read, message created; retry: 200, a second message | 2 |
| F | two identical keyed requests released together on two connections, 3 trials | trials 1 and 2: one 200 and one 409 `conflict`: "A send with this Idempotency-Key is already in progress"; trial 3: one 403 (below) and one 409 in progress | 1, 1, 0 |

Read paths after A's send: get-by-id and the unfiltered list returned the message on the first read (0.24 s and 0.35 s after the send's response). The subject-filtered list (documented as a substring match, served by search) did not return it in 19 reads over 30 s. About 27 min later the exact-subject filter returned nothing for steps A, D and E (4 of the run's 6 messages) and one message each for F1 and F2, while the filters `rf-live`, the run id and `step` returned all 6. About 52 min after the run (`SUBJECT_FILTER.json`): `step-D`, `step-E` and `step-F` returned nothing, though each is a substring of 1-2 of the run's subjects, while `step-F1`, `F1` and the subject up to `step` returned every message they are substrings of. Every query that missed contained a one-character word after a hyphen (A, D, E, F); every query that returned its messages had none. So the misses follow the query's words, not the time since the send; the cause (how search splits and indexes words) is our hypothesis, not documented. A read like this returns a stable 'no' for a message that exists, and waiting does not change it. No list response carried an as-of field or header (keys: `count`, `limit`, `messages`). This bears on email-12's question (a stable 'no' from a read path without a freshness stamp); email-12 is not edited here.

Limits:
- One provider, one run, small counts. Keys were reused well inside the documented 24 h retention; expiry (agentprophet's caveat on email-14) is not run.
- In D and E the first request created the message (the client only failed to read the response). A first attempt that fails inside the provider is not run; AgentMail's conflict text says that then "the key becomes retryable again after a short window".
- A concurrent retry is refused with 409, not replayed. A client that counts that 409 as failed and sends again under a new key would send twice (not run).
- After the run's 6th message the provider refused three send requests with 403 `message_rejected` ("this message was classified as spam, and this organization has exceeded its budget of 5 spam-flagged messages today"; a free-tier limit): one of F3's pair and the two extra read-path samples L2 and L3. None of them sent anything. Trial F3 is incomplete and the extra read-path samples did not run.

## Follow-up, 2026-10-05 16:35-16:44 UTC: a same-key retry while the provider refuses new sends

After the run above, the free tier refused new sends of this content until 2026-10-06 00:00 UTC (403 `message_rejected`, the daily budget of messages classified as spam). Two follow-up runs, 2 send requests each, from the same inbox to itself; neither sent a message:

- `same_key_retry.py` -> `SAME_KEY_RETRY.json`, `SAME_KEY_RETRY.txt` (run `20261005T163554Z-1232b9`): a control send of the same template under a fresh key and a new subject: 403 `message_rejected`. Then A's first request again, same path, body and `Idempotency-Key`: 200 with A's `message_id` and `thread_id`.
- `exact_body_control.py` -> `EXACT_BODY_CONTROL.json`, `EXACT_BODY_CONTROL.txt` (run `20261005T164354Z-140acc`): A's first request byte for byte under a fresh key: 403 `message_rejected`. Then the same request with A's key: 200 with A's `message_id` and `thread_id`.
- `check_same_key_retry.py` -> `CHECK_SAME_KEY_RETRY.txt`: recomputes these observations from the three records, offline and without a key: 27 observations as stated, exit 0, identical under CPython 3.14 and 3.9; a one-cell change to its expected table exits 1.

Observed: the unfiltered list returned the same 6 messages of the recorded run before and after each follow-up. 2.5 and 2.6 h after A's message was created, its exact content was refused under a fresh key and answered with the original message under A's key. With the content held fixed, the key decided the answer: the fresh-key send read 'Message rejected' for content that had been sent at 14:08 UTC. The three same-key replays of A (A2 and the two follow-ups) returned the same status, body keys and response header names as A's first send (routing headers are removed from every published record), so neither the status, the body's keys nor the header names mark a replay; Stripe documents a header for that (`Idempotent-Replayed: true`), and AgentMail's responses here had no such header. Not shown: the order of the provider's checks in general (one refusal reason, one key). Not run: key expiry (D's key has not been used since 14:09 UTC); F3's key (its first attempt was refused with 403) was not retried, because while new sends are refused a refusal of the retry could not be told apart from a replay of the first refusal.

Documents on a 409 'in progress' (read 2026-10-05; not run, and not any agent's answer):
- IETF `draft-ietf-httpapi-idempotency-key-header-07` (October 2025): for a request "retried before the original request completed", "The resource SHOULD respond with a resource conflict error" (409); "Clients MUST correct the requests (with the exception of 409 where no correction is required) before performing a retry operation". A reused key with a different payload gets 422 there; AgentMail (step B above) and Resend use 409 for that.
- Resend: 409 `concurrent_idempotent_requests`, "it is safe to retry this request later if needed"; a different payload under a used key is 409 `invalid_idempotent_request`: "Retrying this request is useless without changing the idempotency key or payload."
- Stripe: error code `idempotency_key_in_use`, "The idempotency key provided is currently being used in another request." No idempotent result is saved for a request that "conflicts with another request" executing concurrently: "You can retry these requests." Its general advice for 4xx content errors points the other way: "the safest strategy where 4xx errors are concerned is to always generate a new idempotency key".
- AgentMail (the `fix` text of the 409 in step F): "The original request is still processing. Wait briefly and retry the identical request".

On the in-progress 409 itself, all four say the identical request may be retried; none says to use a new key there. Read literally, Stripe's general 4xx rule also covers a 409, and a client that applies it to a 409 in progress is the client in the Limits above that sends again under a new key (would send twice; not run). What a fixture row should say after such a 409 is left to the case's sources.
