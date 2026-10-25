"""Compare same-workload soak reports collected on different devices."""
from __future__ import annotations
import argparse, json, math, statistics, sys
from pathlib import Path

COMPARE_SCHEMA = "qwp777-device-comparison-1"
SOAK_SCHEMA = "qwp777-soak-report-1"
class DeviceCompareError(ValueError):
    pass

def _load(value, label):
    if isinstance(value, (str, Path)):
        try:
            value = json.loads(Path(value).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DeviceCompareError(f"cannot read {label} soak report: {exc}") from exc
    if not isinstance(value, dict) or value.get("report_schema") != SOAK_SCHEMA:
        raise DeviceCompareError(f"{label} input must be a {SOAK_SCHEMA} report")
    if not isinstance(value.get("samples"), list) or not value["samples"]:
        raise DeviceCompareError(f"{label} report must have at least one sample")
    return value

def _percent_change(old, new):
    if old is None or new is None or old == 0:
        return None
    return (new - old) / old * 100.0

def _valid_nonnegative(value, label, allow_none=False):
    if allow_none and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise DeviceCompareError(f"{label} must be a finite non-negative number" + (" or null" if allow_none else ""))
    return float(value)

def compare_soak_reports(previous_report, current_report):
    previous = _load(previous_report, "previous")
    current = _load(current_report, "current")
    p_circuit, c_circuit = previous.get("circuit", {}), current.get("circuit", {})
    workload_keys = ("num_qubits", "gate_count", "shots_per_iteration", "seed_base", "noise_probability", "identity_sha256")
    differences = {k: {"previous": p_circuit.get(k), "current": c_circuit.get(k)}
                   for k in workload_keys if p_circuit.get(k) != c_circuit.get(k)}
    if differences:
        raise DeviceCompareError("soak reports have different workloads: " + json.dumps(differences, sort_keys=True))
    p_summary, c_summary = previous.get("summary", {}), current.get("summary", {})
    p_times = [_valid_nonnegative(s.get("duration_seconds"), f"previous sample {i} duration") for i, s in enumerate(previous["samples"])]
    c_times = [_valid_nonnegative(s.get("duration_seconds"), f"current sample {i} duration") for i, s in enumerate(current["samples"])]
    p_py = [_valid_nonnegative(s.get("python_tracemalloc_current_bytes_after_cleanup"), f"previous sample {i} traced memory") for i, s in enumerate(previous["samples"])]
    c_py = [_valid_nonnegative(s.get("python_tracemalloc_current_bytes_after_cleanup"), f"current sample {i} traced memory") for i, s in enumerate(current["samples"])]
    p_rss = [_valid_nonnegative(s.get("rss_current_bytes_after_cleanup"), f"previous sample {i} RSS", True) for i, s in enumerate(previous["samples"])]
    c_rss = [_valid_nonnegative(s.get("rss_current_bytes_after_cleanup"), f"current sample {i} RSS", True) for i, s in enumerate(current["samples"])]
    p_rss = [v for v in p_rss if v is not None]
    c_rss = [v for v in c_rss if v is not None]
    p_runtime, c_runtime = previous.get("runtime", {}), current.get("runtime", {})
    fp_keys = ("os_system", "os_release", "machine_architecture", "python_version", "python_implementation")
    same_fingerprint = all(p_runtime.get(k) == c_runtime.get(k) for k in fp_keys)
    p_dur, c_dur = statistics.median(p_times), statistics.median(c_times)
    p_mem, c_mem = statistics.median(p_py), statistics.median(c_py)
    p_rss_max = max(p_rss) if p_rss else None
    c_rss_max = max(c_rss) if c_rss else None
    return {
        "report_schema": COMPARE_SCHEMA,
        "workload": {k: p_circuit.get(k) for k in workload_keys},
        "samples": {"previous": len(previous["samples"]), "current": len(current["samples"])},
        "software": {"previous": previous.get("software", {}), "current": current.get("software", {})},
        "environment": {"same_host_fingerprint": same_fingerprint,
                        "previous_runtime": p_runtime, "current_runtime": c_runtime,
                        "note": "A matching fingerprint is not a full hardware identity; different fingerprints are expected for cross-device tests."},
        "median_duration_seconds": {"previous": p_dur, "current": c_dur,
                                     "change_percent": _percent_change(p_dur, c_dur)},
        "median_python_tracemalloc_current_bytes_after_cleanup": {"previous": p_mem, "current": c_mem,
                                     "change_percent": _percent_change(p_mem, c_mem)},
        "maximum_sampled_rss_bytes": {"previous": p_rss_max, "current": c_rss_max,
                                     "change_percent": _percent_change(p_rss_max, c_rss_max)},
        "summary": {"workloads_match": True, "cross_host_comparison": not same_fingerprint,
                    "rss_available_both_sides": bool(p_rss) and bool(c_rss)},
        "caveats": [
            "Same circuit identity, qubit count, shot count, seed base and noise setting are required for comparison.",
            "Cross-device time and RSS deltas are descriptive; CPU frequency, thermals, OS, Python build and background activity affect results.",
            "tracemalloc measures tracked Python allocations, not total process memory; RSS is best-effort and may be unavailable."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare matching QWP-777 soak reports from two devices or runs.")
    parser.add_argument("previous", help="first soak report JSON")
    parser.add_argument("current", help="second soak report JSON")
    parser.add_argument("-o", "--output", help="write comparison JSON")
    args = parser.parse_args(argv)
    try:
        report = compare_soak_reports(args.previous, args.current)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, DeviceCompareError) as exc:
        print(f"qwp777-device-compare: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
