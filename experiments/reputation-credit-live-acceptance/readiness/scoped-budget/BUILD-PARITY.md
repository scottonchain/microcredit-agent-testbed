# Build parity and lifecycle review

Codex (AI), November 5, 2026. Exact canonical source is1812e7d with its
OpenZeppelin submodule f9f7db03f3df020aace3958b8fb7de8891d133e5. The source,
IScoreProvider interface, selected settings and dependency manifest are hashed;
every imported library file is checked against that manifest. The reviewer also
checked all318 manifest entries against the clean canonical subtree.

The earlier npm5.3.0 build was reproducible but not exact vendor parity:11 of20
imported files differed, three with code-token differences. The vendor adds
ERC7913/Bytes code and requires Cancun for MCOPY even though this pool uses the
address-based signature API. We therefore compile and execute the full pool on
Cancun, using the exact vendor. The previous Shanghai23272-byte artifact remains
historical, not the current release candidate.

Selected candidate:23246 bytes,1330 below EIP170. Unmodified source with canonical
solc0.8.33/viaIR/runs200 and explicit Cancun:24377 bytes. Canonical foundry.toml
contains no explicit EVM target; the live deployment's exact compiler invocation
and runtime identity still require owner evidence. Matching size is not identity.
Author and independent reviewer artifacts are byte-for-byte identical:
SHA256 fb5f210a93bc9878d99786df40ef15f627eb168615472a03c7db7fc4ba7d14ab.

## What was changed and tested

The new Solidity budget and origination patch remain unchanged. The selected
optimizer is runs1 with an explicit Yul sequence omitting the full inliner.
Original signature verification and all existing ABI functions are retained.
Inlining changes code layout, gas use and available gas at external calls;
passing tests is not a proof of all behavioral or resource equivalence. No helper
CALL replaces ERC1271 verification, preserving its pool caller identity.

Thirteen full-pool groups and six budget groups pass. Full-pool execution uses
pinned Hardhat2.26.3's in-process Cancun provider with normal size limits, no fork
URL and no listening socket. Generated fixture keys remain in memory. Ganache
continues to test the standalone budget on Shanghai. This is entirely local;
no real/testnet funds, signer deployment or RPC rerouting occurs.

Lifecycle coverage includes direct and signed requests, signed disbursement,
partial direct/final signed repayment, cancellation without allowance refill,
interest/principal/fee allocation checked against timestamp arithmetic and actual
receipt fields, premature default rejection, secured default consuming sponsor
stake, and unsecured default leaving a lender loss despite burned credit. It also
covers replay/expiry/bad signatures, ERC1271 caller compatibility, failed-transfer
atomic rollback and signed servicing after issuance stop/revocation.

A differential case compares zero-interest, below-cap request/disbursement/partial
and full repayment/cancellation/withdrawal accounting to the unmodified canonical
source under its default optimizer. It is deliberately a limited comparison;
default and nonzero interest have separate invariant tests, not a complete
differential proof. The mock token is not canonical USDC; permits, maximum-sized
queues/backer sets, arbitrary wallet implementations and live provider failures
remain outside this result.

## Remaining release boundary

This candidate requires a NEW isolated pool. It cannot patch the current immutable
pool. The budget is a fixed external dependency: before activation verify its
runtime, immutable pool/owner/caps, and the pool's one-time binding. Matching a
pool getter alone is not authenticity. The accepted budget's consume path has no
external callbacks; a substituted budget is not equivalent.

Require accepted runtime/source owner, drain/lease clearance, exact deployed
runtime comparison including immutable values, authentic reader acquisition,
complete journal/consent/executor wiring, and separately reviewed wallet lifecycle.
Execution and reservation-release gates remain disabled. A budget stop prevents
new requests, not disbursement of prior commitments; those remain reserved. No
human readiness, predictive creditworthiness or live deployment is claimed.
