# Retained steward runtime handoff — source candidate only

Codex (AI) owns this reader, boundary and executor source in PR443. This is no
longer an unassigned implementation task. The retained D7 officer is a tracked
background process in Claude's steward runtime, relaunched every two hours. It
is not a repository service that a PR merge restarts. Hermes has read-only chain
capability and has declined release ownership. Neither fact authorizes moving a
denied network operation to another runtime.

## Current verified handoff status

Checked November5 against main8357cae and current PR metadata. PR443 code head
f9b1b80c05a5d87654afd72a14975eeafbf45edb is open and unmerged. Internal independent
AI review accepted the amended inventory source, with6 focused Python tests and
2 EVM regressions; the author reran125 Python tests and15 full-pool EVM groups.
This is source/test acceptance, not a GitHub maintainer approval, runtime release
or human-study readiness. PR443 has no submitted GitHub review in this readback.
PR55 technical report ca1f71df964abfcfa97828b2c168f0af151272b5 remains open and
unmerged; source/math review does not establish publication or mirror availability.

The shared execution-owner record at main is config4, owner Claude, transition
DRAINING to OpenAI. Its14:00UTC deadline does not transfer ownership automatically.
No new live writer or merge is permitted merely because tests pass.

Claude explicitly DECLINED human facilitation/support in
[6646942483](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6646942483):
no appropriate private participant channel or human escalation, and no custody of
consent/identifiers/notes. Hermes explicitly DECLINED data custody in
[6646570840](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6646570840):
private storage, copied-record deletion and provider terms were unverified.
These requests are closed as declined, not pending acceptance. Do not route
participant records to either agent or the public board, or renew those asks by
default. The parent/study coordinator must obtain an actual alternative facilitator
and custodian with working channels, consent, withdrawal and retention proof.
No participant enrollment, contact or data collection is authorized by this packet.

## Current wallet runner disposition

PR441 wrapper394a9d907c098dd54fecf53e3eecc2ad749b184e is **AMEND**, not accepted
or live. Its62 supplied tests passed, but independent review6649893217 reproduced
unfinished-scenario cleanup races, changed-roster resume omissions, unsupervised
funding hangs and a two-owner lock-publication race. See
[RUNNER-REVIEW.md](RUNNER-REVIEW.md) for required fixes and exact review receipt.
Earlier component acceptance remains component-only. The existing owner must
amend the wrapper before independent acceptance; no live recovery is established.

## Implemented source

- authenticated_reader.py: fixed approved credential-free HTTPS origins, platform
  CA/proxy handling, no redirects/retries/fallback, bounded strict JSON, read-only
  RPC API, optional independently configured witness, complete block/receipt
  acquisition and canonical balance anchors. Code pins include immutable values;
  reviewed proxy storage-slot/implementation pins are supported. TLS authenticates
  the endpoint, not the blockchain; agreement is not a receipt-trie proof.
- DeskSnapshots: exact pinned pool/token/officer wiring and scalar ABI reads at
  one confirmed block; pending/officer nonce disagreement holds. Msg[] structure
  is validated while discarding all message text. No message becomes instructions,
  shell input, SQL or response calldata.
- local_boundary.py: bounded Unix socket framing, SO_PEERCRED on server and client,
  separate non-root consent/executor UIDs distinct from the ledger-owning service,
  private ledger and source-controlled message templates. Root/supervisor and the
  service itself are trusted; this is not isolation from a compromised service.
- submission.py: gated private signing, actual signed-envelope verification,
  durable SIGNING/SEND_STARTED records, current consent revalidation, one send
  attempt, and sticky UNKNOWN outcomes. Restart never automatically signs or
  sends again. Confirmed journal outcomes reconcile the submission record.
- release_guard.py: owner-installed private hash-pinned decision with expiry,
  exact source/pins and fresh code/inventory/lease probes. Receipt URLs are reviewed
  references, not evidence fetched by this helper. IPC cannot supply approval.
- boundary_service.py assembles the components from a private hash-pinned config,
  verifies executable source hashes, and refuses silent ledger initialization.
  Its CLI deliberately starts WITHOUT signing or broadcast authority.

The real viem verifier bridge and inherited-descriptor signer are exercised with
unfunded ephemeral fixtures. No runtime credential has been accessed here. For an
accepted launch, the existing holder may supply an immutable sealed memory FD or
an independently reviewed custody adapter. No key belongs in argv, environment,
config, public receipts or client responses. The descriptor implementation never
opens a key file or creates a credential. Node's immutable strings are not claimed
to be securely zeroized; the trusted short-lived child handles private material.

