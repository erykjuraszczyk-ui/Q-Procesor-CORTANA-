"""Portable, opt-in timing and Python-allocation profiler for QWP-777 experiments.

Measurements are host-specific diagnostics, not release pass/fail performance claims.
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
from qwp777_runtime_info import collect_runtime_info

PROFILE_SCHEMA = "qwp777-profile-report-1"

class ProfileError(ValueError):
    pass

def profile_circuit(payload, repeats=5, shots=None):
    if not isinstance(payload, dict):
        raise ProfileError("circuit payload must be a JSON object")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 100:
        raise ProfileError("repeats must be an integer in 1..100")
    required = {"num_qubits", "gates"}
    if not required.issubset(payload):
        raise ProfileError("circuit payload must contain num_qubits and gates")
    effective_shots = shots if shots is not None else payload.get("shots", 1000)
    if isinstance(effective_shots, bool) or not isinstance(effective_shots, int) or not 1 <= effective_shots <= 1_000_000:
        raise ProfileError("shots must be an integer in 1..1000000")
    seed = payload.get("seed", 7)
    samples = []
    peaks = []
    for _ in range(repeats):
        tracemalloc.start()
        started = time.perf_counter()
        try:
            result = run_experiment(
                payload["num_qubits"], payload["gates"], effective_shots, seed,
                payload.get("noise_probability", 0.0))
            elapsed = time.perf_counter() - started
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        samples.append(elapsed)
        peaks.append(peak)
    return {
        "report_schema": PROFILE_SCHEMA,
        "software": {"release": result["release"], "api_version": result["api_version"]},
        "circuit": {"num_qubits": payload["num_qubits"], "gate_count": len(payload["gates"]),
                    "shots_per_repeat": effective_shots, "repeats": repeats, "seed": seed},
        "timing_seconds": {
            "samples": samples,
            "minimum": min(samples),
            "median": statistics.median(samples),
            "mean": statistics.fmean(samples),
            "maximum": max(samples)
        },
        "python_tracemalloc_peak_bytes": {"samples": peaks, "maximum": max(peaks), "mean": statistics.fmean(peaks)},
        "runtime": collect_runtime_info(),
        "interpretation": [
            "Timing and traced allocations depend on hardware, OS, Python build, and workload.",
            "tracemalloc reports traced Python allocations, not total resident process memory.",
            "No machine-independent performance threshold is implied by this report."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Profile a QWP-777 circuit's execution time and Python allocations.")
    parser.add_argument("circuit", help="JSON circuit file")
    parser.add_argument("--repeats", type=int, default=5, help="measurement repetitions (1..100; default: 5)")
    parser.add_argument("--shots", type=int, help="override circuit shots (1..1000000)")
    parser.add_argument("-o", "--output", help="write report JSON to this path")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.circuit).read_text(encoding="utf-8"))
        report = profile_circuit(payload, repeats=args.repeats, shots=args.shots)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ProfileError, ValueError) as exc:
        print(f"qwp777-profile: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
