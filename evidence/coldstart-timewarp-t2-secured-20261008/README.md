# COLDSTART-TIMEWARP t2 (secured-stake default), local Anvil fork, synthetic time

AI disclosure: produced by hermes-agent-909 (AI agent).

- Runner: scenarios/cold-start-three-communities/run_timewarp.py (this branch), base run.py unchanged.
- Fork: Base Sepolia block 47820167 (pinned hash in expected-code-hashes.json), chain id 31337, one fresh fork, discarded afterwards.
- Path: 5 USDC lender deposit + SEPARATE 1 USDC stake(uint256); NO score published; pre-borrow assertions: score/grantedCredit/creditCommitted = 0, stakeOf = stakeCommitted = 1 USDC, getBacking = [1 USDC, 0].
- Clock: anvil_setNextBlockTimestamp + evm_mine only (2 x 30 days + 1 s), synthetic. impairLoan and markDefaulted sent permissionlessly by the treasury actor.
- Predeclared assertions (journal kinds predeclared_expectations / predeclared_assertion_results), all true: stakeOf fell exactly 1 USDC (to 0), totalStaked fell exactly 1 USDC (to 0), creditLoss == 0, firstLossReserve unchanged, totalShares unchanged, unrelated lenders unchanged, borrower defaultedLoans == 1, backing edge consumed, stakeCommitted == 0.
- Observed: totalAssets 20,000,000 before and after default (slashed stake of 1 USDC is paid into the pool as lenderCash; lenders lose nothing), firstLossReserve 0 throughout.
- A first attempt stopped at the stake tx ("Failed/missing receipt": the receipt was read once without polling); runner fixed to poll for the receipt; the evidence here is from the second, fresh fork. The first attempt's journal is not included (it stopped before any default).
- Limits: synthetic time, one operator controls all actors, 1 USDC scale, reserve was 0 so the reserve leg is NOT exercised; it does not show officer-free transitive trust or a paid-job gate.
- Note: run_timewarp.py still contains the earlier setup_staked() helper (commit ed424e3) unused by t2; t2 uses secured_setup().
