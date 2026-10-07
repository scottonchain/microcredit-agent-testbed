# Required end state: algorithmic trust graph and staking

Codex (AI), 2026-10-07. Direct operator clarification TRANSITIVE-TRUST-20261007-R2 confirms the end state already recorded in claim:transitive-trust-endstate-20261007: after bootstrap, the system operates through transitive trust and staking, with algorithmic creditworthiness. Credit officers are temporary bootstrap roles and should be redirected. This is a requirement, not an invitation to preserve discretionary issuance indefinitely. Design below is a candidate, not implemented or deployed functionality.

## Two different algorithm outputs

1. **Eligibility/risk ranking:** a deterministic, published function of the directed trust graph, stake commitments, payment/default evidence and time. Its purpose is to prioritize or price allocations. Raw wallet count, path count, repayment count or centrality does not create dollar credit. A risk probability inferred from the graph still requires empirical calibration; algebraic conservation is not statistical creditworthiness.
2. **Spendable borrowing capacity:** an actually reserved allocation of stake-backed guarantees through eligible trust paths, limited by uncommitted underlying resources and lender liquidity. The algorithm can route backing; it cannot multiply it. The ranking is not a substitute for the resource ledger.

Received backing remains nontransitive in today's deployed pool. Replacing that rule requires contract/theory work and an explicit migration. A graph-scoring oracle supplying discretionary-looking scores is not the final mechanism: use on-chain deterministic validation or a permissionless verifier of allocation certificates, so no credit officer's signature is needed to grant capacity after transition.

## Candidate mechanism: consented, stake-rooted capacity flow

Each stake root r has a finite remaining capacity S_r. An edge u→v means u authorizes a stated amount, expiry, maximum onward depth and onward use/risk policy, not an unlimited assertion that v is good. An ultimate loss-bearing stake owner must explicitly consent to downstream borrowers or the stated delegation policy. The intermediary cannot silently pledge someone else's money. Specify whether an intermediary only routes permission or commits its own loss-bearing stake; different semantics must never be conflated.

Represent available stake roots as edges from a super-source. Borrower demand is a sink, and trust edges have residual capacity. For each loan, choose bounded simple authorized paths, reserve an amount on every path edge and the underlying root stake, and save the allocation certificate with the loan. Aggregate reservations across ALL open requests/loans:

- sum of outgoing loan allocations for a root ≤ that root's actual eligible stake;
- sum of allocations using an edge ≤ its consented capacity;
- every intermediate routing vertex conserves inflow/outflow for that allocation;
- disbursed/requested principal ≤ reserved eligible backing and usable pool liquidity;
- no stake or guarantee can simultaneously cover another loan, the root's own borrowing, withdrawal or incompatible commitment;
- the loan certificate binds every root, edge, amount, version/nonce, expiry and downstream consent. Capacity-reduction/revocation cannot release a live reservation.

Per-borrower independent max-flow queries are insufficient: two queries can each return the same full capacity. Origination must atomically reserve against the shared global ledger. Max-flow itself can be computed off-chain; a bounded path certificate is enough to verify feasibility on-chain. Global optimality affects allocation quality, not the safety of a feasible reservation. Bound path count/depth/work explicitly and measure gas; no unbounded EVM graph traversal. Use canonical unique resource IDs for every stake lot; cycles, parallel paths, aliases and repeated appearances do not clone a resource. Reject cyclic loan certificates; an account with no authorized route from backing has no spendable capacity.

Example: R stakes100 and delegates100 through A, who delegates to B. B may receive up to100 capacity, not100 at each hop. If60 is reserved for B, A and any alternate path sharing R can jointly use at most the remaining40. If B defaults on60, the committed60 can be slashed from R's authorized stake; A does not incur an unstated loss or create replacement capacity by forwarding. With split paths, slash allocated lots according to exact integer accounting and bound rounding residuals; the current pro-rata1-micro counterexample remains a required regression.

The source-resource constraint gives a candidate principal-exposure bound: the sum of all allocated secured exposure cannot exceed backing stake. This is not yet a complete protocol proof. Default/recovery timing, partial repayments, split-loan rounding, cancellations, front-running, path revocation, reserves, legacy grants, concurrent origination and conservation of actual cash must be proved/tested together. Honest sponsors can still be deceived into consenting; a stake bound limits loss, not fraud probability. Cycles can corrupt ranking even when they cannot mint collateral, so test ranking manipulation separately.

## Sunset officers without abandoning existing borrowers

Bootstrap officers can qualify productive opportunities and assign bounded initial lines while the graph acquires actual relationships and capital. Preserve an explicit cumulative loss budget and existing grants/loan commitments. No automatic conversion of an unsecured bootstrap line into secured stake and no claim that a graph makes real paid work exist.

Transition gates:

1. Publish/test the routing, ranking and consent/default semantics with conserved capacity and adversarial graph fixtures; include shared-root diamonds, cycles, Sybil expansion, simultaneous borrowers, stake exit and multi-hop default. Compare liquidity/capital/gas and direct-financing alternatives honestly.
2. Independently review the implementation, fix CI30 and critical accounting defects, and rehearse migration on an exact-state fork. Current ordinary single-hop evidence does not validate this new mechanism.
3. Stop NEW discretionary officer issuance as the new routing route becomes usable. Legacy grants/obligations run off under their original accounting and high-water budget; do not zero scores or release backing mid-loan merely to claim issuance is zero. Clearly partition legacy unsecured exposure from new algorithmic backed exposure.
4. Verify that an independently operated newcomer can obtain an authorized multi-hop allocation, borrow, repay and release commitments with no officer granting a score, no oracle heartbeat needed for the new path, and no discretionary exception. Test failures/outages/defaults too.
5. Only after legacy exposure is settled/explicitly migrated, disable its new-issuance route and confirm new capacity depends on backing rather than remaining manual overrides. Keep necessary governance/security roles; redirect officer agents rather than falsely equating removal of issuers with removal of every operational role.

Redirect officers to finding useful funded jobs, gathering verifiable outcome evidence, helping participants manage consent/disputes, auditing manipulation and monitoring protocol/risk controls. They may suggest an endorsement, but cannot create spendable capacity by assessment alone. Routing/credit access continues when all former officers are offline.

## Current ownership and status

Claude leads existing action:transitive-trust-sync and the theory/default/algorithm design; the sync decides HOW to implement the required target and the first milestone, not whether the operator's target is optional. Codex supplies shared-resource reservation fixtures, economic comparison and evidence/migration acceptance. Hermes supplies execution/funding/actual relationship evidence, while preserving current live3/source5 obligations. Existing04am Denver sync/hourly work and October commitments remain unchanged.

No new protocol/graph ranking, transitive capacity contract, permissionless certificate verifier, mainnet deployment, successful migration or economic demand is claimed. The immediate result is a recorded target and a falsifiable mechanism candidate. Every simulation going forward must label current single-hop deployment versus proposed multi-hop code, and show zero new officer issuance in the post-bootstrap lane; simulation scaffolding cannot quietly keep a privileged officer granting scores.
