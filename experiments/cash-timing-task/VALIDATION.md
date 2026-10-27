# Validation of candidate v1

Codex, 2026-10-23. Internal checks only, not independent use.

- `node experiments/cash-timing-task/test.js`: exact-cent arithmetic, first deficit, largest deficit, final balance, same-day ordering, malformed input, empty input and static no-network/no-storage checks passed.
- Chromium with Playwright `setContent`: calculate, invalid chronology error, removal of stale result, restore example, and absence of automatic external requests passed.
- Actual `file://` navigation in this managed environment returned `ERR_BLOCKED_BY_ADMINISTRATOR`. Browser-content behavior was tested; downloading/opening the file as an end user was NOT verified here. Do not claim a successful file-opening test. The plain paper method is independently readable without running HTML.
- `python tools/check.py`: 31/31 checks, 483 unit tests passed; no live operations.

No actual user, bank, accounts or personal data tested. No deployment.
