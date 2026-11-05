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

Six EVM test groups exercise the standalone budget: borrower reuse, correlated
controller/group limits, portfolio limit, authority/permanent stop, expiry and
individual revocation. Ganache runs IN PROCESS, without a listening RPC port,
external provider or funded wallet. Ephemeral fixture accounts exist only in the
local EVM. These tests do not execute the full pool lifecycle, meta signatures,
existing wallet cleanup or deployed service. Ganache's native websocket binding
was unavailable and it used its JavaScript fallback; all six tests passed.

The full patched pool compiles but its final Cancun/runs1 runtime is25721 bytes,
1145 over EIP170. The build command intentionally FAILS its deployment-size gate.
Osaka/runs1 gives the same size; runs200 was larger. This is NOT a deployable full
pool candidate yet. The standalone budget tests passed independently. Integration
requires a reviewed size reduction or architecture revision and full-pool tests,
not an unlimited-code-size chain or an unchecked compiler setting.
