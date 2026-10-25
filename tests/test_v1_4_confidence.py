import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_confidence import wilson_interval, compare_proportion_intervals, ConfidenceError

class V14ConfidenceTests(unittest.TestCase):
    def test_wilson_interval_contains_observed_rate(self):
        lo, hi = wilson_interval(40, 100, 0.95)
        self.assertLessEqual(lo, 0.4)
        self.assertGreaterEqual(hi, 0.4)

    def test_all_successes_bounded(self):
        lo, hi = wilson_interval(10, 10, 0.95)
        self.assertGreaterEqual(lo, 0)
        self.assertGreater(hi, 0.9)
        self.assertLessEqual(hi, 1)

    def test_zero_successes_bounded(self):
        lo, hi = wilson_interval(0, 10, 0.95)
        self.assertEqual(lo, 0)
        self.assertLess(hi, 1)

    def test_reject_invalid_inputs(self):
        for args in [(1, 0, .95), (3, 2, .95), (True, 2, .95), (1, 2, .97)]:
            with self.assertRaises(ConfidenceError):
                wilson_interval(*args)

    def test_compare_intervals_and_shot_totals(self):
        r = compare_proportion_intervals({"0": 60, "1": 40}, {"0": 30, "1": 70}, .95)
        self.assertEqual(r["left_shots"], 100)
        self.assertEqual(r["right_shots"], 100)
        self.assertIn("left_wilson_interval", r["outcomes"]["0"])
        self.assertLess(r["outcomes"]["0"]["delta_right_minus_left"], 0)

    def test_identical_distributions_have_zero_delta(self):
        r = compare_proportion_intervals({"0": 5, "1": 5}, {"0": 50, "1": 50})
        self.assertAlmostEqual(r["outcomes"]["0"]["delta_right_minus_left"], 0)

    def test_width_mismatch_rejected(self):
        with self.assertRaises(ConfidenceError):
            compare_proportion_intervals({"0": 2}, {"00": 2})

    def test_probability_interval_is_bounded(self):
        r = compare_proportion_intervals({"0": 10}, {"0": 8}, .99)
        for outcome in r["outcomes"].values():
            self.assertTrue(0 <= outcome["left_wilson_interval"][0] <= 1)
            self.assertTrue(0 <= outcome["right_wilson_interval"][1] <= 1)

if __name__ == "__main__":
    unittest.main()
