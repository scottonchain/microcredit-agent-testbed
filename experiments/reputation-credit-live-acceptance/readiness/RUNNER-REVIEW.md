# Runner lifecycle independent acceptance work order

Codex (AI) owns independent integration review; Claude remains the PR441 source
writer. Accepted component headc1f9922457f2b4cf80238a8e625c6bdc141ea675 has32 local
component tests and review6649143758. At this checkpoint PR441 is open/unmerged
with that same head: no runner integration to review. Request6649188807 remains
unanswered in the recorded PR comments. No acceptance is inferred from assignment.

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
