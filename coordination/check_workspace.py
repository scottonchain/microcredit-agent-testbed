#!/usr/bin/env python3
"""Check the five local checkouts and their generated deployment/card mirrors. No network calls."""
import argparse
import json
from pathlib import Path
import re
import subprocess

REPOS = (
    "microcredit-agent-testbed", "microcredit-contract", "microcredit-theory",
    "microcredit-vision", "scottonchain.github.io",
)


def read_json(path):
    return json.loads(path.read_text())


def check(root, *, sync_cards=False, verify_remotes=True):
    root = Path(root).resolve()
    errors = []
    for name in REPOS:
        repo = root / name
        if not repo.is_dir():
            errors.append(f"Missing checkout: {name}")
            continue
        if verify_remotes:
            result = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                                    capture_output=True, text=True)
            actual = result.stdout.strip().removesuffix(".git")
            allowed = {f"https://github.com/scottonchain/{name}", f"git@github.com:scottonchain/{name}"}
            if result.returncode or actual not in allowed:
                errors.append(f"Unexpected or missing origin: {name}")
    if errors:
        return errors

    testbed = root / REPOS[0]
    contract = root / REPOS[1]
    deployment = read_json(testbed / "deployments/current.json")
    card_file = testbed / "agent-card.json"
    card = read_json(card_file)
    chain = card["chain"]
    expected = {
        "chainId": deployment["chain_id"], "rpc": deployment["rpc_url"],
        "pool": deployment["pool"], "lens": deployment["lens"],
        "scoreProvider": deployment["scores"], "testToken": deployment["token"]["address"],
        "contractCommit": deployment["source"]["contract_commit"],
    }
    for field, value in expected.items():
        observed = chain.get(field)
        if isinstance(value, str) and value.startswith("0x") and isinstance(observed, str):
            observed, value = observed.lower(), value.lower()
        if observed != value:
            errors.append(f"Canonical agent card disagrees with deployment: {field}")

    generated = (contract / "packages/nextjs/contracts/deployedContracts.ts").read_text()
    marker = f"  {deployment['chain_id']}: {{"
    if marker not in generated:
        errors.append("Generated app contracts omit the recorded chain")
    else:
        section = generated.split(marker, 1)[1].split("\n  },", 1)[0]
        for name, field in (("DecentralizedMicrocredit", "pool"), ("MicrocreditLens", "lens"),
                            ("OracleScoreProvider", "scores")):
            match = re.search(r"\b" + name + r':\s*\{\s*address:\s*"(0x[0-9a-fA-F]{40})"', section)
            if not match or match[1].lower() != deployment[field].lower():
                errors.append(f"Generated app address differs: {name}")
        if re.search(r"\bMockUSDC:\s*\{", section):
            errors.append("Recorded Circle-token deployment must not resolve MockUSDC")
    config = (contract / "packages/nextjs/utils/microcredit.ts").read_text()
    if deployment["token"]["address"].lower() not in config.lower():
        errors.append("App token configuration differs from the recorded deployment")
    if f'deployedCommit: "{deployment["source"]["contract_commit"]}"' not in config:
        errors.append("App deployed-source label differs from the recorded deployment")
    for repo in (testbed, root / "scottonchain.github.io"):
        mirror = repo / ".well-known/agent-card.json"
        if sync_cards and not errors:
            mirror.parent.mkdir(parents=True, exist_ok=True)
            mirror.write_bytes(card_file.read_bytes())
        if not mirror.is_file() or mirror.read_bytes() != card_file.read_bytes():
            errors.append(f"Agent card mirror differs: {repo.name}/.well-known/agent-card.json")

    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2],
                        help="parent directory containing all five named checkouts")
    parser.add_argument("--sync-cards", action="store_true", help="replace only the two known card mirrors")
    args = parser.parse_args(argv)
    try:
        errors = check(args.root, sync_cards=args.sync_cards)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Workspace check failed: {exc}\n")
    for error in errors:
        print("FAIL:", error)
    if errors:
        return 1
    print("PASS: five repository origins; recorded deployment, generated app and three agent cards agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
