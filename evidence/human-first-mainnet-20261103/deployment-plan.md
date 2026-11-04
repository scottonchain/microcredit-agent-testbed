# D16 deployment and servicing configuration plan

Codex (AI), November 4, 2026. Prepared against testbed main
`dc85d77f2fd7653e1e791cf85cb833eb3e41272e`, contract
`7ceaf07d46bc2ebe244175af60f027bd8f2a8995` and the D7 app source at
`b80b15a9142ac19de42de9e6e58b98aceee38abe`. This completes the **preparatory plan**
in D16's November 24 row. No deployment, key, account, audit, fee quote or
security readiness is claimed. The [structured mapping](deployment-plan.json)
is a review artifact, not an environment file or executable configuration.

**Decision: NO_GO for opening the unrestricted public pool as this human pilot.
CHANGE to private dollar servicing and the named lender's own treasury first.**
This is the team's architecture decision for the present evidence, not a request
that the operator solve the design. An eligible lender can keep the intended
100 USDC as its own treasury until an actual case and permitted fiat route exist;
no public borrower smart contract is necessary to lend and collect dollars.
The private operating records and provider interface below are the preparation
for that simpler candidate. No new implementation is justified before the real
lender/account terms and an actual case determine what it must do.

The public-pool configuration below is a **parked conditional comparison**, not
an unowned engineering queue or a claim of mainnet readiness. Re-entry requires
a real case demonstrating benefit from that contract over the private ledger,
plus a reviewed design enforcing its required legal/admission boundary across
every route. Keep the operator's intended 100 USDC intact; do not deploy, convert
or spend it from this decision. This preparatory phase ends with that decision,
the operating interface and the conditional map completed.

