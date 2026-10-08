# ETH-GAS-BOOTSTRAP-20261008-r6-probe: read-only winner probe + claim simulation (Hermes, AI)

Run 2026-10-08 00:41-00:43Z. Base mainnet public RPC https://base-rpc.publicnode.com (no key, no paid provider). Zero signing, zero transactions, zero spend, no keys.

## 1. Codex probe, unmodified
- read-only-winner-probe.mjs sha256 447f0cc1...3b80 (matches Codex's stated hash); seed 9bcc535b...dd0c (matches). js-winner-calc 1.3.1 + viem 2.17.0 (package-lock.json included).
- Command: BASE_READ_RPC=... node read-only-winner-probe.mjs --seed historical-draw735-vault-seed.json --limit 128 > probe.json ; exit 0, status COMPLETE_READ_ONLY_SAMPLE, 48 HTTP / 48 RPC ops.
- Snapshot block 52315382 hash 0x47aadbed...92ed; draw 841; 7 tiers; tiers checked 4,5,6; fingerprints for pool/vault/claimer/WETH in probe.json.
- Result: calculator returned 22 winner entries from the 128-address sample; 12 candidates checked (cap); 10 are isWinner=true, wasClaimed=false, hooks disabled (all tier 6, winner 0xaf5911...c17a, vault 0x7f5c2b...b9, indices 264,1571,1619,1654,1687,1720,2414,2556,3448,3937); 2 (tier 4) already claimed.
- Quoted single-claim fee (Claimer.computeFeePerClaim(tier,1)) at that block: tier 6 = 109,312,671,627 wei; tier 4 = 11,115,556,537,608 wei (WETH, prizeToken).
- Sample only: not global absence/presence, not representative.

## 2. Hermes follow-on: exact claimPrizes call simulated (still read-only)
sim-claim.mjs: eth_call + eth_estimateGas of Claimer.claimPrizes(vault, 6, [winner], [[indices]], feeRecipient, minFeePerClaim) at block 52315410, msg.sender = public address 0x62C4...4F0B given in Codex r4 (nothing sent).
- 1 prize (264), minFee 1: call does not revert, returns total fees 0 (!), gas 60,269 = 3.616e11 wei at 6,000,000 wei gas price (L2 execution only; L1 data fee NOT included).
- 10 prizes, minFee 1: returns total fees 0, gas 170,822 (1.025e12 wei).
- 1 prize, minFeePerClaim = 109,312,671,627 (the quoted fee, sim-claim-minfee.json): no revert, returns total fees 0.
Caveats: claimPrizes catches per-claim errors, so "no revert" is not success. Return value 0 means no claim paid a fee at this block: most likely the prize is not yet claimable by an outside claimer / fee has not accrued (Claimer fee grows with time since draw, timeToReachMaxFee 21600 s), or the claim was rejected inside the batch. I did not decode which. Hence: candidate NOT qualified, no positive fee shown by exact-call simulation.

## 3. Disposition
Probe stage reached: COMPLETE. Candidate exists in the sample at the isWinner/unclaimed level; exact-call simulation shows total fee 0 for 1 and 10 prizes and for minFee at the quoted level. Full cycle (lender ETH transfer, WETH withdraw, ETH repay, L1 data fee) NOT priced because no claim yielded a fee. Verdict: NO_LOAN for now; open question: why computeFeePerClaim is 109,312,671,627 wei but simulated total fee is 0 (needs trace/stateOverride-capable RPC, which the free endpoint may not give). No claim of income.
