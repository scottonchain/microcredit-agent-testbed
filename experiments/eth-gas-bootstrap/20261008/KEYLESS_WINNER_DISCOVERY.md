# Keyless winner discovery for Hermes

2026-10-08. Source inspection, not a live Goldsky response or claim execution.

Official workflow endpoint reported by root from fresh `pt-v5-winners` clone
commit `6a16853aaa738482b4e0f2833f0c9bff87c01441`:
`https://api.goldsky.com/api/public/project_cm3xb1e8iup5601yx9mt5caat/subgraphs/pt-v5-base/v0.0.1/gn`

Use read-only GraphQL POST, no key. Probe metadata first (record schema error if
unsupported, not “no accounts”):

```graphql
query Probe {
  _meta { block { number hash } hasIndexingErrors }
  prizeVaults(first: 100) { id }
}
```

Exact account fields and nested filter are from official pt-v5-utils-js source
commit `395efd98a3426eec139f82bba592e54bec103b74`,
`src/utils/getSubgraphPrizeVaults.ts` (blob
`9d7e17521a9724a66ca3fb3ae10f1b5a44305ec7`). Added explicit stable ordering:

```graphql
query Accounts($first: Int!, $lastId: String, $prizeVaultAddress: String!) {
  accounts(first: $first, orderBy: id, orderDirection: asc,
    where: { id_gt: $lastId, prizeVault_: { id: $prizeVaultAddress } }) {
    id
    user { address }
  }
}
```

Variables: `first=100`, `lastId=""`,
`prizeVaultAddress="0x7f5c2b379b88499ac2b997db583f8079503f25b9"`.
Page using last returned id, stop at fewer than 100 results. Do not skip zero
current balances: historical TWABs can matter. For a bounded immediate subset,
record how many pages/users examined; absence there is not global absence.

Claims query fields are from official `src/utils/getSubgraphClaimedPrizes.ts`,
same repo commit, blob `4110cb286efcbdbfb461122839845d5d5067bc23`:

```graphql
query Claims($id: String!) {
  draw(id: $id) {
    id
    prizeClaims(first: 100) { id payout fee timestamp }
  }
}
```

`id="841"` only after fresh RPC agrees; this is already-claimed history, not
unclaimed winners. Onchain `wasClaimed` is authoritative before submission.

For fresh winners, direct library `@generationsoftware/js-winner-calc` version
**1.3.1** is inspected; “2.1.1” is archived CLI version, not this library.
Official code commit `442688d182bc7dba100c729530d3f3db5fd336d1`, `src/index.ts`
blob `dddf9e06d48dcf8bd630d8da8c9f424c90b45460`:

```js
import { computeWinners } from '@generationsoftware/js-winner-calc';
const winners = await computeWinners({
  chainId: 8453, rpcUrl: approvedRpcUrl,
  prizePoolAddress: '0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb',
  vaultAddress: '0x7f5c2b379b88499ac2b997db583f8079503f25b9',
  userAddresses, prizeTiers: [5,6],
  blockNumber: freshBlockNumberBigInt,
  multicallBatchSize: 2048, accountTwabBatchSize: 128, debug: false
});
```

No subgraph dependency inside computeWinners once address inventory exists.
Tier array [5,6] corresponds to the last two tiers ONLY if fresh RPC confirms
seven tiers; otherwise derive tiers from current numberOfTiers.
Important source caveat: library getVaultPortion call does not forward
blockNumber in inspected index.ts, so do not claim every constituent RPC read
was pinned without fixing/recording the call or examining the helper. Fresh
onchain `isWinner`, `wasClaimed`, hook checks and exact call simulation must
confirm candidate regardless of calculator output.

Fallback inventory already fetched without a key:
`historical-draw735-vault-seed.json` in this same directory, 1104 userAddresses,
79,152 bytes, SHA256
`9bcc535bff6cfcf212c9355351541e353862606f3c4ee4c5fa2583635dc0dd0c`.
This is **historical accounts, not current winners**. Incomplete for new users;
may be useful for a finite current computation while indexer access is checked.

Official current frontend archived URL pattern for draw841 returned 404 both
through GitHub connector and public web:
`https://raw.githubusercontent.com/GenerationSoftware/pt-v5-winners/main/winners/vaultAccounts/8453/0x45b2010d8a4f08b53c9fa7544c51dfd9733732cb/draw/841/winners.json`

Both draw-results-mainnet (Feb18,2025) and pt-v5-winners (June25,2026) are
archived. Use artifacts as inputs/metadata, never as current availability.
