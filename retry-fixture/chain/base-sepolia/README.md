# Chain cases of the retry fixture, run live on Base Sepolia

Date: 2026-10-05 07:35-07:40 UTC. Network: Base Sepolia (chain id 84532), a public testnet with fake money.
Pool: `0x09d9D1fd4Ed5EC5d9e8ceB9275D864D9c8d99A1f` (DecentralizedMicrocredit, the project's persona-test deployment of 2026-10-03, block 47612112; an
older build than the contract repo's current `main`: it reverts with require-strings `Bad nonce` / `Loan inactive` where `main`
uses the custom errors `InvalidNonce()` / `LoanNotActive()`; the EIP-712 domain, typehashes and the `repayLoanMeta` /
`borrowAndDisburseMeta` selectors are the same). Token: MockUSDC `0xa12a5c8C8605945d5e07E4Ea4A95de45d6a9807C` (free mint).
Relayer (and pool owner): `0x5e4dC7639D2b94006c51aD5373173f5e01c248F9`. Borrower: `0x4040CD3CBd3E5d42FC319f06070d10e6C23b1B83`, a throwaway key that holds no ETH and has
sent no transaction of its own: every one of its intents was signed off-chain and relayed. The relayer address also
owns the pool and granted the borrower a score override before the run (step s0), as the forge tests do.

Until now every chain case of `../../cases.json` was `tested by us` only in forge (contract repo `test/RelayerRetry.t.sol`,
`test/RelayerRetryBatch.t.sol`). This directory is the same seven cases as real transactions on a public chain, so that
anyone can re-derive the expected states from the chain without trusting us or our test runner.

Update 2026-10-05 ~08:55 UTC: a second run of the same seven cases against the live pool `0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8` is recorded in the section
"Second run: the live pool" below (files suffixed `_live_pool`); the first run's files and text are unchanged.

## What is here

