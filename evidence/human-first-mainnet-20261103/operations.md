# D16 pilot operations: dollars for people, USDC in the lender's treasury

Codex (AI), November 4, 2026. This completes the operations-note deliverable
listed for November 24 in [D16](../../coordination/directions/human-first-mainnet.md).
It is an operating specification and an executable budget, **not a
funding-ready packet, adopted loan terms, a legal opinion or deployment authority**.
Source baseline: testbed `527d70452d6f950f808a74b6f7b8f61e9875155c`;
contract `7ceaf07d46bc2ebe244175af60f027bd8f2a8995`;
app branch `b80b15a9142ac19de42de9e6e58b98aceee38abe`.
No party, account, key or agreement is created by this note.

## The route this operates

The candidate US pilot uses a named Colorado lender of record. The lender
pays and collects dollars from its own accounts and converts only its own
treasury. A borrower needs no cryptocurrency account. The business-purpose
door and consumer-purpose door remain separate, as specified in the
[legal analysis](legal-analysis.md) and [compliance drafts](compliance/README.md).
Their conclusions remain the team's candidate analysis; this arithmetic does
not verify a legal exemption or turn a household expense into a business loan.

The live test app currently demonstrates passkey borrowing, sending and repaying
test USDC. It does **not** implement this dollar-servicing route. Its existing
test-wallet key in GitHub Actions is not a named lender, a dollar account,
mainnet custody or authority to deploy. Keep its testnet drip controls intact.
The old live testnet pool's CI-30 defect is not evidence of the fixed source
having been deployed. No mainnet address or reserve custodian is assigned here.

## Price and cost check before accepting a case

Run the offline tool from the repository root:

```sh
python experiments/self-service-borrower-app/operations_budget.py \
  evidence/human-first-mainnet-20261103/operations-budget-examples.json
python -m unittest discover -s experiments/self-service-borrower-app -p 'test_operations_budget.py'
```

The examples are explicitly fictional. Every unavailable cost remains `null`;
the result requests measurement. The tool has no network, signing or payment
path and always returns `execution_authorized: false`. It rejects incomplete
budgets, extra fields (including unsupported borrower fees), missing cost lines,
negative amounts and fractional-cent input. Rates are integer basis points;
money is integer dollar cents. The draft convention rounds interest down and
allocated lender costs up. It changes neither the app nor the contract's pricing.

For the draft first loan, $10 principal at 9.33% nominal for 90 days gives
23 cents interest after rounding down: the borrower receives $9.77 and owes
$10. The one-payment annualized-cost diagnostic uses the amount actually
advanced, not $10: `0.23 / 9.77 * 365 / 90`, about 9.547%. It is a conservative
arithmetic screen, not a legally defined APR calculation. At 12% nominal the
same discount produces 29 cents interest and exceeds the 12% diagnostic; the
whole-cent maximum is 28 cents. Do not describe nominal rate as the all-in rate.
The round-two example of 25 cents is explicitly for **90 days**, and passes this
diagnostic; a 30-day version would not. Both business and consumer agreements
still disclose the actual dollars advanced, all charges and total due.

Two independent cost stops apply; passing one does not waive the other:

| Existing rule | Consequence for the operating budget |
| --- | --- |
| D7: all-in per-loan cost above 15 cents stops the pilot | Include fiat fees, gas and paymaster, assessment of rejected applicants, evidence review, support, allocated fixed provider charges and capital-lock cost. Lender bears these costs; do not add them to borrower debt. |
| D16: round-trip rail cost above 10% of a $10 loan requires CHANGE | At $10 the ceiling is $1; a 47-cent rail can pass this rule while failing D7. |

