# Browser re-run on app build a6a87b3 (wait for the loan to be visible), BASE-SEPOLIA-USDC-001 (AI-run, Hermes)

App https://scottonchain.github.io/pool/ (fetched 2026-10-06 23:42Z: both the home and /borrower/ pages contain the string a6a87b3; I did not read the banner text itself). Script: scripts/demo/testnet-walkthrough.mjs at contract main 258affb plus the local changes in local-script-changes.diff (flags and logging only; the script is not changed between 258affb and a6a87b3). The app is the live site; the pool is unchanged.
Pool 0x73872B8fB7F1771C67911f03edc75aBdc9514973, USDC 0x036CbD53842c5426634e7929541eC2318f3dCF7e, chain 84532. Borrower wallet 0x108450c748EEF7AeF23e64739bC508f56E596247. Amounts: lend 2, borrow 1. Public RPC https://sepolia.base.org. Runs 1 to 6 are full runs (lend, borrow, repay, withdraw) from a loop; run-7 is a repay-only run I started by hand to finish loan #11. All files kept, failures included.

| Flow | Attempts | Both transactions sent | Notes |
| --- | --- | --- | --- |
| lend (approve, depositFunds) | run-1 to run-6 | 6 of 6 | |
| borrow (requestLoan, disburseLoan), fresh | run-1, 2, 3, 4, 6 | 5 of 5 | loans #7 to #11 requested and disbursed by the wallet without the recovery card |
| borrow, run-5 | n/a | not a test | the borrow button was not on the page because loan #10 was still Active (run-4's repay failed, below); step timed out at 60 s |
| repay (approve, repayLoan) | run-1, 2, 3, 5, 7 passed | 5 of 7 | run-4 and run-6: the approve send got HTTP 429 from the public RPC (SEND FAILED in the .out file), nothing was sent, the loan stayed Active; run-5 and run-7 repaid those loans afterwards |
| withdraw | runs 1-6 | each run's withdraw step passed (see JSON) | |

Not observed: the amber stopped-step box (no borrow stopped on this build, so there was nothing to save). Console errors were not captured by the script; the page text and wallet calls are logged where a step failed. Not done: the wrong-network check on this build and a --reject-disburse run.

Reading: on this build the fresh borrow sent both transactions in 5 of 5 where 258affb sent the second in 0 of 4. Five of five is a clear change from 0 of 4, not proof of every case; the failures that did occur were public-RPC rate limits on the repay approve.
