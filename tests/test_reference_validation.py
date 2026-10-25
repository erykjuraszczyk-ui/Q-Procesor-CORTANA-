import sys, unittest, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_reference import statevector_probabilities, validate_probability_distribution, ReferenceError
from qwp777_statistics import summarize_counts, StatisticsError
from qwp777_differential_validation import compare_counts_to_reference, DifferentialValidationError

class ReferenceValidationTests(unittest.TestCase):
    def test_zero_state_distribution(self):
        self.assertEqual(statevector_probabilities(2, []), {"00": 1.0})

    def test_x_distribution(self):
        self.assertEqual(statevector_probabilities(1, [{"gate":"X","qubits":[0]}]), {"1": 1.0})

    def test_bell_distribution(self):
        p = statevector_probabilities(2, [{"gate":"H","qubits":[0]},{"gate":"CX","qubits":[0,1]}])
        self.assertAlmostEqual(p.get("00", 0), 0.5)
        self.assertAlmostEqual(p.get("11", 0), 0.5)
        self.assertEqual(len(p), 2)

    def test_measurement_rejected_in_reference(self):
        with self.assertRaises(ReferenceError):
            statevector_probabilities(1, [{"gate":"MEASURE","qubits":[0]}])

    def test_distribution_validation(self):
        self.assertTrue(validate_probability_distribution({"0":0.25,"1":0.75}))
        with self.assertRaises(ReferenceError):
            validate_probability_distribution({"0":0.7})

    def test_statistics_entropy(self):
        summary = summarize_counts({"0":50,"1":50}, shots=100)
        self.assertAlmostEqual(summary["shannon_entropy_bits"], 1.0)
        self.assertEqual(summary["observed_outcomes"], 2)

    def test_statistics_deterministic_entropy(self):
        self.assertAlmostEqual(summarize_counts({"1":100})["shannon_entropy_bits"], 0.0)

    def test_statistics_reject_mismatch(self):
        with self.assertRaises(StatisticsError):
            summarize_counts({"0":4}, shots=5)

    def test_compare_bell_empirical(self):
        result = compare_counts_to_reference(
            2,
            [{"gate":"H","qubits":[0]},{"gate":"CX","qubits":[0,1]}],
            {"00":500,"11":500}
        )
        self.assertAlmostEqual(result["total_variation_distance"], 0.0)
        self.assertAlmostEqual(result["hellinger_distance"], 0.0)

    def test_compare_deterministic_empirical(self):
        result = compare_counts_to_reference(1, [{"gate":"X","qubits":[0]}], {"1":100})
        self.assertEqual(result["observed_probabilities"], {"1":1.0})
        self.assertEqual(result["reference_probabilities"], {"1":1.0})

if __name__ == "__main__":
    unittest.main()
