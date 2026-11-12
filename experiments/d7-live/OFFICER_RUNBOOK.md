# Credit-desk officer daemon: runbook for a held reply

Scope: `desk-daemon.mjs` as of PR 458 (journal v2). Test network only, test tokens, one officer key, one daemon process.
This is operating guidance for whoever runs the daemon. It is not an acceptance of the daemon for release.

## What the journal is

The daemon records every reply transaction it is about to send in a state file, `<LOG>.state.json` (or `STATE_FILE`), **before** it
broadcasts. One entry per request, keyed `applicant#applicant-message-count`, with the nonce, the hash once known, the block it was
recorded at, and whether the reply is confirmed (`mined`). Its job is to make sure one request gets at most one officer reply even
when a receipt wait times out, an RPC node lags, a send call throws after the broadcast, or the process restarts.

## When a reply is "held"

An entry that is not confirmed is **held**. The heartbeat's `held` count is the number of held entries. A held reply is not sent again,
and the applicant waits, until chain evidence settles it:

| Evidence | Result | Effect |
| --- | --- | --- |
| Receipt shows success | mined | confirmed successful decision, no resend |
| The block that used our nonce holds our transaction (or, when our hash is unknown, a `reply` to this applicant) but no receipt could be read | mined (included) | **conservative no-resend state; success is not established** |
| Receipt shows a revert | reverted | entry dropped, the next poll answers the request |
| A different transaction from the officer account used our nonce | dropped | entry dropped, the next poll answers the request |
| Nonce not used yet, the RPC cannot show nonce history, our recorded start block is already past our nonce, or no evidence | unknown | **holds, with no time limit** |

The daemon stores both "confirmed by a successful receipt" and "included, receipt unavailable" as `mined: true`, because both mean "do not send
again". Operator reporting must keep them apart: only a successful receipt shows the officer's decision reached the desk. An included
transaction whose receipt cannot be read may still have reverted.

Age never releases a held reply. After `STUCK_AFTER_MS` (default 5 minutes) the daemon logs `earlier-reply-stuck` (repeated at that
interval) and a person is needed. A background sweep re-checks held entries every 30 seconds, so most settle without anyone acting.

## What "dropped" means

`dropped` means a different transaction used our nonce, so the one we recorded can never execute. It does **not** prove that ours was
never sent: it may have been replaced by a different transaction from the same key (for example a manual fix). A resend after
`dropped` is intended.

## RPC requirement

Settling by nonce history needs `eth_getTransactionCount` and `eth_getBlockByNumber` at an earlier block number. A non-archive node that
prunes old state cannot answer, so every held entry reads "unknown" and stays held. Use an RPC that serves history for at least the span
between the recorded block and the head (minutes to hours), or accept that a person settles stuck entries as below.

## Clearing a stuck entry safely

Do **not** delete the entry from the state file or delete the file. That removes the evidence that a transaction may have executed and
can produce a second officer message.

1. Read the entry (applicant, nonce, hash, `fromBlock`) from the state file while the daemon runs or after stopping it.
2. On a block explorer or a trusted RPC, look for the officer account's transaction AT THAT NONCE. Only a positive finding settles an entry:
   - the transaction at that nonce is our recorded hash, or a `reply` to this applicant: the reply was sent (included). Set the entry to
     confirmed (stop the daemon, set `"mined": true` for that entry, start it), or wait for the sweep once the RPC can show it. Read its
     receipt if you can: only a successful receipt shows the decision reached the desk; if the receipt is a revert, remove that entry so the
     next poll answers;
   - the transaction at that nonce is a different one: ours can never execute; remove only that entry (stop the daemon first) so the next
     poll answers.
3. **There is no deletion path from absence.** An unused nonce, an empty pending view, a failed lookup, an RPC that cannot show history, or
   the passage of time does not show that the broadcast never left: a node's pending view can omit a transaction accepted elsewhere, and an
   uncertain broadcast can appear later. In every such case leave the entry held, and fix the cause (a node that serves history; waiting
   for the nonce to be used) before anything is edited.
4. Record the outcome without publishing applicant-linked data. On the public board post only a sanitized outcome and a count (for example
   "one held reply settled as included, receipt not yet readable") and a reference to where the restricted evidence is kept. Do not post
   the entry key (it contains the applicant's address), the applicant's messages, or the matched transaction next to the applicant.

Never edit an entry without a positive finding. If unsure, leave it held: a held reply costs the applicant a wait, a wrong release can cost a
duplicate message. The manual `"mined": true` edit mirrors what the daemon itself does when it finds our transaction; it has not been
exercised against a live node.

## A journal file that will not load

If the state file exists but cannot be read, parsed or validated (wrong version, missing fields), the daemon exits with code 3 and logs
`state-unreadable` with a reason class. It sends nothing. Do not delete the file to get it started. Restore it from a copy, or reconcile
the entries from chain evidence as above and write a valid file.

## Other settings

`STATE_FILE` (journal path), `STUCK_AFTER_MS` (report age, default 300000), `LAST_REPLY_TTL_MS` (how long a confirmed entry is kept to
cover a lagging read, default 3600000), `RECEIPT_TIMEOUT_MS` and `MODEL_TIMEOUT_MS` (defaults 180000); the millisecond settings are
clamped, the path is not. One process owns one journal; a second daemon on the same key is not supported and is not made safe by this file.
