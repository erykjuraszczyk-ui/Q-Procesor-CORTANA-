"""Conservative analysis of memory trends in a QWP-777 soak report.

Findings are anomaly candidates, not proof of memory leaks.
"""
from __future__ import annotations
import argparse, json, math, statistics, sys
from pathlib import Path

ANALYSIS_SCHEMA = "qwp777-stability-analysis-1"
SOAK_SCHEMA = "qwp777-soak-report-1"

class StabilityAnalysisError(ValueError):
    pass

def _finite_nonnegative(value, label, allow_none=False):
    if allow_none and value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise StabilityAnalysisError(f"{label} must be a finite non-negative number" + (" or null" if allow_none else ""))
    return value

def _slope(values):
    if len(values) < 3:
        return None
    xs = list(range(len(values)))
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(values)
    den = sum((x - x_mean) ** 2 for x in xs)
    return sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values)) / den if den else None

def _load(report_or_path):
    if isinstance(report_or_path, (str, Path)):
        try:
            report = json.loads(Path(report_or_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StabilityAnalysisError(f"cannot read soak report: {exc}") from exc
    else:
        report = report_or_path
    if not isinstance(report, dict) or report.get("report_schema") != SOAK_SCHEMA:
        raise StabilityAnalysisError("input must be a qwp777-soak-report-1 report")
    samples = report.get("samples")
    if not isinstance(samples, list) or not samples:
        raise StabilityAnalysisError("soak report must contain a non-empty samples list")
    return report

def analyze_soak_report(report_or_path, min_samples=5,
                         python_growth_threshold_bytes=1_048_576,
                         rss_growth_threshold_bytes=16_777_216):
    """Detect conservative suspicious-memory-growth candidates in soak samples."""
    report = _load(report_or_path)
    if isinstance(min_samples, bool) or not isinstance(min_samples, int) or min_samples < 3:
        raise StabilityAnalysisError("min_samples must be an integer >= 3")
    python_growth_threshold_bytes = _finite_nonnegative(python_growth_threshold_bytes, "python_growth_threshold_bytes")
    rss_growth_threshold_bytes = _finite_nonnegative(rss_growth_threshold_bytes, "rss_growth_threshold_bytes")
    samples = report["samples"]
    py_values, rss_values, durations = [], [], []
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise StabilityAnalysisError(f"sample {index} must be an object")
        py = _finite_nonnegative(sample.get("python_tracemalloc_current_bytes_after_cleanup"),
                                 f"sample {index} Python current bytes")
        rss = _finite_nonnegative(sample.get("rss_current_bytes_after_cleanup"),
                                  f"sample {index} RSS bytes", allow_none=True)
        duration = sample.get("duration_seconds")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration < 0:
            raise StabilityAnalysisError(f"sample {index} duration_seconds must be finite and non-negative")
        py_values.append(py)
        durations.append(float(duration))
        if rss is not None:
            rss_values.append((index, rss))
    enough = len(samples) >= min_samples
    findings = []
    py_delta = py_values[-1] - py_values[0]
    py_slope = _slope(py_values)
    py_candidate = enough and py_delta >= python_growth_threshold_bytes and py_slope is not None and py_slope > 0
    if py_candidate:
        findings.append({"id": "python_tracemalloc_growth", "severity": "warning",
                         "observed_growth_bytes": py_delta, "threshold_bytes": python_growth_threshold_bytes,
                         "slope_bytes_per_iteration": py_slope,
                         "message": "Tracked Python allocations increased over the sampled soak window."})
    rss_delta = None
    rss_slope = None
    rss_candidate = False
    if len(rss_values) >= min_samples:
        rss_series = [value for _, value in rss_values]
        rss_delta = rss_series[-1] - rss_series[0]
        rss_slope = _slope(rss_series)
        rss_candidate = rss_delta >= rss_growth_threshold_bytes and rss_slope is not None and rss_slope > 0
        if rss_candidate:
            findings.append({"id": "rss_growth", "severity": "warning",
                             "observed_growth_bytes": rss_delta, "threshold_bytes": rss_growth_threshold_bytes,
                             "slope_bytes_per_sample": rss_slope,
                             "message": "Sampled process RSS increased over the soak window."})
    status = "insufficient_data" if not enough else ("anomaly_candidate" if findings else "no_suspicious_growth")
    return {
        "report_schema": ANALYSIS_SCHEMA,
        "software": report.get("software", {}),
        "input": {"report_schema": SOAK_SCHEMA,
                  "circuit_identity_sha256": report.get("circuit", {}).get("identity_sha256"),
                  "samples_total": len(samples),
                  "rss_samples_total": len(rss_values)},
        "configuration": {"min_samples": min_samples,
                          "python_growth_threshold_bytes": python_growth_threshold_bytes,
                          "rss_growth_threshold_bytes": rss_growth_threshold_bytes},
        "metrics": {
            "python_tracemalloc_current_bytes_after_cleanup": {
                "first": py_values[0], "last": py_values[-1], "delta": py_delta,
                "minimum": min(py_values), "maximum": max(py_values),
                "linear_slope_bytes_per_iteration": py_slope},
            "rss_current_bytes_after_cleanup": {
                "first": rss_values[0][1] if rss_values else None,
                "last": rss_values[-1][1] if rss_values else None,
                "delta": rss_delta, "minimum": min((v for _, v in rss_values), default=None),
                "maximum": max((v for _, v in rss_values), default=None),
                "linear_slope_bytes_per_sample": rss_slope, "available": bool(rss_values)},
            "duration_seconds": {"median": statistics.median(durations), "maximum": max(durations)}},
        "summary": {"status": status, "findings_total": len(findings),
                    "findings": findings,
                    "interpretation": "An anomaly candidate is a heuristic signal for investigation, not proof of a leak."},
        "caveats": [
            "tracemalloc measures tracked Python allocations, not total process memory.",
            "RSS may be unavailable, noisy, or affected by allocator behavior and host background activity.",
            "A short soak cannot establish that a memory leak is present or absent; repeat longer tests on target devices."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze a QWP-777 soak report for conservative memory-anomaly candidates.")
    parser.add_argument("soak_report", help="qwp777-soak-report-1 JSON")
    parser.add_argument("--min-samples", type=int, default=5, help="minimum sample count before declaring no suspicious growth (default: 5)")
    parser.add_argument("--python-growth-threshold-bytes", type=int, default=1_048_576)
    parser.add_argument("--rss-growth-threshold-bytes", type=int, default=16_777_216)
    parser.add_argument("-o", "--output", help="write analysis JSON")
    args = parser.parse_args(argv)
    try:
        report = analyze_soak_report(args.soak_report, args.min_samples,
                                     args.python_growth_threshold_bytes, args.rss_growth_threshold_bytes)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, StabilityAnalysisError) as exc:
        print(f"qwp777-stability-analyze: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