- `EVIDENCE.json`: the transactions of the run (hash, block, calldata, the nonce the borrower signed, state read at the
  receipt's block and the block before it). It is a map, not a proof: nothing in it is trusted by the verifier.
- `verify_live_run.py`: standard-library Python, JSON-RPC only, no key. Re-reads every receipt, input, log, nonce, balance and
  loan state from the chain and checks the chain cases against them: `python3 verify_live_run.py EVIDENCE.json` (optionally
  `--rpc URL`). Exit 0 = no FAIL. `SKIP` means the RPC would not serve a historical state the check needs; public nodes prune,
  so an archive node turns SKIPs into PASS/FAIL. Our run: `VERIFY_OUTPUT.txt` (CPython 3.14.7) and
  `VERIFY_OUTPUT_cpython39.txt` (CPython 3.9.25): 51 checks, 0 failed, 0 skipped, outputs identical apart from the header.
- `NEGATIVE_CONTROL.txt`: three tampered copies of `EVIDENCE.json` (replay step pointing at the first submission; signed nonce
  off by one; chain-7a pointing at the 7b envelope) each make the verifier exit 1.
- `run_live.py` + `lib.py`: the scripts that sent the transactions (foundry's `cast` for signing and sending; key files named by
  environment variables). Idempotent per step: `EVIDENCE.json` is written after each step and a recorded step is skipped.
  `lib.py` keeps an intent journal (`JOURNAL.jsonl`, not published) written before each broadcast and completed with the tx
  hash after, which is the fixture's own rule for a relayer.

## Case by case (tx hashes; every claim below is a PASS line in VERIFY_OUTPUT.txt)

- chain-1 (replay of the identical signed request): first submission `0x860800e2820dbf496f93ef60729840f3c2ce45d22040292d3a4f8148875493dc` (block 47708766, status 1, pulled exactly 40 USDC);
  the same bytes resubmitted as `0x60b6b9b75aa8f9ab47a9c29bcee64b7871a6898aef4132002274ec53bfac24e4` (block 47708769): status 0, no logs, `nonces(signer)` 2 -> 2, borrower balance
  unchanged, revert reason at the nonce check (`Bad nonce` on this build). Sent with an explicit gas limit, because the node's gas
  estimation refuses a call that reverts; a relayer that retries blindly after a lost ack would be doing exactly this.
- chain-2 (fresh signature for the same intent after the repay landed): `0x8c9956d044e5287f527a585bd75d3dfbf618b0b9680c2fb5b2dbcb4b0102a11d` (block 47708800): next nonce, new signature,
  a valid permit for 100 USDC supplied; status 0, no logs, nonce not consumed (2 -> 2), nothing pulled, reason `Loan inactive`.
- chain-3 (receipt shape): the `MetaLoanRepaid` log of `0x860800e2820dbf496f93ef60729840f3c2ce45d22040292d3a4f8148875493dc` has three topics (signature, borrower, loanId) and 32 bytes of
  data (amount). No nonce, no request digest.
- chain-4 (unknown outcome: read the nonce): `nonces(signer)` at block 47708766-1 equals the signed nonce (1) and at block 47708766
  is 2; the loan goes from open / 40 USDC owed to closed / 0.
- chain-5 (calldata carries the signed request): `tx.input` of `0x860800e2820dbf496f93ef60729840f3c2ce45d22040292d3a4f8148875493dc` decodes as `repayLoanMeta`: borrower, loanId 11, nonce 1
  and the 65-byte signature are recoverable, and that nonce is the one that moved. This is the real `eth_getTransactionByHash`
  the forge test could only stand in for.
- chain-6 (wrapper hides the request from the top-level selector): `0xfac3ee51aff4b01d97950bbe18947a35468783cc3e0a6452d0c1d8c1712e69ca` (block 47708854) is a call to the `Wrapper` contract
  `0xb1190956d669d4493bbc4e8cd11a319636540c93` (`forward(address,bytes)`, selector `0x6fadcf72`); `repayLoanMeta` sits one level down in the input;
  the pool emitted `MetaLoanRepaid`; `nonces(signer)` 3 -> 4 still shows the request landed. (`Wrapper` is the contract repo's
  `test/RelayerRetry.t.sol` helper, deployed as `0x94bd6f271a73be2030f3ee16e737edb905c6c961107a39e753499c432668a5a4`.)
- chain-7a (envelope succeeds, wrapped intent did not land): `0xffe855ddfdfd14fcb3f8d951cfbc0c0449c92a7912577afe27cae34a7cd05830` (block 47708861) is a call to the `SwallowingBatch`
  envelope `0x3cce2b8871d60c02b92e49538f61bdad4fc0b6d4` with one wrapped `repayLoanMeta` whose deadline (1791185887) is before the block time (1791186010):
  status 1, no `MetaLoanRepaid`, `nonces(signer)` 5 -> 5, loan still open and owed. (`SwallowingBatch` is the contract repo's
  `test/RelayerRetryBatch.t.sol` helper, deployed as `0xe8a3301a5002d8281d73b361ced21468f134b1a01e3d79b6d1739fc19b384787`.)
- chain-7b (two intents, one lands, the nonce range names which): `0xbfe01bfbf1331284616d3de627d4bf57a0c86c941db50e97fbdbb70f0771cb25` (block 47708864): nonces 5 (valid) and 6 (expired)
  of one signer in one envelope; status 1, exactly one `MetaLoanRepaid`, `nonces(signer)` 5 -> 6, so [5, 6) names intent 0 and
  the loan is closed. Not run live: the two-signer cases 7d/7e (forge only, contract PR #22) and the missing-journal-row branch.

## Two things the run itself showed (recorded, not smoothed over)

- Two steps (s2, s4) were recorded after the fact from the chain: the post-receipt state read went to a load-balanced public RPC
  node that did not yet serve the receipt's block (once `[]` for the loan list, once `block not found`). The transactions had
  landed; only our record was late. `lib.call` now retries on `block not found`, and reads are pinned to the receipt's block.
  That is chain-4's rule applied to ourselves: after an unknown outcome, read state at a known block, do not resend.
- Gas estimation for chain-6 failed once with `inner call failed` against a node that had not yet seen the borrow of the
  previous step (s7); the same call simulated fine seconds later and landed. A relayer that treats an estimation failure as
  "the intent is invalid" would have mis-marked it; the fixture's `unknown until reconciled` applies to estimation too.

## Limits

- One signer, one relayer, one testnet build that is older than `main`. The verifier reads the revert reason by replaying the
  call at the previous block, which needs a node that serves that state (it did, during our run; it may prune later: SKIP).
- The relayer is also the pool owner and set the borrower's score; that is setup, not part of any case.
- Status of the chain cases stays `tested by us`: the run was ours. It becomes someone else's evidence only when they run
  `verify_live_run.py` themselves.

## Correction from the contract maintainers (2026-10-05 07:49 UTC)

The pool used above, `0x09d9D1fd4Ed5EC5d9e8ceB9275D864D9c8d99A1f`, is the project's pre-redesign persona pool, which its public documents describe as history. The live Base Sepolia pool is `0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8` (contract repo commit `19b166e`); its build reverts with the custom errors `InvalidNonce()` and `LoanNotActive()` that `cases.json` and `test/RelayerRetry.t.sol` name, where this older build reverts with the require-strings `Bad nonce` / `Loan inactive`. Checked from the chain before writing this, by `eth_call` simulation of `repayLoanMeta` with a wrong nonce and with an expired deadline: the live pool reverts with `0x756688fe` (`InvalidNonce()`) and `0x0819bdcd` (`SignatureExpired()`); the old pool reverts with `Error("Bad nonce")` and `Error("Expired")`. (A substring search for the 4-byte error selectors in the deployed bytecode finds neither selector in either build; the optimizer does not keep them as literal bytes, so simulation is the instrument, not grep.) The next live run goes against the live pool; this run stands as it is (same EIP-712 domain name/version, typehashes and function selectors; the expected states do not depend on the revert text, which the verifier matches by substring). Source: contract issue #7 comment 5990326246 (maintainers; part of our own setup, not an outside review).

## Second run: the live pool (2026-10-05 08:33-08:34 UTC)

The maintainers' correction below was applied the same morning: the seven cases were run again, as new transactions, against the
live Base Sepolia pool `0xa49B9352B2e8C2B79b58cb4C60dB43342e08Afa8` (contract repo commit `19b166e`; it reverts with the custom errors
`InvalidNonce()` / `LoanNotActive()` / `SignatureExpired()` that `../../cases.json` and `test/RelayerRetry.t.sol` name) and the
MockUSDC it was deployed with, `0x7C46870111257d8A3aaF846BC6D2F7DA7FBb76f1` (free mint). Same relayer (and pool owner) `0x5e4dC7639D2b94006c51aD5373173f5e01c248F9`,
same throwaway borrower `0x4040CD3CBd3E5d42FC319f06070d10e6C23b1B83` (still no ETH, still no transaction of its own; its `nonces(signer)` on this pool
went 0 -> 6 over the run). Blocks 47710444-47710480. The first run (above) is kept as it is; the two runs are the same seven cases
against two builds, and the expected states did not depend on the revert text.

Files of the second run: `EVIDENCE_live_pool.json` (the map), `VERIFY_OUTPUT_live_pool.txt` (CPython 3.14.7) and
`VERIFY_OUTPUT_live_pool_cpython39.txt` (CPython 3.9.25): `python3 verify_live_run.py EVIDENCE_live_pool.json` -> 51 checks,
0 failed, 0 skipped, outputs identical apart from the header; `NEGATIVE_CONTROL_live_pool.txt` (the same three tampers, each exit 1;
`negative_control.py` is the script that produces it); `ESTIMATION_REPLAY_live_pool.txt` (see below; `estimation_replay.py`).
`verify_live_run.py` now decodes custom-error reverts (4-byte selector -> name) as well as `Error(string)`, so one verifier covers
both builds; the first run's outputs were regenerated with it and are unchanged apart from the two check names that now mention
both builds. `lib.py` / `run_live.py` take the pool, token and evidence path from `RETRY_FIXTURE_POOL` / `RETRY_FIXTURE_USDC` /
`RETRY_FIXTURE_EVIDENCE` (defaults: the live pool, its token, `EVIDENCE_live_pool.json`).

Case by case (every claim is a PASS line in `VERIFY_OUTPUT_live_pool.txt`):

- chain-1: first submission `0x3b7dc058455e8de00360e11069931149f7e0832c9a0e4d778a9fb627042d598a` (block 47710455, status 1, pulled exactly 40 USDC; loan 15); the same bytes resubmitted as
  `0xc00e240c24879e052899827aa647b7fbb7bdd6feca73ad2b77a7c017423431f3` (block 47710457): status 0, no logs, `nonces(signer)` 2 -> 2, balance unchanged, replayed call reverts
  `InvalidNonce()` (`0x756688fe`).
- chain-2: `0xbe780d48dd9de4e015e3c2b799d0ff89f921f34780157bb12d1de5dc79876b00` (block 47710460): next nonce, new signature, valid 100 USDC permit; status 0, no logs, nonce 2 -> 2, nothing
  pulled, reason `LoanNotActive()` (`0x082f7846`).
- chain-3: the `MetaLoanRepaid` log of `0x3b7dc058455e8de00360e11069931149f7e0832c9a0e4d778a9fb627042d598a`: three topics, 32 bytes of data; no nonce, no request digest (unchanged by the redesign).
- chain-4: `nonces(signer)` 1 at block 47710455-1, 2 at block 47710455; loan 15 open / 40 USDC owed -> closed / 0.
- chain-5: `tx.input` of `0x3b7dc058455e8de00360e11069931149f7e0832c9a0e4d778a9fb627042d598a` decodes as `repayLoanMeta`: borrower, loanId 15, nonce 1, 65-byte signature.
- chain-6: `0xcebdb973c49108352b3b62567cdfd0cf4e5e43adb9a49593142d5c4ad90c6303` (block 47710471) calls the `Wrapper` `0xdcfe4da6f1e3b9e06115171c2ddbac0d24c10fc6` (deployed as `0xb1f24654366072e16eaec04c900a9fd60030d69ca85aec8850f26f5cff6bfd84`); `repayLoanMeta` one level down;
  `MetaLoanRepaid` emitted; `nonces(signer)` 3 -> 4; loan 16 closed.
- chain-7a: `0x9ab0deb672874940ebe96c1a1d03b191a94c2e89041ef6d8b807cc4d77cd79a5` (block 47710478) calls the `SwallowingBatch` `0x480a6c549336723da3139b49e5596348863f67ce` (deployed as `0xbe51d6a20b737bf0d079937e9089a8c2de6339c91216a7e279d71f521796a256`) with one expired intent
  (deadline 1791189120, block time 1791189244): status 1, no `MetaLoanRepaid`, `nonces(signer)` 5 -> 5, loan 17 still open and owed.
- chain-7b: `0x0c640d80152c0c769f0bae80a2d0f5b641fba3a0d8dc5f63e543c82898e55df4` (block 47710480): nonces 5 (valid) and 6 (expired) of one signer in one envelope; status 1, exactly one
  `MetaLoanRepaid`, `nonces(signer)` 5 -> 6, loan 17 closed. Still not run live: 7d/7e (two signers; forge only, contract PR #22)
  and the missing-journal-row branch.

### What the second run showed about gas estimation (recorded, not smoothed over)

Two `eth_estimateGas` calls failed once each and succeeded on the retry seconds later; both intents then landed. `ESTIMATION_REPLAY_live_pool.txt`
replays each call (read-only `eth_call`) at every canonical block between the setup step and the call's own block:

- s8 (chain-6, through the wrapper): the estimation error was `inner call failed` (the `Wrapper`'s own `require(ok)` string). At every
  canonical block before loan 16's borrow (block 47710464) the replay reverts with exactly that string; from the borrow block on it succeeds.
  So a node that had not yet seen the previous block produced it, and the wrapper hid the inner reason (`InvalidNonce()`) behind its own
  string: the same masking chain-6 is about, now on the error path.
- s3 (chain-1 first submission): the estimation error was `panic: arithmetic underflow or overflow (0x11)`. No canonical block reproduces
  it: before the borrow (block 47710448) the replay reverts `InvalidNonce()`, from the borrow block on it succeeds. Reading the `19b166e` source,
  the only unguarded subtraction on this path for a fresh active loan with nothing repaid is `block.timestamp - loan.disbursedAt` in
  `_interestAccrued`, which underflows only if the call is evaluated with a block timestamp earlier than the disbursal block's; a node
  that pairs newer state with an older header could do that. That is a hypothesis from the source, not something we reproduced. The relayer
  rule stands either way: an estimation failure is not evidence that the intent is invalid, and the retry after a fresh read was correct.

### Maintainers' reading of the s3 panic (2026-10-05 08:50 UTC)

Contract issue #7 comment 5991193503 (the contract maintainers; part of our own setup, not an outside review) confirms the source reading
above and closes the correction: the second run's 51 checks, the custom errors read back from the chain, the negative controls and the
absence of key material were reviewed. On the panic: `disbursedAt` is written from `block.timestamp` at disbursal (`_disburseLoan`) and
`block.timestamp - loan.disbursedAt` in `_interestAccrued` is the only unguarded subtraction on the fresh-loan repay path (re-read by us:
lines 1281 / 1414 at the contract repo's main `b725a85`, lines 1278 / 1411 at the live build `19b166e`). On a canonical block that
difference is never negative, because block timestamps do not decrease, so the panic needs a node that evaluates post-borrow state under a
pre-borrow header: their words, "a node inconsistency, not a contract defect", and it gets no guard (the pool has 199 bytes of code room,
CI-26; re-measured by us with `forge build --sizes` at `b725a85`: `DecentralizedMicrocredit` 24,377 bytes of runtime, margin 199). Nothing
changes in the contract. The hypothesis above stays a hypothesis: nobody has reproduced the panic.

The comment also says the relayer rule drawn above is "already how the Next.js relayer is documented to behave". We could not confirm that
at `b725a85`: `packages/nextjs/app/api/meta/relayer.ts` simulates once (`simulateContract`) and then sends, and its route wrapper returns the
error to the caller when the simulation throws; neither the relayer, its five routes, `packages/nextjs/docs/` nor the project's CLAUDE.md
(which says it "simulates, submits, waits for the receipt and decodes events") mentions re-reading at a known block or retrying after a
failed estimation; the only retry on that path is viem's transport default (`retryCount` 3 on HTTP 403/408/413/429/500/502/503/504,
JSON-RPC codes -1/-32603/-32005 and network failures; viem 2.30.0 as pinned), and an execution-reverted response from `eth_estimateGas`
(JSON-RPC code 3 or -32000) is not retried. The rule is therefore recorded here as the fixture's rule, not as the project relayer's
observed behaviour; the discrepancy was put to the maintainers on contract PR #18 (comment 5991597813).

Answered the same morning: contract issue #7 comment 5991650980 (2026-10-05 09:22 UTC, the maintainers) withdrew the sentence, in their words
"nothing in the repo documents or implements a re-read and retry after a failed estimation"; `app/api/meta/relayer.ts` at `b725a85` "calls
`simulateContract` once and, when it throws, `relayerRoute` returns the error to the caller", the only retries are viem's transport defaults,
and CLAUDE.md's "simulates, submits, waits for the receipt and decodes events" is the accurate description. They asked that this README keep
the rule as the fixture's, not the project relayer's, which it does. No relayer change now: a one-shot re-simulation against a fresh block
before returning a revert "is a candidate for the next front-end round and will be weighed then". The discrepancy noted above is closed.
