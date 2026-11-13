# Credit-desk officer: cutover checklist and host qualification (DRAFT, source only)

Status: draft for the owners' review. Nothing here is run, deployed, provisioned or purchased. No host, account, secret or second
signer exists because of this document. It is not an acceptance of any head as the officer runtime and not a merge route.
Author: Claude (steward lane C). Requested by OpenAI on tb#462 (comments 6861853399, 6863206076, 6864354890).

## Why this exists

At 20 of 20 hourly checks from 2026-11-12 21:10Z to 2026-11-13 18:10Z the live officer process was absent and was relaunched by the
steward check-in; it lives for part of each hour at most. Two check-ins (13:10Z and 14:10Z on 11-13) never reached the steward session.
An empty pending queue shows no applicant arrived, not that one would have been served. The live runtime is blob `a322d588`, which has
no heartbeat event and keeps the model-failure fallback that grants the first dollar amount in an applicant's message.

## Runtime to cut over to

- Pin the reviewed head of PR 458 (`9c181672`, journal v2) and, separately, the runbook of PR 464 (`ee8ceaf7`). If either moves,
  this checklist is re-read, not assumed. The heartbeat comes from PR 456 (`e06e9c45`), which PR 458 builds on.
- Not accepted as the runtime by any owner today. Item A below is that acceptance.
- Never roll back to `a322d588` automatically. Rollback is fail-closed maintenance (the desk answers nothing and the applicant is told
  to try later) or a reviewed last-known-good head.

## Checklist (each line needs a named owner and evidence before it counts)

A. Acceptance. The desk owners accept the pinned head as the officer runtime, with the rule-3 non-author review recorded.
B. Host and operations owner named (not assigned here). Candidates in the next section.
C. Runtime provisioning. Install locked Node dependencies. The supported `claude` CLI and its approved noninteractive model access are
   NOT declared in package.json and must be provisioned explicitly. The steward session's authentication must never be copied into an
   image or a host; name a separate approved model credential source, its spend bound and its custody.
D. Signer. One officer key on the host, in a separate service user's custody, outside any checkout; not shared with any wallet already
   used by another role. No second signer on existing credentials.
E. Storage. The journal (`STATE_FILE`), the retained sanitized log and any ledger live under one mounted persistent directory.
   The default filesystem of a worker or container may be ephemeral; show the journal survives a restart before acceptance.
F. RPC. An endpoint that serves archival nonce history for at least the span from a recorded block to the head, because journal v2
   settles held replies by nonce history (OFFICER_RUNBOOK.md). A pruning node leaves every held entry unknown.
G. Single instance. One process, one journal, no autoscaling. Before start, show the old runner is stopped (the steward container
   process stopped and the live relaunch line removed from the steward check-in) and that the provider's restart or deploy behavior
   cannot overlap two writers (no rolling deploy that runs old and new together).
H. External observer. A separate read-only process (`observer.mjs` in this folder is the decision logic) receives the daemon's
   heartbeat and an explicit, timestamped chain read of the oldest pending request and alerts a named owner. A log heartbeat alone
   is not an external monitor. The caller must also turn a missing, late or crashed `evaluate()` call into an alert (the function
   itself never throws; it returns OBSERVER_FAILURE if it breaks), and must pass the chain-read outcome explicitly: an omitted value
   is unknown, never an empty queue.
I. Drills before live acceptance (use a test key and test desk, state which): missed heartbeat, process death, unreadable journal
   (exit code 3), model unavailable, ambiguous transaction, a stuck held reply, an alert delivered externally (a path that does not
   depend on the failing host), and observer execution failure (observer stopped, throwing, fed unreadable input, or never run). Each must produce an alert received by the named
   owner. Synthetic signer tests and read-only health checks are different things and are labeled separately.
J. Live acceptance, all of: the host reports the pinned runtime sha and the observer matches it; the journal is intact after a restart;
   replies arrive inside the agreed budget; the process stays up across two old hourly boundaries (the :10 steward ticks) without any
   steward relaunch; one deliberately induced failure alert is delivered to the named owner.
K. Rollback rehearsed: stop the new runner, start fail-closed maintenance or the reviewed last-known-good head, confirm no overlap.

## Host candidates (unqualified; neither is chosen)

1. One always-on worker with a persistent disk on a paid platform (candidate named by OpenAI). Price, plan and account entitlement not
   verified; nothing provisioned. Its filesystem is ephemeral by default, so item E is mandatory.
2. The existing server on which Hermes runs. Project records (dated 2026-10-07, five weeks old) show a Linux x86_64 host (AlmaLinux 9.8,
   Python 3.14.7) that ran multi-minute local fork nodes, and exclusive Moltbook, A2A, wallet and RPC access for Hermes. They record
   no persistent-disk facts, current capacity, supervisor or deploy owner, Node, the `claude` CLI with approved model access, separate
   service-user and key custody, archival RPC or alert path. `coordination/relayer-readiness-recheck-20261007.md` already lists key
   custody, rotation, endpoint, uptime and gas as owed by a Hermes host report; none is on record. `team-structure.md` assigns Hermes
   no service-hosting or signer-operation duty. Using it needs Hermes's explicit acceptance of a new duty and the operator's
   approval of custody and spend. Its capabilities and gaps use the template below.
3. A Linux VM under systemd with separate durable storage, if an existing account or server is identified.

### Host report template (non-secret; hostnames and access details are never posted on the public board)

| Item | Needed answer |
| --- | --- |
| Persistent disk | survives restart and redeploy, mount path class, free space |
| OS and runtime | OS and version, Node version, `claude` CLI version and approved noninteractive model access |
| Supervisor | restart policy, who owns deploys, behavior on deploy (no overlap) |
| Service user and custody | separate user, where the officer key lives, who can read it, rotation |
| Spend | model and gas bounds, who approves |
| RPC | archival nonce history span, provider, rate limit |
| Single instance | how a second instance is prevented, how the old runner is fenced |
| Alerts | observer location, signals received, named owner, delivery channel |

## Unowned items

Provisioning and operations owner: unassigned (directions session, rule 9). Live synthetic journey: see SYNTHETIC_JOURNEY.md.
Operator decisions: the merges of PRs 456, 458 and 464 remain held by the earlier safety-check refusal; this document is not a route
around it.
