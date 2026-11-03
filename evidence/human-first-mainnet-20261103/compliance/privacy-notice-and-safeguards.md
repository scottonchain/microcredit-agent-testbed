# Privacy notice (template) and one-page safeguards program

Draft by Claude Code (AI), November 3, 2026. A non-bank lender is a financial institution under the Gramm-Leach-Bliley Act's privacy and safeguards rules as administered by the FTC [secondary, general, legal analysis section 5]. The notice contents follow 16 CFR 313.6(a) and the program follows the elements of 16 CFR 314.4 (a qualified individual, a written risk assessment, a written incident response plan and the rest), both read on November 3 ([primary reads](../primary-reads-20261103.md)); whether these FTC rules reach a lender of this kind is the [secondary, general] point. Fields in [brackets] are placeholders.

## Part 1. Privacy notice (given at intake, before the interview starts)

**[LENDER OF RECORD] privacy notice**

**What we collect.** When you apply for a loan we collect what you tell us in the interview (what the money is for, how much and for how long, where repayment will come from, who vouches for you), the evidence you choose to show us (for example a pay stub, a sales record or an order), your name, address, state of residence, date of birth, and the bank account or payment handle you give us for sending and receiving dollars. If you borrow, we also collect your payment history with us.

**What we do not collect.** We do not obtain a credit report about you. We do not ask about race, colour, religion, national origin, sex, marital status or whether your income comes from public assistance, and we do not use your name, address or the way you speak to decide your loan.

**How we use it.** To decide whether to lend to you and how much, to send you money and receive your repayments, to tell you the reasons for a decision, to keep the records the law requires, to screen against government sanctions lists, and to contact you about your loan.

**Who we share it with.** Our bank and the payment services we use to send and receive dollars (they see your name and account details, not your interview); the sanctions-screening service (your name and address); the computer systems we use to run the interview and keep records, under contracts that require them to protect it. We do not sell your information and we do not share it with marketers. We share it with others only when the law requires us to.

**What is public.** Our loan ledger is a public computer program. It records loan amounts, dates and repayment status under a number, never your name, address, interview or evidence. Your backer, if you have one, knows that they backed you; they do not see your interview.

**How we protect it.** Your interview and evidence are stored encrypted, and every access by a person is logged. Only the lender of record and the people the lender names in writing can open them. Nothing you tell us is ever placed in a public repository.

**How long we keep it.** Application records for [25 months] after a decision; loan records for [the life of the loan plus 3 years]; then we delete them unless the law requires longer.

**Your choices.** You can ask us for a copy of what we hold about you, ask us to correct it, or ask us to delete your application if you did not borrow, by writing to [contact]. If you applied and we declined, you will receive our reasons in writing without asking.

**Changes.** If this notice changes, we will tell you by email before the change applies to you.

[LENDER OF RECORD], [address in Colorado], [contact]. Version [n], [date].

## Part 2. Safeguards program (one page, for the lender of record to adopt)

**Purpose.** To protect the information described in the privacy notice, in proportion to a pilot of about twenty loans run by one lender of record with agent software.

| Element | What the pilot does |
| --- | --- |
| Responsible person | The lender of record is the qualified individual responsible for this program and signs this page. |
| What is protected | Interview transcripts and dossiers, evidence files, names, addresses, dates of birth, bank account and payment details, repayment records, adverse-action notices, backer deposit statements, OFAC screening results. |
| Where it lives | One private, encrypted records store named here: [system and location]. Never a public repository, never a chat transcript, never a board comment, never a log that is shared. The world model and the evidence folders hold counts and aggregates only. |
| Who can open it | The lender of record, and each person or agent the lender names on an access list kept with this page. Agent sessions that run the interview write to the store and read back only the dossier fields the scorecard needs. |
| Encryption and access logging | At rest: encrypted with a key held by the lender of record. In transit: TLS. Every human access is logged with who, when and which record. |
| Service providers | The bank, the payment services, the sanctions-screening service and the interview and storage systems, each under written terms that require them to protect the information; the list is kept with this page. |
| Retention and disposal | As stated in the privacy notice; deletion is logged. |
| Risk review | Before the first loan and after any incident, the lender of record walks through: where the data is, who can reach it, what would happen if a key, a session or a provider were compromised, and what changed since the last review. The walk-through is written down, one page. |
| Incident response | If information is exposed: stop the exposure, record what happened and when, tell the affected people within [a stated number of days] in plain words, and record what changed to prevent a repeat. Notification obligations under Colorado's data-breach law apply [secondary; check C.R.S. 6-1-716]. |
| Training | Each person on the access list reads this page and the privacy notice before first access. |
| Testing | Once before the first loan and once a quarter: confirm that the store is encrypted, that the access log works, that a deleted record is gone, and that no interview text appears anywhere public (a search of the repositories and the board for a known test phrase). |

Signed: [lender of record], [date].
