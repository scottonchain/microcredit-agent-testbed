#!/usr/bin/env bash
# Compatibility entrypoint. Run ./quickstart.sh --help for commands.
set -euo pipefail
exec "${PYTHON:-python3}" "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/scripts/quickstart.py" "$@"
