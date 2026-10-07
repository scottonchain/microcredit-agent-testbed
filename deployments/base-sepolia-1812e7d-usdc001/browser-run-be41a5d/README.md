# One full run on app build be41a5d, BASE-SEPOLIA-USDC-001 (AI-run, Hermes)

App https://scottonchain.github.io/pool/ (fetched 2026-10-07 ~02:08Z: the home page contains the string be41a5d; the script prints "build commit be41a5d"). Script: scripts/demo/testnet-walkthrough.mjs at contract main be41a5d (detached checkout, unmodified; the only untracked file is scripts/demo/package-lock.json). Pool 0x73872B8fB7F1771C67911f03edc75aBdc9514973, USDC 0x036CbD53842c5426634e7929541eC2318f3dCF7e, chain 84532, borrower 0x108450c748EEF7AeF23e64739bC508f56E596247, lend 2, borrow 1, public RPC https://sepolia.base.org, SEND_SPACING_MS 8000. Runner script: be41.sh (it runs a --resume-pending pass first only if cast shows a loan in status 1 or 2; none did).

| Step | Result |
| --- | --- |
| open and connect | ok (build commit be41a5d, banner present, wallet connected) |
| lend 2 USDC (approve, depositFunds) | ok, two txs |
| borrow 1 USDC (requestLoan, disburseLoan) | ok, two txs, loan #17 |
| repay (approve, repayLoan) | ok, two txs, loan #17 repaid |
| withdraw 2 USDC | ok, one tx |

One run, exit 0, 0 failed steps, no 429 and no stopped-step box in the output. A fresh `cast call getLoanTerms(17)` after the run returns status 3. Not tested on this build: wrong-network, --reject-disburse. One run does not rule out the earlier intermittent failures. Note: this run did not look at the visual styling; the runner checks selectors, text and flows only.
