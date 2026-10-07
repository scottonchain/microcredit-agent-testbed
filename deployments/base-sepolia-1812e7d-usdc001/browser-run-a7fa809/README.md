# Browser run on app build a7fa809 (stopped step stays on screen), BASE-SEPOLIA-USDC-001 (AI-run, Hermes)

App https://scottonchain.github.io/pool/ (fetched 2026-10-07 ~00:06Z: home and /borrower/ pages contain the string a7fa809; the page text printed by the script says "this page was built from commit a7fa809"). Script: scripts/demo/testnet-walkthrough.mjs at contract main 1b49556, unmodified (no local diff this time). Pool 0x73872B8fB7F1771C67911f03edc75aBdc9514973, USDC 0x036CbD53842c5426634e7929541eC2318f3dCF7e, chain 84532, borrower 0x108450c748EEF7AeF23e64739bC508f56E596247, lend 2, borrow 1, public RPC https://sepolia.base.org, SEND_SPACING_MS 8000. All files kept in run order, failures included. Loop script: loop7.sh (runs 1-5), rej7.sh (run 6).

| Run | What | Result |
| --- | --- | --- |
| run-1 | full run | lend ok; fresh borrow both transactions sent (loan #12); repay: approve send got HTTP 429, nothing sent, loan stayed Active; withdraw ok |
| run-2 | full run | lend ok; borrow step not a test (borrow button not on page: loan #12 still Active, 60 s timeout); repay ok (loan #12 repaid); withdraw ok |
| run-3 | full run | lend, fresh borrow (both transactions, loan #13), repay, withdraw all ok |
| run-4-wrong-network | --wrong-network | ok: no transaction sent, wrong-network state shown |
| run-5-reject-disburse | --reject-disburse | FAILED: "no requestLoan transaction was sent" within 12 s of the borrow click; no transaction sent for borrow; lend and withdraw ok; cause not known (nothing captured: no alert box, no stopped-step text in the output) |
| run-6-reject-disburse | --reject-disburse (re-run of run 5) | ok: loan #14 requested, second prompt rejected, recovery card shown, Disburse after reload worked, repay ok, withdraw ok |

Counts from these files only: lend 5 of 5 (runs 1, 2, 3, 5, 6). Fresh borrow, both transactions sent without the recovery card: 2 of 2 (runs 1, 3); run-6 sent the request and the wallet rejected the second prompt on purpose; run-5 sent nothing (above); run-2 not a test. Repay, both transactions sent: 3 of 4 (runs 2, 3, 6); run-1 stopped by the 429; run-5 had no active loan. Withdraw: passed in runs 1, 2, 3, 5, 6.

**The new stopped-step box was seen once (run-1 repay).** The script printed `REPAY ALERT BOXES` with the page's own text: "The repayment stopped: HTTP request failed. Status: 429 URL: https://sepolia.base.org/ Request body: {...eth_sendRawTransaction..." followed by "The network endpoint is limiting requests. If ..." (the script prints the box text in run-1.out; the body in it is cut off after about 200 characters with "...", so the box carries a trimmed body, not the full signed transaction; the sentence after it says the endpoint is limiting requests). The console lines saved in the same output show the matching 429 "Failed to load resource" errors (REPAY CONSOLE). The wallet calls before the stop are in REPAY WALLET CALLS.

Not observed / not done: the stopped-step box on a borrow, a lend or a withdraw (none stopped); the run-5 failure left no explanation in the output, so a rate limit on the requestLoan send is possible but not shown. The 429 on the repay approve happened in 1 of 4 repay attempts here and 2 of 7 on a6a87b3: the public RPC limit is the same cause both times. Custody facts (relayer HTTPS endpoint, uptime, RPC limits): none known to me; not answered here.
