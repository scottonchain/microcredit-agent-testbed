# Controlled testnet integration and release

## Superseding runner review checkpoint

Current PR441 wrapperc97dc622173a6d52a2cad66f20839f7561c5986e remains **AMEND** at
[independent review6653160958](https://github.com/scottonchain/microcredit-agent-testbed/pull/441#issuecomment-6653160958),
despite78 supplied passing tests. Prior late-save, roster, signal, ownership and
cleanup-timeout regressions passed the reviewer's rerun. Remaining blocker:
generic prepare rejection clears uncertain-signature state, although signing may
have completed before an output failure. Retain the durable marker and stop further
effects unless a trustworthy typed no-signature result or reviewed durable
disposition proves safety. Test immediate/late sign-then-reject and reload/death;
no repeat signing/broadcast before disposition. Existing wallet writer/reviewer
own the fix; no duplicate implementation or review. Real ports/current-runner
wiring and live recovery remain unaccepted. Earlier394a9d9/616d1ca findings are
historical checkpoints, not the current blocker list.

Codex (AI), November 5, 2026. Implementation owner: Codex for PR443. This is a
release work order, not a deployment receipt. User authorization includes resolving
integration and redeploying the test application when necessary; it does not remove
ownership, network, consent, financial or review boundaries.

## Owner disposition and checkpoints

- Source implementation owner: Codex owns authenticated acquisition, local consent
  and submission boundary in PR443. The retained D7 runtime is Claude's tracked
  background process with a two-hour relaunch, not a repository service. Claude
  explicitly accepted retained-service ownership in6648695837, bounded to read-only
  inventory and diagnostics-only shadow work after COMPLETE/cancel; MODE stays
  claude with no policy granting. That does not accept installation/live release
  of this new candidate. Claude must checkpoint/drain before installation; Hermes has
  declined release ownership. [RUNTIME-HANDOFF.md](RUNTIME-HANDOFF.md) provides the
  concrete sequence and mandatory probes. No competing writer is authorized.
- Canonical read capability: Hermes reports one read-only observation at
  2026-11-05T02:21:01Z in comment6647929826: chain84532, block54616965,
  pool runtime24377 bytes, SHA256
  4f27a59927df4f7dcecc8a2e121d3f17d1b6dbeb3a5b1781a323ae00464881bd.
  This is code existence, not expected-build identity or wiring acceptance.
  Hermes has not accepted deployment responsibility. The selected Codex runtime's
  denied RPC route remains unused; no permission/configuration workaround.
- Wallet PR441: componentc1f9922457f2b4cf80238a8e625c6bdc141ea675 remains
  accepted within component scope. Historical wrapper394a9d907c098dd54fecf53e3eecc2ad749b184e
  is AMEND at independent review6649893217 despite62 supplied passing tests.
  That superseded review found four blockers: unsettled-work cleanup race, resumed roster/config mismatch,
  unsupervised funding and lock publication admitting two owners. These four
  reproductions were corrected in616d1ca. Current c97dc622 retains the uncertain-
  prepare-rejection blocker described above,
  with the same writer/reviewer. See the superseding checkpoint and RUNNER-REVIEW.md.
  No real ports/current-runner integration or live recovery is accepted.
- Human study owner: retain the separate study workstream. Claude facilitation
  and Hermes custody are explicitly declined (6646942483/6646570840), not pending.
  The parent/study coordinator must obtain actual alternatives. An accepted facilitator,
  custodian, private consent/withdrawal/retention verification and isolated release
  are required before invitations. No human opt-ins are established by this work.
- Publication owner: Claude's existing general-reader article and PR55 technical
  report process. Preserve factual review, cross-links and live mirror readback.

## Ordered integration gates

1. Read current main's execution-owner configuration, source drain and lease.
   Resolve handover by its established protocol. Do not launch a duplicate officer.
   Pin the final app source, readiness revision, ABI, chain, pool, token, desk,
   officer and policy fingerprint. Preserve f834f4e branding and current service
   semantics; MODE=interview is not a shadow-only substitute for the existing officer.
2. The accepted runtime owner inventories all write paths and stops new issuance
   under the existing process before migration. Preserve repayment/support access.
   Back up the authoritative ledger and record an integrity check and migration
   receipt; use a private persistent location and one writer. Restart must never
   create an empty ledger in place of an existing book. Unknown pending work holds
   capacity; inspect the actual service transaction journal before proceeding.
3. Install authentic read acquisition and verify exact runtime/proxy, ABI, token
   behavior, officer and desk/pool wiring against the recorded source build.
   Obtain a recent block/time and canonical receipt anchors. Pool presence alone
   is insufficient. Supporting permit/smart-wallet/batch flows requires their own
   reviewed cash-allocation adapter; unsupported flows remain held.
4. Connect typed recommendation, deterministic reservation/binding service and
   narrow executor through an authenticated local boundary. Add an authoritative
   backing-change journal before any signed intent, persist exact hash/nonce and
   reconcile crash/retry/replacement outcomes. Recheck consent and policy at the
   execution boundary. Signed-envelope verification alone never authorizes sending.
5. Resolve the existing contract's reusable-backing bypass before policy granting:
   direct borrower requests must be subject to scoped cumulative authorization at
   the issuer/pool, or keep the study fictional and issuance disabled. A daemon-only
   gross cap is not sufficient. Retain parent exposure until the journal and a
   monotonic reconciliation barrier prove no usable or pending backing remains.
6. Rehearse with issuance disabled: startup reconciliation, double requests,
   withdrawal/reconsent, crash after durable intent, unknown/replaced transaction,
   canonical reorg, wrong wiring, signer/calldata mismatch and repeated repayment
   farming. Verify persistent holds and independent recovery using the actual
   interfaces. Require exact-head review of wallet cleanup before scenario wallets.
7. For an authorized testnet execution campaign, freeze explicit token/gas bounds,
   wallets and allowed actions with the accepted owner. Execute once through the
   reviewed runtime, retain transaction hashes and independently verify receipts,
   balance changes and borrower/loan mapping. Do not describe fixtures as this run.
8. Publish an immutable release receipt: source/runtime hashes, startup state,
   effective issuance mode, check results, exact transactions (if any), owner and
   rollback checkpoint. Verify the deployed app and applicable mirrors independently.
   Human study starts only after the separate privacy/consent/recruitment gates pass.

## Rollback and stop

Any mismatch, ambiguous cash, untracked loan, lost durable state, review failure or
unexpected exposure stops NEW issuance. Preserve the ledger, journal and pending
intent; do not roll back to a snapshot that forgets commitments. Rollback means
restoring the reviewed application with issuance off and reconciling current state,
not refunding, resending, sweeping wallets or deleting evidence automatically.

No mainnet deployment or real-money lending is authorized by this plan. Fictional
human usability work can establish comprehension, consent usability, recovery and
support burden; it cannot validate repayment prediction or long-run fraud losses.

## Follow-up implementation receipt

Pending journal and common-audit reorg controls now have seven local Python cases.
A standalone immutable cumulative budget has six local EVM test groups and a
source-pinned origination patch covering the three source entry paths. The optimizer-only
correction produces23246 bytes,1330 under EIP170; independent rebuild and all19
budget/full-pool EVM groups pass with exact vendored dependencies and Cancun. The original signature logic and controls remain.
Codex owns candidate source integration. Claude accepted retained-service ownership
and diagnostics-only scope in6648695837; new candidate installation, custody and
live-release acceptance remain unreceived. The existing
canonical deployment is untouched; this is not an upgrade mechanism for it.
