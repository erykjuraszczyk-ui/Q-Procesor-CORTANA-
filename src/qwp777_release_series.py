"""Aggregate release audit, regression, and health reports into a version history.

The tool summarizes supplied evidence; it never reruns tests or infers that a missing
metric means success. A clean report is not proof of correctness.
"""
from __future__ import annotations
import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from qwp777_conformance import compare_backend_counts, ConformanceError

SCHEMA = "qwp777-release-series-report-1"
_SUPPORTED = {
    "qwp777-release-audit-report-1": "audit",
    "qwp777-regression-report-1": "regression",
    "qwp777-regression-report-2": "regression",
    "qwp777-health-report-1": "health",
}


class ReleaseSeriesError(ValueError):
    """Raised when an input report cannot be summarized safely."""


def _load(path_value):
    path = Path(path_value)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseSeriesError(f"cannot read report {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseSeriesError(f"{path}: report root must be a JSON object")
    schema = payload.get("report_schema")
    if schema not in _SUPPORTED:
        raise ReleaseSeriesError(f"{path}: unsupported report_schema {schema!r}")
    kind = _SUPPORTED[schema]
    release = payload.get("software", {}).get("release") if isinstance(payload.get("software"), dict) else None
    if not release and kind == "health":
        releases = sorted({
            item.get("software", {}).get("release")
            for item in payload.get("reports", [])
            if isinstance(item, dict) and isinstance(item.get("software"), dict)
            and item.get("software", {}).get("release")
        })
        if len(releases) == 1:
            release = releases[0]
        elif len(releases) > 1:
            release = "multi-release"
    if not release:
        match = re.search(r"(?:v|version[-_])?(\d+\.\d+\.\d+)", path.name, re.IGNORECASE)
        release = match.group(1) if match else "unknown"
    generated = payload.get("generated_utc") or payload.get("generated_at")
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        raise ReleaseSeriesError(f"{path}: summary must be an object")
    return {"path": str(path), "file": path.name, "report_schema": schema,
            "kind": kind, "release": str(release), "generated_utc": generated,
            "summary": summary, "payload": payload}


def _status(report):
    kind, summary = report["kind"], report["summary"]
    if kind == "audit":
        passed = summary.get("passed")
        return "passed" if passed is True else "failed" if passed is False else "unknown"
    if kind == "regression":
        if summary.get("passed") is True and summary.get("cases_failed", 0) == 0:
            return "passed"
        if summary.get("passed") is False or summary.get("cases_failed", 0) > 0:
            return "failed"
        return "unknown"
    value = summary.get("overall_status", report["payload"].get("overall_status", "unknown"))
    if value == "review_required":
        return "review_required"
    if value in {"passed", "ok", "informational_or_ok", "no_suspicious_growth"}:
        return "informational_or_ok"
    return str(value) if value is not None else "unknown"


def _version_key(release):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", release)
    return (1, *(int(part) for part in match.groups())) if match else (0, release.casefold(), 0, 0)


def _compare_regression_payloads(previous, current):
    prev_cases = {c["name"]: c for c in previous.get("cases", []) if isinstance(c, dict) and isinstance(c.get("name"), str)}
    cur_cases = {c["name"]: c for c in current.get("cases", []) if isinstance(c, dict) and isinstance(c.get("name"), str)}
    transitions = []
    for name in sorted(set(prev_cases) | set(cur_cases)):
        old, new = prev_cases.get(name), cur_cases.get(name)
        if old is None:
            transitions.append({"name": name, "status": "added_in_current"})
            continue
        if new is None:
            transitions.append({"name": name, "status": "removed_from_current"})
            continue
        old_pass, new_pass = bool(old.get("passed")), bool(new.get("passed"))
        old_counts, new_counts = old.get("actual_counts"), new.get("actual_counts")
        distribution_changed = None
        tvd = None
        if isinstance(old_counts, dict) and isinstance(new_counts, dict) and old_counts and new_counts:
            try:
                measure = compare_backend_counts(old_counts, new_counts)
                tvd = measure.get("total_variation_distance")
                distribution_changed = tvd > 0 if isinstance(tvd, (int, float)) else None
            except (ConformanceError, ValueError, TypeError):
                distribution_changed = None
        if old_pass and not new_pass:
            status = "regression_failure"
        elif not old_pass and new_pass:
            status = "fixed_since_previous"
        elif not old_pass and not new_pass:
            status = "failure_persists"
        elif distribution_changed:
            status = "counts_changed_but_passed"
        else:
            status = "unchanged_and_passed"
        transitions.append({"name": name, "status": status,
                            "previous_passed": old_pass, "current_passed": new_pass,
                            "distribution_changed": distribution_changed,
                            "total_variation_distance": tvd})
    status_counts = {}
    for item in transitions:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    return {
        "previous_release": previous.get("software", {}).get("release", "unknown"),
        "current_release": current.get("software", {}).get("release", "unknown"),
        "cases_shared": len(set(prev_cases) & set(cur_cases)),
        "cases_added": len(set(cur_cases) - set(prev_cases)),
        "cases_removed": len(set(prev_cases) - set(cur_cases)),
        "regression_failures": status_counts.get("regression_failure", 0),
        "cases_with_changed_distributions": sum(x.get("distribution_changed") is True for x in transitions),
        "status_counts": status_counts,
        "clean": status_counts.get("regression_failure", 0) == 0,
        "cases": transitions,
    }


def build_release_series(paths):
    """Build a multi-release history from supported reports supplied by the caller."""
    if not paths:
        raise ReleaseSeriesError("at least one report path is required")
    inputs = [_load(value) for value in paths]
    releases = {}
    for item in inputs:
        version = item["release"]
        releases.setdefault(version, []).append(item)
    ordered_versions = sorted(releases, key=_version_key)
    release_rows = []
    regression_by_release = {}
    for version in ordered_versions:
        group = releases[version]
        statuses = [_status(item) for item in group]
        audit_reports = [x for x in group if x["kind"] == "audit"]
        regression_reports = [x for x in group if x["kind"] == "regression"]
        health_reports = [x for x in group if x["kind"] == "health"]
        if regression_reports:
            # Keep the last supplied regression report for this release; file order is preserved.
            regression_by_release[version] = regression_reports[-1]["payload"]
        failed_audits = sum(_status(x) == "failed" for x in audit_reports)
        failed_regressions = sum(_status(x) == "failed" for x in regression_reports)
        warning_health = sum(_status(x) == "review_required" for x in health_reports)
        audit_checks = [x["summary"].get("checks_total") for x in audit_reports if isinstance(x["summary"].get("checks_total"), int)]
        audit_passed = [x["summary"].get("checks_passed") for x in audit_reports if isinstance(x["summary"].get("checks_passed"), int)]
        tests_run = [x["payload"].get("unit_tests", {}).get("tests_run") for x in audit_reports
                     if isinstance(x["payload"].get("unit_tests"), dict)
                     and isinstance(x["payload"]["unit_tests"].get("tests_run"), int)]
        cases_total = [x["summary"].get("cases_total") for x in regression_reports if isinstance(x["summary"].get("cases_total"), int)]
        cases_failed = [x["summary"].get("cases_failed") for x in regression_reports if isinstance(x["summary"].get("cases_failed"), int)]
        if failed_audits or failed_regressions:
            status = "failed"
        elif warning_health:
            status = "review_required"
        elif audit_reports and all(_status(x) == "passed" for x in audit_reports) and (not regression_reports or all(_status(x) == "passed" for x in regression_reports)):
            status = "passed"
        elif any(s == "unknown" for s in statuses):
            status = "unknown"
        else:
            status = "informational"
        release_rows.append({
            "release": version, "status": status,
            "reports_total": len(group), "report_files": [x["file"] for x in group],
            "report_types": {kind: sum(x["kind"] == kind for x in group) for kind in ("audit", "regression", "health")},
            "audit_checks_total": sum(audit_checks) if audit_checks else None,
            "audit_checks_passed": sum(audit_passed) if audit_passed else None,
            "unit_tests_run": max(tests_run) if tests_run else None,
            "regression_cases_total": sum(cases_total) if cases_total else None,
            "regression_cases_failed": sum(cases_failed) if cases_failed else None,
            "health_reports_requiring_review": warning_health,
            "failed_audit_reports": failed_audits,
            "failed_regression_reports": failed_regressions,
            "records": [{"file": x["file"], "kind": x["kind"], "report_schema": x["report_schema"],
                         "generated_utc": x["generated_utc"], "status": _status(x)} for x in group],
        })
    transitions = []
    regression_versions = [v for v in ordered_versions if v in regression_by_release]
    for previous_version, current_version in zip(regression_versions, regression_versions[1:]):
        transition = _compare_regression_payloads(regression_by_release[previous_version], regression_by_release[current_version])
        transitions.append(transition)
    transitions_with_regressions = sum(x["regression_failures"] for x in transitions)
    transitions_requiring_review = sum(
        1 for x in transitions
        if x["cases_added"] or x["cases_removed"] or x["cases_with_changed_distributions"]
    )
    failed_release_count = sum(x["status"] == "failed" for x in release_rows)
    review_release_count = sum(x["status"] == "review_required" for x in release_rows)
    overall = ("failed" if failed_release_count or transitions_with_regressions
               else "review_required" if review_release_count or transitions_requiring_review
               else "history_clean_or_informational")
    return {
        "report_schema": SCHEMA,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_status": overall,
        "summary": {
            "reports_total": len(inputs), "releases_total": len(release_rows),
            "audit_reports_total": sum(x["kind"] == "audit" for x in inputs),
            "regression_reports_total": sum(x["kind"] == "regression" for x in inputs),
            "health_reports_total": sum(x["kind"] == "health" for x in inputs),
            "failed_releases": failed_release_count,
            "releases_requiring_review": review_release_count,
            "release_transitions_compared": len(transitions),
            "cross_release_regression_failures": transitions_with_regressions,
            "transitions_requiring_review": transitions_requiring_review,
            "clean": overall in {"history_clean_or_informational"},
        },
        "releases": release_rows,
        "transitions": transitions,
        "caveats": [
            "This report summarizes supplied JSON artifacts; it does not rerun test suites.",
            "Only transitions between provided regression reports can be evaluated.",
            "A missing report or metric is not treated as a pass.",
            "Distribution changes are empirical count differences, not a scientific conclusion about correctness.",
            "A clean history is not proof of universal correctness or hardware equivalence.",
        ],
    }


def render_html(report):
    def esc(value):
        return html.escape("unknown" if value is None else str(value))
    release_rows = []
    for row in report.get("releases", []):
        release_rows.append("<tr>" + "".join("<td>" + esc(v) + "</td>" for v in (
            row.get("release"), row.get("status"), row.get("reports_total"),
            row.get("audit_checks_passed"), row.get("audit_checks_total"), row.get("unit_tests_run"),
            row.get("regression_cases_failed"), row.get("health_reports_requiring_review"))) + "</tr>")
    transition_rows = []
    for row in report.get("transitions", []):
        transition_rows.append("<tr>" + "".join("<td>" + esc(v) + "</td>" for v in (
            row.get("previous_release"), row.get("current_release"), row.get("cases_shared"),
            row.get("cases_added"), row.get("cases_removed"), row.get("regression_failures"),
            row.get("cases_with_changed_distributions"), row.get("clean"))) + "</tr>")
    caveats = "".join("<li>" + esc(v) + "</li>" for v in report.get("caveats", []))
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>QWP-777 Release Series</title><style>body{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem;color:#172033}"
            "table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #ccd2dc;padding:.55rem;text-align:left}"
            "th{background:#f2f4f8}.status{font-weight:700}</style></head><body><h1>QWP-777 Release Series</h1><p>Generated UTC: <code>" +
            esc(report.get("generated_utc")) + "</code></p><p>Overall status: <strong class=\"status\">" + esc(report.get("overall_status")) +
            "</strong></p><h2>Release history</h2><table><thead><tr><th>Release</th><th>Status</th><th>Reports</th><th>Audit passed</th><th>Audit total</th><th>Tests</th><th>Regression failures</th><th>Health reviews</th></tr></thead><tbody>" +
            "".join(release_rows) + "</tbody></table><h2>Adjacent regression comparisons</h2><table><thead><tr><th>Previous</th><th>Current</th><th>Shared cases</th><th>Added</th><th>Removed</th><th>New failures</th><th>Distribution changes</th><th>Clean</th></tr></thead><tbody>" +
            "".join(transition_rows) + "</tbody></table><h2>Caveats</h2><ul>" + caveats + "</ul></body></html>\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build a multi-release QWP-777 regression and health history report.")
    parser.add_argument("reports", nargs="+", help="release audit, regression, or consolidated health report JSON files")
    parser.add_argument("--json", default="release-series.json", help="JSON history report path")
    parser.add_argument("--html", default="release-series.html", help="HTML history report path")
    args = parser.parse_args(argv)
    try:
        report = build_release_series(args.reports)
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        Path(args.html).write_text(render_html(report), encoding="utf-8")
        print(json.dumps({"overall_status": report["overall_status"], "releases_total": report["summary"]["releases_total"],
                          "transitions_compared": report["summary"]["release_transitions_compared"],
                          "json": args.json, "html": args.html}))
        return 1 if report["overall_status"] == "failed" else 0
    except (ReleaseSeriesError, OSError) as exc:
        print(f"qwp777-release-series: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