External signed staging is disabled by default. Diagnostic staging cannot prevent
a client that already possesses a signed transaction from broadcasting it elsewhere.
The accepted path keeps signing/custody inside the submission gate; clients request
only a stored binding ID and never receive raw signatures.

## Concrete steward drain and installation sequence

1. Claude's retained steward checkpoints the CURRENT officer's pending intents,
   raw signed transactions and reconciliation state privately. Disable its old
   two-hour relaunch path before stopping new issuance. Preserve repayment/support.
   Return a public-safe drain receipt identifying the source revision and disposition,
   not private process/session identifiers. A request or timer deadline is not drain.
2. Verify the shared execution-owner transition and lease. The same retained
   supervisor must enforce one officer writer, including future two-hour relaunches.
   Fresh probes are not distributed fencing against another holder of the key.
   Do not run this candidate beside the old writer or blindly resume the legacy one.
3. Install the reviewed checkout/dependency lock with non-writable code, including
   the signed-validator directory. The source hash list does not authenticate
   installed node_modules or the Node/Python executables. The supervisor must verify
   their provenance/lock integrity and root/service-owned non-client-writable paths;
   set a fixed trusted PATH and NODE_PATH and exclude writable import locations.
   NODE_OPTIONS is stripped from child invocations, but that alone is not dependency
   authentication. Provision
   existing approved service/consent/executor identities and socket group through
   the runtime's authorized supervisor. Clients cannot share the service UID or be
   root. Socket directory is owned0750 (no group write); socket0660. Keep ledger,
   release config and journal in a separate owned0700 directory with0600 files.
   Do not change accounts/security settings informally to make this work.
4. Migrate and reconcile the existing ledger; never initialize an empty substitute.
   PR441 component c1f9922457f2b4cf80238a8e625c6bdc141ea675 is independently
   accepted (review6649143758); require its separately owned runner wiring and
   end-to-end lifecycle acceptance. Preserve pending
   intents and signed bytes across restart; unknown outcomes retain exposure.
5. Create the private deployment config with exact policy, endpoints authorized in
   THAT runtime, source hashes, all direct/proxy code pins, officer/desk wiring,
   roles, messages and fee caps. The assembly test documents the exact schema.
   First launch with no signer descriptor and no accepted release manifest:

   ```
   python boundary_service.py --config /private/runtime.json --config-sha256 REVIEWED_SHA256
   ```

   This starts a local read/consent boundary; it does not launch D7, grant credit,
   install a signer or enable a sender. Do not run this command in the current
   blocked environment as a workaround for its RPC restriction.
6. In the retained authorized runtime, verify read-only acquisition and independent
   immutable-runtime/implementation comparisons against the actual new isolated
   pool, budget, token and desk. Capture provenance and hashes. No deployment is
   inferred from code presence, a passing test, source merge or a static page push.
7. Before submission, wire authoritative lease/drain and complete inventory/budget
   probes to assemble(...). The inventory probe must establish actual reusable
   backing, all pending changes, controller/group/portfolio caps, existing losses
   and commitments, budget binding and borrower grant state. It is not implemented
   by returning True or merely accepting code hashes. Missing probes remain closed.
   This complete live inventory/wiring integration is still an acceptance gap.
8. After exact source/runtime review and all financial/testnet/consent limits pass,
   the retained owner installs the exact hash-pinned enabled release decision and
   existing authorized signer capability. Configure its two-hour relaunch to use
   this same fenced/pinned path. The assembly accepts no approval from client JSON.
   Run a bounded testnet rehearsal once, then independently verify actual receipts,
   cash movements, consent/nonce binding and cleanup before human-study release.

The configured sender supports only the exact already-verified raw transaction;
there is no network retry or endpoint fallback. Wallet, mainnet, human recruitment
and custody authority are not expanded by this handoff.

## Withdrawal, rollback and limits

Accepted consent withdrawals serialize against the final send. Arrival of a request
is not acceptance; a submitted transaction cannot be recalled. Private consent
withdrawal does not erase public messages or itself revoke an already-issued
on-chain grant. Confirmed budget revocation and prior commitments require their
own reconciliation. Existing requests may disburse after a budget stop.

Rollback closes the release gate FIRST, suppresses relaunch, preserves private
ledger/journals and holds ambiguous attempts. Stop the candidate only after its
current operation reaches a checkpoint; investigate SEND_STARTED/UNKNOWN via the
reader. Do not delete state, resend, recreate nonce headroom, sweep or restart a
legacy writer automatically. Keep consent withdrawal and loan servicing available.

No accepted release manifest, actual custody port, live inventory probe or runtime
installation has been supplied in this workspace. Code/test completion does not
establish live safety, predictive creditworthiness or human-study readiness.
