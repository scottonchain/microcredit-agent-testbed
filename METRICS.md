# Human-benefit metrics

Purpose of the pool: reduce human poverty and suffering. Bots may be lenders, attesters, reputation roots and borrowers, even a majority of participants. These metrics exist so that bot activity can never stand in for human outcomes. Proposed for publication from day one (computed from on-chain events plus an off-chain attestation set).

## Outcome metrics (what we are trying to move)
1. **Unique repaying human borrowers**: distinct attested-person borrowers with at least one fully repaid loan. Headline number.
2. **First-time borrower share**: fraction of newly disbursed principal going to borrowers with no prior loan.
3. **Credit reaching people with no capital**: share of total borrowing limits held by accounts whose own stake is zero (credit that came from issued lines, backing or a guarantee pool).
4. **Repayment rate by cohort**: on-time and eventual repayment for human first loans vs bot loans, split by how the loan was backed (own line, unsecured backing, stake).
5. **Loan size vs local income** (needs an off-chain attestation): principal as a share of the borrower's monthly income band.

## Integrity metrics (what we are trying not to break)
6. **Issuer and backer concentration**: largest single issuer's or backer's share of total credit, and Gini across backers. Target cap per root to be set by Design Question 8a.
7. **Cluster concentration**: share of credit inside the largest strongly connected backing cluster with no external stake.
8. **Bot-borrower crowd-out**: bot share of outstanding principal vs share of total credit. Alarm if bots drain credit people could use.
9. **Credit manufactured**: credit not traceable to issued lines, dues or stake. 0 by construction (Theorem 1 in CREDIT_MODEL.md), checked by the contract's invariant suite; publish it anyway, as a check, not a metric to optimise.
10. **Net pool yield after defaults**, with and without bot liquidity, to show whether bot borrowing is net-positive.

## Rules
- A metric that bots can raise by looping funds among themselves (volume, loan count, active addresses) is not an outcome metric and must not be reported as one.
- "Human" means an attested person (see Design Question 8c, 8e). The attestation method is an open question; until it is chosen, report outcome metrics 1 to 5 as "attested" and "unattested" separately.
- Every metric needs a public query or script so anyone can recompute it.

Contributions: open an issue with a query, a proposed threshold, or a way to game one of these.
