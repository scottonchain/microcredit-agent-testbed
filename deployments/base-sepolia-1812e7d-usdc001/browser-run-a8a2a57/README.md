# `--reject-disburse` x3 on app build a8a2a57, BASE-SEPOLIA-USDC-001 (AI-run, Hermes)

App https://scottonchain.github.io/pool/ (fetched 2026-10-07 ~00:30Z: home and /borrower/ pages contain the string a8a2a57; the script prints "build commit a8a2a57"). Script: scripts/demo/testnet-walkthrough.mjs at contract main a8a2a57, unmodified (checked out FETCH_HEAD of origin main; the only untracked file is scripts/demo/package-lock.json). Pool 0x73872B8fB7F1771C67911f03edc75aBdc9514973, USDC 0x036CbD53842c5426634e7929541eC2318f3dCF7e, chain 84532, borrower 0x108450c748EEF7AeF23e64739bC508f56E596247, lend 2, borrow 1, public RPC https://sepolia.base.org, SEND_SPACING_MS 8000. Runner script: rej8.sh (runs 1-3 in order, failures included).

| Run | Result |
| --- | --- |
| run-1-reject-disburse | all steps ok: lend; borrow (loan #15 requested, second prompt rejected, recovery card shown and still shown after reload, Disburse sent); repay ok (loan #15 repaid); withdraw ok |
| run-2-reject-disburse | lend ok; borrow ok (loan #16 requested, second prompt rejected, recovery card shown and after reload, disbursed); repay FAILED: the approve send got HTTP 429, nothing sent, loan #16 stayed Active; withdraw ok |
| run-3-reject-disburse | lend ok; borrow step FAILED but is NOT a test of the borrow path: the borrow button was not on the page ("Active Loan & Repayment" shown, loan #16 still Active from run 2) and the 60 s wait timed out; repay ok (loan #16 repaid); withdraw ok |

Why run 3 started with an Active loan: rej8.sh is meant to run a `--resume-pending` pass when `cast` shows an Active loan before a run. No resume pass ran between run 2 and run 3 (no run-N-resume file exists), so that check did not trigger; I did not find out why. rej8.log also holds repeated `Error: Broken pipe (os error 32)` lines from the `cast ... | head -1` calls in that check. The runner itself was not changed.

Counts from these files only: `--reject-disburse` borrow path actually exercised: 2 of 3 (runs 1, 2), both passed with the recovery card shown and kept after reload. Run 3 not a test. The a7fa809 run-5 failure ("no requestLoan transaction was sent", page never asked the wallet) did NOT recur in the 2 tests; it is not explained either, and 2 tests do not rule it out. Lend 3 of 3. Withdraw 3 of 3. Repay, both transactions sent: 2 of 3 (runs 1, 3); run 2 stopped by the 429.

**The stopped-step box on a8a2a57 (run-2 repay):** the script printed `REPAY ... ALERT BOXES` with the page text: "The repayment stopped: HTTP request failed. Status: 429 The network endpoint is limiting requests. If this says nothing was sent, wait a minute and press the button again." There is no endpoint URL and no request body in it (both were in the a7fa809 box). The console lines (429 "Failed to load resource") and the wallet calls before the stop are printed in the same .out file.

**New runner dump (cd1a2e0), seen at run-3's failed borrow step:** the page text, `ALERT BOXES: []`, and `WALLET CALLS (last 12)`. The page text shows the Active-loan state with no borrow button, which is the cause here.

Loans #15 and #16: runner lines "loan #15 repaid" (run 1) and "loan #16 repaid" (run 3); a fresh `cast call getLoanTerms` read of both ids after the runs returns status 3 for both. Custody facts (relayer HTTPS endpoint, uptime, RPC limits): none known to me; not answered here.
