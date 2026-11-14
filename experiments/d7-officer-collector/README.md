# Officer collector and alert contract (source only)

`collector.mjs`, `alertstate.mjs`, `delivery.mjs`, `watchdog.mjs` (no I/O, never throw); `test-collector.mjs` 361 offline checks
(`node test-collector.mjs`); `fixtures/` log fixtures and `emitter-schema.json`; `CONTRACT.md` the contract and the NOT covered
list; `ACCEPTANCE_RECORD_TEMPLATE.md` blank, creates no permission. Needs the observer in `../d7-officer-observer/` (PR 470).
No network, key, chain read, host, recipient or deployment; not a runtime acceptance and not a merge route.
