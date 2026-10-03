# Human-benefit metrics

Purpose of the pool: reduce human poverty and suffering. Bots may be lenders, attesters, reputation roots and borrowers, even a majority of participants. These metrics exist so that bot activity can never stand in for human outcomes. Proposed for publication from day one (computed from on-chain events plus an off-chain attestation set).

## Outcome metrics (what we are trying to move)
1. **Unique repaying human borrowers**: distinct attested-person borrowers with at least one fully repaid loan. Headline number.
2. **First-time borrower share**: fraction of newly disbursed principal going to borrowers with no prior loan.
3. **Capacity reaching people with no capital**: share of total borrowing capacity held by accounts whose own locked stake is zero (capacity that came from vouches, sponsors or a guarantee pool).
4. **Repayment rate by cohort**: on-time and eventual repayment for human first loans vs bot loans, split by vouch depth.
5. **Loan size vs local income** (needs an off-chain attestation): principal as a share of the borrower's monthly income band.

## Integrity metrics (what we are trying not to break)
6. **Root concentration**: largest single root's share of total capacity, and Gini across roots. Target cap per root to be set by Design Question 8a.
7. **Cluster concentration**: share of capacity inside the largest strongly connected vouch cluster with no external stake.
8. **Bot-borrower crowd-out**: bot share of outstanding principal vs share of total capacity. Alarm if bots drain capacity people could use.
9. **Credit manufactured without stake**: sum of capacity not traceable to locked deposits or slashable roots. Target: 0 (invariant, not a metric to optimise).
10. **Net pool yield after defaults**, with and without bot liquidity, to show whether bot borrowing is net-positive.

## Rules
- A metric that bots can raise by looping funds among themselves (volume, loan count, active addresses) is not an outcome metric and must not be reported as one.
- "Human" means an attested person (see Design Question 8c, 8e). The attestation method is an open question; until it is chosen, report outcome metrics 1 to 5 as "attested" and "unattested" separately.
- Every metric needs a public query or script so anyone can recompute it.

Contributions: open an issue with a query, a proposed threshold, or a way to game one of these.
