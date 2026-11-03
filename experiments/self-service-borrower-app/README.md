# Self-service borrower app (direction D7): arithmetic and gate 2 demonstration

Claude Code (AI), 2026-11-01. Supporting material for
[coordination/directions/self-service-borrower-app.md](../../coordination/directions/self-service-borrower-app.md),
a PROPOSED direction awaiting review. Nothing here is a deployment, a loan offer or
evidence of human benefit.

## `steady_state.py`

Break-even and growth arithmetic for a small revolving pool, plus a seeded ruin
estimate for a finite reserve under the one-fifth exposure rule. Standard library.

```bash
python3 steady_state.py --table
python3 steady_state.py --default 0.01 --lgd 1 --cost 0.02 --reserve 100
python3 -m unittest discover -s . -p 'test_*.py'
```

Every input is a labelled assumption; no live default rate or cost is measured.

## `pool_stability.py` (November 2)

Proven ruin bound (Lundberg exponent on the capped reserve process), an agent screen on
first-time applicants (sensitivity, false rejection, cost per applicant), two loan tiers with
backing shares, both scorecards (pool alone; pool plus backers' stakes), a labelled design
search across the raw default band and the power of the pilot stop rule. Standard library.

```bash
python3 pool_stability.py --recommended   # open-access and named-cohort designs, bound and simulation
python3 pool_stability.py --search        # the labelled grid, ordered by what passes the band
python3 pool_stability.py --stop-rule     # P(two defaults in twenty) by true default rate
python3 -m unittest discover -s . -p 'test_*.py'
```

Result, in one line: at the live rate the pool grows with a proven ruin bound below one in a
million when first loans are capped at 10 USDC, screened and fully backed by a named person's
stake, repeat loans at 20 USDC stay fully backed (open access) or half backed (named cohort,
one line per person), the term is 90 days and lending pauses below a quarter of the seed. The
whole system (pool plus stakes) grows only while the raw first-loan default is at most about
11%, an admitted 3.4% after the screen. Every rate is a labelled assumption until the pilot
measures it. Details in the direction document's stability section.

## `screening/` (November 3): the trust interview, documents, dossier and policy

The real screen behind [D17, the trust ladder](../../coordination/directions/trust-ladder.md) and D16
requirement 1. The practice app's credit desk approves every proper request (and says so); this
package is what decides when money is real. Standard library; the Claude extractor is opt-in.

```bash
python3 -m screening --all-examples --today 2026-11-03     # four worked cases, one line each with reasons
python3 -m screening --example mismatch --today 2026-11-03 # the full record: application, documents, dossier, decision
python3 -m screening --questions                           # the interview script the app renders
python3 -m screening.server --port 8765 --data-dir ~/private-intake --pool-record pool-record.json
python3 -m unittest test_screening                         # 28 tests; also run by tools/check.py
```

Seven taps (six multiple choice, one consent) are the whole practice interview; a real loan adds a
name, a sentence, who pays, the backer's account and up to three documents. Documents are hashed
and reduced to claims (who, how much, how often, when, in whose name) by a rule-based extractor for
labelled text or by Claude for PDFs and images, with the cost measured from token usage. The dossier
tags every statement stated, evidenced or verified and codes contradictions. The policy
(`policy.py`, version `2026-11-03.1`) has published weights summing to 100, four hard rules (no
backing, a default or open loan, a severe contradiction, and a cap at the backing, a fifth of the
reserve and the request), and reasons written as adverse-action reasons. A linked practice-desk
record (borrowed and repaid, no default) is worth 5 points and never substitutes for backing.
Records written by the server stay under `--data-dir`, outside any repository.

`--extractor claude` needs the `anthropic` package and a key; it was not run live in the authoring
session. The pool record (backer stake, borrower loans, practice record) is read by
`experiments/d7-live/pool-record.mjs` from the chain and passed as JSON.

## `demo/`: gate 2, an account with no ETH borrows, sends and repays

Node 22 and viem 2.57.14. Addresses come from `deployments/current.json`; the
Circle Paymaster address is the published Base Sepolia v0.8 one, verified by
`eth_getCode` on 2026-11-01.

```bash
cd demo && npm install
npm run dry-run          # read-only: chain, contracts, credit of a fresh account, exact calldata, bundler probe
OWNER_PRIVATE_KEY=0x... BUNDLER_URL=... npm run live   # submits user operations; see limits below
```

**Dry run (tested 2026-11-01, block 53178986):** chain 84532 answers, pool code
24,377 bytes, paymaster code 141 bytes, pool APR 933 bps, total assets 15 USDC,
utilisation 0; a fresh account shows zero credit and zero borrow limit, as it
should; the seven planned calls encode. The bundler probe failed because
`public.pimlico.io` is not allowed by the authoring session's network policy.

**Live path: untested.** It follows Circle's v0.8 quickstart (EIP-7702 simple
account, EIP-2612 permit to the paymaster, `pimlico_getUserOperationGasPrice`,
200,000 verification and 35,000 postOp gas). The authoring session held no funded
key and could not reach a bundler, so it has never been executed. Treat its first
run as a test, not a demonstration. It needs:

1. a throwaway Base Sepolia key with test USDC (Circle faucet), never committed;
2. a reachable bundler: Circle's quickstart uses the keyless
   `https://public.pimlico.io/v2/84532/rpc`; `api.pimlico.io` requires an API key;
3. no ETH at all, which is the point: every step's gas is paid in USDC through the
   paymaster, 10% surcharge.

Steward condition (2026-11-01): no session runs the live path with a funded key it holds; a fork rehearsal and a headless passkey test come first, then a run by an independent operator with their own throwaway key.

The demo stakes the account's own USDC to open its first loan, so it proves the
plumbing (no wallet software, no ETH, borrow, send, repay) and nothing about
creditworthiness, demand or benefit. `passkey_probe.cjs` shows the passkey primitive working headlessly (P-256 create and
sign through the virtual authenticator against a localhost page, 2026-11-01). Wiring it
to an account is the next step and is not in `demo.mjs`: either Circle Modular Wallets (Console client key and passkey
domain) or a WebAuthn P-256 signer on an account that validates it, exercised
headlessly with Playwright's virtual authenticator before any person is asked.
