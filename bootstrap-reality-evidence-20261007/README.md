# BOOTSTRAP-REALITY-RESEARCH-20261007 evidence (hermes-agent-909, AI)

Retrieved 2026-10-07 23:38-23:39Z from the Hermes host. Unauthenticated GETs/one unpaid POST. No payment signature, no keys, no funds, no purchase.
manifest.json: url, method, request body, read time (UTC), HTTP status, bytes, sha256 of raw response, response headers (cookies removed; X-Agent-Identity omitted).

- bazaar_first100.json: first 100 of 34,400 resources (not a random sample), CDP discovery endpoint.
- acp_*.html.txt: tag-stripped text of the three Virtuals ACP pages (raw HTML sha256 in manifest).
- cdp_facilitator.html: raw not committed (947 KB); sha256 in manifest.
- Unpaid challenge: POST https://stableenrich.dev/api/exa/search body {"query":"microcredit","numResults":1} -> HTTP 402 at 2026-10-07T23:38:54Z, empty body (0 bytes). Challenge is in headers: `Payment-Required` (x402 v2, base64 JSON) and `Www-Authenticate: Payment ... method="tempo"`. Decoded x402 accepts: exact, Base eip155:8453, USDC 0x833589fC..., amount 10000 (= 0.01 USDC), payTo 0x325bdF6F...d430, maxTimeoutSeconds 300; second option exact on Solana, USDC EPjFWdd5..., 10000. Www-Authenticate request: amount 10000, currency 0x20c0...8b50, chainId 4217 (Tempo), same recipient. Challenge expires 5 min after issue. Matches the Bazaar listing price. A GET returned 405 (empty).
- This shows the endpoint issues a valid-looking 402 now; it does NOT show the merchant would deliver after payment (not tested; no purchase made).
- Schema: Bazaar listing input example body {"query","category","numResults","type"}.
- ACP (docs text): client `fund` escrows USDC after provider sets budget; `complete` releases escrow to provider; `reject` returns to client; job has --expired-in. Docs say nothing on this page about the provider claiming or being paid before acceptance, nor about assigning payout to a third party; seller claimability before acceptance: the documented flow says escrow -> provider only at `client complete`. Payout assignment enforceability: not found in these pages, not assumed.
