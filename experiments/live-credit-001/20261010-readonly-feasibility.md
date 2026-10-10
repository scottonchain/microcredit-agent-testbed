# LIVE-CREDIT-001: read-only feasibility on the deployed pool (2026-10-10)

Author: Claude Code (AI agent), contract lead, for board #15 comment 6102756409.
Scope: items 1, 3 (contract side) and 4. Every value below comes from public RPC
reads on Base Sepolia. No transaction was sent, no key was used and nothing was spent.
Hermes owns item 2 (one consenting outside agent with a paid job). This is a plan for
review, not an authorization: the officer, G3 and public-execution gates still stand.

## 1. The record matches the chain

Reads at block 47951258 (pool_health) and 47951292 (role and parameter reads).

| Check | Result |
| --- | --- |
| Chain id at `https://sepolia.base.org` | 84532, matching `deployments/current.json` |
| Pool `0x73872B8f…4973` wiring | `usdc()` = `0x036CbD53…CF7e` (Circle test USDC); `scoreProvider()` = `0x554c6bB6…05e4`; `paused()` false |
| Roles | pool owner, oracle and guardian, and provider owner and reporter: all `0x5e4dC763…48F9` (the Hermes deployment key in `deployments/base-sepolia-1812e7d-usdc001/README.md`) |
| Source | contract `1812e7d` (on `main`). Its ABI and source define every function used below. |
| Pool state (`metrics/pool_health.py`) | assets 15.00, cash 15.00, lent 0, reserved 0, staked 0, 8 lenders, APR 933 bps (EFFR 433 + premium 500); credit integrity holds (sum of limits 97.00 = granted 97.00) |
| Loans | 24 ids: 23 Repaid, 1 Cancelled, none open |
| Issued lines | 3 scored accounts: Avery (team persona) 0.92 (92 USDC), `0x7954…C96e` 0, the issue-2 newcomer 0.05 (5 USDC); `maxLoanAmount` 100 USDC |
| Score freshness | last report 2026-10-08 21:34:50 UTC; `maxScoreAge` 7 days, so **every issued line reads 0 after 2026-10-15 21:34:50 UTC** unless the reporter publishes again |
| Headroom for one new loan | utilisation cap 90% of 15.00 = 13.50; liquidity buffer 5% leaves 14.25; so at most **13.50 USDC** of new principal right now |

## 2. An outside agent has already borrowed and repaid on this pool

The outside newcomer of testbed issue 2 (`0x9ecdaae8…af04`) holds a 5 USDC issued
line, published by the reporter at 2026-10-08 21:34:50 UTC. Loan 24:

| Step | Transaction | Block |
| --- | --- | --- |
| `requestLoan(5 USDC)` | `0x7b0524a2d1eb2acc495771227d123c4640d149f5bf60e8eb45e5f9db19d64ca2` | 47902409 |
| `disburseLoan(24)` | `0x8282a4406c66dbf7692881d9864c5fe90d8489e2f85b57ced4e2ebaabdb1f7f0` | 47902411 |
| `repayLoan` (status now Repaid) | `0x35a959af3a05474c724e9ae3d3661a34257579cde9fffebfe851aa86cd4a9bd0` | 47902417 |

The borrower posted these hashes on issue 2. Repayment came six blocks after
disbursement, inside the interest-free first day, from the borrower's own test USDC.
The mechanics therefore work end to end for an outside agent. Not shown: a job,
a buyer, income, or repayment from earnings. The borrower now holds 0.0200 ETH and
20.00 test USDC, and its line has 5.00 USDC available.

## 3. Routes to a credit line on the deployed contract

`getBorrowLimit` = (issued credit − credit committed to others) + backing received.
`requestLoan` needs: not paused, no default, limit > 0, amount ≤ available, and the
utilisation and liquidity checks above. There is no KYC or officer check on-chain.

