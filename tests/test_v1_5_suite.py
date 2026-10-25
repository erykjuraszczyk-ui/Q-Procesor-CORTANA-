import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_conformance_suite import run_conformance_suite

class V15SuiteTests(unittest.TestCase):
    def test_default_suite_passes(self):
        report = run_conformance_suite()
        self.assertTrue(report["summary"]["passed"], report)
        self.assertEqual(report["summary"]["cases_total"], 6)
        self.assertEqual(report["summary"]["cases_passed"], 6)

    def test_reproducible_fixed_seed(self):
        left = run_conformance_suite(shots=128, seed=1234)
        right = run_conformance_suite(shots=128, seed=1234)
        self.assertEqual(left, right)

    def test_shot_bounds(self):
        with self.assertRaises(ValueError):
            run_conformance_suite(shots=5)

if __name__ == "__main__":
    unittest.main()
