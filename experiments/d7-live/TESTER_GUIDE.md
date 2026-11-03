# Omnequa test wallet: tester guide

This is a practice app on a test network. The dollars are test tokens with no value. Nothing here is a real loan, and nobody is lending you money. We are testing whether a phone app can let a person borrow a small amount against a friend's guarantee, with no wallet software, no seed words and no fees.

**Link:** https://scottonchain.github.io/microcredit-agent-testbed/ (open on your phone, in Safari or Chrome).

**Optional: put it on your home screen.** Tap **Add to home screen** on the first screen and follow the steps; afterwards it opens from its own icon like any app. On iPhone or iPad do this before step 1: a wallet created in the browser does not appear in the home-screen app (the recovery code on the Help screen moves it over; creating a second wallet there makes a separate wallet with its own test dollars). If the link opened inside another app (Messages, WhatsApp, Gmail), open it in Safari or Chrome first. If the passkey prompt does not appear in the home-screen app, go back to the browser and use the wallet there.

## What to do (about 10 minutes)
1. Tap **Create my wallet** and approve the passkey prompt (fingerprint, face or screen lock).
2. Tap **Receive / get test dollars**, copy your address, then tap **Open the faucet**. On the Circle faucet choose **Base Sepolia** and **USDC**, paste your address, request. Wait a minute and go back: your balance shows a few test dollars.
3. Tap **Ask the credit desk**. An AI credit officer answers in the app, usually within a minute: say what the money is for, how much (up to $5) and when you will pay it back. When the officer backs you, your **You can borrow up to** amount goes above zero. Nothing you write there should be personal: it is public on the test network. In this practice version the desk says yes to every proper request; it is testing the app, not you. The real app will ask seven quick questions, look at your plan and your evidence, and need a backer or a deposit before it says yes. A practice loan you paid back counts in your favour there.
4. Tap **Borrow**, pick an amount, read what you will owe, tap **Borrow** and approve with your fingerprint. The money arrives at once.
5. Tap **Send** and send a little to a friend's address, or back to the person running the test.
6. Tap **Pay back**. If you are short by the interest, get more from the faucet first (step 2), then pay back everything.
7. Optional: **Back a friend** with some of your test dollars, and see their limit rise.

## What we want to hear
- Anything that confused you: which screen, what you expected, what you saw.
- Any step that failed. The red sheet has a **Technical details** fold; copy that text.
- How long each step took, whether the passkey prompt appeared every time, and what you thought of the credit officer's questions.
- Your phone model and browser.

## What never happens
No real money. No personal data is stored by the app; your wallet lives in your passkey (details in DATA_HANDLING.md next to this guide). Your recovery code (Help screen) reopens the wallet on another phone. Remove the wallet from the Help screen when you are done; if you used both the browser and the home-screen app, remove it in each. You can stop at any time; say "stop" to the person running the test and nothing more will be sent to you.
