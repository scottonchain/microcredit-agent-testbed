# Open Referral schema-tools issue 8: bounded characterization

Codex (AI), October 24, 2026. This diagnostic examines two assumptions in schema compilation. It does not propose a change to supported profile semantics.

[Issue 8](https://github.com/openreferral/hsds_schema_tools/issues/8) reports failure after removing the service_at_location entity. The reporter’s linked profile repository was unavailable at the time of this check; these synthetic inputs do not reproduce that profile or establish a current operator failure.

Sources: main `8ca351861dd82dfc347140123f7764fde6da1e9a` and [PR 12](https://github.com/openreferral/hsds_schema_tools/pull/12) head `206560f42291c66e1adfe8b343428281c4b34d1b`.

| Synthetic input | Main | PR 12 |
|---|---|---|
| Entity and reference present | Success; 10 output files | Same |
| Entity and reference removed | KeyError: service_at_location.json; 7 output files | Same |
| Entity present, reference removed | KeyError: service_at_locations; 7 output files | Same |

All inputs remain unchanged. Partial output counts do not establish that the generated files are invalid. PR 12 changes other operations, leaving these two unconditional operations in place.

## Reproduce

Read the script and the four extracted functions before execution. With Python’s standard library and the two pinned hsds_schema.py source files:

```text
python characterize.py MAIN_hsds_schema.py PR12_hsds_schema.py --output EMPTY_SCRATCH_DIRECTORY
```

Use an empty scratch directory. The script verifies both source hashes, extracts four functions by AST, generates synthetic inputs, and checks the six results in results.json. No package installation, module-level execution, CLI run, or profile download occurs. These checks characterize current behavior; they are not desired-behavior regression tests.

## Limits

This is a function-level characterization, not a profile-conformance or full generation test. Whether omission should succeed or produce an intentional rejection remains a maintainer decision. [Specification issue 592](https://github.com/openreferral/specification/issues/592) discusses the future of compiled schemas; no competing implementation is proposed. No human-service outcome, user uptake, income or welfare has been tested.
