# Kenya regulatory primary-source audit

Prepared by Codex on 8 October 2026. Read-only research; no regulator, provider, or borrower contact, application, account access, or transaction. Evidence register: `kenya-regulator-sources.json`. This is an evidence and implementation-gate assessment, not a legal classification decision.

## Findings that change the pilot plan

**The VASP framework is no longer merely a consultation draft.** CMA publishes the actual government Gazette text of the Virtual Asset Service Providers Regulations, 2026, Legal Notice 134. It was made on 3 July, published in Gazette Supplement 185 on 22 July, and uploaded by CMA on 27 July 2026 [S4]. The March consultation [S5] and November 2025 announcement that licences had not yet been issued [S3] describe earlier states; neither establishes the position today.

**The claimed final September 2026 non-deposit-taking credit rules require a primary-text fetch before we apply their provisions.** The alleged instrument is Legal Notice 191, Gazette Supplement 234, dated 29 September 2026. The candidate Kenya Law PDF/page returned HTTP 403 in this audit [U1]. Searches found reporting of that instrument, but reporting is not treated as primary proof here. This does not show the instrument is absent or a draft. It means its final provisions, commencement, transitional treatment, and any subsequent amendments are unverified by this audit.

CBK's accessible August 2025 document is unequivocally a consultation draft [S1], with an unfilled legal-notice number. Its KES 20 million licensing/registration boundary must **not** be treated as the verified final threshold. A May 2026 regulatory impact statement uploaded in June still describes draft rules and future publication [S2]. The URL misleadingly ends in “Regulations-2025.pdf” while the document title says 2026. Neither document establishes the October legal position.

## Dates and status

| Instrument or notice | Verified dates | Status established here |
| --- | --- | --- |
| CBK Act consolidated copy [S0] | Law as at 4 November 2025; CBK URL uploaded March 2026 | Enacted parent statute; latest amendments after this consolidation not exhaustively checked |
| NDTCP draft [S1] | CBK consultation notice 7 August 2025; comments due 5 September | Draft, not a gazetted final regulation |
| NDTCP impact statement [S2] | Text dated May 2026; URL directory June 2026 | Preparatory statement, not final regulation |
| Alleged NDTCP LN 191 [U1] | Alleged Gazette publication 29 September 2026 | Primary text inaccessible; finality/effective date not independently established |
| VASP Act [S3/S6] | Assent 15 October; Gazette 21 October; commencement 4 November 2025 | Enacted and commenced |
| VASP consultation [S5] | CBK notice 18 March 2026 | Draft consultation at that date |
| VASP LN 134 [S4] | Made 3 July; Gazette 22 July; CMA upload 27 July 2026 | Issued Gazette regulations, not merely draft |

Under the general commencement rule in section 27(1) of the Interpretation and General Provisions Act [S7], subsidiary legislation ordinarily operates on publication unless written law sets another date, subject to annulment. The VASP PDF has no express delayed commencement clause identified in the reviewed text. Thus 22 July is the supported ordinary operative-date inference; checking later annulment, judicial orders, and amendments remains necessary for a definitive current opinion. The three dates above are not interchangeable.

## Who should be lender of record for a 20–50-person pilot?

The enacted CBK Act [S0], sections 2, 33R and 33S, reaches lending to the public **or a section of it**, digital or offline, with or without interest. It provides a licensing rule unless another written law permits the business. No exemption based solely on 20–50 participants was evidenced. Naming the activity a pilot, social loan, or algorithmic loan does not establish an exemption.

Operational recommendation: select an **existing authorized lender** whose permitted activity and approved product fit the actual loan. Candidate categories requiring separate verification are a Banking Act institution, Microfinance Act institution, appropriately authorized SACCO with eligible members, or non-deposit-taking credit provider. These are search branches, not blanket approvals. The 2025 draft exclusions corroborate the separate-regime categories [S1] but are not proof of their final 2026 treatment.

The pilot specification must identify the legal entity making the loan, contractual creditor, asset and currency, source of capital, collection role, decision authority, borrower eligibility, complaints path, and customer-data roles. Verify its current regulator entry and licence conditions, then obtain the final LN 191 text and check any product/outsourcing requirements. If an employer advances wages or a merchant extends incidental trade credit, document that exact relationship before relying on an incidental-credit exclusion. An unrelated lending pool does not become an employer or merchant by description.

Deposits, staking, pooled public capital, payment execution, custody, conversion, and lending need separate role analysis. An algorithm for creditworthiness is an implementation choice; it does not designate a lender of record.

## VASP scope relevant to USDC/ETH settlement

The Act's sections 8–10 require authorization for covered business in or from Kenya; its First Schedule separates CBK wallet/payment/stablecoin roles from CMA exchange/broker/manager/issuance roles [S6]. Section 47 gives providers operating at commencement one year to comply; 4 November 2026 is the resulting anniversary, not an automatic grace period for a new entrant.

Regulation 4 extends scope to targeting local consumers or deriving Kenyan economic benefit regardless of physical presence, and regulation 14 addresses conversion business authorization [S4]. Accordingly, an offshore entity or agent does not establish an exemption by location. Current actual provider licences were not established here. Permission for remittance, payment, lending, and virtual-asset activity must each be checked for its own service.

## Eversend / Cogni Systems remittance claim

Searches of the accessible **June 2026** CBK licensed-money-remittance directory's full extracted text [S8] found neither “Cogni” nor “Eversend.” CBK directory landing pages currently link separate legacy-path PDFs [U2/U3]; those timed out. A page's “Posted On” alongside daily exchange rates is not the directory's issue date.

Conclusion: **current CBK authorization for Cogni Systems Limited / Eversend remains unverified**, not disproved. A later licence, licensed partner, or different legal name could explain the discrepancy. Record the exact authorized entity and licence number from a current CBK register or Gazette before relying on it. Even a verified remittance licence would not establish VASP or lender authorization.

## Immediate tasks without contacting anyone

1. Fetch and preserve LN 191's actual Gazette PDF from Kenya Law or CBK; verify masthead, making date, commencement, scope, transition and registration/licensing rules. Record a byte hash.
2. Select one proposed lender entity and verify its current licence, permitted product and exact responsibilities. Do not assume small pilot size authorizes a lending business.
3. Resolve Cogni/Eversend's legal-name/licence evidence; model provider status as unverified until then.
4. Keep pilot economics conditional on a lawful, executable payment/settlement route and verified lender responsibilities. Read-only cost research and technical simulation can proceed separately.
