# Primary-source lending and trust-network comparison

Unauthenticated GitHub API commit/tree and pinned raw primary repository files. No wallet/key access, deployment, transaction, RPC verification or secondary search.

Source availability and official deployment artifacts are not evidence of current deployed bytecode, adoption, economic success, or agent borrowing demand.

## Union V2

Distinct LP supply and guarantor stake. Credit equals sum min(voucher free stake, remaining directed vouch). Borrow locks guarantor stake and reverts if uncovered; locked stake cannot be withdrawn or cancelled. Overdue write-off reduces guarantor stake and repays principal.

No multi-hop credit computation observed: getCreditLimit iterates only this borrower’s direct vouchers. Received credit is not new stake.

Fund market, stake USDC, direct vouch borrower, membership/fee configuration, borrow for an actual cashflow purpose. Base configuration effectiveCount=0 avoids needing multiple initial members but does not eliminate stake requirement.

Official pinned README and Base mainnet deployment/config artifacts; no independent RPC code/balance or actual lending activity checked.

- [Pinned source, lines 492–498](https://github.com/unioncredit/union-v2-contracts/blob/67bc59b7ee759783531a198246095f2ae1d980cd/contracts/user/UserManager.sol#L492)
- [Pinned source, lines 767–781](https://github.com/unioncredit/union-v2-contracts/blob/67bc59b7ee759783531a198246095f2ae1d980cd/contracts/user/UserManager.sol#L767)
- [Pinned source, lines 806–846](https://github.com/unioncredit/union-v2-contracts/blob/67bc59b7ee759783531a198246095f2ae1d980cd/contracts/user/UserManager.sol#L806)
- [Pinned source, lines 881–950](https://github.com/unioncredit/union-v2-contracts/blob/67bc59b7ee759783531a198246095f2ae1d980cd/contracts/user/UserManager.sol#L881)
- [Pinned source, lines 609–665](https://github.com/unioncredit/union-v2-contracts/blob/67bc59b7ee759783531a198246095f2ae1d980cd/contracts/market/UToken.sol#L609)
- [Pinned source, lines 23–55](https://github.com/unioncredit/union-v2-contracts/blob/67bc59b7ee759783531a198246095f2ae1d980cd/deployments/base-mainnet/config.json#L23)

## Aave V3 credit delegation

Collateral owner authorizes a delegate via debt-token allowance. Borrow remains on onBehalfOf collateral owner; validation enforces nonzero collateral, health factor and collateral needed. Delegation does not turn a relationship into uncollateralized protocol debt.

Allowance is directed delegator-to-delegatee, not a multi-hop conserved staking graph.

Capitalized sponsor can delegate collateral-based borrowing power; useful precedent for explicit principal loss bearer, not borrower history generating unsecured liquidity.

Core source retrieved, no deployed-address/runtime or present liquidity verified.

- [Pinned source, lines 21–39](https://github.com/aave/aave-v3-core/blob/782f51917056a53a2c228701058a6c3fb233684a/contracts/protocol/tokenization/base/DebtTokenBase.sol#L21)
- [Pinned source, lines 223–265](https://github.com/aave/aave-v3-core/blob/782f51917056a53a2c228701058a6c3fb233684a/contracts/protocol/libraries/logic/ValidationLogic.sol#L223)
- [Pinned source, lines 70–105](https://github.com/aave/aave-v3-core/blob/782f51917056a53a2c228701058a6c3fb233684a/contracts/protocol/libraries/logic/BorrowLogic.sol#L70)

## Goldfinch

TranchedPool creates an explicit borrower credit line, junior and senior funding positions, role-restricted drawdown, transfers USDC to configured borrower. Such underwriting and customer/business cashflow is distinct from algorithmic graph routing.

No multi-hop trust-credit computation in inspected pool/credit-line sources.

Specific borrower and scheduled productive cashflow plus risk-bearing capital precede public liquidity; useful cashflow structuring precedent, not permissionless agent credit proof.

Repo README says mainnet deployed; historical source only, no present repayment or underwriting efficacy established.

- [Pinned source, lines 58–90](https://github.com/goldfinch-eng/mono/blob/bb251675d8a28d046f4d4763e1cf8874ee7c2723/packages/protocol/contracts/protocol/core/TranchedPool.sol#L58)
- [Pinned source, lines 200–240](https://github.com/goldfinch-eng/mono/blob/bb251675d8a28d046f4d4763e1cf8874ee7c2723/packages/protocol/contracts/protocol/core/TranchedPool.sol#L200)
- [Pinned source, lines 166–168](https://github.com/goldfinch-eng/mono/blob/bb251675d8a28d046f4d4763e1cf8874ee7c2723/README.md#L166)

## TrueFi historical specification

2020 design discusses reputable institutional borrowers, staked voting/credit prediction, expected-value approval and minimum loan 1M TUSD. Source explicitly calls itself an actively designed plan.

Not transitive stake-backed lending; institutional risk assessment is not identity-free microcredit.

Useful negative comparison: human/legal institutional underwriting and large tickets do not establish autonomous-agent microloan viability.

SPECIFICATION ONLY: do not treat proposed economics or historical roadmap as deployed behavior or verified loan outcomes.

- [Pinned source, lines 1–32](https://github.com/trusttoken/truefi-spec/blob/d2752e44908e83d56d7b0fe015c3afa808bb53d8/README.md#L1)

## Trustlines

Bilateral creditline agreements, signed balances/debts and mediated path transfers. Each edge’s credit capacity bounds flow. These are network IOUs, not a USDC lending pool with funded default cover.

Actual path routing along trustlines, but it routes bilateral credit/debt; path existence does not create external dollar collateral.

Provides graph-capacity/conservation precedent; a USDC version must separately reserve origin stake and specify enforceable default liability.

Contract source inspected, not chain deployment/usage.

- [Pinned source, lines 95–110](https://github.com/trustlines-protocol/contracts/blob/12fd38040c5dfa106319767cef6002fef74af8b8/contracts/currency-network/CurrencyNetworkBasic.sol#L95)
- [Pinned source, lines 653–680](https://github.com/trustlines-protocol/contracts/blob/12fd38040c5dfa106319767cef6002fef74af8b8/contracts/currency-network/CurrencyNetworkBasic.sol#L653)
- [Pinned source, lines 15–37](https://github.com/trustlines-protocol/contracts/blob/12fd38040c5dfa106319767cef6002fef74af8b8/contracts/currency-network/CurrencyNetwork.sol#L15)

## Circles V2

Hub records trust relations; operateFlowMatrix requires operator authorization, verifies registered entities/trust and matches netted flows before effecting token path transfers.

Token acceptance/path fungibility, not cash underwriting or borrower creditworthiness.

Use explicit authorization and flow-conservation validation as engineering precedent; do not count token circulation as loan revenue or USDC loss protection.

Source and deployment instructions only; no current activity independently established.

- [Pinned source, lines 347–369](https://github.com/aboutcircles/circles-contracts-v2/blob/39338244683e4d9c38cb05c60db8846b5851318b/src/hub/Hub.sol#L347)
- [Pinned source, lines 553–590](https://github.com/aboutcircles/circles-contracts-v2/blob/39338244683e4d9c38cb05c60db8846b5851318b/src/hub/Hub.sol#L553)

## Bootstrap implication

Union establishes that direct trust plus economically committed stake can open a cash credit line without a borrower credit score. A graph extension can route that same finite underwriting budget through consenting intermediaries, but it must never recursively treat a borrowed balance or received trust as new loss-bearing capital. The graph supplies access and risk allocation; independently paid productive work supplies repayment. Agent trading is unsuitable as the first deterministic bootstrap demonstration because neither profit nor settlement can be assumed. The present project pool has neither verified transitive routing nor resolved CI30; a local graph model is an explicit prototype, not proof these capabilities are deployed.
