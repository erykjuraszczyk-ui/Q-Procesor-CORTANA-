# Migration guide: QWP-777 v2.2.0 → v2.3.0

## Public API

The exported names and callable signatures in `qwp777_api` are unchanged. The API version advances to `2.3`, while the result payload remains `qwp777-experiment-1`. Existing scripts using `run_circuit` or `run_experiment` do not need signature changes.

## New diagnostics

- `src/qwp777_soak.py` runs repeated workloads and reports iteration timing, Python allocation samples and best-effort process RSS from Linux/Android procfs.
- `src/qwp777_profile_compare.py` compares two profile reports for matching workload parameters and outputs changes in median duration and mean traced peak allocation.
- The unified release audit now includes a small soak-test smoke check.

These tools are opt-in. They do not add symbols to `qwp777_api.__all__`, and they do not change simulator semantics.

## Measurement notes

`tracemalloc` only measures traced Python allocations. RSS from procfs reflects resident process memory but may be unavailable on some systems. Timing and memory values depend on the OS, Python build, workload, background activity, thermal state and power policy. Run the soak tool separately on each device you need to support; this release has not been pre-certified on every Android/Termux configuration.

## Suggested validation

```bash
python -m unittest discover -s tests -v
python src/qwp777_release_audit.py -o release-audit.json
python src/qwp777_profile.py examples/deterministic_x.json --repeats 5 -o profile.json
python src/qwp777_soak.py examples/deterministic_x.json --iterations 100 --warmup 3 -o soak.json
```

Older API snapshots and regression baselines remain preserved.
