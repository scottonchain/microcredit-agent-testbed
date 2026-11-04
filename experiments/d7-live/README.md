# The live practice lending app

This experiment tests whether someone can ask for a small loan, understand an
offer, borrow and repay on a phone or desktop without learning wallet software,
finding gas or visiting a faucet. It is a Base Sepolia practice app: test tokens
have no value and nothing here is a real loan. Start at
[Omnequa's practice-app page](https://omnequa.org/try/). The app guides the tester;
[TESTER_GUIDE.md](TESTER_GUIDE.md) supplies context and feedback prompts.

## How the current implementation works

1. **Passkey wallet.** The browser creates a WebAuthn credential and derives a
   Coinbase smart account. It stores the credential id and public key, not a
   private key. The recovery code restores those references; signing still needs
   the matching passkey. See [app/src/core.js](app/src/core.js).
2. **Request and conversation.** The person selects amount, purpose and intended
   repayment timing, or writes to the credit desk. Messages go to the CreditDesk
   contract and are public. The officer daemon reads them and replies; it can
   back a tester from the desk's stake. This is actual backing, not credit
   manufactured by a reputation score. See [desk-daemon.mjs](desk-daemon.mjs).
3. **Borrow and repay.** The app sends signed user operations to the configured
   public bundler. A sponsor paymaster covers test gas; the desk supplies a test
   token interest buffer. The existing pool supplies principal and records the
   loan, repayment and backing. The UI reads the result from the chain. This is
   sponsored gas, not a measured borrower-paid Circle Paymaster route.
4. **Optional transfers and backing.** Send, receive and back-a-friend actions
   remain under More. Sending principal away does not cancel the debt.

[app/config.json](app/config.json) owns this app's addresses and service URLs;
[the deployment record](../../deployments/current.json) identifies the recorded
pool. A config file does not establish current service availability or balances.
The static app and the officer daemon are separate: a page that loads does not
prove the officer is answering. See [DATA_HANDLING.md](DATA_HANDLING.md) before
writing to the public desk.

## What the test must establish

Measure taps to first loan and repayment, completion without a blocking problem,
understanding of amount owed and due date, and whether anyone mistakes practice
tokens for real money. The [persona loop](persona-loop/README.md) exercises local
forks with fictional testers; it does not demonstrate real human usability or
repayment behaviour. [USABILITY.md](USABILITY.md) states the interaction rules.

The [trust interview](INTERVIEW.md) is a separate shadow assessment. Its published
score and reasons are logged beside the actual officer decision; they do not
authorize live backing. Synthetic expected outcomes do not validate credit risk.

Test-token repayment establishes mechanics, not spendable earnings, demand,
creditworthiness or sustainable lending. Count the desk's backing losses, gas
sponsorship, token prefunding and officer cost when evaluating economics. A pool
balance increase alone is not a whole-system profit measurement.

## Ownership and next gates

Maintain this app here, not in generated delivery files. The older contract
frontend remains in `microcredit-contract/packages/nextjs`; it is a different
client. Keep release and source revisions explicit rather than assuming contract
main, app branch and deployed bytecode match.

The canonical next steps, owners and permissions stay in
[D7](https://github.com/scottonchain/microcredit-agent-testbed/blob/main/coordination/directions/self-service-borrower-app.md),
[D16](https://github.com/scottonchain/microcredit-agent-testbed/blob/main/coordination/directions/human-first-mainnet.md),
[D17](https://github.com/scottonchain/microcredit-agent-testbed/blob/main/coordination/directions/whatsapp-local-currency-channel.md) and the
[world model](../../world-model/README.md). Testnet readiness does not authorize
mainnet lending. Real-money readiness also needs the lender, lawful currency
rails, consent, risk assessment and a measured human-benefit comparison.
