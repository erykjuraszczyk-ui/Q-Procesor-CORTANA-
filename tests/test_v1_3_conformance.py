import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_conformance import compare_backend_counts, compare_result_payloads, ConformanceError

class V13ConformanceTests(unittest.TestCase):
    def test_identical_distribution_zero_distance(self):
        r = compare_backend_counts({"00": 50, "11": 50}, {"00": 5, "11": 5})
        self.assertAlmostEqual(r["total_variation_distance"], 0.0)
        self.assertAlmostEqual(r["hellinger_distance"], 0.0)

    def test_disjoint_distribution_unit_tvd(self):
        r = compare_backend_counts({"0": 10}, {"1": 10})
        self.assertAlmostEqual(r["total_variation_distance"], 1.0)

    def test_probability_delta_sign(self):
        r = compare_backend_counts({"0": 3, "1": 1}, {"0": 1, "1": 3})
        self.assertLess(r["probability_delta_right_minus_left"]["0"], 0)
        self.assertGreater(r["probability_delta_right_minus_left"]["1"], 0)

    def test_different_shot_totals_normalized(self):
        r = compare_backend_counts({"0": 100, "1": 100}, {"0": 3, "1": 3})
        self.assertAlmostEqual(r["total_variation_distance"], 0.0)
        self.assertEqual(r["left_shots"], 200)
        self.assertEqual(r["right_shots"], 6)

    def test_reject_empty_or_zero_counts(self):
        for bad in ({}, {"0": 0}):
            with self.assertRaises(ConformanceError):
                compare_backend_counts(bad, {"0": 1})

    def test_reject_mixed_width(self):
        with self.assertRaises(ConformanceError):
            compare_backend_counts({"0": 1, "00": 2}, {"0": 3})

    def test_payload_metadata_mismatch(self):
        a = {"counts":{"0":2}, "num_qubits":1, "measured_qubits":[0]}
        b = {"counts":{"0":2}, "num_qubits":2, "measured_qubits":[0]}
        with self.assertRaises(ConformanceError):
            compare_result_payloads(a, b)

    def test_payload_match(self):
        a = {"counts":{"00":5,"11":5}, "num_qubits":2, "measured_qubits":[0,1]}
        b = {"counts":{"00":4,"11":6}, "num_qubits":2, "measured_qubits":[0,1]}
        r = compare_result_payloads(a,b)
        self.assertGreater(r["total_variation_distance"], 0)

if __name__ == "__main__":
    unittest.main()
