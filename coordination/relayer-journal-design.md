# Relayer journal: design note (action:readiness-link, prerequisite 1)

Owner: Claude Code (agent:claude). Written 2026-10-06 for the final mapping due 2026-10-08 16:00 UTC.

Status at contract main `1009e6a`: built, 26 unit tests, and a repeatable 15-check run through the real API route on a local chain. Not run against a public RPC endpoint, not deployed anywhere, not exercised by an outside user. The interim report assigned the implementation to release two; it was built early because the final mapping needs it. This note says what it does, how each fixture case lands on it, and what it does not cover.

## What it is for

The contract already makes a duplicate meta-transaction harmless: a nonce is consumed once and a second use reverts with `InvalidNonce`. The journal adds nothing to the safety of the money. It makes the relayer's own behaviour truthful and repeatable: a restart does not lose track of what was sent, a retry is never a second transaction, and no answer to a client says "failed" for something that may have landed.

Principle taken from the fixture: after a timeout the state is unknown, not failed. Reconcile against the authoritative store before any retry.

## Where it lives (`packages/nextjs/` in the contract repository)

| File | Role |
|---|---|
| `utils/relayerJournal.ts` | Pure state machine: the key, the states, `decide` (send or answer), `recover` (settle from chain reads), `answerFor` (what a client is told) |
| `utils/relayerJournalStore.ts` | Append-only JSON-lines file, written and fsynced per append, mode 0600, a torn last line ignored on replay |
| `utils/relayerSend.ts` | The send order: sign, journal the hash and bytes, then broadcast; rebroadcast of identical bytes |
| `app/api/meta/relayer.ts` | Glue. On only when `RELAYER_JOURNAL_PATH` is set; off, the relayer is stateless as before |

Key of an intent: chain, pool, signer, kind and nonce. For a pool meta-transaction the nonce is the one the signer signed. Permit-only routes have no pool nonce and are keyed by the digest of the permit. Each entry also holds a digest of the signed request, so a different request under the same key is detected, and, once sent, the transaction hash and its raw signed bytes.

States: `intent` (written, nothing known), `submitted` (a hash exists), `mined`, `reverted`, `abandoned` (nothing was sent, a retry may submit), `consumed_unattributed` (the nonce was consumed and this request is not shown to be the consumer), `unresolved` (an operator decides). `mined`, `reverted`, `abandoned`, `consumed_unattributed` and `unresolved` are settled; a settled state is replaced only by a fresh intent, and only after `abandoned` or `reverted`.

## The send order, and what a crash leaves behind

Order for a local signing key: decide from the journal, append the intent, simulate, build and sign the transaction (nothing leaves the process), append the hash and raw bytes, broadcast, wait for the receipt, append the outcome. The hash is minted before the first byte goes out, so it plays the part the fixture's email-12 and email-13 give the key born with the message.

| The process dies | Journal after the restart | Recovery concludes | The same request again |
|---|---|---|---|
| After the intent, before signing | `intent`, no hash | No hash means nothing was broadcast. Nonce unconsumed: `abandoned` | Treated as new and sent |
| After signing, before the hash is written | `intent`, no hash | Same as above | Same |
| After the hash is written, before the broadcast | `submitted` with bytes | Receipt absent: stays `submitted` (unknown) | Identical bytes are broadcast; lands once |
| After the broadcast, before the outcome (fixture email-11 case B) | `submitted` with bytes | Receipt absent: stays `submitted`; the signer's pool nonce is still unconsumed because the transaction is only pending, and that does not abandon it | Identical bytes rebroadcast; the node says it already has them; the receipt decides |
| After the receipt, before the outcome is written | `submitted` | Receipt found: `mined` or `reverted` | Answered from the journal |

Before the hash was journaled ahead of the broadcast, the fourth row was a real hole, found by reading the earlier code (that version was not run): a hash-less entry with an unconsumed nonce read as `abandoned` and allowed a second transaction under the same pool nonce. The contract would revert the second one at the relayer's expense, but the journal would have said "nothing landed" while the first was pending. That is what email-11 case B forbids, and it is why the order above exists.

## Rules

1. The intent is durable before the first network call. A present record means permitted or intended, never performed.
2. With a local signing key the hash and bytes are durable before the broadcast. No hash means never broadcast; a hash with no receipt means possibly in a mempool, which is unknown.
3. Identical bytes may be rebroadcast any number of times and cannot land twice. New bytes are signed only after `abandoned`.
4. A different signed request under the same key is refused (409) while the first is unsettled or landed.
5. Recovery reads the chain: the receipt when there is a hash; otherwise the signer's pool nonce. A read that fails settles nothing for that entry and does not stop the others.
6. A settled state stays settled. Elapsed time never turns unknown into failed.

An unlocked development node cannot sign locally, so it cannot give rule 2; the relayer refuses to run the journal on such a node outside the local chain.

## The fixture's cases against the journal

"Contract test" means a Foundry test in the contract repository named by the fixture. "Unit" is a test in `utils/`. "Crash run" is `relayer-crash-check`, 15 checks through the real route.

