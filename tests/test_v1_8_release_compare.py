import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_release_compare import compare_release_reports, ReleaseCompareError

class V18ReleaseCompareTests(unittest.TestCase):
    def _report(self, release, cases):
        return {
            "report_schema":"qwp777-regression-report-2",
            "software":{"release":release},
            "summary":{"cases_total":len(cases)},
            "cases":cases
        }

    def test_same_release_reports_clean(self):
        previous=self._report("1.7.0",[{"name":"bell","actual_counts":{"00":50,"11":50},"passed":True}])
        current=self._report("1.8.0",[{"name":"bell","actual_counts":{"00":50,"11":50},"passed":True}])
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"p.json"; c=Path(temp)/"c.json"
            p.write_text(json.dumps(previous)); c.write_text(json.dumps(current))
            result=compare_release_reports(p,c)
        self.assertTrue(result["summary"]["clean"])
        self.assertEqual(result["cases"][0]["status"],"unchanged_and_passed")
        self.assertAlmostEqual(result["cases"][0]["total_variation_distance"],0)

    def test_regression_failure_detected(self):
        previous=self._report("1.7.0",[{"name":"bell","actual_counts":{"00":50,"11":50},"passed":True}])
        current=self._report("1.8.0",[{"name":"bell","actual_counts":{"00":100},"passed":False}])
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"p.json"; c=Path(temp)/"c.json"
            p.write_text(json.dumps(previous)); c.write_text(json.dumps(current))
            result=compare_release_reports(p,c)
        self.assertFalse(result["summary"]["clean"])
        self.assertEqual(result["cases"][0]["status"],"regression_failure")

    def test_added_removed_cases(self):
        previous=self._report("1.7.0",[{"name":"old","actual_counts":{"0":10},"passed":True}])
        current=self._report("1.8.0",[{"name":"new","actual_counts":{"0":10},"passed":True}])
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"p.json"; c=Path(temp)/"c.json"
            p.write_text(json.dumps(previous)); c.write_text(json.dumps(current))
            result=compare_release_reports(p,c)
        self.assertEqual(result["summary"]["cases_added"],1)
        self.assertEqual(result["summary"]["cases_removed"],1)

    def test_bad_report_schema_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"p.json"; c=Path(temp)/"c.json"
            p.write_text(json.dumps({"report_schema":"wrong"})); c.write_text("{}")
            with self.assertRaises(ReleaseCompareError):
                compare_release_reports(p,c)


    def test_legacy_v1_regression_report_schema_supported(self):
        previous={
            "report_schema":"qwp777-regression-report-1",
            "software":{"release":"1.7.0"},
            "cases":[{"name":"legacy-case","actual_counts":{"0":10},"passed":True}]
        }
        current=self._report("1.8.0",[{"name":"legacy-case","actual_counts":{"0":10},"passed":True}])
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"legacy.json"; c=Path(temp)/"current.json"
            p.write_text(json.dumps(previous)); c.write_text(json.dumps(current))
            result=compare_release_reports(p,c)
        self.assertTrue(result["summary"]["clean"])
        self.assertEqual(result["cases"][0]["status"],"unchanged_and_passed")

if __name__ == "__main__":
    unittest.main()
