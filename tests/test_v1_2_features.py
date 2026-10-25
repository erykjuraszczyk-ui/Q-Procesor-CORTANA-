import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_noise import apply_bit_flip_noise, NoiseModelError
from qwp777_experiment import run_experiment, ExperimentError
from qwp777_qiskit_adapter import run_with_qiskit, OptionalBackendUnavailable

class V12FeaturesTests(unittest.TestCase):
    def test_zero_noise_keeps_counts(self):
        self.assertEqual(apply_bit_flip_noise({"00": 4, "11": 3}, 0, 1), {"00": 4, "11": 3})

    def test_full_noise_flips_bits(self):
        self.assertEqual(apply_bit_flip_noise({"00": 2, "10": 1}, 1, 1), {"01": 1, "11": 2})

    def test_noise_reproducible(self):
        data = {"000": 20, "111": 20}
        self.assertEqual(apply_bit_flip_noise(data, 0.2, 42), apply_bit_flip_noise(data, 0.2, 42))

    def test_noise_preserves_total_shots(self):
        result = apply_bit_flip_noise({"00": 7, "11": 9}, 0.3, 8)
        self.assertEqual(sum(result.values()), 16)

    def test_noise_rejects_bad_probability(self):
        with self.assertRaises(NoiseModelError):
            apply_bit_flip_noise({"0": 1}, 1.1)

    def test_experiment_noise_metadata(self):
        gates = [{"gate":"X","qubits":[0]}, {"gate":"MEASURE","qubits":[0]}]
        result = run_experiment(1, gates, shots=20, seed=9, noise_probability=0)
        self.assertEqual(result["noise_model"]["probability"], 0.0)
        self.assertEqual(result["counts"], {"1": 20})

    def test_experiment_rejects_bad_noise(self):
        with self.assertRaises(ExperimentError):
            run_experiment(1, [{"gate":"MEASURE","qubits":[0]}], 10, 1, 2.0)

    def test_optional_backend_validation_or_dependency_message(self):
        # If installed, run a tiny deterministic circuit; otherwise ensure the error is actionable.
        try:
            result = run_with_qiskit(1, [{"gate":"X","qubits":[0]}, {"gate":"MEASURE","qubits":[0]}], 10, 1)
        except OptionalBackendUnavailable as exc:
            self.assertIn("qiskit-aer", str(exc))
        else:
            self.assertEqual(result["counts"], {"1": 10})

if __name__ == "__main__":
    unittest.main()
