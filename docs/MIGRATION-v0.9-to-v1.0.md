# Migration notes: v0.9.0 → v1.0.0 Stable

- Existing CLI usage is retained.
- Existing result fields remain; new `release` and `api_version` fields are added.
- `schema_version` remains `qwp777-experiment-1`.
- New `qwp777_api.run_circuit(config)` is the recommended entry point.
- The runner now rejects duplicate measurements of the same qubit and gates placed after measurement starts. Such circuits previously had underspecified output behavior.
- Consumers should not compare the whole result object byte-for-byte because metadata may grow in later releases. Compare documented fields instead.
