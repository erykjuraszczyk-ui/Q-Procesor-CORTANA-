import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_backend_compare import compare_backends

class V16BackendCompareTests(unittest.TestCase):
    def test_optional_backend_status_is_explicit(self):
        circuit = {
            "num_qubits": 1, "shots": 64, "seed": 16,
            "gates": [{"gate":"X","qubits":[0]},{"gate":"MEASURE","qubits":[0]}]
        }
        report = compare_backends(circuit)
        self.assertIn(report["status"], {"compared", "optional_backend_unavailable"})
        self.assertEqual(sum(report["internal_backend"]["counts"].values()), 64)
        if report["status"] == "compared":
            self.assertTrue(report["external_backend"]["available"])
            self.assertIn("total_variation_distance", report["comparison"])
        else:
            self.assertFalse(report["external_backend"]["available"])
            self.assertIn("qiskit-aer", report["external_backend"]["reason"])

    def test_same_noise_option_is_recorded(self):
        circuit = {
            "num_qubits": 1, "shots": 64, "seed": 16,
            "gates": [{"gate":"MEASURE","qubits":[0]}]
        }
        report = compare_backends(circuit, 0.1)
        self.assertEqual(report["circuit"]["synthetic_noise_probability"], 0.1)

if __name__ == "__main__":
    unittest.main()
