# Scoped origination candidate — not installed

Codex (AI), November 5, 2026. A backing balance is reusable on the existing pool;
repayment can therefore recreate available credit. This candidate adds cumulative
principal authorization at the common `_originateLoan` entry used by direct
requestLoan, requestLoanMeta and borrowAndDisburseMeta. It is a source patch for a
NEW isolated pool, not a change to the deployed immutable canonical contract.

ScopedOriginationBudget stores fixed portfolio/controller/group ceilings and one
nonrenewable borrower grant with expiry. Only its immutable pool can consume it.
Consumption happens atomically at loan request and is never refunded on repayment
or cancellation. Later pool failure reverts the consumption in the same EVM
transaction. A pool owner binds the budget once; the setter checks code presence
and matching pool address. There is no reset, replacement or disable path. Budget
owner can permanently stop new consumption or irreversibly revoke an individual.
Identity labels are reviewed inputs, not proof of independent humans/controllers.

## Scope: preparation only

This directory prepares a candidate for a NEW isolated test pool. It does not establish that
on-chain enforcement is necessary, or better than off-chain administration: whether the
off-chain bounds elsewhere in this packet (`bounds.py`, `backing_book.py`) already cover the
same ceilings is not compared here. It does not authorize, deploy or accept that pool or this
bytecode build, and it does not change the canonical Base Sepolia descriptor
(`deployments/current.json`), which stays the one live target. The selected build fits
EIP-170 only under a non-canonical optimizer sequence (runs 1, explicit Yul steps without the
full inliner), so it is a different bytecode build from the canonical one; matching size is
not identity. Merging this packet accepts preparation artifacts only, not the on-chain
mechanism, this build, or live acceptance.

A grant revocation or stop prevents NEW origination. It does not cancel already
requested loans, which may still be disbursed. Those commitments remain charged.
A pending revocation is not confirmed withdrawal enforcement: service issuance
must stop immediately, then reconcile the on-chain revocation and all prior
requests. Loan recovery and repayment are not stopped. Conservative lifetime
request caps can exhaust on cancelled loans; this deliberate availability cost
prevents cancellation from becoming an allowance-recycling path.

This enforces a cumulative principal ceiling, not affordability, fair treatment,
identity independence, expected loss, a cash guarantee or solvent backing. Other
pool authorization/liquidity checks still apply. Exact runtime, immutable values,
owner and source acceptance are required: a malicious lookalike budget can expose
the same pool getter. No existing service is wired to this contract.

## Reproduction

JavaScript dependencies are pinned in package.json/package-lock.json (every locked entry
carries an integrity hash and resolves from the npm registry). This directory is TEST TOOLING
ONLY: compiler, in-process EVM providers and a client library, declared as devDependencies.
No key, signer, wallet or network client ever runs from this tree. Install without lifecycle
scripts, because several transitive packages (the Ganache native add-ons such as keccak,
secp256k1, leveldown, bufferutil and utf-8-validate, and fsevents) carry install scripts that
are not needed here:

```
npm ci --ignore-scripts
```

Checked after this instruction was added: with that install, Ganache and Hardhat start on their
pure-JavaScript paths and the six standalone budget tests pass against a budget artifact compiled
with this directory's compiler settings. The thirteen full-pool tests need the canonical pool
source and the exact OpenZeppelin tree below and were not re-run for this change.

Supply the canonical OpenZeppelin submodule contracts directory as the fourth argument:

```
node compile.cjs /path/to/canonical1812/DecentralizedMicrocredit.sol /path/to/interfaces /tmp/budget-artifact.json /path/to/canonical-openzeppelin/contracts
BUDGET_ARTIFACT=/tmp/budget-artifact.json node --test test_budget.cjs test_pool.cjs
```

The compiler pins solc0.8.33 and verifies original/patched source, interface,
settings and imported dependency hashes. It rejects runtime over EIP170's24576
bytes. The canonical library revision isf9f7db03f3df020aace3958b8fb7de8891d133e5;
its contents differ from npm5.3.0 despite that version label. No npm replacement
is used by the selected build. See [BUILD-PARITY.md](BUILD-PARITY.md).

Nineteen EVM groups pass independently: six budget and thirteen full-pool groups.
The full pool runs on pinned Hardhat2.26.3's in-process Cancun provider, with normal
size limits and no fork URL/listening socket. Standalone budget tests use Ganache
Shanghai. Coverage includes signed/direct lifecycle, cancellation, exact interest
and fee allocation, secured/unsecured default, atomic failure recovery, signature
compatibility and a limited differential canonical-baseline scenario. The mock
token is not production USDC; permit/service/runtime acceptance remains separate.

## Size correction and verified scope

Selected settings:solc0.8.33,viaIR,runs1, explicit Yul sequence without full inliner,
Cancun. The exact vendored candidate is23246 bytes,1330 below EIP170. The original
canonical1812 foundry settings (solc0.8.33,viaIR,runs200) contain no explicit EVM
fork; using Cancun reproduces a24377-byte baseline. Matching size does not prove
live runtime identity. The previous npm/Shanghai23272-byte result is historical.

An independent AI reviewer reproduced the entire build artifact byte-for-byte and
all19 EVM groups. The selected optimization preserves the source and signature
call path; no feature or guard was removed. New isolated deployment, exact runtime
identity, accepted owner/lease, consent/journal/executor and human-study gates remain.

Optimizer rationale: [Solidity optimizer documentation](https://docs.soliditylang.org/en/latest/internals/optimizer.html)
explains that inlining can increase size. Changed gas usage and external-call gas
availability still require review; passing these tests is not a complete proof of
compiler equivalence. Build measurements, tests and limits are in BUILD-PARITY.md.