[Round two, section 6](round2.md#6-all-in-estimate-for-one-pilot-loan-10-usdc-principal-025-usdc-interest-90-days)
reports roughly 47–49 cents for stack B and 99–101 cents for C including its
allocated fixed items. Neither fits D7's 15-cent all-in budget. Stack A is an
unverified low-cost candidate, not a measured zero-cost route: its business
fee schedule remains unseen and float is not free. No provider is selected
for real use by this note. For a public price used in a provisional comparison,
mark `reported`; never relabel it `measured`. Actual account eligibility,
terms, complete charges and a final round-trip receipt are required to unlock
the rail. Record the denominator explicitly: a funded first loan, or an observed
cohort's completed loans including repeats. Allocate only evidenced costs and
volume for a measured result; assumed future repeats cannot lower today's bill.
The tool requires `allocation_basis` (`funded_first_loan` or
`completed_cohort_loan`) and `volume_basis` (`assumed` or `observed`). Claimed
measured prices with assumed volume still return `VOLUME_MEASUREMENT_REQUIRED`;
the caller's labels do not themselves authenticate invoices or receipts.

D7's assumed 10-cent screen at 65% admission costs `10 / 0.65 = 15.3846`
cents per funded first loan, before its assumed two cents servicing or fiat
rails. `allocated_cost_cents(1000, 65)` conservatively budgets 16 cents for
100 applications and 65 funded loans. This is an assumed scenario that fails
the first-loan cost gate, not a measured cost of the zero-inference-charge prototype.
The frozen stability model instead averages over an assumed lifetime mix of about
one fifth first loans and four fifths repeats; that is a different denominator,
not an arithmetic defect. A measured cohort allocation needs its actual
application costs and completed repeat volume. Preserve both figures and labels.
Reduce or replace the costly step and remeasure; do not hide rejected applicants
or transfer the expense to the borrower. Keep the interview as intake unless
outcome data justify its screening role.

The consumer pilot's own conservative rule is fewer than 25 consumer loans per
calendar year. Stop before accepting number 25 under this pilot rule. The legal
draft's separate discussion of a 26th-loan disclosure trigger does not enlarge
the pilot. Maintain a private lender-wide counter, not one counter per wallet.

## Custody, reservation and daily reconciliation

The named lender controls the dollar accounts, treasury signer and pause/migration
authority. Who that is remains unfilled; never repurpose an agent's testnet key.
Keep secrets in the approved custody system, outside chat, repositories and
logs. A deployment plan must specify key recovery and who can pause when the
primary custodian is unavailable before real funds are accepted.

Maintain separate balances for sponsor capital, available lender cash, outstanding
principal, restricted backing, withheld interest, earned interest, protocol fees
and costs. A contract's token balance is not its lendable cash. Before reserving
a loan, check the exact current contract accounting and existing commitments:

1. One privately identified person has at most one open line; a new passkey or
   recovered browser profile does not create a new person. No public identity list.
2. First loan no more than $10, repeat no more than $20 after an on-time repayment;
   principal at most one fifth of the reserve; pause new lending below $25.
3. First loans fully backed by a separately identified backer's reserved deposit
   or the applicant's own locked deposit. Open-access repeat loans stay fully
   backed; only the approved named-cohort design permits half-backed repeats.
   One deposit cannot be reserved twice or withdrawn while committed.
4. For the later local-currency stage, total open exposure **per currency** is at
   most one fifth of the reserve. The pool absorbs currency changes. The borrower
   receives, repays and is quoted only the contracted local-currency amounts.

These checks require verified balances and identity/consent records. The budget
tool does not check them. A desk-backed **real tester** cohort can test usability
without independent backers; fictional personas cannot satisfy D7 gate 3 or
demonstrate a real backer's willingness to risk money.

## One payment, two reconciled records

Keep the case records private and encrypted using the
[safeguards draft](compliance/privacy-notice-and-safeguards.md). Use a random case
reference rather than names, addresses or transcripts in any necessary chain
mapping. Even a hashed identity is not suitable for public GitHub evidence.
The record must contain the accepted agreement text/hash/time, purpose and
evidence tags, terms, notices, backing reservation, each bank receipt's unique
provider ID and settled status, and each corresponding chain operation and
confirmed result. Public evidence carries safe aggregates only.

| State | Evidence required to advance |
| --- | --- |
| Proposed | Intake/evidence, distinct person, actual cash gap, NO_LOAN comparison, backing and all gates; no money moves. |
| Accepted and reserved | Exact agreement and privacy notice accepted; backing/cash reserved once; sanctions step completed; no unresolved match. |
| Dollar disbursement pending | A unique provider operation ID. A timeout means reconcile that ID, not send again. |
| Dollar disbursement settled | Final bank receipt and exact amount received, followed by the reviewed lender-to-pool accounting operation. A test token transfer is not this receipt. |
| Repayment pending | A receipt or ACH initiation is provisional until final settlement under provider terms. Mark paid for the borrower promptly when final; pause collections on a disputed/uncertain receipt. |
| Dollar repayment final; pool settlement pending | Credit each provider receipt once. Set aside the lender's corresponding USDC and prepaid-interest reserve; do not credit an extra borrower payment when settling the pool. |
| Closed | Dollar obligation discharged and chain settlement confirmed, exact outstanding zero, backing released once. A defaulted chain loan also returns zero from the outstanding getter: inspect the loan status and repayment events, not the getter alone. |

The current contract source's
[`getCurrentOutstandingAmount` and `_repay`](https://github.com/scottonchain/microcredit-contract/blob/7ceaf07d46bc2ebe244175af60f027bd8f2a8995/packages/foundry/contracts/DecentralizedMicrocredit.sol#L1077)
accrue interest from disbursement, apply repayment to interest first and close a
repaid loan only when its exact outstanding is paid. Partial repayment does not
reduce the principal used for future interest. CI-30 no longer forgives sub-cent
debt. A $10 bank payment cannot, by itself, repay a $10 pool loan plus interest.

For a prepaid-interest first loan, retain the withheld interest in a restricted
lender settlement balance. Combine that balance with the returned dollar principal
when settling the lender's pool debt. This is **one borrower payment**, not two.
The fixed contract calculates in USDC micro-units and its exact interest can
exceed the cent-rounded charge. Settlement delay, rounding, conversion costs,
bank reversals and an agreed extension can also create differences. The lender
funds any excess; never surprise-charge it to the borrower. Reconcile actual
received USDC rather than assume that one dollar always converts without cost.
Conversely, an unused restricted balance is not free revenue until the accepted
agreement's refund obligations and exact settlement have been satisfied.

On each operating day, independently compare the bank's final receipts, private
case records, treasury movements and pool loan status/events at a named block.
Unmatched or duplicate IDs, mismatched amounts, reorged/pending transactions,
unfunded reservations or unexplained balance differences pause new disbursements.
An outbound timeout is never evidence of failure and never authority to retry
blindly. The adapter implementing this reconciliation is not present in the live
test app and needs a reviewed sandbox demonstration before real use.

## Early payment, default and support

The draft agreement already promises no prepayment fee and a free cancellation
window. Before adoption it must also state how **prepaid first-loan interest**
is returned; its current explicit early-interest paragraph addresses repeats.
The executable draft rule prorates earned interest by days actually used,
rounds earned interest down, and refunds the balance: 23 cents prepaid for
90 days gives a 16-cent refund on day 30. Free cancellation refunds all withheld
interest; return only the dollars actually received, not the gross principal.
These are candidate terms for incorporation before signing, not a change to any
existing loan. Lender absorbs chain-close costs and any remaining on-chain debt.

Use the support contact named in the agreement and provide a receipt of every
final payment. Offer a human escalation path and an accessible non-Meta channel;
no WhatsApp account or access to a borrower's contacts is assumed. No agent sends
real reminders from this note. The draft's existing limits apply: no late fees,
no workplace contact, no more than weekly overdue contact, no debt sale or credit
bureau reporting, an agreed written extension of up to 30 days. No added third
party or harassment as a lateral workaround. Do not change due dates on chain
without the corresponding agreed terms and reconciled lender costs.

At default, record actual outstanding, amount recovered from backing, lender
loss and backer loss separately. Stop at the existing two-defaults-in-20 trigger,
a consumer-protection failure, a zero-purpose loan or the cost stop. A backer's
loss is a system loss even if pool cash grows. The template currently describes
debt passing to the backer; do not promise both final discharge and a new personal
debt. The named lender must reconcile the adopted backer statement, borrower
agreement and lawful recovery treatment before accepting a deposit.

### Backer's deposit statement to fill privately before use

“I, [backer], ask [named lender] to reserve $[amount] of my own deposit for
[privately identified borrower] under agreement [reference]. I understand this
earns no interest, fee, token reward or other return. I can lose up to $[amount]
if that borrower defaults. I cannot withdraw the committed part while that loan
is open. The uncommitted balance remains mine. I have read how default, release,
refund and any claimed right of recovery work: [adopted terms consistent with
the borrower's agreement]. No one has promised that this is risk-free. I can
contact [support] to ask about the deposit. [Acceptance, version/hash and date].”

This statement is incomplete until the lender, borrower reference, amount and
consistent recovery terms exist. No yield to backers, public deposit-taking or
automatic claim that the borrower now owes a private backer is introduced here.

## Incidents, measurement and the actual unlock

On key compromise, ledger mismatch, duplicate movement, sanctions uncertainty,
complaint about pressure, privacy exposure or provider suspension, stop new
applications/disbursements and use the reviewed pause procedure where authorized.
Preserve restricted evidence, reconcile uncertain transfers, keep repayment/support
available and communicate through the agreed contact. Do not rotate credentials,
redeploy, report personal data publicly or spend funds merely to clear an alert.
Follow the compliance draft's applicable reporting deadlines through the named
lender. Resume only after the cause is fixed, receipts reconcile and an independent
check accepts the remediation.

Keep the human scorecard separate from pool sustainability: actual spendable
earnings net of paid charges, displacement and harms, compared with NO_LOAN,
prepayment and direct cash on the same cases; sponsor capital consumed and locked;
pool and backing losses; all costs. Transactions, a passkey demonstration,
synthetic repayment and this note count as no human income.

The operations deliverable is now specified and executable. The **real pilot**
still requires the following evidence, which this note does not manufacture:

- A named accountable lender adopting the legal/compliance/loan/backer terms,
  support and custody design; actual eligible accounts and a reviewed dollar-to-
  pool servicing adapter. The default Colorado design alone supplies none of them.
- D7's five consenting real testers/prospective borrowers and the required backing,
  or the explicitly stated desk-backed real-tester alternative; actual purposes,
  cash gaps, full costs, repayment routes and same-case simpler alternatives.
- Primary provider terms and a measured final round trip meeting **both** cost
  gates; full costs rather than the prototype's extraction-time bill alone.
- Shadow scoring on actual outcomes, or a reasoned change that leaves the
  interview as intake and retains verified backing; no synthetic calibration claim.
- Fixed-source audit/bounty and mainnet-readiness receipts, the deployment/cost
  plan and the funding-ready packet. Mainnet deployment and the operator's
  intended 100 USDC remain a separate checkpoint. No mainnet action occurs here.

This is the strongest adjacent finish available without another person's consent
or new financial/account authority: complete the operating budget and reconciliation
specification now, retain the protected November 8 observation window, and never
represent the missing human outcome as completed.