The authoritative production procedure remains the contract repository's
[DEPLOYMENT.md](https://github.com/scottonchain/microcredit-contract/blob/7ceaf07d46bc2ebe244175af60f027bd8f2a8995/docs/DEPLOYMENT.md),
with its three broadcast approvals: legal review, owner approval of the exact
environment and saved dry run, and ADMIN signer confirmations. D16's candidate
analysis says counsel is optional, while this production runbook still names
counsel sign-off. This plan does not silently waive the production gate; the
actual owner must reconcile and record the applicable approved gate before
broadcast. Routine technical choices and measurements stay with the team.

## What is being prepared

Target Base mainnet, chain **8453**, with native Circle USDC, six decimals.
The current demo is Base Sepolia **84532**, uses test USDC, and records old pool
source `1812e7d`; it is not the fixed production deployment. The Base mainnet
token candidate in the mapping is the address used by the project's existing
[read-only ACP receipt](../lateral-completion-20261104/acp-trace-readonly.json).
It must match Circle's current official address list
and actual target-chain contract before populating `USDC_ADDRESS`.

The initial product is the lender's own dollar-servicing operation described in
[operations.md](operations.md), with private intake, a $10 first-loan cap,
$20 repeat cap after on-time repayment, 90-day terms, actual backing and
separate human/pool scorecards. The borrower receives and repays dollars.
The pool is a lender treasury/loan-record component; the test app is not
converted to mainnet merely by replacing its addresses.

For a later public-pool comparison, the existing fixed pool has a 90-day
meta-origination seam and can leave score issuance inactive. That avoids making
the conversational score a source of unsecured credit, but does not demonstrate
the complete legal/admission boundary. It is therefore not the selected opening
route; the present candidate keeps human loans in the private servicing ledger.

## Limits the underlying contract does not enforce

Source inspection, not a new audit, establishes four material differences:

- `MAX_LOAN` scales score-issued credit. Backing can create greater borrowing
  capacity; it is not a universal $20 principal cap, a $10 first-loan cap,
  a reserve-fraction limit or one-person/one-loan enforcement.
- `requestLoan` and `requestLoanMeta` use the fixed **30-day** default.
  `borrowAndDisburseMeta` signs `repaymentPeriod` and `maxAprBps`; the D16 route
  must use **7,776,000 seconds (90 days)** and the accepted APR bound. A call
  through the default seam cannot be reported as the 90-day pilot.
- A whitelisted `RELAYER` restricts meta methods. Direct borrowing, deposits,
  staking and backing remain public. The pool's origination code does not
  check Colorado residence, consumer disclosures or one active loan per person.
  An adapter protects its own path; it cannot alone close these other paths.
- A disabled score reporter/forwarder stops new oracle issuance, not secured
  borrowing. Existing dues can also contribute credit. No score override,
  no unknown score issuer and full secured-backing checks are required for the
  intended pilot, but none of these facts makes the whole pool admission-controlled.

Consequently **do not fund or open the base pool as a restricted human pilot**
until a reviewed design demonstrates the required boundary across all entry
points, including unsolicited share deposits, direct 30-day loans, multiple
loans, unapproved recipients and after-pause behavior. Decide the enforcement
design only if a real case later justifies the public protocol;
do not invent a private-contract implementation or describe the generic pool as
already having one. The selected adjacent candidate is the named eligible
lender's own balance-sheet loan with a private ledger, rather than an unrestricted
public lending pool. An existing licensed partner is another possible lender,
not evidence that such a partner exists or has agreed.

The D7 `CreditDesk.sol` explicitly says **TESTNET ONLY**. Its conversations are
public in `Said`/`Replied` events and `thread()`. Its officer can change backing
and it has simple test ownership; it is not the private intake, production
custody or mainnet compliance adapter. No D16 deployment of that desk is planned.

## Roles and addresses: no placeholders that can execute

| Role | Candidate responsibility | Required evidence before use |
| --- | --- | --- |
| Named lender of record | Adopts borrower/backer terms, owns dollar accounts, handles support and regulatory duties | Operator names the legal person/entity and confirms intended jurisdiction/product; default Colorado design alone does not name one. |
| ADMIN | Existing script requires a code-bearing multisig; controls timelock proposer/executor/canceller and KYC oracle role; guardian can pause immediately | Real Base address, code, signer/control confirmation, recovery plan and separation from deployer. No multisig created here. |
| Gas-only deployer | Temporary pool/provider owner until timelock accepts ownership | Real public address and nonce, custody by hardware wallet/encrypted keystore, approved gas budget; no funded test-wallet reuse by assumption. |
| Lender treasury | Owns sponsor assets and dollar-conversion balances; no customer crypto account | Named lender's actual account/wallet control and permitted provider terms; reserve, float and restricted balances separated. |
| Servicing relayer (parked pool route only) | Submits the reviewed lender-bookkeeping meta route, pays gas and reconciles receipts | Selected address and custody, whitelist readback, signer/domain/nonce/deadline controls; source and deployed adapter evidence. Not required to open the selected private ledger route. |
| Backing custodian/backers | Holds actual separately reserved stake; no yield promised | Adopted deposit statement and loss/recovery terms, verified control and uncommitted balances; never count the same capital twice. |
| Pool, provider, lens, timelock | New deployments from the approved source | Addresses come only from approved dry run and successful deployment receipts, then code/configuration/ownership checks. All currently unknown. |

For the parked pool route, the `borrower` field of a meta-request is a protocol account, not evidence
of a human's identity or consent. For a lender-custodied bookkeeping design,
document which lender-controlled account represents each private case, who signs
for it and where the principal is sent (`to`). Human agreement acceptance and
the on-chain signing account are separate records. Do not call a lender-generated
signature a borrower's signature or assume wallet aliases provide identity.
The provider and lender must accept this custodial design before implementation.

## Configuration to take into the approved dry run

The exact values and missing fields for the parked public-pool comparison are
in [deployment-plan.json](deployment-plan.json). Missing ADMIN/deployer/relayer
addresses are not requests to create those accounts for the selected private
servicing candidate.

| Script field | D16 preparatory choice and reason |
| --- | --- |
| `USDC_ADDRESS`, `ADMIN` | Required and unknown until verified; null in the mapping, never fictional addresses. |
| `EFFR_BPS` | Deployment-day New York Fed EFFR with observation date/source; no stale 433-bps rate substituted. |
| `RISK_PREMIUM_BPS` | Unset pending a reviewed pricing/calibration receipt. The generic calibrated default is 800; its runbook forbids lowering it without rerunning calibration. Historical D7 total 933 bps is a comparator, not a mainnet quote. At historical EFFR 433, the generic 800 totals 1233 bps and fails the consumer 12% ceiling before discounting. |
| `MAX_LOAN` | Proposed 20,000,000 micro-USDC, matching repeat-tier reference. First/repeat/aggregate caps still need separately verified enforcement. |
| `TIMELOCK_DELAY` | Retain 172,800 seconds/two days; do not shorten to finish a session. |
| `RESERVE_BPS` | Retain 4500 generic interim share of repaid interest until the required owner decision/review changes it. This is not an initial reserve allocation of 100 USDC. |
| `PROTOCOL_FEE_BPS` | Zero; no new borrower fee or backer yield. |
| `ISSUANCE_BUDGET_LINES`, `MAX_INCREASE_PER_REPORT_LINES` | Proposed 1 and 1, the smallest positive values accepted by the existing script, with no reporter/forwarder and zero initial scores/held budget. These are dormant capacity, not authority to issue a line of 20 USDC. Setting either to 0 would fail the script's validation. |
| `MAX_SCORE_AGE` | Retain 604,800 seconds; inert without an approved publisher. |
| `CRE_FORWARDER`, `CRE_WORKFLOW_OWNER`, `CRE_WORKFLOW_ID` | Explicitly omitted together. No CRE or conversational-score integration assumed. Verify zero reporter/forwarder and all score overrides absent. |
| `RELAYER` | Unknown until selected; mandatory for the planned restricted meta route. Do not inherit an unrelated test relayer. Direct-method limitations still apply. |

Run the existing exact-cent operating budget for the proposed real case's term,
price and complete measured costs. Both the 15-cent all-in stop and 10% rail stop
apply, with the funded-first-loan versus observed-cohort denominator explicit.
For the consumer door, check discounted net proceeds, no fees and the conservative
pilot counter before loan 25. If the required legal price, cost, benefit and risk
bounds cannot hold simultaneously, record CHANGE/NO_LOAN; do not force a quote.

## Where the intended 100 USDC goes

The mathematical pilot reserve, `lenderCash`, deposit shares and contract
`firstLossReserve` are different quantities. Calling `fundReserve(100e6)` adds
100 to both `lenderCash` and junior `firstLossReserve`; `totalAssets` subtracts
that junior reserve. With no other capital this leaves **zero lendable assets**
under the utilization check. It is not the revolving pilot with 100 USDC in D7.

The funding packet must give a nonduplicated allocation to lendable sponsor
`depositFunds` (shares held by the named lender, not offered to the public),
any junior `fundReserve`, actual backers' locked stakes and treasury settlement
float. Withheld interest is restricted per-case settlement money, not fresh
capital. Proposed amounts remain null until the lender, backing source, fiat
route and case sizes exist; no transfer instruction is issued. If the same
sponsor 100 also supplies backing or bank float, subtract that use from available
lendable capital. Backing funded by another person is separately identified
risk-bearing capital, not evidence that a sponsor dollar created their capital.

## Dry-run sequence and the cost recipe

Nothing below broadcasts or asks for a secret. The approved executor later
uses the production runbook's existing script and its custody controls.

1. Freeze the reviewed contract/adapter source, compiler/dependency versions,
   ABI and parameter/role mapping. Attach applicable audit/bounty receipts and
   legal/owner/signers gate evidence. A unit test is not an audit.
2. With actual public ADMIN/deployer/relayer addresses, target-chain RPC,
   token and deployment-day rate, execute the runbook's `forge script`
   **without `--broadcast`**, matching actual sender and nonce. Do not use
   an Anvil account or dummy multisig and call it the production dry run.
3. Save the full output privately, source/configuration hash, target block,
   actual environment values without secrets and every proposed transaction.
   Validate source/configuration, token, role and ownership checks. The script
   initially leaves the contracts unpaused and ownership acceptance pending;
   disabled issuance is not a pause.
4. Price each deployment/configuration/governance call using its dated L2 gas
   estimate and chosen fee cap, plus Base's applicable L1 data fee estimate and
   every other applicable chain charge, including any operator surcharge.
   `eth_estimateGas` alone is not the all-in Base fee. Include pause, two
   timelock schedules, two executions, whitelist/configuration, any additional
   enforcement contracts and later funding calls separately. Use the chain's
   documented fee-estimation interface with actual unsigned call data; record
   method, block, assumptions and quote expiry. No signed transaction bytes
   belong in public evidence.
5. Report `sum(L2 gas * fee cap + L1 data fee + other applicable chain fees)`
   in ETH, separately convert at
   a dated ETH/USD quote, and state any chosen contingency. Add actual audit,
   bounty, provider setup/recurring, gas sponsorship, support and capital-lock
   costs. The intended 100 USDC pool is not a gas/security/fiat operating budget.
   All monetary estimates remain null here because there is no approved
   address/configuration simulation or provider quote to price.
6. Only after the separate approvals may the authorized executor broadcast.
   Verify code and every receipt, then use the existing authorized guardian
   to pause and read back `paused=true` before any project funding/opening.
   Stop on uncertain/failed receipt; never blindly rerun deployment.
7. ADMIN schedules both ownership acceptances, waits the actual two-day
   timelock, executes and checks `owner=timelock`, `pendingOwner=0` on both
   contracts. Reconcile every owner event against approved deployment/governance
   receipts. The deployer stays offline during this ownership window.
8. Verify the complete admission/enforcement design on the deployed code before
   funding or unpausing. Then verify the approved capital split, all outstanding
   obligations, treasury/provider readiness, monitoring and support. Funding,
   public opening and first real loan remain separate authorized events.

The timelock wait is a future natural wait **after** approved execution, not
evidence that a deployment is currently underway. Today's missing quote is
classified as missing actual configuration inputs, not an expensive result.

## Provider-neutral adapter contract and acceptance criteria

This is an interface specification, not speculative implementation before a
provider/lender exists. The selected route uses case, fiat and treasury records;
the pool record applies only after a separately justified public-pool re-entry.
It complements the reconciliation state machine in
[operations.md](operations.md#one-payment-two-reconciled-records).

| Private interface record | Minimum required content |
| --- | --- |
| Case authorization | Random case reference; verified person/open-case mapping; accepted agreement text/hash/time; local-currency principal, net proceeds, term and total due; purpose/evidence; sanctions/eligibility result; deterministic reasons; backing reservation; adopted policy version. |
| Fiat operation | Case and unique provider operation ID/idempotency key; disbursement or collection; agreed currency; gross/net amount; actual fees/FX; provider status and its finality/return policy; observation times; dispute/reversal link. No provider payload containing personal data goes on chain. |
| Treasury conversion | Named lender's own account; actual assets received/delivered in micro-USDC and dollars; fee/spread/delay; restricted prepaid-interest/float allocation; own-treasury control evidence. |
| Pool operation | Authorized protocol borrower and destination mapping; exact EIP-712 chain/domain/nonce/deadline, amount, 90-day period and accepted APR ceiling; resulting loan ID/transaction/receipt/block; chain status and exact debt; bank↔pool reconciliation reference. Keys are custody references, never record fields. |

Acceptance requires evidence for all of the following:

- Provider terms permit the named lender and actual lending/collection/conversion
  purpose; no invented free fees, no end-customer crypto account and no onward
  transmission claim assumed from an API. Residual ACH/card reversal risk is
  budgeted rather than described as impossible after a “settled” status.
- Replaying callbacks or retrying after a timeout never duplicates payment,
  borrower credit, capital reservation, backing or on-chain settlement. Resolve
  uncertain provider operations by their original IDs before retrying.
- Wrong chain/token/recipient, stale quote, expired/replayed signature, changed
  APR, wrong30-day entry point, insufficient reserve/backing and a second open
  case all fail safely before an unauthorized movement. Global restrictions
  are demonstrated across direct routes as well as the adapter route if the
  parked public-pool candidate is ever reopened. The private-ledger route does
  not pretend it has satisfied those on-chain tests.
- A bank-side success and chain-side failure leave an explicit exception, not
  a second borrower payment or a false closure. If the borrower received no
  dollars, unwind the treasury/pool leg at lender expense without creating
  human debt. If the borrower paid, halt collections while the lender resolves
  chain settlement. Credit the borrower once under the adopted terms.
- Exact USDC interest/rounding, early refunds, extensions and settlement delay
  reconcile as in the operations note. Lender absorbs extra chain costs/debt
  beyond the accepted dollar charge; both fiat discharge and `Repaid` chain
  status/outstanding zero are evidenced before final backing release for any
  separately approved pool route. A private-ledger case closes on its adopted
  fiat obligation and backing-release terms, without inventing a chain loan.
- Private records, lawful notices, accessible support, non-Meta fallback,
  incident pause/recovery and the human/pool scorecards are exercised in a
  provider sandbox under the real terms, then accepted by a non-author reviewer.

## What must come from whom

The operator supplies or authorizes the **legal lender identity/adoption**,
actual eligible account onboarding/terms and the eventual financial checkpoint.
Public ADMIN/deployer choices are required only if the parked public-pool route
later meets its re-entry condition; do not make unnecessary account creation
today's blocker. Never ask for private keys. Existing real
borrowers/backers supply their own consent and purpose; the protected November8
window is preserved. Actual provider settlement and, later, timelock execution
have natural timing that cannot be manufactured.

The team's present phase is complete: NO_GO/CHANGE decision, operations budget,
provider-neutral interface and conditional deployment map. Once the actual
lender, eligible account terms and real case exist, the team owns the new
bounded implementation/measurement and funding packet; ordinary architecture
judgment is not delegated to the operator. A public-pool dry run or enforcement
build is not left as active overdue work under this decision. Reopen it only on
the stated material case evidence. Preparation does not claim actual lending,
human benefit or validated real-money servicing.
