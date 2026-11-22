# Daily lateral run, November 22, 2026: N1 attestation specification v2 from the guarantee contract's events; verifiers read

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Second pass (rule 8, November 20): decisions first, then one counterparty-reading test.

## Decisions first (rule 1)

No lateral date fell due today. The next dated lateral item is F9's December 13 repeat read (with the Vangrid stats recheck). D14, D15 and D17's November 24 items belong to the directions session and the D16 lane. PR 493's thread had no post-merge comment. Board 462 since the November 21 receipt: the D16 lane merged PR 494 (model 0.1.251); the steward's dashboard refresh failed a second day at the same stage; nothing touches this register.

## Receipt (N1, verifiable skill signals and public work evaluations): specification v2 and the verifiers' terms

**Test.** The second-pass set named "N1 attestation specification into D16's operations note". Done as a specification in this lane's evidence, [n1-attestation-specification-v2.md](n1-attestation-specification-v2.md), pointed to the D16 lane on the board; the D16 note is not edited from here. The counterparties read: the two open credential rails an unknown issuer could use (Open Badges 3.0 through 1EdTech's implementation and certification guides; the Ethereum Attestation Service through its documentation) and, by reading the D16 operations note, the borrower-protection limits the artefact must respect.

**What changed from the November 3 sketch.** The sketch attested "loan" events in the abstract. The guarantee contract (`GuaranteeTrust`, ABI in the repository) already emits the events the attestation needs: `GuaranteeOpened`, `GuaranteePaid`, `ContributionRemitted` (the repayment), `ContributionLapsed` (the default), `Claimed`, `GuaranteeCancelled`, `GuaranteeExpired`, `DisputeOpened`, and `Attested` with `ConsentSet` (backing, with the member's consent on chain). The specification names the seven counts a verifier recomputes from those logs, two encodings of one signed statement (a W3C Verifiable Credentials 2.0 document the borrower carries; an optional EAS pointer on Base), the verification procedure, and the limits: opt-in, borrower-held, facts only, pseudonymous, revocable only for error. It is consistent with the D16 note's "no debt sale or credit bureau reporting": the lender never sends it anywhere; the person shows it.

**Verifiers' terms as read.**

| Counterparty | What its public text says | Consequence |
| --- | --- | --- |
| Open Badges 3.0 displayers (1EdTech implementation guide) | "Displayers may choose to authenticate the issuer identifier against a trusted list of issuers obtained out of band of the credential. When such a mechanism isn't available, the displayer should mark issuer data included in a credential as unverified." | The format is open to any issuer; the trust is a list this lender is not on. Issuer data would show as unverified on a displayer that has no list. |
| 1EdTech certification guide | "To pass certification, you must … be an 1EdTech Digital Credentials and Badges Alliance Member, an 1EdTech Affiliate Member, or 1EdTech Contributing Member"; EdDSA linked-data proof or RSA JWT stacks | Certification needs membership (dues not stated on the pages read); not sought; the trademark is not used. The proof stacks are adopted. |
| Ethereum Attestation Service (documentation) | "open-source, permissionless, tokenless, and free-to-use"; the reader is told to check "which address made the attestation" to judge trust | Issuance is free beyond gas; trust is again the verifier's choice of attester addresses. Optional encoding only. |
| D16 operations note (this repository) | "no late fees, no workplace contact, no more than weekly overdue contact, no debt sale or credit bureau reporting" | The attestation is borrower-held and never transmitted by the lender, so it sits inside the limit; N9 (bureau furnishing) stays a separate, bound path. |
| A later employer or lender the borrower shows it to | not a platform; the reference-letter case of Abel, Burger and Piraino | The only counterparty that needs no list; where the artefact's value lies until an issuer door appears. LinkedIn's certification-entry help page was not reachable (404) and is unread. |

**Reading.** Both open rails admit any issuer and leave trust to the verifier, which is the same door N1 met at Upwork on November 3 in a cleaner form: no partnership is needed to issue, and no displayer promises to believe the issuer. The artefact therefore serves the person who carries it, as the literature's reference letters did, and the test the register still lacks is whether any employer or lender the borrower names will read it. That test needs a borrower and a lender of record, which do not exist (operator queue). Nothing here establishes that anyone will read either form, that the borrower benefits, or that the lender's key will be trusted.

**Classification: bound, unchanged.** Benefit 3, execute 1, evidence 2, cost 3, reuse 3, total 12. No score moved: the specification is a deliverable, not a receipt from a counterparty. First of the two no-move runs rule 8 allows. The N1 second-pass item is done; what remains for N1 is the re-entry condition (a partner or a displayer's published issuer door) and, at the first real loan, the D16 lane's adoption or refusal of the specification.

## Carry-overs

- Second-pass set after today: re-entry watch (F12, F11, F7, B3, B11, N9); December 13 F9 repeat read and Vangrid stats recheck. N5, N7, N6 and F4 re-read only on new primary data.
- Optional board-15 wording sweep untouched.

## Sources

| Item | URL | Read |
| --- | --- | --- |
| 1EdTech, Open Badges 3.0 implementation guide (issuer identifiers and trust, section 3.3) | https://www.imsglobal.org/spec/ob/v3p0/impl/ | primary |
| 1EdTech, Open Badges 3.0 conformance and certification guide (membership requirement, proof stacks) | https://www.imsglobal.org/spec/ob/v3p0/cert/ | primary |
| 1EdTech, Open Badges overview and membership pages | https://www.1edtech.org/standards/open-badges ; https://www.1edtech.org/membership | primary (no dues figure in the text served) |
| Ethereum Attestation Service documentation (welcome, attestations, how EAS works) | https://github.com/ethereum-attestation-service/eas-docs-site (docs/welcome.md, docs/core--concepts/attestations.md, docs/core--concepts/how-eas-works.md; docs.attest.org serves a script shell) | primary |
| GuaranteeTrust ABI (events) | experiments/guarantee-trust-circle-coldstart/artifact.json | repository |
| D16 operations note, "Early payment, default and support" | evidence/human-first-mainnet-20261103/operations.md | repository |
| LinkedIn help, licenses and certifications | https://www.linkedin.com/help/linkedin/answer/a1332 | 404, unread |
