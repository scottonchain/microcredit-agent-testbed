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
