# Browser run of the released app, BASE-SEPOLIA-USDC-001 (AI-run, Hermes)

App https://scottonchain.github.io/pool/ built from f116695 (banner: deployed commit 1812e7d). Script scripts/demo/testnet-walkthrough.mjs from branch claude/dreamy-ramanujan-32oscs at f116695, plus the local changes in local-script-changes.diff (Chromium launch path and --no-sandbox, connect-button selector, borrower-tx filtering, --resume-pending/--repay-only/--withdraw-only/--skip-back flags, repay button selector `Pay`, failure dumps).
Pool 0x73872B8fB7F1771C67911f03edc75aBdc9514973, USDC 0x036CbD53842c5426634e7929541eC2318f3dCF7e, chain 84532.
Borrower wallet (fresh, zero granted credit, funded 25 USDC + 0.003 ETH): 0x108450c748EEF7AeF23e64739bC508f56E596247. Backer: Avery 0xc5E42B0fB0c109E55f4A40CccfCF3fed1Fc39009.
The first wallet 0x4e23411897B1c2BC31e3db03e074c370596Cd4E6 only served attempt a1 (connect failed before any transaction) and a first full run that backed it; its 25 USDC were moved to the fresh wallet. Files are in the order the steps were run; failed attempts are kept. JSON holds addresses, hashes, balances only (scanned for the key files: none).
