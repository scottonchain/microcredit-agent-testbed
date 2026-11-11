# Adverse-action notice (template) and the scorecard's reason codes

Draft by Claude Code (AI), November 3, 2026. Regulation B (12 CFR 1002.9) requires a creditor to notify an applicant of adverse action and to give the specific principal reasons; a statement that the applicant failed to reach a qualifying score, or that an internal standard was not met, is insufficient [primary: 1002.9(b)(2), legal analysis section 1]. Regulation B covers business credit as well as consumer credit [primary: 1002.9(a)(3)]. The design satisfies the rule by construction: the deterministic scorecard emits the reasons, and this notice carries them. Every regulatory statement below was read from 12 CFR 1002.9, 1002.12 and Appendices A and C to part 1002 on November 3 ([primary reads](../primary-reads-20261103.md)); the ECOA notice text is Form C-1 of Appendix C.

## When to send, and what it must contain [primary: 1002.9(a)(1) and (a)(2)]

- Within 30 days after receiving a completed application, when the decision is a decline, a counter-offer the applicant does not accept, or a termination or unfavourable change of an existing arrangement.
- Content: a statement of the action taken; the creditor's name and address; the ECOA notice (section 3 below); and either the specific principal reasons or a statement that the applicant may ask for them within 60 days, in which case the reasons are given within 30 days of the request. This template always gives the reasons.
- Business credit, applicant revenues of one million dollars or less [primary: 1002.9(a)(3)(i)]: the notice may be oral or written and the right to reasons may be disclosed at the time of application; this template gives written reasons regardless, because the app can.
- Incomplete applications [primary: 1002.9(c)]: a notice of incompleteness naming what is missing and a reasonable time to supply it is an alternative to a decline; the app uses it when the dossier lacks a required item.

## 1. The notice (borrower-facing)

**From:** [LENDER OF RECORD, legal name, mailing address in Colorado, contact]

**To:** [applicant's name], [address]

**Date:** [date]    **Application:** [application id of date]

**Our decision.** We are not able to offer you a loan at this time. [Variant for a smaller amount: We can offer you a loan of $[amount] instead of the $[amount] you asked for; the terms are in the agreement attached, and you may decline it.] [Variant for an existing loan: We are not able to offer a further loan while your loan of [date] is [overdue / in default].]

**The main reasons for our decision are:**

1. [Reason text from the reason-code table, for example "You did not show us where the repayment would come from (no pay stub, sales record, order or other evidence of income was provided)."]
2. [Reason text, for example "No person has placed a deposit to back your loan, and you did not place a deposit of your own."]
3. [Reason text, if any; at most four reasons, the ones that weighed most.]

These reasons come from our written lending rules, which weigh the evidence you gave us; they do not come from anything about who you are. If something has changed, or you can show us more evidence, you may apply again at any time.

**No credit report was used.** We did not obtain a consumer report about you from any credit bureau in making this decision.

**Your rights.** [ECOA notice, section 3 below, verbatim.]

If you have questions about this notice, contact us at [contact].

## 2. The scorecard's reason codes (bind these to the November 17 scorecard)

The scorecard's published weights produce a score and a cap; each factor that lowered the score below the admission line or the cap below the requested amount is a candidate reason, ranked by its weight, and the top four are printed. The code table is the single source of the printed text, so that the app never improvises a reason.

| Code | Factor (scorecard input) | Printed reason |
| --- | --- | --- |
| R01 | Repayment source not evidenced | You did not show us where the repayment would come from (no pay stub, sales record, order or other evidence of income was provided). |
| R02 | Repayment source evidenced but insufficient for the amount and term | The income or sales you showed us do not cover repayment of $[amount] within [days] days. |
| R03 | No backer deposit and no own deposit | No person has placed a deposit to back your loan, and you did not place a deposit of your own. |
| R04 | Backer's deposit below the required share of the loan | The deposit backing your loan is $[amount], which covers less than the $[required] our rules require for a first loan of $[requested]. |
| R05 | Purpose not stated, or not a productive input | You did not tell us what the money is for, or the purpose you gave is not one our rules cover (we lend for a business input: stock, tools, a licence, a deposit on work). |
| R06 | Purpose stated as personal, family or household, and the Door B yearly count or cap is reached | Your loan would be for a personal purpose, and we have reached the number of such loans our rules allow this year. |
| R07 | Contradiction between statements, or between statements and evidence | What you told us about [the purpose / the repayment source / the amount] does not match the evidence you provided ([brief, factual]). Where the contradiction is between two of the applicant's own statements: What you told us about [the amount / the purpose] does not match what you told us earlier ([the two statements, brief]). (The interview module prints the second form from its contradictions list, November 11.) |
| R08 | An open loan with this lender | You already have a loan with us that is not yet repaid; one loan at a time. |
| R09 | A prior default with this lender not settled | A previous loan with us is recorded as unpaid; it must be settled first. |
| R10 | Residence outside Colorado | We currently lend only to Colorado residents. |
| R11 | Under 18, or capacity not confirmed | We could not confirm that you are at least 18 years old. |
| R12 | Identity or control could not be verified (one person, one line) | We could not confirm that you are the person named in the application, or that the account you gave us is yours. |
| R13 | Sanctions screen match not resolved | We are unable to proceed with this application. (No further reason is printed; see [ofac-screening-step.md](ofac-screening-step.md).) |
| R14 | Requested amount above the first-loan cap | The most we lend on a first loan is $[cap]; you asked for $[requested]. (This is a counter-offer, not a decline.) |

Rules for the printed text: factual, specific to the applicant's file, no score numbers, no reference to "internal standards" or "our model" as the reason, and never a reason that is or stands in for a prohibited basis.

## 3. The ECOA notice (verbatim text of Form C-1, Appendix C to part 1002 [primary]; agency from Appendix A)

> The federal Equal Credit Opportunity Act prohibits creditors from discriminating against credit applicants on the basis of race, color, religion, national origin, sex, marital status, age (provided the applicant has the capacity to enter into a binding contract); because all or part of the applicant's income derives from any public assistance program; or because the applicant has in good faith exercised any right under the Consumer Credit Protection Act. The federal agency that administers compliance with this law concerning this creditor is Federal Trade Commission, Consumer Response Center, 600 Pennsylvania Avenue NW, Washington, DC 20580 [Appendix A: "Finance Companies, and All Other Creditors Not Listed Above"; a creditor with over 10 billion dollars in assets would name the Bureau instead].

## 4. Inputs the scorecard must never take (prohibited bases and proxies)

Not an input, not a feature, not a text field the model may read for scoring: race, colour, religion, national origin, sex, marital status, age (except the capacity-to-contract check, a yes or no), receipt of public-assistance income, the exercise of rights under the Consumer Credit Protection Act. Not an input because it stands in for one of those: the applicant's name, address beyond the state-of-residence check, language or dialect of the interview, photograph, voice, neighbourhood, school, or any derived variable from them [the Massachusetts settlement over a college default-rate variable, legal analysis round one, is the cautionary case]. The interview transcript is summarised into the dossier's tagged statements (purpose, amount, term, repayment source, evidence, backer); the scorecard reads the dossier's fields, never the transcript.

## 5. Records

Keep, for each adverse action, the notice as sent, the dossier version and scorecard version that produced it, and the reason codes, for at least 25 months (12 months for business credit) [primary: 12 CFR 1002.12(b)(1)]. Keep them in the private records store, never in a public repository.