| Route | Who acts | Calls | Notes |
| --- | --- | --- | --- |
| A. Issued line | the reporter key (Hermes) | `publishScores(abi.encode(epoch+1, [borrower], [score]))` | Only listed accounts change; score = amount / 100 USDC (5 USDC = 50000). Refreshes every line's 7-day clock. Already used for the newcomer. A team decision and a gas spend. |
| B. Secured backing | any third party, such as the job buyer | `USDC.approve(pool, x)`, `stake(x)`, `back(borrower, x)` | No team role. At least 1 USDC. The stake is slashed into the pool on default. A buyer who will stake could usually just prepay, so compare the two first. |
| C. Score override | pool owner (same key) | `setScoreOverride` | Admin path; not proposed. |

## 4. Minimal end-to-end plan (draft for review; nothing here is authorized)

For borrower `B` (Hermes's consenting outside agent), buyer `J`, job `X`, amount `a`
(at most the headroom, and at most what `X` actually needs up front):

0. **Gates, before any transaction.** `X` has a named buyer, price, deliverable and
   due date, and `B` consents. Compare the loan against prepayment by `J`, direct
   funding and no loan; record `NO_LOAN` if prepayment works. A one-use, exact-job
   officer approval for (`B`, `X`, `a`) is recorded under the operator's dual-gate
   direction, and the operator authorizes the public-chain execution.
1. **Read-only preflight** (cast, no gas): `paused()` false, `isFresh()` true with at
   least the job's duration left, `getBorrowLimit(B)`, headroom ≥ `a`, `B`'s ETH ≥ gas
   for four transactions.
2. **Line.** Route A: the reporter publishes `B`'s score `a`/100 USDC (Hermes, gas).
   Or route B: `J` stakes `a` and backs `B` (J's gas and USDC).
3. **Borrow.** `B`: `requestLoan(a)`, then `disburseLoan(id)` (anyone may call it).
   Receipt: both hashes and the `LoanRequested` event.
4. **Work and payment.** `B` delivers `X`; `J` pays `B` (an onchain USDC transfer
   gives a receipt; an offchain payment needs J's confirmation).
5. **Repay from that income.** `B`: `USDC.approve(pool, owed)`, then
   `repayLoan(id, getCurrentOutstandingAmount(id))`. Five USDC for 30 days at 933 bps
   is about 0.04 USDC of interest, and none in the first day.
6. **Close and record.** `getLoanTerms(id)` status 3 (Repaid); `completedLoans(B)`
   up by one; for route B, `J` lowers its backing to 0 and unstakes. Publish the hashes
   with the job receipt. A repayment counts as job-funded only if a traceable payment
   from `J` precedes it.

Who supplies what: lenders' 15 USDC funds the principal; `B` pays its own gas (the
newcomer already holds enough), or a team relayer submits meta-transactions; the
reporter's gas or `J`'s stake and gas supply the line; `J` supplies the income.

## 5. Blockers and deadlines

- No borrower with a paid job is identified yet (Hermes, item 2). Without one this
  repeats loan 24 and proves nothing new.
- The officer approval and public execution need the operator's authorization; this
  report grants neither.
- Issued lines lapse at 2026-10-15 21:34:50 UTC. A plan using route A after that
  needs a new report, which is a reporter transaction.
- Headroom is 13.50 USDC; a larger job needs more lender cash first.

## Reproduce

```bash
python3 metrics/pool_health.py                 # needs Foundry's cast on PATH
R=https://sepolia.base.org; P=0x73872B8fB7F1771C67911f03edc75aBdc9514973
cast call --rpc-url $R $P "getLoanTerms(uint256)(uint8,uint256,uint256,uint256,uint256)" 24
cast call --rpc-url $R $P "getBorrowLimit(address)(uint256,uint256)" 0x9ecdaae8635f06a26cd27f686697e97aa293af04
cast call --rpc-url $R 0x554c6bB61eDF0CAfB90ff31813540369Cb0105e4 "getScores()(address[],uint256[])"
cast call --rpc-url $R 0x554c6bB61eDF0CAfB90ff31813540369Cb0105e4 "lastReportAt()(uint256)"
```
