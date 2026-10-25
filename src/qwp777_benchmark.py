"""Bounded scaling benchmark for qubit/shot workloads.

Benchmarks are opt-in diagnostics. Their workload budget is a conservative proxy,
not a prediction of wall time or a cross-machine performance score.
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from qwp777_experiment import run_experiment
from qwp777_memory import estimate_tableau_memory, MemoryEstimateError
from qwp777_runtime_info import collect_runtime_info

BENCHMARK_SCHEMA = "qwp777-benchmark-report-1"
DEFAULT_QUIBITS = (1, 2, 4, 8, 16, 32)
DEFAULT_SHOTS = (1, 10, 100)
DEFAULT_WORK_BUDGET = 30_000_000

class BenchmarkError(ValueError):
    pass

def _validate_int_list(values, name, minimum, maximum):
    if not isinstance(values, (list, tuple)) or not values:
        raise BenchmarkError(f"{name} must be a non-empty list")
    checked = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise BenchmarkError(f"each {name} value must be an integer in {minimum}..{maximum}")
        if value in checked:
            raise BenchmarkError(f"{name} values must be unique")
        checked.append(value)
    return tuple(checked)

def estimate_work_units(qubits, shots, repeats, gate_count):
    """Conservative proxy: n^2 x gate count x shots x measured passes."""
    return qubits * qubits * max(1, gate_count) * shots * (repeats + 1)

def _ghz_measurement_circuit(qubits):
    gates = [{"gate": "H", "qubits": [0]}]
    gates.extend({"gate": "CX", "qubits": [q, q + 1]} for q in range(qubits - 1))
    gates.extend({"gate": "MEASURE", "qubits": [q]} for q in range(qubits))
    return gates

def run_scaling_benchmark(qubit_sizes=DEFAULT_QUIBITS, shot_sizes=DEFAULT_SHOTS,
                          repeats=2, seed=2026, max_work_units=DEFAULT_WORK_BUDGET):
    qubits = _validate_int_list(qubit_sizes, "qubit_sizes", 1, 777)
    shots_values = _validate_int_list(shot_sizes, "shot_sizes", 1, 1_000_000)
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 10:
        raise BenchmarkError("repeats must be an integer in 1..10")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1:
        raise BenchmarkError("seed must be an integer in 0..4294967295")
    if isinstance(max_work_units, bool) or not isinstance(max_work_units, int) or not 1 <= max_work_units <= 1_000_000_000:
        raise BenchmarkError("max_work_units must be an integer in 1..1000000000")
    planned = []
    total_work = 0
    for n in qubits:
        gates = _ghz_measurement_circuit(n)
        for shot_count in shots_values:
            units = estimate_work_units(n, shot_count, repeats, len(gates))
            total_work += units
            planned.append((n, shot_count, gates, units))
    if total_work > max_work_units:
        raise BenchmarkError(
            f"planned workload proxy {total_work} exceeds --max-work-units {max_work_units}; "
            "reduce qubits/shots/repeats or explicitly raise the budget")

    rows = []
    for case_index, (n, shot_count, gates, units) in enumerate(planned):
        timings = []
        total_counts = 0
        outcome_keys_valid = True
        for repeat_index in range(repeats):
            case_seed = (seed + case_index * 1009 + repeat_index) % (2**32)
            started = time.perf_counter()
            result = run_experiment(n, gates, shot_count, case_seed, 0.0)
            timings.append(time.perf_counter() - started)
            total_counts = sum(result["counts"].values())
            outcome_keys_valid = outcome_keys_valid and all(
                isinstance(key, str) and len(key) == n and set(key) <= {"0", "1"}
                for key in result["counts"]
            )
            if total_counts != shot_count:
                raise BenchmarkError(f"result count invariant failed for n={n}, shots={shot_count}")
        # Separate traced-memory pass keeps tracemalloc instrumentation out of timed samples.
        tracemalloc.start()
        try:
            memory_result = run_experiment(n, gates, shot_count, (seed + case_index * 1009) % (2**32), 0.0)
            _, peak_bytes = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        estimate = estimate_tableau_memory(n)
        rows.append({
            "num_qubits": n, "shots_per_run": shot_count, "repeats": repeats,
            "gate_count": len(gates), "work_units_estimate": units,
            "timing_seconds": {
                "samples": timings, "minimum": min(timings),
                "median": statistics.median(timings), "mean": statistics.fmean(timings),
                "maximum": max(timings)
            },
            "tracemalloc_peak_bytes": peak_bytes,
            "estimated_tableau_list_container_bytes": estimate["estimated_list_container_bytes"],
            "result_invariants": {
                "counts_sum_matches_shots": sum(memory_result["counts"].values()) == shot_count,
                "outcome_keys_are_bitstrings": outcome_keys_valid,
                "passed": sum(memory_result["counts"].values()) == shot_count and outcome_keys_valid
            }
        })
    return {
        "report_schema": BENCHMARK_SCHEMA,
        "software": {"release": rows and memory_result["release"], "api_version": memory_result["api_version"]},
        "configuration": {"qubit_sizes": list(qubits), "shot_sizes": list(shots_values),
                          "repeats": repeats, "seed": seed, "max_work_units": max_work_units,
                          "planned_work_units": total_work, "timed_runs_per_case": repeats,
                          "additional_traced_memory_pass_per_case": 1},
        "summary": {
            "cases_total": len(rows), "cases_passed": sum(1 for row in rows if row["result_invariants"]["passed"]),
            "cases_failed": sum(1 for row in rows if not row["result_invariants"]["passed"]),
            "maximum_elapsed_seconds": max(row["timing_seconds"]["maximum"] for row in rows),
            "maximum_tracemalloc_peak_bytes": max(row["tracemalloc_peak_bytes"] for row in rows)
        },
        "runtime": collect_runtime_info(), "cases": rows,
        "caveats": [
            "Benchmark measurements are host-specific and should be repeated on the target device.",
            "tracemalloc is sampled in a separate pass and does not report process RSS.",
            "The work-units figure is a conservative workload proxy, not a prediction of CPU seconds.",
            "The generated circuit is a GHZ-style Clifford workload, not a general quantum-circuit benchmark.",
            "QWP-777 is an educational software prototype, not physical quantum hardware."
        ]
    }

def _parse_csv_ints(raw, name):
    try:
        values = [int(part.strip()) for part in raw.split(",") if part.strip()]
    except ValueError as exc:
        raise BenchmarkError(f"{name} must be comma-separated integers") from exc
    if not values:
        raise BenchmarkError(f"{name} must not be empty")
    return values

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a bounded QWP-777 qubit/shot scaling benchmark.")
    parser.add_argument("--qubits", default=",".join(map(str, DEFAULT_QUIBITS)), help="comma-separated qubit sizes (default: 1,2,4,8,16,32)")
    parser.add_argument("--shots", default=",".join(map(str, DEFAULT_SHOTS)), help="comma-separated shot counts per run (default: 1,10,100)")
    parser.add_argument("--repeats", type=int, default=2, help="timed repeats per workload (1..10; default: 2)")
    parser.add_argument("--seed", type=int, default=2026, help="root seed (0..4294967295)")
    parser.add_argument("--max-work-units", type=int, default=DEFAULT_WORK_BUDGET, help=f"safety budget (default: {DEFAULT_WORK_BUDGET})")
    parser.add_argument("-o", "--output", help="write JSON report to this path")
    args = parser.parse_args(argv)
    try:
        report = run_scaling_benchmark(_parse_csv_ints(args.qubits, "--qubits"),
                                       _parse_csv_ints(args.shots, "--shots"),
                                       args.repeats, args.seed, args.max_work_units)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (BenchmarkError, MemoryEstimateError, OSError) as exc:
        print(f"qwp777-benchmark: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
