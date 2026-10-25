"""Deterministic regression checks against a checked-in baseline fixture."""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
from qwp777_experiment import run_experiment
from qwp777_conformance import compare_backend_counts, ConformanceError
from qwp777_version import __version__, API_VERSION

class RegressionError(ValueError):
    pass

_DEFAULT_BASELINE = Path(__file__).resolve().parents[1] / "regression" / "baselines" / "v1.5.0.json"

def run_regression_suite(baseline_path=None):
    path = Path(baseline_path) if baseline_path else _DEFAULT_BASELINE
    try:
        baseline_bytes = path.read_bytes()
        fixture = json.loads(baseline_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegressionError(f"cannot read baseline fixture: {exc}") from exc
    if not isinstance(fixture, dict) or fixture.get("baseline_schema") != "qwp777-regression-baseline-1":
        raise RegressionError("unsupported or missing baseline_schema")
    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RegressionError("baseline must include a non-empty cases list")
    results = []
    seen = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise RegressionError(f"baseline case {index} must be an object")
        name = case.get("name")
        if not isinstance(name, str) or not name or name in seen:
            raise RegressionError(f"baseline case {index} has an invalid or duplicate name")
        seen.add(name)
        try:
            actual = run_experiment(
                case["num_qubits"], case["gates"], case["shots"], case["seed"],
                case.get("noise_probability", 0.0))
            expected_counts = case["expected_counts"]
            distance = compare_backend_counts(expected_counts, actual["counts"])
        except (KeyError, TypeError, ValueError, ConformanceError) as exc:
            raise RegressionError(f"invalid baseline case {name}: {exc}") from exc
        expected_counts = dict(sorted(expected_counts.items()))
        actual_counts = dict(sorted(actual["counts"].items()))
        outcomes = sorted(set(expected_counts) | set(actual_counts))
        count_deltas = {key: actual_counts.get(key, 0) - expected_counts.get(key, 0) for key in outcomes}
        passed = actual_counts == expected_counts
        results.append({
            "name": name,
            "passed": passed,
            "comparison_mode": "exact-counts-for-fixed-seed",
            "expected_counts": expected_counts,
            "actual_counts": actual_counts,
            "count_delta_actual_minus_expected": count_deltas,
            "total_variation_distance": distance["total_variation_distance"],
            "hellinger_distance": distance["hellinger_distance"],
            "probability_delta_actual_minus_expected": distance["probability_delta_right_minus_left"],
            "shots": case["shots"],
            "seed": case["seed"],
            "noise_probability": case.get("noise_probability", 0.0),
            "baseline_release": fixture.get("baseline_release", "unknown"),
            "current_release": __version__,
            "detail": "Counts match the saved baseline." if passed else "Counts differ from the saved baseline."
        })
    passed_count = sum(1 for item in results if item["passed"])
    changed_count = sum(1 for item in results if item["total_variation_distance"] > 0)
    summary = {
        "cases_total": len(results), "cases_passed": passed_count,
        "cases_failed": len(results)-passed_count, "passed": passed_count == len(results),
        "cases_with_distribution_changes": changed_count,
        "maximum_total_variation_distance": max(item["total_variation_distance"] for item in results),
        "mean_total_variation_distance": sum(item["total_variation_distance"] for item in results) / len(results)
    }
    return {
        "report_schema": "qwp777-regression-report-2",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {"release": __version__, "api_version": API_VERSION},
        "baseline": {
            "path": str(path),
            "baseline_release": fixture.get("baseline_release"),
            "sha256": hashlib.sha256(baseline_bytes).hexdigest(),
            "case_count": len(cases),
            "comparison_mode": "exact-counts-for-fixed-seed"
        },
        "summary": summary,
        "cases": results,
        "caveats": [
            "Exact-count regression is appropriate for a fixed implementation and fixed seeds.",
            "An intentional simulator algorithm change may require a reviewed baseline update.",
            "TVD and Hellinger distance compare empirical distributions; they do not explain the cause of a difference.",
            "Passing regression tests is not proof of universal circuit correctness or hardware equivalence."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run QWP-777 regression cases against saved fixed-seed counts.")
    parser.add_argument("--baseline", help="path to baseline JSON (defaults to bundled v1.5.0 baseline)")
    parser.add_argument("-o", "--output", help="write regression report JSON to this path")
    args = parser.parse_args(argv)
    try:
        report = run_regression_suite(args.baseline)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0 if report["summary"]["passed"] else 1
    except (OSError, RegressionError) as exc:
        print(f"qwp777-regression: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
