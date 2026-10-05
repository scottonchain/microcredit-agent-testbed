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
