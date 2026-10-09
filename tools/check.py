#!/usr/bin/env python3
"""One offline verification entrypoint for maintained testbed code.

Each suite runs in its own process because older flat modules use names such as
model and lib. No live sender, RPC, archive execution or network probe is run.
Historical Python/shell sources are syntax-checked without importing them; the
frozen v3 ledger and conformance fixture are checked without changing their files.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tokenize

ROOT = Path(__file__).resolve().parents[1]
SUITES = (
    "bootstrap", "coordination", "scripts", "metrics", "team-mail", "world-model", "retry-fixture",
    "retry-fixture/reference", "retry-fixture/chain/base-sepolia", "retry-fixture/chain/base-sepolia/reconcile",
    "research/calibration-v3-replay-archive",
)
REFERENCE_CHECKS = (
    "run_email_cases", "scorecard", "horizon_score", "resend_authority", "shipped_gate", "in_progress_409",
)


def syntax_check():
    paths = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\0")
    counts = {"python": 0, "shell": 0}
    for filename in sorted(set(paths)):
        path = ROOT / filename
        if not path.is_file():
            continue
        if path.suffix == ".py":
            with tokenize.open(path) as source:
                compile(source.read(), str(path.relative_to(ROOT)), "exec")
            counts["python"] += 1
        elif path.suffix == ".sh":
            subprocess.run(["bash", "-n", str(path)], cwd=ROOT, capture_output=True, text=True, check=True)
            counts["shell"] += 1
    return counts


def checks():
    for suite in SUITES:
        if (ROOT / suite).exists():
            yield suite, [sys.executable, "-m", "unittest", "discover", "-s", suite, "-p", "test_*.py"]
    yield "world-model schema and relationships", [sys.executable, "world-model/validate.py", "--check-schema"]
    yield "retry case ledger", [sys.executable, "retry-fixture/validate_cases.py"]
    for name in REFERENCE_CHECKS:
        yield f"retry model: {name}", [sys.executable, f"retry-fixture/reference/{name}.py", "--json"]
    for name in ("check_record", "check_same_key_retry", "check_key_expiry"):
        yield f"recorded email evidence: {name}", [sys.executable, f"retry-fixture/live/{name}.py"]
    yield "fork runner offline self-test", [sys.executable, "scenarios/cold-start-three-communities/run.py", "--self-test"]
    yield "frozen v3 ledger", [sys.executable, "calibration-v3/validate_ledger.py", "calibration-v3/corpus.json"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="list checks without running them")
    parser.add_argument("--json", action="store_true", help="one machine-readable summary")
    args = parser.parse_args(argv)
    if args.list:
        print("syntax (all tracked Python and shell; no imports)")
        for label, _ in checks():
            print(label)
        print("frozen v3 conformance: starter, submission checker, score")
        return 0
    results = []
    try:
        syntax = syntax_check()
        results.append({"check": "source syntax", "ok": True, **syntax})
    except (OSError, SyntaxError, subprocess.CalledProcessError) as error:
        results.append({"check": "source syntax", "ok": False, "output": str(error)})

    if not args.json:
        result = results[-1]
        print(f"{'PASS' if result['ok'] else 'FAIL'} source syntax", flush=True)
        if not result["ok"]:
            print(result["output"])

    def run(label, command, output=None):
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
            summary = {"check": label, "ok": result.returncode == 0, "exit_code": result.returncode}
            match = re.search(r"Ran (\d+) tests?", result.stderr)
            if match:
                summary["tests"] = int(match.group(1))
                # An explicitly listed unit-test suite must discover a test.
                if summary["tests"] == 0:
                    summary["ok"] = False
            if not summary["ok"]:
                summary["output"] = result.stdout + result.stderr
            elif output:
                output.write_text(result.stdout, encoding="utf-8")
        except (OSError, subprocess.TimeoutExpired) as error:
            summary = {"check": label, "ok": False, "output": str(error)}
        results.append(summary)
        if not args.json:
            count = f" ({summary['tests']} tests)" if "tests" in summary else ""
            print(f"{'PASS' if summary['ok'] else 'FAIL'} {label}{count}", flush=True)
            if not summary["ok"]:
                print(summary.get("output", ""))
        return summary["ok"]

    for label, command in checks():
        run(label, command)
    with tempfile.TemporaryDirectory(prefix="microcredit-conformance-") as directory:
        submission = Path(directory) / "submission.json"
        if run("frozen v3 starter", [sys.executable, "calibration-v3/starter.py", "calibration-v3/fixture/corpus.json"], submission):
            run("frozen v3 submission checker", [sys.executable, "calibration-v3/check_submission.py", "calibration-v3/fixture/corpus.json", str(submission), "--any-corpus"])
            run("frozen v3 scorer", [sys.executable, "calibration-v3/score.py", "calibration-v3/fixture/corpus.json", str(submission), "calibration-v3/fixture/key.json"])
    failed = [result for result in results if not result["ok"]]
    total = sum(result.get("tests", 0) for result in results)
    summary = {"ok": not failed, "unit_tests": total, "checks": results}
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"{len(results) - len(failed)}/{len(results)} checks passed; {total} unit tests. No live operations executed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
