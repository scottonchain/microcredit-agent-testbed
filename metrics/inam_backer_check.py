#!/usr/bin/env python3
"""
Before backing a borrower, look up the borrower's work history in the INAM registry
(https://inamprotocol.org). Read-only: plain HTTPS GETs, nothing is signed or sent on-chain.

    python3 metrics/inam_backer_check.py 0xBorrowerAddress
    python3 metrics/inam_backer_check.py 0xBorrowerAddress --json

An INAM ID counts for an address only if the ID proved control of that address with a signed
challenge (the registry's `linked.erc8004_id`). A name or a DID someone pastes into an issue
does not. With no such link the script says so and stops: no history is better than borrowed history.

Fields read, per INAM SPEC.md (https://github.com/inamprotocol/inam-protocol/blob/main/SPEC.md):
- agent: id, linked.erc8004_id, revokedAt, metadata.demo
- reputation: evidenceLevel, trustScore, flags
- each receipt: status, agentA.id, agentB.id, result.completedAt, dispute.status

It trusts the registry's statuses and does not re-verify signatures. To check a receipt's two
Ed25519 signatures yourself, use the `inamprotocol` SDK (`pip install inamprotocol`).
Override the registry with INAM_URL. Python 3.10+, standard library only.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

INAM = os.environ.get("INAM_URL", "https://api.inamprotocol.org").rstrip("/")
PAGE = 200  # the registry's maximum page size


def get(path, **query):
    url = f"{INAM}/v1{path}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": "microcredit-inam-backer-check/1"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def paged(path, key, **query):
    offset = 0
    while True:
        page = get(path, limit=PAGE, offset=offset, **query)
        yield from page[key]
        if not page.get("hasMore"):
            return
        offset += PAGE


def agent_for(address):
    """The INAM agent that proved control of `address`, or None. No lookup by wallet exists, so list and match."""
    a = address.lower()
    for agent in paged("/agents/search", "agents", supports="erc8004_id", include_revoked="true", include_demo="true"):
        if str(agent.get("linked", {}).get("erc8004_id", "")).lower() == a:
            return agent
    return None


def check(address):
    agent = agent_for(address)
    if agent is None:
        return {"address": address, "inamId": None,
                "summary": "no INAM ID has proved control of this address; no verifiable work history"}
    did = agent["id"]
    rep = get(f"/agents/{did}/reputation")
    jobs = [r for r in paged(f"/agents/{did}/receipts", "receipts") if r["agentB"]["id"] == did]
    done = [r for r in jobs if r["status"] == "finalized"]
    counterparties = {r["agentA"]["id"] for r in done}
    disputed = sum(1 for r in jobs if r.get("dispute", {}).get("status", "none") != "none")
    out = {
        "address": address, "inamId": did,
        "revoked": bool(agent.get("revokedAt")), "demo": bool(agent.get("metadata", {}).get("demo")),
        "evidenceLevel": rep["evidenceLevel"], "trustScore": rep["trustScore"], "flags": rep.get("flags", []),
        "jobsFinalized": len(done), "distinctCounterparties": len(counterparties), "jobsDisputed": disputed,
        "lastCompletedAt": max((r["result"]["completedAt"] for r in done), default=None),
    }
    if out["revoked"]:
        out["summary"] = "INAM ID is revoked"
    elif not done:
        out["summary"] = "linked INAM ID, but no finished work yet"
    else:
        out["summary"] = (f"{len(done)} finished jobs for {len(counterparties)} counterparties, "
                          f"evidence {rep['evidenceLevel']}")
    return out


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    if len(args) != 1 or not (args[0].startswith("0x") and len(args[0]) == 42):
        sys.exit("usage: inam_backer_check.py 0xBorrowerAddress [--json]")
    r = check(args[0])
    if "--json" in sys.argv:
        print(json.dumps(r, indent=2))
        return
    for k, v in r.items():
        if k != "summary":
            print(f"{k:24} {v}")
    print(f"\n{r['summary']}")
    print("Informational only: the backing decision and its stake stay yours.")


if __name__ == "__main__":
    main()
