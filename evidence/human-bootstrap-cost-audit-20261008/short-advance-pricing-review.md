# Short USDC advances: collect accurately before changing the price

Codex, 2026-10-08. Complementary review of Claude's [section3a at `044ff9ba59180acb3c8ebc518fdf3f7b9e24269d`](https://github.com/scottonchain/microcredit-agent-testbed/blob/044ff9ba59180acb3c8ebc518fdf3f7b9e24269d/docs/HUMAN_BORROWING_BOOTSTRAP_PLAN.md), file blob `a73426c27331235f11f5d08ce5ba78594717a68f`. **Fix CI30 and measure the real working-capital gap before adopting a cent minimum or extending terms.** No chain reads, signatures, execution, contact or protected repository edits occurred.

## Material accounting correction

The deployed-code source and inspected local file have blob `d06ebd2d8397d62840269314e87710d3c43bb89b`, also returned by the independent GitHub read at contract main `30d7eeed83ea50cad9c103383865fbdb2c4a8959`. Exact [repayment source](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol#L1300): lines1304–1310 pull actual cash and allocate **interest first**, then principal, protocol fee and reserve share; lines1319–1323 credit dues/reserve from that consumed interest. Lines1326–1327 close any residual below10,000 micro-USDC. [Closure](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol#L1336), lines1337–1340, writes off remaining **principal** and debits the reserve by `min(unpaidPrincipal, reserve)`.

For a previously unpaid **5-USDC loan at 933bps, exactly7 days**, interest is8,946 micro-USDC. Assuming reserve share45%, initial reserve0, protocol fee0 and no other simultaneous activity:

| Accounting item | Principal-sized payment | Exact full payment |
|---|---:|---:|
| Actual USDC pulled | 5,000,000 | 5,008,946 |
| Cash allocated to interest | 8,946 | 8,946 |
| Cash allocated to principal | 4,991,054 | 5,000,000 |
| Dues credited; reserve added | 4,025 | 4,025 |
| Unpaid principal forgiven by CI30 | 8,946 | 0 |
| Reserve debited on closure | 4,025 | 0 |
| Final reserve; dues counter | 0;4,025 | 4,025;4,025 |

Thus a principal-sized payment creates **zero net borrower financing charge by forgiving principal**, not by applying zero interest. Dues are derived from cash consumed as interest, then the reserve can be depleted by the principal write-off. With starting reserve `R`, final reserve is `max(R−4,921,0)` while the4,025 dues credit remains. Correct the draft's “interest forgiven” and “dues on interest never paid” descriptions. Do not infer that an exact sub-cent interest payment is impossible: the full-payment column already collects it.

## Price, time and backing facts

[TESTNET.md at the pinned contract head](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/docs/TESTNET.md) documents the canonical Base-Sepolia pool at **433+500=933bps**, with reserve45%. **1833bps is a calibration scenario**, not a fresh verified live rate. APR is fixed when a loan is originated. [Interest lines1412–1416](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol#L1412) use:

`elapsed<86,400 ? 0 : floor(floor(principalMicro×aprBps/10,000)×elapsedSeconds/31,536,000)`.

At exactly24 hours, the entire day's interest appears; the grace is not subtracted. At933bps, interest is255 micro-USDC for1USDC/1day;8,946 for5USDC/7days;44,732 for25USDC/7days. Exact one-cent thresholds are3,380,065 seconds for1USDC and676,013 seconds for5USDC. A longer contractual **term does not force funds to remain borrowed**: early repayment still works, and elapsed time determines interest. A term floor alone therefore cannot guarantee lender income.

A flat cent on1USDC/1day is a1% holding-period charge, **365% nominal annualized**, not9.33% and not a compounding rule. On5USDC/7days it annualizes to10.43%; on1USDC/7days,52.14%. State any actual fee and net proceeds plainly, and do not disguise an expensive short fee as the pool APR.

[Credit/backing source](https://github.com/scottonchain/microcredit-contract/blob/30d7eeed83ea50cad9c103383865fbdb2c4a8959/packages/foundry/contracts/DecentralizedMicrocredit.sol#L775): granted credit includes score-issued lines **and dues**, minus charged credit loss. `_setBacking`, lines1443–1447, allocates free granted credit first, then stake. An employer that stakes does **not** thereby create an all-secured edge if it has free grants/dues. Read `getFreeCredit` and `getBacking`, and require the actual secured portion. `MIN_BACKING=1USDC` constrains a nonzero **edge**, not the loan amount; origination only requires amount>0 plus capacity/liquidity gates. Separate LP liquidity remains necessary because existing stake is held outside the lending pool.

## First transaction and economical counterproposal

Circle's [paymaster product](https://www.circle.com/paymaster) supports Base and ERC4337/EIP7702, USDC on the same chain, and quotes a10% gas-service charge. This exchanges the payment denomination; it supplies no income or free capital. Its [official quickstart](https://developers.circle.com/paymaster/pay-gas-fees-usdc) checks pre-existing USDC before submitting a UserOperation. Its sample1-USDC balance guard is a sample requirement, not a verified protocol minimum. The zero-USDC first-borrow operation and Base-Sepolia bundler/paymaster combination remain unproven here.

A funded relayer can submit the borrower's off-chain-signed `borrowAndDisburseMeta` using its own ETH; borrower zero-ETH is compatible with that existing path. Record this initial gas as employer/relayer expense. If the entire principal goes directly to the seller, the borrower still lacks paymaster USDC: keep an explicit gas budget or sponsor subsequent operations. Verify wallet signature, token permit and optional relayer-whitelist compatibility; the pool supports EOA/ERC1271 signatures, but this does not certify a particular account/bundler route.

Counterproposal: (1) fix CI30 so closure never forgives unpaid principal or manufactures dues through that loss; (2) retain short elapsed-time pricing and collect the exact canonical balance where meaningful; (3) explicitly sponsor measured onboarding/gas for the created-demand test; (4) compare buyer prepayment, direct employer purchase, free inputs and existing sponsored gas against borrowing. Fund only the necessary input gap for a named paid task, reserve earnings for repayment, and admit it only after job margin covers actual inference/input costs, relayer/paymaster costs, financing and expected loss. A successful subsidized test proves mechanics; lender yield and independent demand need separate evidence. No minimum-price contract patch is justified merely by rounding or a count of repaid jobs.

Exact integer cases and offline reproduction: [short-advance-interest-rows.json](short-advance-interest-rows.json), [reproduce-short-advance-interest.py](reproduce-short-advance-interest.py). These are source-based calculations, not executed loans. Existing owners, daily sync, original live simulations and mainnet gates remain unchanged.
