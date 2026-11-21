# Daily lateral run, November 21, 2026: B8 payment trace read from the public ledger and the chain

Claude Code (AI), the daily lateral-register run. Public sources only; no contact, spend, account or deployment. Second pass (rule 8, November 20): decisions first, then one counterparty-reading test.

## Decisions first (rule 1)

No lateral date fell due today. The register's next dated item is F9's December 13 repeat read. D14, D15 and D17's November 24 items belong to the directions session and the D16 lane (DIRECTIONS.md rows 37, 38, 40 and 64), not to this register. Post-merge comments on PR 491 were read: Codex closed its two findings on main at 21:03Z November 20 (comment 7050553759) and asked for nothing further.

## Receipt (B8, local-knowledge oracles sold to agents): the payment trace

**Test.** The second-pass set named B8's payment trace as the next test and assumed it needed "a lane with a wallet". It did not: the bounty board at data.vangrid.io serves its ledger and its totals from two public, unauthenticated endpoints, and the escrow contract's USDC movements are readable from Base through a public RPC. The counterparties read are the bounty buyers (104 wallets that have had a bounty accepted), the platform (Vangrid, whose contributor terms were read) and the contributors (whose payout leg this test tried to find).

**Method and limits.** `GET data.vangrid.io/api/stats` and `GET data.vangrid.io/api/bounties?limit=200&offset=N` read at about 19:55Z (1,132 rows, every row of the ledger; fields include status, amount, fee basis points, chain, buyer address, posted-by-agent, test flag and the create, accept and refund transaction hashes). Titles, briefs and buyer addresses are not kept; the committed [extract](vangrid-ledger-and-chain-trace-20261121-redacted.json) holds aggregates, the platform's own published contract and operator addresses, and sampled transaction hashes (public chain records). On Base, USDC `Transfer` logs were read from `base-rpc.publicnode.com` in 50,000-block spans (the Base public RPC and six other free endpoints refuse or cap log queries) for the escrow contract `0x66Ad8BB1c13c24a587ABD99b43F66c9D8BA15afb` and the operator wallet `0xd59fb12af112c3e55b13bdfa2a807235370e6025` (Vangrid's attester from the November 10 receipt) from block 54,357,701 (November 7, 14:31Z, by the ledger's own block-to-time pairs) to 60,503,118 (about 19:58Z today); receipts of 30 randomly sampled accept transactions (seed 20261121) and the 8 most recent were decoded through `mainnet.base.org`. Arc (chain 5042, 2 bounties) was not read: its explorer refuses this proxy.

**Ledger, August 10 to November 21 (platform-reported, confirmed on chain only where stated).**

| Item | Value |
| --- | --- |
| Bounties | 1,132 (Base 1,130, Arc 2); accepted 1,083; expired and refunded 27; cancelled 18; open 4 |
| USDC escrowed, accepted | 755,622 created; 725,076 accepted; 28,445 refunded or cancelled; 2,101 locked |
| Fee | 1,000 basis points on every bounty; contributor terms: platform 10 percent, reconstruction about 5 dollars, "the rest to the contributor" (example: 50 pays 40) |
| Accepted amount | median 405 USDC, quartiles 200 and 1,000, range 1 to 4,800; 311 of 1,132 at or above 1,000 |
| Buyers | 106 wallets, 104 with an accept; top wallet 11.4 percent of accepted USDC, top ten 33 percent; 39 wallets with ten or more accepts, 6 with one |
| Posted by agent | 1 of 1,132 (50 USDC on Arc, September 27, cancelled); the stats endpoint reports `agent_bounties` 3, the ledger flag 1 |
| Bulk orders | 24 orders, 222 items |
| Time to accept | median 6.0 hours, quartiles 4.2 and 9.3; 8.3 percent inside an hour, 93.9 percent inside a day |
| Volume by month created | August 181 (131,640 USDC); September 618 (384,920); October 251 (183,700); November 1 to 21: 82 (55,362); last 7 days 15 (10,515) |

**Chain, November 7 to 21 (primary, read-only).**

| Item | Value |
| --- | --- |
| Ledger accepts in the window | 40, 26,990 USDC |
| USDC out of the escrow | 46 transfers, 30,845 USDC: 40 to the operator wallet (26,990, every accept transaction hash matched), 6 refunds to buyer wallets (3,855), 0 to any other address |
| USDC into the operator wallet | 26,990, all from the escrow; two other senders, 0 USDC (zero-value transfers from look-alike addresses, the address-poisoning pattern) |
| USDC out of the operator wallet | 26,990 in 40 transfers to one address, 100 percent of value; 19 zero-value transfers to two look-alike addresses; 0 to any bounty buyer |
| Accept transactions decoded | 38 of 38 succeeded; each releases the full bounty amount from the escrow to the operator wallet in a single transfer; no split to a contributor, no fee transfer |

**Reading.** Three things the public record establishes. First, the board is real and busy by its own ledger: about 725,000 USDC of bounties accepted in fourteen weeks at a median of 405 USDC, with acceptance a few hours after posting and a spread across about a hundred buyer wallets. Second, the agent side of "agents pay humans" is empty here: one bounty in 1,132 was posted through the agent API and it was cancelled; every other bounty was posted from a wallet on the board, and the ledger carries nothing that marks any buyer as an agent or as independent of the platform. Third, the settlement written on chain is buyer to escrow to platform: on acceptance the escrow pays the whole bounty to Vangrid's operator wallet, which forwards every dollar to one address, and no USDC reaches a contributor from either address on Base in the fourteen days read. The contributor's payment, "Vangrid pays you the reward" in the quickstart and "the rest to the contributor" in the bounty terms, is therefore made off this chain or in another form; it cannot be read from the public record, and no realized payout to any person is observed. Two aggregates that must not be over-read: the ledger's amounts are the buyer's escrow, not the contributor's receipt (the published split would make the contributor's share about 90 percent less 5 dollars, if paid as written); and the hours-to-accept figure is a platform timestamp pair, not a measured filming time. The ledger does not establish who the buyers are, whether they are independent of the platform, or whether any contributor is in a low-income geography; the monthly decline from September is a fact of this ledger, not a market finding.

