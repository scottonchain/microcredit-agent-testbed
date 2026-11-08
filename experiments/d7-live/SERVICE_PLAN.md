# Officer service: durable operation plan (offline stage)

Status: design and offline proof only. Nothing here is wired into `desk-daemon.mjs`, activated, funded or deployed.
No host is authorized (see the board inventory), so no cutover is possible yet.

## Problem

The live credit-desk officer is `desk-daemon.mjs`, one background process. It runs in a container that is recreated about
every hour, so replies to applicants can wait up to an hour or more. The app says so (waiting text, commit 647aea3a on
the focus-fix branch). Today the daemon has no sole-writer lease, no persisted record of an operation in flight (its
in-flight set lives in memory), no status output, and no timeout on its RPC and model calls.

## What this branch adds (all under `service/`, tested by `test-service.mjs`)

| Piece | File | Behavior |
| --- | --- | --- |
| Sole-writer lease with fencing | `lease.mjs` | One holder at a time. A new holder after expiry gets a higher token. The old holder is refused (`StaleWriter`) before each chain write, and again just before the broadcast. Released leases keep the token, so it never goes backwards. |
| Pending-operation journal | `pending.mjs` | An operation is written before its chain write; the signed transaction hash is written before broadcast. States intent, sent, done, abandoned. An unreadable journal stops the service. |
| Reconcile before replay | `pending.mjs` | After a restart, each open operation is decided from chain facts: confirm, failed, wait, replay-allowed, hold. Nothing is replayed without a decision. A recorded transaction that stays unmined past a bound is held for a person. |
| Bounded calls and backoff | `timing.mjs` | `withTimeout` for RPC and model calls; capped exponential backoff with bounded jitter for restarts. |
| Sanitized status | `status.mjs` | Time of the last completed poll, whether it worked, time of the last reply, count of open operations. Readers see unknown (no or unreadable file), stale (old), degraded (recent failed poll) or ok. No heartbeat is invented: reading never writes, and only a completed poll updates the file. |
| Poll cycle | `worker.mjs` | Lease, reconcile, then one journaled and fenced write at a time, then status. Chain access is injected. |

## A fact the design depends on

`CreditDesk.reply()` does not revert for an applicant who is not pending: a blind second reply appends a second officer
message to the thread (and re-backs if the amount differs). So replay safety cannot rely on the contract. It relies on
the journal: the transaction hash is recorded before broadcast, so "replay-allowed" is only returned when no transaction
can exist, and "already applied" means the applicant is no longer in `pending()`. If the applicant writes again after the
reply, they are pending again and a fresh reply to the new message is correct.

## Proof (offline, `node --test test-service.mjs`)

Stale-writer refusal (zero writes after takeover); a second instance does no work; restart after a crash before the chain
write, after the chain write, after the hash is journaled but before broadcast, and with the RPC down during reconcile;
hung RPC bounded; status states; backoff bounds; nothing wired into the live daemon. Deliberate breakages of the fence,
of replay-on-unmined, of journal-before-broadcast and of status honesty each fail tests.

## Not proven

No real chain, no real signer, no model call, no container boundary, no host. The `chain` object the worker needs
(`pending`, `prepare` returning `{txHash, broadcast}`, `receipt`, `applied`) has not been implemented against viem and the
desk ABI; that is the first wiring step. The lease directory must live on storage that survives the host's restarts.

## Staged cutover (when a host is authorized; none is now)

1. Authorized owner names the host and confirms: same policy, mode, funding limits and signer; credentials stay in their
   existing approved storage; no spend or signing authority beyond what the existing worker already has.
2. Implement the `chain` adapter and wire `worker.mjs` behind a flag, off by default; review the exact head.
3. On the host, dry run against a fork or read-only chain: status and lease only, no writes.
4. Disable the old supervisor (the hourly relaunch) and verify its absence: no `desk-daemon.mjs` process anywhere, then
   start the one worker. The lease is the fence if the old process comes back.
5. Publish the sanitized status only as unknown, stale, degraded or ok.
6. Verify operation across at least two former hourly container boundaries and report actual poll and reply receipts.

If no eligible host exists, the options are those on the board and the app keeps the honest periodic-service text.
