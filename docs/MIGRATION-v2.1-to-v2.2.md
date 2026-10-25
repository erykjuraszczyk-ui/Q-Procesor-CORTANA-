# Migration guide: QWP-777 v2.1.0 → v2.2.0

## Compatibility
The public exports/callable signatures in `qwp777_api` are unchanged. The experiment result schema stays `qwp777-experiment-1`; the metadata API version changes from `2.1` to `2.2`.

## Performance and memory
`run_experiment` now asks the stabilizer simulator not to materialize a separate copy of the final tableau after every shot. This is safe for the experiment runner because it uses only the measurement map. Direct callers of `StabilizerSimulator.run(gates)` still receive the final tableau unless they explicitly use `include_tableau=False`.

## New tools
- `python src/qwp777_memory.py 32` estimates the tableau's Python list-container memory. This is not total RSS and excludes other allocations.
- `python src/qwp777_benchmark.py --qubits 1,2,4,8,16,32 --shots 1,10,100 --repeats 2 -o benchmark-report.json` runs bounded scaling benchmarks.

The benchmark has a work budget so large workloads are rejected by default rather than starting accidentally. Benchmark values vary by Python build, OS, and hardware.
