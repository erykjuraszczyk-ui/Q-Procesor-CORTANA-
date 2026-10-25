import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qwp777_soak import run_soak, SoakError, main

CIRCUIT = {"num_qubits": 1, "shots": 3, "seed": 12,
           "gates": [{"gate": "X", "qubits": [0]}, {"gate": "MEASURE", "qubits": [0]}]}

class V23SoakTests(unittest.TestCase):
    def test_soak_report_has_valid_samples_and_runtime_memory_fields(self):
        report = run_soak(CIRCUIT, iterations=4, warmup=1, max_work_units=100000)
        self.assertEqual(report["report_schema"], "qwp777-soak-report-1")
        self.assertEqual(report["software"]["release"], "3.1.0")
        self.assertEqual(report["summary"]["iterations_completed"], 4)
        self.assertTrue(report["summary"]["all_count_totals_valid"])
        self.assertEqual(len(report["samples"]), 4)
        self.assertIn("maximum_sampled", report["summary"]["rss_current_bytes"])
        self.assertGreaterEqual(report["summary"]["python_tracemalloc_peak_bytes_overall"], 0)
        json.dumps(report)

    def test_workload_budget_prevents_unplanned_heavy_soak(self):
        with self.assertRaises(SoakError):
            run_soak(CIRCUIT, iterations=10, warmup=0, max_work_units=10)

    def test_iterations_and_shots_are_validated(self):
        for iterations in (0, -1, 10001, True):
            with self.subTest(iterations=iterations), self.assertRaises(SoakError):
                run_soak(CIRCUIT, iterations=iterations, warmup=0)
        with self.assertRaises(SoakError):
            run_soak(CIRCUIT, iterations=1, warmup=0, shots=0)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            circuit_path, report_path = Path(tmp)/"circuit.json", Path(tmp)/"soak.json"
            circuit_path.write_text(json.dumps(CIRCUIT), encoding="utf-8")
            code = main([str(circuit_path), "--iterations", "2", "--warmup", "0",
                         "--max-work-units", "100000", "-o", str(report_path)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(report_path.read_text(encoding="utf-8"))["summary"]["iterations_completed"], 2)

if __name__ == "__main__":
    unittest.main()
