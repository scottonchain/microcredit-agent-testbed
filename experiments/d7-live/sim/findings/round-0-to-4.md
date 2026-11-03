# Persona simulation findings, rounds 0 to 4 (days 0 to 31, fork of the live pool)

Claude (AI), 2026-11-01. Eight personas (lender, backer, three borrowers, a first-time user, an adversary with up to five wallets, an auditor) drove passkey smart wallets through the CLI with a shared clock. Invariants (credit conservation, pool solvency) held at every audit. Nothing here is real money.

## Behaviour observed
- Lender (Kofi) lent 150 of 200 and would not add more until the board showed who backs whom. Fixed: backers per loan in `world` and `status`, and a Backing card in the app.
- Backer (Lina) kept her exposure under a self-set cap, cured nothing, and could not lower a backing until `back` accepted 0 and absolute amounts. Fixed in the CLI and the app (Change link, lower, remove).
- Borrowers repaid early or on time; the procrastinator repaid two days before due without the promised reminder. Interest on 10 USDC for 31 days was 0.08.
- First-time user (Maya) borrowed before seeing the backer's reply because the board has no notifications; she wanted the interest shown before borrowing (the app does; the CLI did not).
- Adversary (Dev): a ring of four wallets, borrow-and-vanish, deposit around repayments, early default, dust deposits and a cure all ended at or below the starting total. The only gain was faucet farming across wallets, which is outside the pool. Faucet limits per person belong to the faucet, not the pool.

## Open items for the contract repository (candidate CI notes, not fixed here)
1. A wallet with an overdue loan can still back others with its free stake and unstake free stake. Backing counts stake, so lenders are not exposed, but a backer who is about to default can still bind a third party's limit to its stake until the default slashes it. Worth a note in CREDIT_INTEGRITY_ISSUES.
2. `back` spends the backer's own history credit (dues) before stake, so a borrower-backer's small dues are consumed silently. The app now says so.

## App changes made from these rounds
Backing card with Change link; loan summary after borrowing; after-repaying summary (interest paid, credit earned, new limit); overdue wording from chain time; absolute-amount backing with lower and remove; wrapped long text; locked versus free stake in the CLI.
