# Runner lifecycle independent acceptance work order

## Superseding runner review checkpoint

PR441 now has wrapper616d1caa95149219b232fdcc33df2a9788a7e525. Existing independent
review[6650540082](https://github.com/scottonchain/microcredit-agent-testbed/pull/441#issuecomment-6650540082)
reports70 supplied tests pass and all four prior reproductions corrected, but
**AMEND remains**: cleanup prepare/broadcast effects can outlive their timeout
wrapper and ownership release. Track actual effect settlement, stop new effects
on unresolved timeout, retain durable uncertain intent and ownership until
quiescence/reconciliation. Test delayed/permanently hung effects and competing
resume. The same writer/reviewer own this delta; no duplicate review or live gate.
The394a9d9 findings below are historical evidence, not the current four-open status.

## Historical394a9d9 review: superseded by the checkpoint above

At the historical checkpoint, PR441 runner adapter394a9d907c098dd54fecf53e3eecc2ad749b184e is
open/unmerged and NOT accepted or live. [Independent review6649893217](https://github.com/scottonchain/microcredit-agent-testbed/pull/441#issuecomment-6649893217)
reports62 supplied component/runner tests passing but four independently reproduced
blockers. Earlier acceptance of componentc1f9922457f2b4cf80238a8e625c6bdc141ea675
does not extend to this wrapper. No real signer/provider adapter or current
scenario-runner wiring is established.

1. An abort-ignoring scenario can continue after timeout, deposit after cleanup,
   and outlive a CLOSED journal/released lock. Require actual scenario/effect
   quiescence before cleanup, closure or ownership release; otherwise retain an
   explicit unresolved state and ownership. A false ok flag alone is insufficient.
2. Resume checks only runId/fundingWallet and can omit added funded wallets.
   Persist and verify exact roster, addresses, chain, token and recovery-policy
   identity before any resumed port action; reject changed configuration without
   effects unless an explicit reviewed migration reconciles the complete inventory.
3. Funding is outside cancellation/deadline supervision and can hang after SIGTERM.
   Require bounded supervised funding with durable intent/outcome checkpoints and
   uncertain-funding reconciliation. Racing into cleanup cannot prove a late
   transfer will not arrive. Test hung funding and cleanup ports explicitly.
4. A partial lock can be deleted as stale during publication, admitting two owners.
   Malformed/partial locks must fail closed; reclamation needs demonstrable dead
   ownership and ownership-safe removal. Releasing a predecessor must never remove
   a successor's lock. Test creation and stale-reclamation interleavings.

Claude remains the existing wallet/runner writer. Amend these paths there; Codex
retains independent exact-revision review of the fixes and regressions. No second
writer, live campaign, merge, credential access or relaxed shared-transition/network
gate is authorized. Acceptance requires reproductions to fail safely on the amended
head, not merely an increased passing test count.

Codex (AI) retains independent integration review; Claude remains the source writer.

When the existing owner delivers an exact head, inspect the diff against that
accepted component and run its documented local command in an isolated checkout.
Use generated local-only identities, mock ports or in-process EVM, temporary
private files and fault injection. No live keys, RPC, funding, or actual signals
against the retained officer. Signal tests must target a disposable child process.

| Scenario | Required independently observed result |
| --- | --- |
| Missing/wrong/duplicate wallet control | Refuse funding before any transfer; retain complete unique wallet inventory |
| Successful scenario | Mandatory terminal cleanup and fresh exact chain/token/recipient/amount reconciliation before CLOSED |
| Scenario exception/timeout/cancel | Cleanup enters once; preserve failure and unresolved obligations, never silently pass |
| SIGINT/SIGTERM during each durable boundary | Disposable child stops issuance, leaves reloadable private intent; recovery does not duplicate signing/transfers |
| Crash before/after prepare, send and receipt save | Restart from last durable journal; inspect known hash; ambiguous outcomes retain exposure |
| Short write, zero write, fsync/rename failure | No broadcast from an unpersisted intent; no successful terminal result after failed final save |
| Wrong receipt chain/token/from/to/amount/status | Sticky mismatch; zero wallet balance cannot turn a wrong-recipient transfer into recovery |
| Reorg or dropped/replaced transaction | Hold/reconcile original intent; no automatic new nonce or signing on uncertainty |
| Later deposit or changed balance | Invalidate prior closure/reconciliation and remeasure complete wallet/funder state |
| Lost signer, insufficient gas, locked value or dust | Explicit unresolved/residual status under reviewed policy; never unconditional CLOSED |
| Concurrent start/relaunch | One owned runner; no duplicate funding/cleanup executor or implicit credential fallback |
| Private journal/public report |0600 private durable signed-intent storage; public report contains no keys/raw signatures/provider errors/participant data |

Preserve the component's semantics when adapting it: a test stub that always
returns verified receipts/control is not lifecycle evidence. Test real runner calls
into the accepted component, actual persisted restart state and counters for side
effects. Independently test negative paths beyond the owner's happy-path suite.

The review receipt identifies exact runner/component revisions, local environment,
commands, failures/corrections, accepted scope and remaining release gates. It
must not call local fixtures live wallet recovery. If source is not yet delivered,
report that exact dependency rather than manufacture a competing implementation.
Shared transition, retained-writer drain and network restrictions remain in force.
