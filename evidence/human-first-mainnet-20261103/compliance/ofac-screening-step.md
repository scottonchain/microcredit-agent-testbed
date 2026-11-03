# OFAC screening step

Draft by Claude Code (AI), November 3, 2026. Sanctions administered by the Office of Foreign Assets Control (OFAC) apply to every US person; a loan or a payment to a sanctioned person or a blocked address is a violation whatever the amount [legal analysis section 1 and 5]. The pilot screens twice: the applicant (name and address) before any decision is communicated, and any wallet address before any on-chain payout. This page is the procedure; the tool, the list formats and the reporting rule were read from ofac.treasury.gov, sanctionssearch.ofac.treas.gov and 31 CFR 501.603 on November 3 ([primary reads](../primary-reads-20261103.md)).

## What is screened, and when

| Moment | What | Against |
| --- | --- | --- |
| After intake, before the scorecard's decision is sent | Applicant's full name, any other names given, address, date of birth; the backer's name and address when a backer deposit is placed | The Specially Designated Nationals and Blocked Persons list (SDN) and OFAC's consolidated non-SDN lists |
| Before any payout to a wallet address (not in the dollars-only design, kept for completeness) | The receiving address | The digital-currency addresses OFAC publishes as identifiers on the SDN list |
| Before each disbursement and on each anniversary of a loan still open | Re-screen the borrower's name | The current lists (they change) |

## How (manual, for a pilot of about twenty loans)

1. Open OFAC's Sanctions List Search (sanctionssearch.ofac.treas.gov; it searches the SDN list and the other OFAC lists and has a "Minimum Name Score" setting). Enter the name; keep the minimum name score at the tool's default and do not treat a low fuzzy match as a hit. Record the search date, the name as entered, and the result (no match; possible match; match).
2. For a possible match: compare the list entry's identifiers (date of birth, nationality, address, identification numbers) against the applicant's; a difference on a strong identifier (a different date of birth, a different country) clears it. Write one line of reasoning in the record. If it cannot be cleared, treat it as a match.
3. For a match: do not disburse, do not communicate reasons beyond the fixed sentence in the adverse-action template (code R13), keep the application record, and the lender of record files any required report [primary: 31 CFR 501.603, reports of blocked property within 10 business days of the blocking, with the contents the section lists]. No further contact with the applicant about the match.
4. For wallet addresses: search the address string in the same tool (digital-currency addresses are listed as identifiers), or match against the SDN list files downloaded that day.
5. Record every screen in the private records store: who screened, when, inputs, result, resolution.

## Automation later

A scripted step can download the SDN and consolidated list files (OFAC publishes the Advanced Sanctions Data Model files and legacy flat files) each day and run a name and address match with a stated algorithm and threshold; the manual procedure above remains the reference, and any automated hit still goes through step 2 by a person. Not built for the pilot; recorded as a November 24 operations item.

## What this step does not do

It does not identify the person (identity is the one-person-one-line rule's job, through the bank account and the backer); it does not screen for anything but sanctions; it does not replace the bank's and the payment services' own screening, which also runs on every dollar transfer.
