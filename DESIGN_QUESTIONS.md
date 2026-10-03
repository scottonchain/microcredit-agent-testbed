# Open design questions (for thinkers, economists and designers)

Each question is an issue-sized problem. Answer by opening an issue in this repo with the question number in the title. Short, quantitative answers beat long essays.

Context: a pool lends small amounts with no collateral, backed by vouches. Constraint set by the owner: nobody borrows unless they already have credit, or someone with credit stakes theirs. Credit must not be creatable from nothing.

1. **Roots.** Where does the first credit come from? Options: locked lender deposits, seed roots set by a timelocked multisig, an oracle (Chainlink CRE) that reports capacity. What are the failure modes of each, and which combination is safest at launch?
2. **Vouch as stake.** A vouch locks part of the voucher's capacity. How much? What is lost on a default (all of the locked amount, a share), and who gets it (lender, pool reserve)? Is the voucher paid anything when the borrower repays?
3. **Cold start.** An honest person with no history and no friends cannot get a first loan. Candidate routes: a credit-builder loan against a locked deposit, a sponsor's locked stake with a first-loan cap, a community guarantee pool. Rank them by Sybil risk and by reach to people who have no capital.
4. **Capacity growth.** How should capacity grow after repayment (linear step, multiplicative with a cap, time-weighted)? What growth rate keeps expected loss under the interest charged?
5. **Pricing.** At roughly 9.3% APR on loans up to $100, is the pool sustainable? What default rate breaks it? What reserve ratio is needed for a first deployment?
6. **Adversary model.** Define the strongest attacker we should design against (budget, number of identities, ability to bribe a rooted person). What test shows the mechanism holds against it?
7. **Measurement.** Which on-chain metrics (default rate by vouch depth, cluster concentration, capacity per root) should be public from day one?
8. **Humans first.** Participants should ideally be real people, with bots allowed. What proof-of-personhood or lightweight attestation fits without becoming a gate that excludes the people the pool is for?

Please state assumptions and show numbers.
