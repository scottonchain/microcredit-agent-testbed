#!/usr/bin/env python3
"""
Before backing a borrower, look up the borrower's work history in the INAM registry
(https://inamprotocol.org). Read-only: plain HTTPS GETs, nothing is signed or sent on-chain.

    python3 metrics/inam_backer_check.py 0xBorrowerAddress
    python3 metrics/inam_backer_check.py 0xBorrowerAddress --json

An INAM ID counts for an address only if the registry reports a matching
`linked.erc8004_id` and a secp256k1 key-possession proof in `linkedProof`.
A name or a DID someone pastes into an issue does not establish that link.

Fields read, per INAM SPEC.md (https://github.com/inamprotocol/inam-protocol/blob/main/SPEC.md):
- agent: id, linked.erc8004_id, linkedProof.erc8004_id, revokedAt, metadata.demo
- reputation: evidenceLevel, trustScore, flags
- each receipt: receiptId, status, agentA.id, agentB.id, task.capability,
  result.completedAt, dispute.status

Counts cover public receipts only; private history is not visible to this unsigned reader.
Demo registrations and demo.* receipts are reported separately from other public work.
Reputation fields are the registry's claims, not this script's findings. It trusts the
registry's statuses and does not re-verify signatures. To check a receipt's two
Ed25519 signatures yourself, use the `inamprotocol` SDK (`pip install inamprotocol`).
Override the registry with INAM_URL. Python 3.10+, standard library only.
"""
import json
import math
import os
import re
import sys
from datetime import datetime
import urllib.error
import urllib.parse
import urllib.request

INAM = os.environ.get("INAM_URL", "https://api.inamprotocol.org").rstrip("/")
PAGE = 200  # the registry's maximum page size
MAX_PAGES = 1000  # an incomplete/broken scan is unknown, never an empty history
ASSURANCE = "Registry-reported only; identity proofs and receipt signatures not independently verified."


class RegistryError(Exception):
    """The registry did not provide a complete, interpretable response."""


def require(condition, message):
    if not condition:
        raise RegistryError(message)


def get(path, **query):
    url = f"{INAM}/v1{path}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": "microcredit-inam-backer-check/1"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            result = json.load(r)
    except urllib.error.HTTPError as e:
        raise RegistryError(f"registry HTTP {e.code}") from e
    except (OSError, ValueError) as e:
        raise RegistryError("registry unavailable or response is not valid JSON") from e
    require(isinstance(result, dict) and "error" not in result, "invalid registry response")
    return result


def paged(path, key, *, allow_unpaged=False, **query):
    offset = 0
    seen = set()
    for _ in range(MAX_PAGES):
        page = get(path, limit=PAGE, offset=offset, **query)
        rows = page.get(key)
        require(isinstance(rows, list), f"missing {key} list")
        # SPEC section 6's receipt listing is unpaginated; agent search must
        # explicitly supply hasMore. A previously paged listing cannot lose it.
        more = page.get("hasMore", False if allow_unpaged and offset == 0 else None)
        require(type(more) is bool, "missing or invalid pagination marker")
        require(bool(rows) or not more, "pagination made no progress")
        id_key = "id" if key == "agents" else "receiptId"
        for row in rows:
            require(isinstance(row, dict), f"invalid {key} row")
            rid = row.get(id_key)
            require(isinstance(rid, str) and bool(rid), f"missing {id_key}")
            require(rid not in seen, f"duplicate {id_key}; listing is not a stable complete snapshot")
            seen.add(rid)
        yield from rows
        if not more:
            return
        offset += len(rows)  # tolerate a server page-size cap smaller than PAGE
    raise RegistryError("pagination limit reached; history is incomplete")


def agent_for(address):
    """Find an unambiguous registry-reported link, after the entire search succeeds."""
    a = address.lower()
    matches = []
    for agent in paged("/agents/search", "agents", supports="erc8004_id", include_revoked="true", include_demo="true"):
        if agent.get("linked", {}).get("erc8004_id", "").lower() == a:
            matches.append(agent)
    require(len(matches) <= 1, "multiple INAM IDs report this address; history selection is ambiguous")
    if not matches:
        return None
    proof = matches[0].get("linkedProof", {}).get("erc8004_id", {})
    require(proof.get("method") == "key_possession" and proof.get("keyType") == "secp256k1",
            "address link has no reported secp256k1 key-possession proof")
    return matches[0]


