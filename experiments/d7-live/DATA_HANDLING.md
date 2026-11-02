# Data handling (test wallet app)

What the app keeps on your phone: one entry in the browser's local storage holding the passkey's credential id and its public key. Nothing else. On iPhone, iPad and Mac Safari, a copy added to the home screen (or Dock) keeps its own entry, separate from the browser's: a wallet created in one is not seen in the other until you restore it there with the recovery code. The passkey is meant to be available to both copies; the operator's phone test is what confirms it. Each wallet gets its own passkey, so creating a second wallet on the same device makes a separate wallet; the first keeps its passkey and its test dollars, and its recovery code reopens it anywhere. Safari may also clear a site's storage after seven days of Safari use without visiting the site; the home-screen app is not cleared this way. Either way, save your recovery code before borrowing. The private key never leaves your phone's passkey store (Secure Enclave, Android keystore or the password manager that holds the passkey). "Remove wallet" on the Help screen deletes the entry in the copy where you tap it (if you used both the browser and the home-screen app, remove it in each); the passkey itself is removed from your phone's own settings.

What the app sends, and to whom:
- Read calls (balances, limits, loans) go to public Base Sepolia RPC endpoints (sepolia.base.org, publicnode.com, drpc.org). They see your wallet address and your IP address, as any website's host does.
- Signed operations go to a public bundler (public.pimlico.io), which puts them on the test network. It sees the operation and your IP address.
- The page itself is served by GitHub Pages, which logs requests as GitHub's privacy statement describes.

What the app never does: no account, no sign-up, no email, no phone number, no name, no cookies of its own, no analytics, no server run by us. The app has no backend. It cannot see who you are.

What is public: every transaction on the test network is public forever, under your wallet address. That includes what you write to the credit desk and what the officer answers, which is why the desk never asks for personal details. That address is not linked to you by anything in the app. Do not reuse this wallet for anything you would not want tied to it.

What the person running the test records: the feedback you choose to send. Your wallet address is visible to the credit desk when you write to it; nobody needs to be sent it. Feedback is kept in private notes, not posted anywhere with your name. Say "stop" and nothing more is sent to you.

Everything here is on a test network with tokens that have no value. No real money, no real loans.
