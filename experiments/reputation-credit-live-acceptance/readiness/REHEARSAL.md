# Local receipt rehearsal and runtime acceptance interfaces

Codex (AI). Source preparation only; no live credentials, external RPC or release.
The human-facing decision served is whether the proposed isolated test app can
safely advance to a supervised fictional-data study. The cheapest new evidence is
actual local contract receipts crossing the reader boundary. This multiplies the
existing canonical-pool tests; it neither establishes credit demand nor makes a
loan preferable to a no-loan study. Incorrect receipts/inventory or unresolved
wallet ownership stops progression. At main8357cae, learning recall for wallet
recovery/lease/inventory returned no annotated matches; this is a retrieval gap.

## Deployment identities and review boundary

The recorded canonical Base Sepolia pool is
0x73872B8fB7F1771C67911f03edc75aBdc9514973, chain84532, source1812e7d,
using test USDC0x036CbD53842c5426634e7929541eC2318f3dCF7e.
These are repository deployment records, not a fresh live identity check.
The proposed scoped-budget pool is a NEW isolated deployment candidate, not a
patch installed at that canonical address. No address exists for its live release
in this packet. Its reviewed exact-vendor runtime measures23246 bytes versus the
canonical-build baseline24377; deployed immutables and wiring still need their
own actual identity checks. Never substitute the canonical pool's address into
a candidate release manifest or infer its controls from local candidate tests.

This rehearsal runs the candidate only on an ephemeral chain31337 with a locally
minted mock token. Its addresses/hashes are neither canonical Sepolia nor a deployed
isolated testnet app. Both phases of the human study remain separately gated;
PhaseA read-only screens do not establish PhaseB transactional readiness.

See [RUNTIME-HANDOFF.md](RUNTIME-HANDOFF.md#current-verified-handoff-status) for
current source reviews, unmerged PRs, config4 drain and explicit facilitator/
custodian declines. Those declines must not be reported as pending acceptance.

## Current wallet runner disposition

PR441 wrapper394a9d907c098dd54fecf53e3eecc2ad749b184e is **AMEND**, not accepted
or live. Its62 supplied tests passed, but independent review6649893217 reproduced
unfinished-scenario cleanup races, changed-roster resume omissions, unsupervised
funding hangs and a two-owner lock-publication race. See
[RUNNER-REVIEW.md](RUNNER-REVIEW.md) for required fixes and exact review receipt.
Earlier component acceptance remains component-only. The existing owner must
amend the wrapper before independent acceptance; no live recovery is established.

## Reproduce

Use the exact reviewed vendor build from scoped-budget/BUILD-PARITY.md. Install
locked dependencies in the supported local environment, then run from this folder:

```
BUDGET_ARTIFACT=/absolute/path/to/guarded-build.json node --test --test-name-pattern=receipt-backed scoped-budget/test_pool.cjs
python -m unittest test_runtime_inventory
```

The test uses Hardhat in-process with normal contract size limits, a generated
borrower key funded only inside the local fixture and minted local mock tokens. No server, fork URL or external
RPC is started. It requests, disburses and repays five local units, verifies exact
Transfer sender/recipient/amount and final borrower token balance, and captures
actual anchored ABI responses. replay_inventory.py sends these through
AuthenticatedSnapshots and CanonicalInventory without any network access. Its
stdout reports local transaction/block hashes and inventory digest. These hashes
exist only in that ephemeral chain, not a public explorer. The actual ABI tape is
kept in memory and contains no key/raw signed transaction. Repeated runs create
new local addresses and therefore new hashes.

## Inventory contract

runtime_inventory.CanonicalInventory reads complete bounded getAllLoanIds,
getLoan/getLoanTerms, getBackedBorrowers/getBackings and scoped budget/grant/usage
state at one confirmed hash, including lender cash, token balance, reserve,
impairment, fees, stake and unclaimed payouts. It requires exact pool/budget wiring and code pins,
sequential immutable loan enumeration, every observed borrower in the installed
registry, secured-only backing and matching loan/borrower/controller/group gross
usage. It includes requested, repaid, defaulted and cancelled lifecycle state;
closed status never means zero historical loss. More than the bounded population
holds rather than truncates. Reorg, inconsistent ABI, unknown borrower, hidden
origination usage and scope-cap violations reject acquisition.

Independent review reproduced an initial omission: equal-gross repayment and
default had identical legacy inventory despite a five-unit cash difference. The
new full-pool regression forks the same local state, performs each outcome and
runs both actual RPC tapes through Python. Lifecycle3 versus4, five-unit lender
cash difference and distinct digests now pass. Credit-only backing does not
absorb that cash loss.

The budget ABI cannot enumerate never-used grants. Completeness of that part of
the installed borrower registry still requires the existing issuer's complete
private issuance journal and exclusive issuance custody. Do not equate the registry
with discovered humans, controllers or consent. getLoan omits principalRecovered;
this snapshot is NOT a replacement for receipt/net-cash reconciliation.

InventoryProbe compares fresh canonical state with the exact digest produced by
an independently reconciled private ledger/receipt baseline. Never bless a changed
snapshot by copying its hash into the baseline. It checks conservative total,
controller and group gross caps against BOTH net and gross authorized budgets.
This deliberately uses a worst-case gross ceiling, without inferring recovery
from credit-only guarantees. Freshness is at most120 seconds here, a restrictive
operational choice, not a finality theorem. An installed quiescence callback must
exclude untracked/concurrent writers and unresolved intents, and remain valid
before/after acquisition. The currently authorized in-flight transaction must be
explicitly accounted for by the supervising reconciliation protocol; blindly
rejecting one's own SIGNING marker would deadlock submission. No such callback is
installed by this test. Inventory equality does not lock the blockchain.

## Lease contract and assembly

LeaseProbe reads a trusted supervisor record containing exact owner, generation,
source revision, issue/expiry and affirmative drain, exclusive-custody and fenced
relaunch evidence. Maximum lease lifetime120 seconds; expired, changed-generation,
unknown-field and incomplete records fail closed. The repository owner JSON alone
cannot attest process/key exclusivity. No file-reading authority, signer or new
lease is created. Trusted attestations are not distributed fencing: the retained
supervisor must actually drain D7 and its two-hour restart path.

The supervisor may supply these adapters via assemble(inventory_probe=...,
lease_probe=...) only after independent baseline/custody review. The executable
adapter is included in the installation source hashes. Default CLI remains without
probes or signer. No enabled release manifest is installed.

## Wallet integration ownership

PR441 component c1f9922457f2b4cf80238a8e625c6bdc141ea675 remains independently
accepted. Claude is the existing wallet writer; integration request6649188807 on
PR441 and board6649189040 asks for disabled local runner wiring, pre-funding key
control refusal, success/failure/timeout/signal handlers, private durable restart,
exact receipt validation, sweep and final accounting. The resulting preparatory wrapper is now under AMEND; it is not accepted
runner wiring or a passing independent lifecycle review. No duplicate wallet writer.

The runner's future terminal result must distinguish CLOSED, pending reconciliation,
unknown broadcast and failed persistence; include the complete scenario-wallet set,
redacted receipt references and fresh funding return accounting. Raw signatures and
key material remain private. A public hash alone does not prove key custody or
recovery. Reconcile against the accepted runner's exact interface once delivered;
do not fabricate an adapter to an unseen implementation.

Release still needs that runner lifecycle, complete private baseline/issuer journal,
accepted current supervisor/drain, actual runtime/source/build identity, authorized
Sepolia rehearsal, and separate study consent/facilitator/recruitment acceptance.
