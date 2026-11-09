# D16 compliance checklist and artefacts (drafted November 3, 2026)

Claude Code (AI), the dedicated D16 lane. These are the artefacts the [legal analysis](../legal-analysis.md) section 6 calls for, drafted the same day so that the November 10 row has them before the trust-interview and rails work needs them. They are drafts for the lender of record to adopt, not legal advice, and nothing here is in force until the operator names the lender of record ([OPERATOR_QUEUE.md](../../../coordination/OPERATOR_QUEUE.md)). Every bracketed field is a placeholder; no borrower, backer or lender is named anywhere in this folder. Labels: **[primary]** rests on a statute or regulation read directly on November 3 (the legal analysis sources table, and this lane's [primary reads](../primary-reads-20261103.md) through the session proxy the same evening); **[recalled]** is standard text or practice reproduced from memory and must be checked against the cited section before first use (none remain after the re-read except where a row says so); **[secondary]** rests on a summary.

## The ten constraints and where each one lives

| Constraint (legal analysis section 6) | Artefact | State |
| --- | --- | --- |
| 1. A named lender of record (default: the operator as sole proprietor in Colorado) | [loan-agreement-template.md](loan-agreement-template.md) header; every notice's letterhead | Drafted; the name is the operator's row in the queue |
| 2. Colorado residents only until a per-state row exists | Residence question at intake (loan agreement, section 1); [per-state-row-template.md](per-state-row-template.md) | Drafted; Colorado row filled from the analysis |
| 3. Business-purpose loans first (Door A); consumer loans only at or below 12 percent and fewer than 25 a year (Door B) | Loan agreement, purpose statement and Door B variant; [uccc-doors-and-counter.md](uccc-doors-and-counter.md) (no filing owed; the Door B counter and the triggers) | Drafted |
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
| ECOA notice wording and the agency line | Appendix C to part 1002, Form C-1 (the sample notice text) and Appendix A to part 1002 ("Finance Companies, and All Other Creditors Not Listed Above: Federal Trade Commission, Consumer Response Center, 600 Pennsylvania Avenue NW, Washington, DC 20580") | [primary], read November 3 ([primary reads](../primary-reads-20261103.md)) |
| Adverse-action timing (30 days) and content | 12 CFR 1002.9(a)(1) and (a)(2); specific reasons (b)(2); incomplete applications (c) | [primary], read November 3 |
| Business-credit notice simplification (revenues of one million dollars or less) | 12 CFR 1002.9(a)(3)(i) | [primary] via the legal analysis |
| GLBA privacy notice elements and the safeguards rule's elements | Regulation P, 12 CFR 1016.6(a) (notice contents; 1016.1(b)(1) excludes business-purpose customers, so the notice is owed to Door B borrowers) and 16 CFR 314.4 (qualified individual, written risk assessment, written incident response plan and the other elements) | [primary], read November 3; the privacy citation corrected from 16 CFR 313.6 on Hermes's review (part 313 now covers only motor-vehicle dealers, 313.1(b)) |
| OFAC SDN search, list download and reports | OFAC Sanctions List Search (sanctionssearch.ofac.treas.gov, with a minimum name score setting; SDN list last updated October 28, 2026 at the read); list formats on ofac.treasury.gov (Advanced Sanctions Data Model, legacy flat files); 31 CFR 501.603 (blocked-property reports within 10 business days) | [primary], read November 3 |
| Colorado UCCC provisions | C.R.S. 5-1-301(15), (25), (37), (47); 5-2-201(1); 5-2-301(1); 5-6-201(2) | [primary], read by the legal analysis and again by this lane on November 3 |
| Colorado deferred-deposit (payday) article | C.R.S. 5-3.1-102(3), (4): the product definition and "instrument"; the reason Door B loans take no pre-authorised debit | [primary], read November 9 |
| Regulation Z thresholds | 12 CFR 1026.2(a)(17)(v); 1026.3(a) | [primary]; 1026.2 re-read by this lane |
| Regulation B record retention | 12 CFR 1002.12(b)(1): 25 months, 12 months for business credit | [primary], read November 3 |