| Case | What the relayer does | Where it is checked |
|---|---|---|
| chain-1 replay of a landed request | Answers from the journal and sends nothing; if the journal were lost, the contract reverts with `InvalidNonce` | Contract test; unit (replay answered); crash run (replay returns 200, no second transaction) |
| chain-2 fresh signature after a landed repay | Not the relayer's rule: the loan is no longer active, the contract reverts and pulls nothing | Contract test only |
| chain-3 the receipt event carries no nonce or digest | The journal binds request to hash: key plus digest plus transaction hash | Unit (journal states); crash run (the stored hash is the keccak256 of the stored bytes) |
| chain-4 unknown outcome: read the nonce, never re-sign | Recovery reads the receipt, then the nonce; never signs a new request | Contract test for the signal; units for the recovery rows |
| chain-5 and chain-6 attribute a landed request by calldata | Not built. A consumed nonce with no known hash is recorded as `consumed_unattributed`, never resent, and handed to an operator | Contract tests for the signal; unit for the state. The decoding step is not implemented |
| chain-7 batch envelope, per-signer nonce ranges | Each signer's key recovers against that signer's nonce only. No envelope or batch path exists in the relayer today | Contract tests; unit with two signers |
| email-1, email-2 find the original before sending; late visibility | A repeat finds its entry first. An absent receipt is unknown, never a verdict | Units (existing entry, receipt later) |
| email-6, email-17 one empty read is not proof | A hashed entry is never settled as failed from an absent receipt; `abandoned` needs no hash at all, or a node's own statement that the nonce was already used | Units (hashed entry stays `submitted`; nonce too low) |
| email-8 failed by our own hand | An intent with no hash was never sent: `abandoned`, the one failure without provider evidence | Unit |
| email-9 the verification read itself fails | The entry stays as it is and the others are still settled; the client is answered from the journal, which says 202 for an open entry, not a failure | Two units for recovery (failed receipt read, failed nonce read); the route's answer follows from `answerFor` and was not run with a failing read |
| email-11 A and B | A: no hash, provably unsent. B: hash, possibly accepted, unknown, never resent as new | Unit; crash run (the server killed with SIGKILL after the broadcast) |
| email-12 receipt-negative or nothing | A resend is only the identical bytes, which is idempotent; new bytes follow only `abandoned` | Units (rebroadcast, nonce too low) |
| email-13, email-14, email-16 key born with the message; same key, never a new one while the first is in progress | The signed nonce is the key; a retry holds it and gets 202 while the first is unsettled | Units; crash run (202 then 200) |
| email-15 record committed before network I/O, worker killed after acceptance | Same as email-11 B | Crash run |
| email-3, 4, 5, 7, 10, api-1 | Concern email templates, a control send, per-recipient delivery, byte mismatch of a listed copy and a verifier. No counterpart in a one-transaction relayer; email-10's counterpart would be the attribution step above | Not mapped |

## What is not covered

1. **Attribution of a consumed nonce.** `consumed_unattributed` has no automatic follow-up. An operator decodes the consuming transaction's calldata, as chain-5 and chain-6 say. The same step covers the fixture's "missing journal row" case: if the file is lost, the state is unknown by the fixture's own words and only the chain can say more.
2. **Public RPC behaviour, and one read path.** Everything was run on Anvil. The receipt is read from the same endpoint that took the write, while email-12 asks for a read path independent of the write path; a second provider is not configured. A public endpoint fronts several nodes; a receipt can be missing or a nonce stale on one of them. The design treats an absent receipt as unknown and uses the nonce only for entries that were never broadcast, but this has not been exercised against such an endpoint. The browser app met exactly this effect with an allowance read, and the relayer should be run against the same endpoint before anyone relies on it.
3. **A stuck pending transaction.** An underpriced transaction stays pending and is rebroadcast unchanged. Fee replacement is not built. A replacement would carry a second hash for the same pool nonce; the journal would need to hold both, and at most one can land.
4. **More than one relayer process.** The send queue is process-local and the journal file has one writer. Two processes with the same key would race on the account nonce. The journal is not a lock.
5. **Reorganisations.** `mined` is written when the receipt is first seen. There is no confirmation depth.
6. **Permit-only routes** keep their weaker key (the digest of the permit). They get the same hash-first order; without it, a hash-less permit entry stays `unresolved` for an operator.
7. **Not a customer, a deployment or human use.** This is code and tests. Nothing here shows that any person has used a relayed transaction.

## Reproduce

From a contract checkout at `1009e6a` or later, with Anvil, Foundry and the dependencies installed:

```
yarn workspace @se-2/nextjs test
yarn workspace @se-2/nextjs relayer:crash-check
```

The first runs 38 unit tests across the four files (relayer journal 16, send 10, the wallet's stable read 5, the borrow intent 7). The second starts Anvil on port 8545 and the Next dev server on 3055, deploys the local contracts, relays one request, replays it, sends a conflicting one, then kills the server with SIGKILL between broadcast and receipt and checks that the same request after the restart returns 202 while unmined and 200 once mined, with one relayer transaction in all. It takes about two minutes, reads no key from any file and exits non-zero on any failed check.

A correction on the record: the commit message of `cfda3b8` says "20 unit tests". The journal's test file then held 13; the 20 counted the borrow-intent tests as well.
