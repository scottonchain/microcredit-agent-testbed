# Test-USDC reconciliation, 2026-11-04

Claude (AI), read-only, answering the board request x-20261104-test-usdc-reconciliation-r1 (testbed issue 15, comment 6636390982) and the operator's follow-ups of 16:50 and 17:01 UTC. Test tokens only. Every number is from public RPC reads on 2026-11-04 at the block named below; no key was used, nothing was signed or sent, no transfer or recovery was attempted. A failed read is reported as unknown, never as zero.

Wallet: `0x38e9845A1Df22c59Bfc693bf2CEAa3361158d6d1` (the root and funding wallet of the October 13 cold-start run; `bridge-verified.json` names it).

## Result in one paragraph

Nothing is lost on the evidence. The 2,000 test USDC arrived on Ethereum Sepolia in October (2,020 with a 20 faucet drop); 1,000 was bridged to Base Sepolia; the other 1,020 is still in the root wallet on Ethereum Sepolia today. Of the 1,000 on Base, 819.8 went to the cold-start roles, 50.0 went to project infrastructure wallets after the run, and 130.2 is still in the root wallet. The roles were never swept: 799.22 sits in 98 wallets exactly as the run left it, and 20.58 sits in the GuaranteeTrust contract.

## Base Sepolia (chain 84532), block 54454080, token `0x036CbD53842c5426634e7929541eC2318f3dCF7e`

| Step | Test USDC | Evidence |
| --- | ---: | --- |
| Minted to the root by CCTP, block 48059142 | +1,000.0 | tx `0x91db8f0a9784fab6756f0825adee79b83fabf0fca7bb2e87af009e267ae92637` |
| Sent to the 98 role wallets (58 transfers) | -819.8 | `root-usdc-transfers-base-sepolia.json` |
| Sent after the run to the sim treasury `0x2aA4069f65931E8b35Ed11aC493b1C3Ab9917212`: 25.0 at block 53608783 (tx `0x0f50e465c7c1fe06ac097fb20fb6b3469e13be20ad01a5a24b08422dd32b2658`) and 20.0 at block 54442771 (tx `0x5db5c2e1b3c2d1a69f406570b77669878a88efe00f660683f49ef1af79b4207b`) | -45.0 | same file |
| Sent after the run to the desk officer `0xb88DC88d538a754f57cAB344C1E09d02C129fcf2`, block 53608900 (tx `0xcd36fc917d36b3dfb3061a51a98319b13f087f2490fad9a03bfc991b7aafa5cc`) | -5.0 | same file |
| Root balance now | 130.2 | `balances-base-sepolia.json`; 1,000 - 819.8 - 50.0 = 130.2 |

No Transfer to the root since the mint (scan of blocks 48059142 to 54454080 in 50,000-block ranges, 0 failed ranges). So there was no sweep and no recovery: the roles still hold what the run left.

Where the 819.8 sits now (block 54454080, 100 addresses read, 0 failed):

| Place | Test USDC | Note |
| --- | ---: | --- |
| 98 role wallets | 799.22 | identical to the committed `role-balances.json` of run 20261013-run1 for every wallet (0 differences); 78 hold USDC, 20 hold none |
| GuaranteeTrust `0x7eD9B2B67E598fd2a1f384CC885c0C860bfD0466` | 20.58 | equals the run's terminal token balance (reserve 15.59 + stake 4.99) |
| Sum | 819.8 | 799.22 + 20.58 |

Gas. The 98 role wallets hold 0.004467 ETH in total (largest 0.00008; of the 78 USDC-holding wallets, 58 hold some ETH and 20 hold none). Those 20 wallets hold 264.92 of the 799.22 and cannot send a transaction themselves. The root holds 0.0248 ETH on Base Sepolia.

## Ethereum Sepolia (chain 11155111), token `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238`, head block 12063857

| Fact | Evidence |
| --- | --- |
| 2,000.0 test USDC arrived at the root in block 11904612 from `0x75c0c372da875a4fc78e8a37f58618a6d18904e8` | tx `0x54f39df5027c084129c5060c06b028ab2719eb666871348fca4e6698a4ff86b0` |
| 20.0 arrived in block 11901343 from `0x3c3380cdfb94dfeeaa41cad9f58254ae380d752d` | tx `0x1a51b1923a1123a9bcbb3b2cce4f3bdd8594d6d34df3c012cb4e4d542ec707e3` |
| Sum 2,020.0 equals `before.sourceUSDC` in `bridge-verified.json` | |
| 1,000 was burned for the bridge (receipt status 1, block 11905319) | burn tx `0xe0083d59...dd98` |
| Balance now: 1,020.0 test USDC, 0.1472 ETH | `balanceOf` and `getBalance` at the head |
| Nonce now: 3 = the three transactions the bridge record lists (bridge-test-ETH, approve-CCTP, burn-CCTP) | `eth_getTransactionCount` |

So the "other 1,000" was never sent anywhere: it is still in the root wallet on Ethereum Sepolia. Unknown: the node prunes old history, so four inflow ranges (11523000 to 11572999, 11773000 to 11822999, 11923000 to 12022999) and one outflow range (11873000 to 11922999, which contains the burn) were unreadable in a log scan. The facts above do not depend on them: the balance and nonce are current-state reads, and the two inflows were found.

## Custody and control (nonsecret)

- The cold-start script derives every role key from the root key and the role id (`coldstart.mjs`, line 289: `keccak256("circle-coldstart-v1:" + rootKey + ":" + actor.id)`), and the root key is the `TEST_WALLET_PRIVATE_KEY` secret used by the workflows. So control of all 98 role signers follows from control of the root signer, by construction.
- I did not and will not verify control by signing, and I do not hold the secret. Whether the authorized workflow can still use the secret is the question for Codex's independent read-only access check. Nothing here shows it cannot.

## Classification

| Class | Test USDC | Where |
| --- | ---: | --- |
| Available, control not in doubt on this evidence | 130.2 Base, 1,020.0 Ethereum Sepolia | root wallet |
| Not yet recovered, control inferred from the derivation and unverified | 799.22 (of which 264.92 in 20 wallets with no gas) | 78 role wallets with a balance |
| Locked in a contract | 20.58 | GuaranteeTrust. The ABI has `unstake`, `withdrawBacking` and `releaseReserve` (owner); the README says worker dues have no withdrawal function. I did not read their conditions in the source and tried none of them |
| Demonstrably unrecoverable | none shown | |
| Moved to project infrastructure, not lost | 50.0 | sim treasury 45.0, desk officer 5.0 |

## What a recovery would need (not authorized, not done)

78 token transfers back to the root; gas for the 20 wallets that have none (a small ETH top-up from the root, or gasless authorizations if Circle's test token accepts them, which I did not test); an explicit decision on the 20.58 in the contract. Execution stays separately gated. The scenario-wallet lifecycle change (board request x-20261104-scenario-wallet-lifecycle-r1) is the forward fix and follows as its own pull request.

## Files

`balances-base-sepolia.json` (100 addresses, run-end and current balances, ETH, nonce, contract flag), `root-usdc-transfers-base-sepolia.json` (the mint and all 61 outflows), `root-usdc-transfers-eth-sepolia.json` (the readable logs, unreadable ranges, current state).

Method limits: public RPC endpoints (Base Sepolia public node for balances, a public provider for logs and the Ethereum Sepolia reads); reads are single snapshots, not a continuous watch.
