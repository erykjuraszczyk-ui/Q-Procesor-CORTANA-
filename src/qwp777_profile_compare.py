"""Compare two QWP-777 profile reports and quantify workload/timing deltas."""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path

COMPARE_SCHEMA = "qwp777-profile-comparison-1"
class ProfileCompareError(ValueError):
    pass

def _read_report(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileCompareError(f"cannot load profile report {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("report_schema") != "qwp777-profile-report-1":
        raise ProfileCompareError(f"{path} is not a qwp777-profile-report-1 report")
    return data

def _percent_change(previous, current):
    if not isinstance(previous, (int, float)) or not isinstance(current, (int, float)) or previous == 0:
        return None
    return (current - previous) / previous * 100.0

def compare_profiles(previous_report, current_report):
    previous = _read_report(previous_report) if isinstance(previous_report, (str, Path)) else previous_report
    current = _read_report(current_report) if isinstance(current_report, (str, Path)) else current_report
    for label, report in (("previous", previous), ("current", current)):
        if not isinstance(report, dict) or report.get("report_schema") != "qwp777-profile-report-1":
            raise ProfileCompareError(f"{label} report is not qwp777-profile-report-1")
    p_circuit, c_circuit = previous.get("circuit", {}), current.get("circuit", {})
    keys = ("num_qubits", "gate_count", "shots_per_repeat", "seed", "repeats")
    differences = {key: {"previous": p_circuit.get(key), "current": c_circuit.get(key)}
                   for key in keys if p_circuit.get(key) != c_circuit.get(key)}
    if differences:
        raise ProfileCompareError("profile workloads are not comparable: " + json.dumps(differences, sort_keys=True))
    p_t = previous.get("timing_seconds", {}).get("median")
    c_t = current.get("timing_seconds", {}).get("median")
    p_a = previous.get("python_tracemalloc_peak_bytes", {}).get("mean")
    c_a = current.get("python_tracemalloc_peak_bytes", {}).get("mean")
    for name, value in (("previous median time", p_t), ("current median time", c_t),
                        ("previous allocation mean", p_a), ("current allocation mean", c_a)):
        if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ProfileCompareError(f"{name} must be a finite, non-negative number")
    p_runtime, c_runtime = previous.get("runtime", {}), current.get("runtime", {})
    same_host_fingerprint = all(p_runtime.get(key) == c_runtime.get(key) for key in
                                 ("os_system", "os_release", "machine_architecture", "python_version", "python_implementation"))
    return {
        "report_schema": COMPARE_SCHEMA,
        "previous_software": previous.get("software", {}),
        "current_software": current.get("software", {}),
        "workload": {key: p_circuit.get(key) for key in keys},
        "timing_median_seconds": {"previous": p_t, "current": c_t,
                                  "change_percent": _percent_change(p_t, c_t)},
        "python_tracemalloc_peak_mean_bytes": {"previous": p_a, "current": c_a,
                                  "change_percent": _percent_change(p_a, c_a)},
        "environment": {"same_host_fingerprint": same_host_fingerprint,
                        "previous_runtime": p_runtime, "current_runtime": c_runtime},
        "caveats": [
            "Compare only runs with identical workload parameters; that check was applied to the fields reported above.",
            "Performance deltas are descriptive, not a universal threshold or proof of causality.",
            "Python tracemalloc does not measure complete process RSS.",
            "Host fingerprints can omit thermal state, power mode, background load and other relevant variables.",
            "Cross-device timing comparisons are not suitable for attributing changes to software alone."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare two QWP-777 profile JSON reports for the same workload.")
    parser.add_argument("previous", help="previous profile JSON")
    parser.add_argument("current", help="current profile JSON")
    parser.add_argument("-o", "--output", help="write comparison JSON to path")
    args = parser.parse_args(argv)
    try:
        report = compare_profiles(args.previous, args.current)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, ProfileCompareError) as exc:
        print(f"qwp777-profile-compare: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
