#!/usr/bin/env python3
"""Clean-checkout regression for the pinned short-advance reproducer."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / 'reproduce-short-advance-interest.py'
COMMITTED = ROOT / 'short-advance-interest-rows.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--contract-repo',
        type=Path,
        required=True,
        help='Explicit checkout of scottonchain/microcredit-contract at the pinned public commit.',
    )
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary = Path(temporary_directory)
        output = temporary / 'rows.json'
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                '--contract-repo',
                str(args.contract_repo.resolve()),
                '--output',
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert output.read_bytes() == COMMITTED.read_bytes(), completed.stdout
        digest = hashlib.sha256(output.read_bytes()).hexdigest()

        wrong_source = temporary / 'DecentralizedMicrocredit.sol'
        wrong_source.write_text('not the pinned contract\n')
        mismatch = subprocess.run(
            [sys.executable, str(SCRIPT), '--contract-source', str(wrong_source), '--output', str(output)],
            capture_output=True,
            text=True,
        )
        assert mismatch.returncode != 0 and 'SHA-256 mismatch' in mismatch.stderr

        missing = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        assert missing.returncode != 0 and 'contract source required' in missing.stderr
        print(f'clean-checkout reproduction passed: {digest}')


if __name__ == '__main__':
    main()
