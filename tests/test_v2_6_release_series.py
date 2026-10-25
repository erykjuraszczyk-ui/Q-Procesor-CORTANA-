import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qwp777_release_series import build_release_series, render_html, ReleaseSeriesError


def regression(release, passed=True, count=None):
    count = count or {"0": 4}
    return {
        "report_schema": "qwp777-regression-report-2",
        "generated_utc": "2026-10-24T00:00:00+00:00",
        "software": {"release": release, "api_version": release.rsplit(".", 1)[0]},
        "summary": {"cases_total": 1, "cases_passed": int(passed), "cases_failed": 0 if passed else 1, "passed": passed},
        "cases": [{"name": "simple_case", "passed": passed, "actual_counts": count}],
    }


class ReleaseSeriesTests(unittest.TestCase):
    def test_aggregates_multiple_release_reports_and_compares_transitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = Path(tmp) / "v2.4.0-regression.json", Path(tmp) / "v2.5.0-regression.json"
            p1.write_text(json.dumps(regression("2.4.0", True)), encoding="utf-8")
            p2.write_text(json.dumps(regression("2.5.0", False)), encoding="utf-8")
            report = build_release_series([p1, p2])
            self.assertEqual(report["summary"]["releases_total"], 2)
            self.assertEqual(report["summary"]["release_transitions_compared"], 1)
            self.assertEqual(report["summary"]["cross_release_regression_failures"], 1)
            self.assertEqual(report["overall_status"], "failed")
            self.assertEqual(report["transitions"][0]["cases"][0]["status"], "regression_failure")

    def test_detects_clean_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = Path(tmp) / "old.json", Path(tmp) / "new.json"
            p1.write_text(json.dumps(regression("2.4.0", True)), encoding="utf-8")
            p2.write_text(json.dumps(regression("2.5.0", True)), encoding="utf-8")
            report = build_release_series([p1, p2])
            self.assertEqual(report["overall_status"], "history_clean_or_informational")
            self.assertTrue(report["summary"]["clean"])

    def test_health_review_is_not_marked_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "health-v2.6.0.json"
            p.write_text(json.dumps({"report_schema": "qwp777-health-report-1", "overall_status": "review_required",
                                     "reports_total": 1, "reports_with_warning_status": 1, "reports": []}), encoding="utf-8")
            report = build_release_series([p])
            self.assertEqual(report["releases"][0]["status"], "review_required")
            self.assertEqual(report["overall_status"], "review_required")

    def test_html_escapes_untrusted_report_data(self):
        report = {"generated_utc": "now", "overall_status": "ok", "releases": [{"release": "<script>", "status": "bad&unsafe",
                  "reports_total": 1, "audit_checks_passed": None, "audit_checks_total": None, "unit_tests_run": None,
                  "regression_cases_failed": None, "health_reports_requiring_review": 0}], "transitions": [], "caveats": ["<script>"]}
        rendered = render_html(report)
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_rejects_unknown_report_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "invalid.json"
            p.write_text(json.dumps({"report_schema": "unknown", "summary": {}}), encoding="utf-8")
            with self.assertRaises(ReleaseSeriesError):
                build_release_series([p])

    def test_requires_at_least_one_report(self):
        with self.assertRaises(ReleaseSeriesError):
            build_release_series([])


if __name__ == "__main__":
    unittest.main()
