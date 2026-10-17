# Historical submission handoff — delivered by Hermes as PR10263

Current status: https://github.com/PolicyEngine/policyengine-us/pull/10263 was submitted21:12:55UTC; the fork blocker described below is resolved by the authorized Hermes route. Do not execute this historical handoff again.

Scott explicitly authorized submitting this exact reviewed fix on October17 at19:53UTC. This is specific PR authorization; broader standing rules remain separate. Fork creation through this worker's GitHub integration returned HTTP403 Resource not accessible by integration. No fork, branch push or upstream PR was created. Claude's existing capable Git-shell writer is the requested execution fallback, without new credentials or expanded access.

Target PolicyEngine/policyengine-us main; source base5ec60b209a4647be9daaf4f8a1500eb1bcdf8a94; exact prepared commit10cf9185357db18c801cf0a8957629c9ad49da40. Use the accompanying patch, preserving explicit noreply author AND committer. Fresh-read issue10262 and competing work, create authorized fork scottonchain/policyengine-us if still absent, push fix-fl-school-readiness-tips and open one PR with the body below. Check for prior success before retrying; read back exact three files, head, identities and CI. Maintainers retain review/merge authority.

## Exact PR title

Fix double-counted tips in Florida School Readiness income

## Exact PR body

Fixes #10262.

Florida School Readiness counts tips both within gross `employment_income` and as a separate `tip_income` source. Remove the separate source so $30,000 in annual gross wages, including $10,000 in tips, produces $2,500 monthly countable income rather than $3,333.33. Add paired YAML regression cases and a changelog fragment.

This follows the existing input convention: tips are a subset of gross employment income, as documented on `employment_income` and used by Nevada CCDP and Washington's long-term-care taxable-wage calculation. It does not change that input convention or introduce a separate treatment for inconsistent tip-only inputs.

Validation on base `5ec60b209a4647be9daaf4f8a1500eb1bcdf8a94`:

- [x] Added tipped regression fails before the correction: one failure, six passes.
- [x] All seven countable-income tests pass after the correction.
- [x] Florida School Readiness folder: 126 tests pass across 17 files in six sequential isolated batches (`test_batched.py --mode per-subdir --workers 1`), 376.2 seconds, peak reported batch RSS 2170 MB.
- [x] `make format` and `git diff --check` pass; partner tests and dependency lockfiles unchanged.
- [ ] Full upstream suite and upstream CI have not been run locally.

axiom: needed

Prepared and tested by Codex (AI), submitted with the repository account owner's explicit authorization. Hermes (AI), a separate internal collaborator, reviewed the exact source patch and upstream conventions without objection; it did not independently rerun these tests. Maintainer review is requested.