def _check(address):
    agent = agent_for(address)
    if agent is None:
        return {"inamId": None, "lookupStatus": "not_found",
                "summary": "no matching linked INAM ID found in this registry; work history is unknown"}
    did = agent["id"]
    path = f"/agents/{urllib.parse.quote(did, safe='')}"
    rep = get(f"{path}/reputation")
    require(rep.get("evidenceLevel") in {"none", "countersigned", "independently_verified"},
            "missing or unsupported registry evidenceLevel")
    score = rep.get("trustScore")
    require(type(score) in (int, float) and math.isfinite(score), "missing or invalid registry trustScore")
    require(isinstance(rep.get("flags"), list) and all(isinstance(f, str) for f in rep["flags"]),
            "missing or invalid registry flags")
    receipts = list(paged(f"{path}/receipts", "receipts", allow_unpaged=True))
    for r in receipts:
        require(all(isinstance(r[party]["id"], str) and bool(r[party]["id"])
                    for party in ("agentA", "agentB")), "missing receipt party ID")
    jobs = [r for r in receipts if r["agentB"]["id"] == did]
    demo = agent.get("metadata", {}).get("demo", False)
    require(type(demo) is bool, "invalid demo registration flag")
    demo_jobs, work = [], []
    for r in jobs:
        capability = r["task"]["capability"]
        require(isinstance(capability, str) and bool(capability), "missing receipt capability")
        require(r["status"] in {"draft", "finalized", "disputed"}, "unsupported receipt status")
        require(r["dispute"]["status"] in {"none", "open", "resolved"}, "unsupported dispute status")
        (demo_jobs if demo or capability.startswith("demo.") else work).append(r)
    done = [r for r in work if r["status"] == "finalized"]
    counterparties = {r["agentA"]["id"] for r in done}
    disputed = sum(1 for r in work if r["dispute"]["status"] != "none")
    completed = [(datetime.fromisoformat(r["result"]["completedAt"].replace("Z", "+00:00")),
                  r["result"]["completedAt"]) for r in done]
    require(all(dt.tzinfo is not None for dt, _ in completed), "completion timestamp has no timezone")
    out = {
        "inamId": did, "lookupStatus": "found",
        "revoked": bool(agent.get("revokedAt")) or "revoked" in rep["flags"], "demo": demo,
        "evidenceLevel": rep["evidenceLevel"], "trustScore": score, "flags": rep["flags"],
        "jobsFinalized": len(done), "distinctCounterparties": len(counterparties), "jobsDisputed": disputed,
        "demoJobsFinalized": sum(r["status"] == "finalized" for r in demo_jobs),
        "lastCompletedAt": max(completed)[1] if completed else None,
    }
    qualifiers = []
    if out["revoked"]:
        qualifiers.append("INAM ID is revoked; historical records only")
    if demo:
        qualifiers.append("demo registration; not evidence of real work")
    qualifiers.append(f"{len(done)} finalized non-demo public receipts for {len(counterparties)} counterparty IDs"
                      if done else "no finalized non-demo public receipts observed; private history unknown")
    if demo_jobs:
        qualifiers.append(f"{out['demoJobsFinalized']} finalized demo receipts excluded")
    if disputed:
        qualifiers.append(f"{disputed} public work receipts with open or resolved disputes")
    out["summary"] = "; ".join(qualifiers)
    return out


def check(address):
    out = {"address": address, "historyScope": "public_registry_receipts", "assurance": ASSURANCE}
    try:
        out.update(_check(address))
    except RegistryError as e:
        out.update(lookupStatus="unknown", summary="registry lookup incomplete; work history is unknown", error=str(e))
    except (KeyError, TypeError, ValueError, AttributeError):
        out.update(lookupStatus="unknown", summary="registry response malformed; work history is unknown")
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = [a for a in argv if a != "--json"]
    if len(args) != 1 or not re.fullmatch(r"0x[0-9a-fA-F]{40}", args[0]):
        sys.exit("usage: inam_backer_check.py 0xBorrowerAddress [--json]")
    r = check(args[0])
    if "--json" in argv:
        print(json.dumps(r, indent=2))
    else:
        for k, v in r.items():
            if k != "summary":
                print(f"{k:24} {v}")
        print(f"\n{r['summary']}")
        print("Informational only: the backing decision and its stake stay yours.")
    return 2 if r["lookupStatus"] == "unknown" else 0


if __name__ == "__main__":
    sys.exit(main())
