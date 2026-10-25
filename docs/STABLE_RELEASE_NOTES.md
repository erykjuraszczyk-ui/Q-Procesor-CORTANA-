# QWP-777 v1.0.0 Stable — Release Notes

## Finalized
- Release metadata is `1.0.0`.
- Public API version remains `1.0`.
- Result schema identifier remains `qwp777-experiment-1` for continuity with v0.9/RC1.
- `run_circuit(config)` validates the result payload before returning it.
- The CLI remains available for the bundled JSON examples.
- The release uses only the Python standard library at runtime.

## Compatibility
The v0.9 CLI usage and core experiment entry points remain available. Result objects contain the additional `release` and `api_version` fields introduced in RC1. The runner rejects repeated measurement of a single qubit and operations after the first measurement; these cases were not supported with fully defined semantics before RC1.

## Verification scope
The packaged test suite and included examples are run locally during build. This report is not a claim of validation across every operating system, Python distribution, or external simulator.
