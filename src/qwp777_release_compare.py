"""Compare regression reports between two QWP-777 releases."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
from qwp777_conformance import compare_backend_counts, ConformanceError
from qwp777_metrics import total_variation_distance, hellinger_distance
from qwp777_version import __version__

class ReleaseCompareError(ValueError):
    pass

_SUPPORTED_REPORTS = {"qwp777-regression-report-1", "qwp777-regression-report-2"}

def _load_report(path, label):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseCompareError(f"cannot read {label} report: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("report_schema") not in _SUPPORTED_REPORTS:
        raise ReleaseCompareError(f"{label} is not a supported QWP-777 regression report")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ReleaseCompareError(f"{label} report cases must be a list")
    case_map = {}
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or not isinstance(case.get("name"), str) or not case["name"]:
            raise ReleaseCompareError(f"{label} case {index} has an invalid name")
        if case["name"] in case_map:
            raise ReleaseCompareError(f"{label} has duplicate case name {case['name']}")
        counts = case.get("actual_counts")
        if not isinstance(counts, dict) or not counts:
            raise ReleaseCompareError(f"{label} case {case['name']} has no actual_counts")
        case_map[case["name"]] = case
    return payload, case_map

def compare_release_reports(previous_path, current_path):
    previous, prev_cases = _load_report(previous_path, "previous")
    current, cur_cases = _load_report(current_path, "current")
    previous_release = previous.get("software", {}).get("release", "unknown")
    current_release = current.get("software", {}).get("release", "unknown")
    results = []
    for name in sorted(set(prev_cases) | set(cur_cases)):
        old = prev_cases.get(name)
        new = cur_cases.get(name)
        if old is None:
            results.append({
                "name": name, "status": "added_in_current",
                "previous_passed": None, "current_passed": bool(new.get("passed")),
                "distribution_changed": None, "total_variation_distance": None,
                "hellinger_distance": None, "count_deltas_current_minus_previous": None
            })
            continue
        if new is None:
            results.append({
                "name": name, "status": "removed_from_current",
                "previous_passed": bool(old.get("passed")), "current_passed": None,
                "distribution_changed": None, "total_variation_distance": None,
                "hellinger_distance": None, "count_deltas_current_minus_previous": None
            })
            continue
        try:
            distribution = compare_backend_counts(old["actual_counts"], new["actual_counts"])
        except ConformanceError as exc:
            raise ReleaseCompareError(f"cannot compare case {name}: {exc}") from exc
        all_outcomes = sorted(set(old["actual_counts"]) | set(new["actual_counts"]))
        deltas = {key: new["actual_counts"].get(key, 0) - old["actual_counts"].get(key, 0)
                  for key in all_outcomes}
        old_pass, new_pass = bool(old.get("passed")), bool(new.get("passed"))
        if old_pass and not new_pass:
            status = "regression_failure"
        elif not old_pass and new_pass:
            status = "fixed_since_previous"
        elif not old_pass and not new_pass:
            status = "failure_persists"
        elif distribution["total_variation_distance"] > 0:
            status = "counts_changed_but_passed"
        else:
            status = "unchanged_and_passed"
        results.append({
            "name": name, "status": status,
            "previous_passed": old_pass, "current_passed": new_pass,
            "previous_shots": sum(old["actual_counts"].values()),
            "current_shots": sum(new["actual_counts"].values()),
            "distribution_changed": distribution["total_variation_distance"] > 0,
            "total_variation_distance": distribution["total_variation_distance"],
            "hellinger_distance": distribution["hellinger_distance"],
            "probability_delta_current_minus_previous": distribution["probability_delta_right_minus_left"],
            "count_deltas_current_minus_previous": deltas
        })
    status_counts = {}
    for case in results:
        status_counts[case["status"]] = status_counts.get(case["status"], 0) + 1
    summary = {
        "cases_compared_or_reported": len(results),
        "cases_shared": len(set(prev_cases) & set(cur_cases)),
        "cases_added": len(set(cur_cases) - set(prev_cases)),
        "cases_removed": len(set(prev_cases) - set(cur_cases)),
        "regression_failures": status_counts.get("regression_failure", 0),
        "cases_with_changed_distributions": sum(1 for c in results if c.get("distribution_changed") is True),
        "status_counts": status_counts,
        "clean": status_counts.get("regression_failure", 0) == 0
    }
    return {
        "report_schema": "qwp777-release-comparison-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "comparator_release": __version__,
        "previous_release": previous_release,
        "current_release": current_release,
        "previous_report": str(previous_path),
        "current_report": str(current_path),
        "summary": summary,
        "cases": results,
        "caveats": [
            "TVD and Hellinger compare empirical distributions, not internal quantum states.",
            "Changes in shot count or random-seed policy can alter empirical distributions.",
            "A `regression_failure` means a case passed previously but failed against its current saved baseline; investigate before release.",
            "A clean report is not exhaustive proof of correctness."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare regression reports from two QWP-777 releases.")
    parser.add_argument("previous", help="previous release regression report JSON")
    parser.add_argument("current", help="current release regression report JSON")
    parser.add_argument("-o", "--output", help="write comparison report JSON to path")
    args = parser.parse_args(argv)
    try:
        report = compare_release_reports(args.previous, args.current)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0 if report["summary"]["clean"] else 1
    except (OSError, ReleaseCompareError) as exc:
        print(f"qwp777-release-compare: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
