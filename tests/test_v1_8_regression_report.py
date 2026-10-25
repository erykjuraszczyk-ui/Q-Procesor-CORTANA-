import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_regression import run_regression_suite

class V18EnhancedRegressionReportTests(unittest.TestCase):
    def test_report_contains_hash_and_distribution_metrics(self):
        report = run_regression_suite()
        self.assertEqual(report["report_schema"], "qwp777-regression-report-2")
        self.assertEqual(len(report["baseline"]["sha256"]), 64)
        self.assertIn("mean_total_variation_distance", report["summary"])
        for case in report["cases"]:
            self.assertIn("hellinger_distance", case)
            self.assertIn("total_variation_distance", case)
            self.assertIn("count_delta_actual_minus_expected", case)
            self.assertEqual(case["total_variation_distance"], 0.0)

if __name__ == "__main__":
    unittest.main()
