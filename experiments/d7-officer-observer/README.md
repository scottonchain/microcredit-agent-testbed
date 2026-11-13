# Officer observer and cutover draft (source only)

`observer.mjs` pure decision logic; `test-observer.mjs` 110 offline checks (`node test-observer.mjs`); `CUTOVER.md` checklist, host
candidates and host-report template; `SYNTHETIC_JOURNEY.md` the end-to-end check spec. No network, key, chain read or deployment.
It does not accept any head as the officer runtime and does not change the held merges.
