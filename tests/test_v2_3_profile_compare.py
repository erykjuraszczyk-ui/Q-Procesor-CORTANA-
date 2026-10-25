import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qwp777_profile import profile_circuit
from qwp777_profile_compare import compare_profiles, ProfileCompareError

CIRCUIT = {"num_qubits": 1, "shots": 3, "seed": 4,
           "gates": [{"gate": "MEASURE", "qubits": [0]}]}

class V23ProfileCompareTests(unittest.TestCase):
    def test_compares_identical_workload_and_returns_deltas(self):
        old = profile_circuit(CIRCUIT, repeats=2)
        new = profile_circuit(CIRCUIT, repeats=2)
        report = compare_profiles(old, new)
        self.assertEqual(report["report_schema"], "qwp777-profile-comparison-1")
        self.assertIn("change_percent", report["timing_median_seconds"])
        self.assertTrue(report["environment"]["same_host_fingerprint"])

    def test_rejects_different_workloads(self):
        old = profile_circuit(CIRCUIT, repeats=1)
        different = profile_circuit({**CIRCUIT, "shots": 4}, repeats=1)
        with self.assertRaises(ProfileCompareError):
            compare_profiles(old, different)

if __name__ == "__main__":
    unittest.main()
