import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_release_audit import summarize_check_status

class V19ReleaseAuditTests(unittest.TestCase):
    def test_all_checks_pass(self):
        report = summarize_check_status({"tests": True, "api": True, "signatures": True})
        self.assertTrue(report["passed"])
        self.assertEqual(report["checks_total"], 3)
        self.assertEqual(report["checks_failed"], 0)

    def test_failed_checks_are_named(self):
        report = summarize_check_status({"tests": True, "api": False, "signatures": False})
        self.assertFalse(report["passed"])
        self.assertEqual(report["failed_checks"], ["api", "signatures"])
        self.assertEqual(report["checks_passed"], 1)

    def test_only_literal_true_counts_as_pass(self):
        report = summarize_check_status({"pass": True, "skipped": "not_run"})
        self.assertFalse(report["passed"])
        self.assertEqual(report["failed_checks"], ["skipped"])

if __name__ == "__main__":
    unittest.main()
