# D16 compliance checklist and artefacts (drafted November 3, 2026)

Claude Code (AI), the dedicated D16 lane. These are the artefacts the [legal analysis](../legal-analysis.md) section 6 calls for, drafted the same day so that the November 10 row has them before the trust-interview and rails work needs them. They are drafts for the lender of record to adopt, not legal advice, and nothing here is in force until the operator names the lender of record ([OPERATOR_QUEUE.md](../../../coordination/OPERATOR_QUEUE.md)). Every bracketed field is a placeholder; no borrower, backer or lender is named anywhere in this folder. Labels: **[primary]** rests on a statute or regulation the maintainer session read directly on November 3 (legal analysis sources table); **[recalled]** is standard text or practice reproduced from memory and must be checked against the cited section before first use; **[secondary]** rests on a summary.

## The ten constraints and where each one lives

| Constraint (legal analysis section 6) | Artefact | State |
| --- | --- | --- |
| 1. A named lender of record (default: the operator as sole proprietor in Colorado) | [loan-agreement-template.md](loan-agreement-template.md) header; every notice's letterhead | Drafted; the name is the operator's row in the queue |
| 2. Colorado residents only until a per-state row exists | Residence question at intake (loan agreement, section 1); [per-state-row-template.md](per-state-row-template.md) | Drafted; Colorado row filled from the analysis |
| 3. Business-purpose loans first (Door A); consumer loans only at or below 12 percent and fewer than 25 a year (Door B) | Loan agreement, purpose statement and Door B variant; [uccc-notification-instructions.md](uccc-notification-instructions.md) (no filing owed; the counter and the triggers) | Drafted |
| 4. Dollars disbursed and collected by the lender from its own accounts; conversion only of the lender's own treasury | Loan agreement, sections 3 and 4 (disbursement and repayment in dollars); [round2.md](../round2.md) sections 4 to 6 for the rails | Drafted |
| 5. Donated reserve; no yield to backers; no public invitation to deposit | Loan agreement, section 8 (backer statement); staker terms are the November 24 operations note | Drafted here only as the backer paragraph |
| 6. Regulation B reasons from the scorecard; no prohibited-basis or proxy inputs; notice template before the first decline | [adverse-action-notice-template.md](adverse-action-notice-template.md), with the scorecard reason codes and the input exclusion list | Drafted; reason codes to be bound to the November 17 scorecard |
| 7. Privacy notice, safeguards page, encrypted interview records, OFAC screen | [privacy-notice-and-safeguards.md](privacy-notice-and-safeguards.md); [ofac-screening-step.md](ofac-screening-step.md) | Drafted |
| 8. Pause and migration key with the lender of record | Loan agreement, section 9 (what happens if the pool pauses); the November 24 deployment plan | Drafted here only as the borrower-facing sentence |
| 9. One person, one line; a backer or deposit behind every first loan | Loan agreement, sections 2 and 8 | Drafted |
| 10. Counsel optional | This README: a one-hour review list at the end | Listed |

## What a loan looks like under these artefacts, start to finish

1. The applicant answers the intake interview in the app (state of residence first; a non-Colorado answer ends with a polite decline and the per-state row is the re-entry). The interview asks what the money is for, how much, for how long, where repayment will come from, what evidence exists, and who vouches. It asks nothing on the prohibited list in the adverse-action template.
2. The OFAC step runs on the applicant's name and address before any decision is communicated, and on any wallet address before any on-chain payout.
3. The scorecard decides and records its principal reasons. A decline sends the adverse-action notice within the Regulation B window; an approval sends the loan agreement.
4. The borrower signs (electronic acceptance in the app is recorded with a timestamp and the agreement's hash). The lender disburses dollars from its own bank account, net of the interest deducted at disbursement for a first loan, and records the loan in the pool contract from its own USDC.
5. The borrower repays dollars to the lender's account by the stated means on or before the due date; the lender records the repayment on chain from its own USDC. Nothing in the borrower's path touches crypto.
6. The privacy notice was given at intake; interview records sit encrypted and access-logged outside any public repository; the loan counter (Door B) is incremented if the loan was consumer-purpose.

## One-hour counsel review list (optional, not a gate)

- The loan agreement's governing-law, business-purpose statement and the Door B interest clause against C.R.S. 5-2-201(1) and 5-1-301(15)(b).
- The adverse-action notice against 12 CFR 1002.9(a)(2) and (b)(2) and the ECOA notice text in Appendix A to Regulation B, and the agency named in it for a non-bank lender.
- Whether the privacy notice's model-form language is required or optional for a lender of this size, and the safeguards program's written-plan element.
- The pause clause: whether a lender may suspend new lending and migrate the ledger without the borrower's consent, as drafted.

## Sources used here beyond the legal analysis

| Item | Basis | Label |
| --- | --- | --- |
| ECOA notice wording and the agency line | 12 CFR 1002.9(b)(1) and Appendix A to Regulation B | [recalled]; check before first use |
| Adverse-action timing (30 days) and content | 12 CFR 1002.9(a)(1) and (a)(2) | [primary] via the legal analysis for (a)(3); [recalled] for the 30-day figure |
| Business-credit notice simplification (revenues of one million dollars or less) | 12 CFR 1002.9(a)(3)(i) | [primary] via the legal analysis |
| GLBA privacy notice elements and the safeguards rule's elements | 16 CFR part 313 (Privacy of Consumer Financial Information) and 16 CFR part 314 (Standards for Safeguarding Customer Information) | [recalled]; the FTC rules apply to non-bank lenders; check the current text |
| OFAC SDN search and list download | OFAC Sanctions List Search (sanctionssearch.ofac.treas.gov) and the SDN list files on ofac.treasury.gov | [recalled]; host denied to this session |
| Colorado UCCC provisions | C.R.S. 5-1-301(15), (37), (47); 5-2-201; 5-2-301; 5-6-201(2) | [primary] via the legal analysis |
| Regulation Z thresholds | 12 CFR 1026.2(a)(17)(v); 1026.3(a) | [primary] via the legal analysis |
