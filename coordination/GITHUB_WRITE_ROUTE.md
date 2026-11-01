# Reliable GitHub execution

Codex (AI), November 1, 2026. This is a diagnostic and routing rule, not a new
credential, permission, writer, or task ledger. It implements the operator's
direction to resolve repeated access failures without requesting another unlock.
The existing [GitHub-first invariant](README.md#github-first-completion-invariant-operator-direction-2026-10-12)
and [identity/lease requirements](issue-12-recurring-task.md) continue to govern.

## Diagnose the right layer

An app's approval setting, its repository access, the current execution's Git
authentication, safe commit identity, and successful publication are different
facts. Public cloning proves none of the write requirements. Do not ask the
operator to repeat an authorization already given merely because a different
execution lacks a configured Git authentication route.

Before preparing a substantial deliverable, run in the actual writer checkout:

```sh
python coordination/github_route_preflight.py --probe-remote
```

The helper performs local checks and one noninteractive `git push --dry-run`.
It prints static diagnostics and booleans, never credentials, remote URLs,
identity addresses, or raw Git errors. It preserves configured credential
providers, proxy settings and trust. It does not publish, change authentication,
change any ref, acquire a lock, or verify persistence across executions. Git's
configured hooks/providers may still run. Without `--probe-remote`, it performs
only local checks and cannot report a candidate write route.

| Observation | Required next action |
| --- | --- |
| App already permits requested actions | Keep that setting; do not request another unlock. |
| Public Git read succeeds but push reports missing authentication | Repair the supported execution credential binding or use the existing verified writer. Do not mistake this for repository denial. |
| Repository/network/policy failure | Diagnose the actual supported connection and configured policy. Do not bypass the proxy, switch identities silently, or copy another worker's credentials. |
| Unknown/unsafe author or committer | Use explicit approved noreply identities. Do not create an unsafe probe commit. |
| Connector cannot fix both commit identities before creation | Use the verified Git-shell writer; issue comments and blob transfer may still work. |
| Dry run succeeds and configured identities are safe | Perform the already-authorized useful write under existing checks, then independently read back exact remote bytes and commit identities. A dry run is only a candidate route. |
| Protected records | Use the existing exact Git lease in addition to the above. No connector parameter replaces the demonstrated protocol. |

## Finish through an owned route

If supported setup repair is unavailable in the current execution, send the
existing Claude writer one exact, idempotent TM2 handoff on board 15: target repo,
base SHA, exact public-safe patch blob and SHA256, expected file scope, checks,
actual authority, and completion receipt required. Preserve concurrent changes.
Use the same logical request until it resolves. A board request or blob is not a
published commit. The existing autonomous continuation owns verification and
follow-through; no new schedule, duplicate writer, or repeated user question.

If another currently active Codex execution has demonstrated a supported write
route, ask it for the non-secret provider/setup recipe and capability evidence.
Reuse only a supported binding that is actually available to this execution.
Never extract or transfer the other execution's token, private endpoint, or
credential files. A recipe is not evidence that setup succeeded here.

Report completion only after the requested commit/PR or publication is read back.
Report a durable authentication repair only after the supported persistent
configuration is confirmed and a subsequent fresh autonomous execution repeats a
safe useful write and readback. Otherwise name the working route and the remaining
setup dependency accurately. Do not call one successful interactive push permanent.

## November 1 evidence

The diagnosing execution found the GitHub app already set to **Allow all actions**
and the connected account's testbed permission **admin**. Public `ls-remote`
returned main `bacd2696d8a2857dcb1c71065c0b5b9d9d744f93`. A noninteractive push dry
run failed with the missing-username diagnostic. No configured Git credential
helper was found. Credential-environment absence was corroborating information,
not the basis for claiming a failed authentication attempt. No credentials or
private identity values are recorded here.

At the same time, another Codex execution reported verified noreply-safe pushes
and lease release for [PR391 and related work](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6560683847).
This demonstrates that access differs by execution; it does not establish this
execution's setup. The [concrete route-repair request](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6560695398)
asks that writer and Claude for the supported setup recipe and an owned fix.
The request was read back exactly. A reply, canonical integration, subsequent
fresh-execution write, and permanent setup repair remain distinct receipts.

Run the focused offline tests with:

```sh
python -m unittest coordination.test_github_route_preflight
```
