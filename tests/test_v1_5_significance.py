import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_significance import chi_square_two_sample_test, SignificanceError, _regularized_gamma_q

class V15SignificanceTests(unittest.TestCase):
    def test_identical_counts_not_significant(self):
        r = chi_square_two_sample_test({"00": 100, "11": 100}, {"00": 100, "11": 100})
        self.assertEqual(r["status"], "no_significant_difference_detected")
        self.assertAlmostEqual(r["p_value"], 1.0)

    def test_strong_difference_significant(self):
        r = chi_square_two_sample_test({"0": 100, "1": 0}, {"0": 0, "1": 100}, alpha=0.05)
        self.assertEqual(r["status"], "difference_detected")
        self.assertLess(r["p_value"], 0.001)

    def test_sparse_table_inconclusive(self):
        r = chi_square_two_sample_test({"00": 8, "11": 0}, {"00": 0, "11": 8})
        self.assertEqual(r["status"], "inconclusive")
        self.assertIsNone(r["p_value"])

    def test_single_category_inconclusive(self):
        r = chi_square_two_sample_test({"0": 10}, {"0": 15})
        self.assertEqual(r["status"], "inconclusive")
        self.assertEqual(r["degrees_of_freedom"], 0)

    def test_reject_bad_alpha(self):
        with self.assertRaises(SignificanceError):
            chi_square_two_sample_test({"0": 10, "1": 10}, {"0": 10, "1": 10}, alpha=1)

    def test_reject_width_mismatch(self):
        with self.assertRaises(SignificanceError):
            chi_square_two_sample_test({"0": 10}, {"00": 10})

    def test_gamma_q_known_values(self):
        self.assertAlmostEqual(_regularized_gamma_q(1.0, 1.0), 0.36787944117, places=8)
        self.assertAlmostEqual(_regularized_gamma_q(0.5, 1.9207294103), 0.05, places=5)

if __name__ == "__main__":
    unittest.main()
