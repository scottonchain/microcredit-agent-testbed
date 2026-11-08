# Omnequa test wallet: tester guide

This is a practice app on a test network. The dollars are test tokens with no value. Nothing here is a real loan, and nobody is lending you money. We are testing whether a phone app can let a person borrow a small amount against a friend's guarantee, with no wallet software, no seed words and no fees.

**Link:** https://omnequa.org/try/ (open the practice app from this page on your phone or desktop browser).

**Optional: put it on your home screen.** Use **Add to home screen** in the app. On iPhone or iPad, do this before creating a wallet: a wallet created in the browser does not appear in the home-screen app (the recovery code on the Help screen moves its reference over; the matching passkey is still needed). Creating a second wallet there makes a separate wallet with its own test dollars. If the link opened inside another app (Messages, WhatsApp, Gmail), open it in Safari or Chrome first. If the passkey prompt does not appear in the home-screen app, go back to the browser and use the wallet there.

## Try it in the app

The app guides you; you do not need to follow a separate setup procedure, install anything or visit a faucet. Tap **Get started** and approve the passkey prompt (fingerprint, face or screen lock). Choose an amount (up to $5), a general purpose and when you plan to pay it back. The AI credit officer checks periodically, so a reply may take about an hour or longer during interruptions; check back in the app and do not resend. Keep everything you write general: the request and replies are public on the test network.

If the desk agrees, read its offer and use the borrow button. The desk backs your test loan from its stake and supplies the few cents needed for interest; gas is sponsored. Your wallet shows what you owe and the due date. Use **Pay back** to repay; if the wallet is short, use the in-app credit-desk option shown there. You never need to fetch test dollars yourself.

**Send money**, **Receive** and **Back a friend** are optional under **More**. Sending your borrowed tokens away leaves less in your wallet for repayment, so test those separately if you want to try them. The core test is asking, borrowing and paying back in the app.

## What we want to hear
- Anything that confused you: which screen, what you expected, what you saw.
- Any step that failed. The red sheet has a **Technical details** fold; copy that text.
- How long each step took, whether the passkey prompt appeared every time, and what you thought of the credit officer's questions.
- Your phone model and browser.

## What never happens
No real money. Do not enter personal details. Your passkey controls the wallet; the browser keeps its credential id and public key, and saves your selected request options (details in DATA_HANDLING.md next to this guide). The recovery code on the Help screen restores the wallet reference on another browser where the matching passkey is available; it does not replace a lost passkey. Remove the wallet from the Help screen when you are done; if you used both the browser and the home-screen app, remove it in each. Public test-network records remain. You can stop at any time; say "stop" to the person running the test and nothing more will be sent to you.
