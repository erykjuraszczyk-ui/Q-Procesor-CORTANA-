import json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_regression import run_regression_suite, RegressionError

class V16RegressionTests(unittest.TestCase):
    def test_saved_v15_baseline_passes(self):
        report = run_regression_suite()
        self.assertTrue(report["summary"]["passed"], report)
        self.assertEqual(report["baseline"]["baseline_release"], "1.5.0")
        self.assertEqual(report["summary"]["cases_total"], 6)
        self.assertEqual(report["summary"]["cases_passed"], 6)

    def test_baseline_mismatch_is_reported(self):
        baseline_path = Path(__file__).resolve().parents[1] / "regression" / "baselines" / "v1.5.0.json"
        fixture = json.loads(baseline_path.read_text())
        fixture["cases"][0]["expected_counts"] = {"1": fixture["cases"][0]["shots"]}
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "baseline.json"
            bad.write_text(json.dumps(fixture))
            report = run_regression_suite(bad)
        self.assertFalse(report["summary"]["passed"])
        self.assertFalse(report["cases"][0]["passed"])

    def test_unsupported_baseline_schema_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            bad = Path(temp) / "baseline.json"
            bad.write_text(json.dumps({"baseline_schema": "wrong", "cases": [{}]}))
            with self.assertRaises(RegressionError):
                run_regression_suite(bad)

if __name__ == "__main__":
    unittest.main()
