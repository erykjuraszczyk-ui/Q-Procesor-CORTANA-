import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qwp777_benchmark import run_scaling_benchmark, BenchmarkError, main
from qwp777_memory import estimate_tableau_memory, MemoryEstimateError
from qwp777_stabilizer import StabilizerSimulator, StabilizerError
from qwp777_experiment import run_experiment

class V22ScalingMemoryTests(unittest.TestCase):
    def test_tableau_memory_estimate_valid_and_monotone(self):
        one = estimate_tableau_memory(1)
        eight = estimate_tableau_memory(8)
        self.assertGreater(one["estimated_list_container_bytes"], 0)
        self.assertEqual(eight["matrix_slots_total"], 4 * 8 * 8)
        self.assertGreater(eight["estimated_list_container_bytes"], one["estimated_list_container_bytes"])

    def test_memory_estimate_rejects_invalid_qubits(self):
        for value in (0, 778, True, 1.5, "2"):
            with self.subTest(value=value), self.assertRaises(MemoryEstimateError):
                estimate_tableau_memory(value)

    def test_simulator_default_preserves_final_tableau(self):
        gates = [{"gate": "MEASURE", "qubits": [0]}]
        result = StabilizerSimulator(1, seed=1).run(gates)
        self.assertEqual(len(result.final_tableau), 2)

    def test_simulator_can_skip_final_tableau_copy(self):
        gates = [{"gate": "MEASURE", "qubits": [0]}]
        result = StabilizerSimulator(1, seed=1).run(gates, include_tableau=False)
        self.assertEqual(result.final_tableau, [])
        with self.assertRaises(StabilizerError):
            StabilizerSimulator(1).run(gates, include_tableau=1)

    def test_experiment_results_unchanged_after_memory_optimization(self):
        gates = [{"gate": "H", "qubits": [0]}, {"gate": "MEASURE", "qubits": [0]}]
        result = run_experiment(1, gates, 32, 314, 0.0)
        self.assertEqual(result["shots"], 32)
        self.assertEqual(sum(result["counts"].values()), 32)
        self.assertEqual(result["schema_version"], "qwp777-experiment-1")

    def test_small_scaling_benchmark(self):
        report = run_scaling_benchmark([1, 2], [1, 3], repeats=1, seed=4, max_work_units=100000)
        self.assertEqual(report["report_schema"], "qwp777-benchmark-report-1")
        self.assertEqual(report["summary"]["cases_total"], 4)
        self.assertEqual(report["summary"]["cases_failed"], 0)
        self.assertTrue(all(row["result_invariants"]["passed"] for row in report["cases"]))

    def test_work_budget_prevents_unbounded_benchmark(self):
        with self.assertRaises(BenchmarkError):
            run_scaling_benchmark([32], [1000], repeats=2, max_work_units=1)

    def test_benchmark_validates_values(self):
        with self.assertRaises(BenchmarkError):
            run_scaling_benchmark([0], [1], repeats=1)
        with self.assertRaises(BenchmarkError):
            run_scaling_benchmark([1], [1], repeats=0)

    def test_benchmark_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "benchmark.json"
            code = main(["--qubits", "1,2", "--shots", "1", "--repeats", "1", "--max-work-units", "100000", "-o", str(target)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["summary"]["cases_passed"], 2)

if __name__ == "__main__":
    unittest.main()
