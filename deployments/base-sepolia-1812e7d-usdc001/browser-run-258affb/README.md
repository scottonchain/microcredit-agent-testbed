# Browser re-run on app build 258affb (allowance wait), BASE-SEPOLIA-USDC-001 (AI-run, Hermes)

App https://scottonchain.github.io/pool/ (banner: build 258affb, pool deployed from 1812e7d). Script: scripts/demo/testnet-walkthrough.mjs at contract main 258affb plus the local changes in local-script-changes.diff (logging only: page text and wallet calls when the borrow does not finish, the time the wallet got each send request and the send error if any; no change to what the app is asked to do).
Pool 0x73872B8fB7F1771C67911f03edc75aBdc9514973, USDC 0x036CbD53842c5426634e7929541eC2318f3dCF7e, chain 84532. Borrower wallet (the zero-credit one from browser-run-f116695, backed 10 USDC by Avery): 0x108450c748EEF7AeF23e64739bC508f56E596247. Amounts: lend 2, borrow 1 (smaller than the first run to save test USDC). Public RPC https://sepolia.base.org.

All files are kept, in run order; the runs were driven by a small loop that resumed a pending loan between full runs. Counts below are from these files only.

| Flow | Attempts | Second transaction sent | Notes |
| --- | --- | --- | --- |
| lend (approve, depositFunds) | run-1, run-6, run-10, run-14 | 4 of 4 | run-2 also tried lend: the approve send got HTTP 429 from the public RPC, nothing was sent (a different failure) |
| repay (approve, repayLoan) | run-4, run-9, run-13 (each after a resumed borrow) | 3 of 3 | run-5 repay-only found no active loan (loan already repaid in run-4); my mistake in running it, kept |
| borrow (requestLoan, disburseLoan), fresh | run-1, run-6, run-10, run-14 | 0 of 4 | requestLoan sent and mined each time (loans #3 to #6); the wallet was never asked for disburseLoan; the page showed "Loan requested, not yet disbursed" with Disburse and Cancel; no error text on the page; step ends after 240 s |
| borrow, Disburse button on the recovery card | run-4, run-9, run-13 | 3 of 3 | the same disburseLoan code path, clicked after a reload (first prompt rejected by the wallet in the --reject-disburse runs) |
| resumed runs without --reject-disburse | run-3, run-7, run-8, run-12, run-15 | n/a | these wait for the loan to become Active and click nothing, so they are not a test of the app; kept because they exist |

Wallet and chain at the end are in the JSON; every transaction hash is public. One wrong-network check was not repeated on this build.

What this shows and does not: the allowance wait fixed nothing it could be tested on as a failure here (lend and repay passed, but the earlier failure was intermittent, so 7 of 7 is encouraging, not proof). The borrow second step failed every time on a fresh request. The source (packages/nextjs/app/borrower/page.tsx, disburseIntent) does assertSameSigner and a simulateContract of disburseLoan right after the requestLoan receipt, with no wait; a public RPC node that has not yet seen the LoanRequested state would fail that simulation before the wallet is asked, which fits "wallet never asked, no page error shown". That is a suspicion; I did not capture the thrown error.
