"""Bounded soak/stability test with best-effort resident-memory sampling.

RSS is sampled from /proc where available. The tool is diagnostic and does not
claim that a short run proves absence of memory leaks or Android compatibility.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import os
import statistics
import sys
import time
import tracemalloc
from pathlib import Path
from qwp777_experiment import run_experiment
from qwp777_runtime_info import collect_runtime_info
from qwp777_version import __version__

SOAK_SCHEMA = "qwp777-soak-report-1"
DEFAULT_MAX_WORK_UNITS = 100_000_000

class SoakError(ValueError):
    pass

def _current_rss_bytes():
    """Return current RSS if exposed by procfs; else None."""
    try:
        for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()
                return int(parts[1]) * 1024 if len(parts) >= 2 else None
    except (OSError, ValueError, IndexError):
        pass
    return None

def _linear_slope(xs, ys):
    if len(xs) < 3 or len(set(xs)) < 2:
        return None
    x_mean, y_mean = statistics.fmean(xs), statistics.fmean(ys)
    denom = sum((x - x_mean) ** 2 for x in xs)
    if denom <= 0:
        return None
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denom

def run_soak(payload, iterations=50, warmup=2, shots=None,
             max_work_units=DEFAULT_MAX_WORK_UNITS, gc_between=True):
    if not isinstance(payload, dict) or not {"num_qubits", "gates"}.issubset(payload):
        raise SoakError("circuit payload must contain num_qubits and gates")
    n = payload["num_qubits"]
    gates = payload["gates"]
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 777:
        raise SoakError("num_qubits must be an integer in 1..777")
    if not isinstance(gates, list) or not gates:
        raise SoakError("gates must be a non-empty list")
    if isinstance(iterations, bool) or not isinstance(iterations, int) or not 1 <= iterations <= 10000:
        raise SoakError("iterations must be an integer in 1..10000")
    if isinstance(warmup, bool) or not isinstance(warmup, int) or not 0 <= warmup <= 100:
        raise SoakError("warmup must be an integer in 0..100")
    effective_shots = shots if shots is not None else payload.get("shots", 1000)
    if isinstance(effective_shots, bool) or not isinstance(effective_shots, int) or not 1 <= effective_shots <= 1_000_000:
        raise SoakError("shots must be an integer in 1..1000000")
    if isinstance(max_work_units, bool) or not isinstance(max_work_units, int) or not 1 <= max_work_units <= 2_000_000_000:
        raise SoakError("max_work_units must be an integer in 1..2000000000")
    planned = n * n * max(1, len(gates)) * effective_shots * (iterations + warmup)
    if planned > max_work_units:
        raise SoakError(f"planned workload {planned} exceeds max_work_units {max_work_units}; reduce workload or explicitly raise the budget")
    seed = payload.get("seed", 7)
    noise_probability = payload.get("noise_probability", 0.0)
    circuit_identity = hashlib.sha256(json.dumps({"num_qubits": n, "gates": gates}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    rss_before = _current_rss_bytes()
    sample_rows = []
    warmup_seconds = []
    tracemalloc.start()
    try:
        for i in range(warmup):
            started = time.perf_counter()
            result = run_experiment(n, gates, effective_shots, (seed + i) % (2**32), noise_probability)
            warmup_seconds.append(time.perf_counter() - started)
            del result
            if gc_between:
                gc.collect()
        for index in range(iterations):
            started = time.perf_counter()
            result = run_experiment(n, gates, effective_shots, (seed + warmup + index) % (2**32), noise_probability)
            elapsed = time.perf_counter() - started
            total_counts = sum(result["counts"].values())
            output_hash = hashlib.sha256(json.dumps(result["counts"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if total_counts != effective_shots:
                raise SoakError(f"iteration {index + 1} returned {total_counts} counts, expected {effective_shots}")
            _, peak = tracemalloc.get_traced_memory()
            del result
            if gc_between:
                gc.collect()
            current, _ = tracemalloc.get_traced_memory()
            sample_rows.append({
                "iteration": index + 1,
                "duration_seconds": elapsed,
                "python_tracemalloc_current_bytes_after_cleanup": current,
                "python_tracemalloc_peak_bytes_cumulative": peak,
                "rss_current_bytes_after_cleanup": _current_rss_bytes(),
                "counts_sha256": output_hash,
                "count_total_valid": True
            })
    finally:
        _, overall_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    durations = [r["duration_seconds"] for r in sample_rows]
    retained = [r["python_tracemalloc_current_bytes_after_cleanup"] for r in sample_rows]
    rss_values = [r["rss_current_bytes_after_cleanup"] for r in sample_rows if isinstance(r["rss_current_bytes_after_cleanup"], int)]
    slope = _linear_slope(list(range(1, len(retained) + 1)), retained)
    return {
        "report_schema": SOAK_SCHEMA,
        "software": {"release": __version__},
        "circuit": {"num_qubits": n, "gate_count": len(gates), "shots_per_iteration": effective_shots,
                    "seed_base": seed, "noise_probability": noise_probability, "identity_sha256": circuit_identity},
        "configuration": {"iterations": iterations, "warmup_iterations": warmup, "gc_between_iterations": bool(gc_between),
                          "planned_work_units_proxy": planned, "max_work_units_proxy": max_work_units},
        "summary": {
            "iterations_completed": len(sample_rows), "all_count_totals_valid": all(r["count_total_valid"] for r in sample_rows),
            "duration_seconds": {"minimum": min(durations), "median": statistics.median(durations),
                                 "mean": statistics.fmean(durations), "maximum": max(durations)},
            "python_tracemalloc_peak_bytes_overall": overall_peak,
            "python_tracemalloc_current_after_cleanup_bytes": {"first": retained[0], "last": retained[-1],
                    "minimum": min(retained), "maximum": max(retained),
                    "linear_slope_bytes_per_iteration": slope},
            "rss_current_bytes": {"before": rss_before, "first_sample": sample_rows[0]["rss_current_bytes_after_cleanup"],
                    "last_sample": sample_rows[-1]["rss_current_bytes_after_cleanup"],
                    "maximum_sampled": max(rss_values) if rss_values else None,
                    "available": bool(rss_values)}
        },
        "warmup_duration_seconds": warmup_seconds,
        "samples": sample_rows,
        "runtime": collect_runtime_info(),
        "interpretation": [
            "RSS is current resident set size read from /proc/self/status when available; None means unavailable on this host.",
            "tracemalloc measures tracked Python allocations, not total process memory.",
            "A short soak is not proof that a memory leak is absent; inspect trends across longer runs and multiple devices.",
            "The workload proxy is conservative guidance, not a guaranteed runtime bound.",
            "This report describes the machine where it ran; Android/Termux compatibility requires a separate run on that device."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a bounded repeated-experiment stability/soak test.")
    parser.add_argument("circuit", help="JSON circuit file")
    parser.add_argument("--iterations", type=int, default=50, help="measured iterations (1..10000; default: 50)")
    parser.add_argument("--warmup", type=int, default=2, help="unreported warmup iterations (0..100; default: 2)")
    parser.add_argument("--shots", type=int, help="override shots per iteration")
    parser.add_argument("--max-work-units", type=int, default=DEFAULT_MAX_WORK_UNITS,
                        help=f"explicit workload-proxy budget (default: {DEFAULT_MAX_WORK_UNITS})")
    parser.add_argument("--no-gc-between", action="store_true", help="do not call gc.collect() after each iteration")
    parser.add_argument("-o", "--output", help="write report JSON to path")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.circuit).read_text(encoding="utf-8"))
        report = run_soak(payload, args.iterations, args.warmup, args.shots,
                          args.max_work_units, not args.no_gc_between)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"qwp777-soak: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
