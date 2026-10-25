import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qwp777_profile import profile_circuit, ProfileError, main
from qwp777_runtime_info import collect_runtime_info

CIRCUIT = {"num_qubits": 1, "shots": 4, "seed": 11,
           "gates": [{"gate": "MEASURE", "qubits": [0]}]}

class V21ProfilingTests(unittest.TestCase):
    def test_profile_report_schema_and_counts(self):
        report = profile_circuit(CIRCUIT, repeats=2)
        self.assertEqual(report["report_schema"], "qwp777-profile-report-1")
        self.assertEqual(report["software"]["release"], "3.1.0")
        self.assertEqual(len(report["timing_seconds"]["samples"]), 2)
        self.assertGreaterEqual(report["timing_seconds"]["minimum"], 0)
        self.assertGreaterEqual(report["python_tracemalloc_peak_bytes"]["maximum"], 0)
        self.assertEqual(report["circuit"]["shots_per_repeat"], 4)

    def test_profile_shots_override(self):
        report = profile_circuit(CIRCUIT, repeats=1, shots=2)
        self.assertEqual(report["circuit"]["shots_per_repeat"], 2)

    def test_repeats_validated(self):
        for bad in (0, -1, 101, True, 1.5):
            with self.subTest(repeats=bad), self.assertRaises(ProfileError):
                profile_circuit(CIRCUIT, repeats=bad)

    def test_shots_validated(self):
        for bad in (0, -1, 1_000_001, True, 2.5):
            with self.subTest(shots=bad), self.assertRaises(ProfileError):
                profile_circuit(CIRCUIT, repeats=1, shots=bad)

    def test_payload_shape_validated(self):
        with self.assertRaises(ProfileError):
            profile_circuit({}, repeats=1)

    def test_runtime_info_json_serializable(self):
        info = collect_runtime_info()
        json.dumps(info)
        self.assertTrue(info["python_version"])
        self.assertTrue(info["os_system"])
        self.assertGreater(info["logical_cpu_count"] or 0, 0)

    def test_cli_writes_json_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            circuit = Path(tmp) / "circuit.json"
            target = Path(tmp) / "profile.json"
            circuit.write_text(json.dumps(CIRCUIT), encoding="utf-8")
            code = main([str(circuit), "--repeats", "1", "-o", str(target)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["report_schema"], "qwp777-profile-report-1")

if __name__ == "__main__":
    unittest.main()