**Classification: bound.** The November 4 lead was "an agent pays a USDC bounty by one HTTP call, a person is paid money for a verified local capture, escrow released on chain". The first clause is live but unused (one cancelled attempt), the second is unobservable from the public record, and the third is true only as far as the platform. The team has no counterparty here on either side: not an agent buyer, not a contributor payout it could point a person to. B8 moves from lead to bound. Score: benefit 2 to 1 (no observed payout to a person), execute 2 to 1 (no agent demand to serve; the team posting bounties itself would be sponsor-paid demand, the B10 shape), evidence 3 unchanged (primary ledger and chain), total 12 to 10. B3's re-entry condition ("the B8 payment trace") is read and not met: the trace shows no per-person payout. Re-entry for B8: a contributor's own payout record or a Vangrid payout ledger readable by address, or the ledger's agent-posted count rising above zero accepted bounties. Recheck the stats endpoint on December 13 beside the F9 repeat read (no new timer; the existing date).

**Process note.** The November 20 set assumed this trace needed a wallet. The assumption was wrong; it cost nothing but it is recorded: before naming a prerequisite for a read, try the public endpoints first. The claim of November 4 (`claim:agent-to-human-ground-truth-rail-exists-20261104`) said the escrow pays the person on chain; today's trace is recorded as counterevidence to that clause and the claim's confidence is lowered.

## Carry-overs

- The carry-over file's "retired" list wrongly included F2 and F8 (parked since PR 491); fixed in the scratchpad file, not a repository change.
- The optional board-15 wording sweep stays optional and untouched.

## Sources

| Item | URL | Read |
| --- | --- | --- |
| Vangrid board totals endpoint | https://data.vangrid.io/api/stats | primary, read-only, 19:55Z |
| Vangrid board ledger endpoint (1,132 rows, paged) | https://data.vangrid.io/api/bounties?limit=200&offset=0 | primary, read-only, 19:55Z; redacted extract committed |
| Vangrid, Bounties (contributor terms: fee, reconstruction cost, "the rest to the contributor") | https://docs.vangrid.io/contribute/bounties.md | primary |
| Vangrid, Quickstart ("Vangrid pays you the reward") and Points and wallet | https://docs.vangrid.io/quickstart.md ; https://docs.vangrid.io/contribute/points-and-wallet.md | primary |
| Vangrid, Bounties for agents (x402 flow, minimum 50 USDC default) | https://docs.vangrid.io/api/agent-bounties.md | primary |
| Base USDC Transfer logs (escrow and operator wallet, blocks 54,357,701 to 60,503,118) | https://base-rpc.publicnode.com | primary, read-only |
| Base transaction receipts (38 accept transactions) | https://mainnet.base.org | primary, read-only |
| PR 491 post-merge thread (Codex closure 7050553759) | https://github.com/scottonchain/microcredit-agent-testbed/pull/491 | primary |
