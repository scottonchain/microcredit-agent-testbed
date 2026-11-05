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

Dependencies are pinned in package.json. With installed dependencies, run:

```
node compile.cjs /path/to/canonical1812/DecentralizedMicrocredit.sol /path/to/interfaces /tmp/budget-artifact.json
BUDGET_ARTIFACT=/tmp/budget-artifact.json node --test test_budget.cjs
```

The compiler verifies the original and patched source SHA256, applies only the
recorded patch, compiles the pool and rejects runtime over EIP170's24576-byte
limit. A compiler success does not verify the canonical deployed build. The
interface input must come from the reviewed source; current test uses the existing
project interface. The canonical1812 submodule record is OpenZeppelin5.3.0 at
f9f7db03f3df020aace3958b8fb7de8891d133e5; npm5.3.0 is pinned for the candidate.
Source/build dependency parity with the deployed runtime is still unverified.

Thirteen EVM test groups pass: six standalone budget groups and seven full-pool
integration groups. Tests deploy the actual candidate pool with normal EIP170
limits. They cover repeated backed loans and repayments without allowance refill,
direct/meta/combined paths, replay/expiry/invalid signatures, caller-sensitive
ERC1271, authority/rebinding, pool-check and post-origination transfer failure
rollback (including nonce and loan inventory), and signed repayment after stop.
The test token deliberately supports a failing transfer; it is not production USDC
or permit validation. Complete wallet/service/canonical deployment acceptance is
still separate. Ganache runs in-process without a listening RPC port, remote
provider or externally funded wallet. Ephemeral keys are generated only in memory.

## Size correction and verified scope

The selected compiler-settings.json uses solc0.8.33, viaIR, runs1 and an explicit
Yul optimizer sequence without the full inliner. It preserves the Solidity source
and original signature call path. Shanghai is the selected EVM target, tested on
Ganache's Shanghai fork; it is a deliberate candidate build setting, not a claim
about the existing deployment settings. Settings and source/interface hashes are
pinned. The original canonical1812 settings (solc0.8.33,viaIR,runs200) are verified
from its foundry.toml; compiling the baseline for Cancun reproduces24377 bytes.
Matching that SIZE does not establish deployed runtime identity.

BUILD-RESULT.json records the comparison. The prior default-sequence candidate
was25721 bytes; the selected full pool is23272, with1304 bytes of headroom. The
compiler rejects oversized outputs; no unlimited-size EVM setting is used. An
independent AI reviewer rebuilt the candidate and reproduced all13 EVM tests.
No feature, guard or signature logic was removed to meet the limit. This resolves
the size blocker for this candidate only. New isolated deployment, exact runtime
identity, owner/lease, consent/journal/executor and human-readiness gates remain.

Optimizer rationale: [Solidity optimizer documentation](https://docs.soliditylang.org/en/latest/internals/optimizer.html)
describes how inlining can increase code size. The selected configuration is
validated by explicit measurements and tests, not assumed equivalent from that
explanation alone. These tests do not constitute a complete compiler audit.
