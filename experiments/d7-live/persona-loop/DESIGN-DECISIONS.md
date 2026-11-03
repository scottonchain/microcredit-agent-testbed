# Design decisions for the test wallet, persona loop of 2026-11-03

Operating rules from the operator (2026-11-03): every tap or click is inefficiency, keep the count as low as possible; a person never follows a step-by-step outside the app; people must be able to use it without thinking; it must work right on desktop (Windows) and on phones; Android install is one button, no instructions.

## D1. Desktop: keep it working, make it look intended, hand off to the phone with a QR code
Research (2026-11-03, two standard searches): no authoritative split of lending applications by device was found; one vendor claims 88 percent of digital lending transactions start on mobile (unverified), and 55 percent of bank customers primarily use mobile apps. Passkey readiness on desktop is high enough not to exclude it: Windows 11 about 85 percent of devices ready, Windows 10 about 70, Chrome on Windows 87, Edge 68 (Corbado benchmark, vendor data). Reading: the phone is the primary device, but a desktop visitor can complete the whole journey with Windows Hello, so the app must not refuse or shame desktop. Decision: on wide screens the app renders as a centred phone-width column inside a calm frame with a side panel "Open on your phone" (QR code of the same link) and nothing else that differs; no separate desktop link on the website, one link for all devices.

## D2. The fast path: fewest taps from the link to the money, and from the money back to a clean slate
Today's count for a first loan is about 12 taps (3 of them the phone's own passkey prompts) plus a faucet detour of 6 or more if the person follows the Receive screen. Target: link, Get started (passkey), tell the desk what you need (one screen: amount chips, purpose chips, when), Ask (passkey), Borrow $X (passkey): 5 taps plus the phone's prompts; pay back: Pay back, Pay back everything (passkey): 2 taps.

## D3. No faucet in the main path
The desk pre-funds 0.10 test USDC for the interest when it backs a person; a $5 loan held 30 days costs about 4 cents, so nobody needs the faucet to borrow and repay in the test. The Receive screen and the Help text put the faucet first today; they move behind "More" and the faucet is offered only when a person is actually short.

## D4. Install: one button, one line after
Chrome's install dialog is the one tap; after it the app says one line (where the icon is) and nothing more. The in-app-browser case keeps one sentence (open in your browser), because no page can install from inside another app.

## D5. Feedback must have a way to be sent
The Help screen's feedback card has no action today. Add one tap that opens a prepared message to the team inbox (no personal data asked).
