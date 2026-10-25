import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qwp777_soak import run_soak
from qwp777_stability_analyze import analyze_soak_report, StabilityAnalysisError
from qwp777_device_compare import compare_soak_reports, DeviceCompareError

CIRCUIT = {"num_qubits": 1, "shots": 4, "seed": 19,
           "gates": [{"gate": "X", "qubits": [0]}, {"gate": "MEASURE", "qubits": [0]}]}

class V24StabilityTests(unittest.TestCase):
    def test_stability_analysis_reports_insufficient_samples(self):
        soak = run_soak(CIRCUIT, iterations=3, warmup=0, max_work_units=1000)
        report = analyze_soak_report(soak)
        self.assertEqual(report["report_schema"], "qwp777-stability-analysis-1")
        self.assertEqual(report["summary"]["status"], "insufficient_data")
        self.assertEqual(report["summary"]["findings_total"], 0)
        json.dumps(report)

    def test_stability_analysis_can_detect_python_allocation_growth(self):
        soak = run_soak(CIRCUIT, iterations=6, warmup=0, max_work_units=1000)
        synthetic = copy.deepcopy(soak)
        for i, sample in enumerate(synthetic["samples"]):
            sample["python_tracemalloc_current_bytes_after_cleanup"] = 1000 + i * 300_000
            sample["rss_current_bytes_after_cleanup"] = None
        report = analyze_soak_report(synthetic, min_samples=5, python_growth_threshold_bytes=500_000)
        self.assertEqual(report["summary"]["status"], "anomaly_candidate")
        self.assertEqual(report["summary"]["findings"][0]["id"], "python_tracemalloc_growth")
        self.assertIn("not proof", report["summary"]["interpretation"])

    def test_stability_analysis_can_detect_rss_growth(self):
        soak = run_soak(CIRCUIT, iterations=6, warmup=0, max_work_units=1000)
        synthetic = copy.deepcopy(soak)
        for i, sample in enumerate(synthetic["samples"]):
            sample["python_tracemalloc_current_bytes_after_cleanup"] = 1000
            sample["rss_current_bytes_after_cleanup"] = 1_000_000 + i * 1_000_000
        report = analyze_soak_report(synthetic, min_samples=5, rss_growth_threshold_bytes=2_000_000)
        self.assertEqual(report["summary"]["status"], "anomaly_candidate")
        self.assertIn("rss_growth", [finding["id"] for finding in report["summary"]["findings"]])

    def test_stability_analysis_rejects_negative_thresholds(self):
        soak = run_soak(CIRCUIT, iterations=3, warmup=0, max_work_units=1000)
        with self.assertRaises(StabilityAnalysisError):
            analyze_soak_report(soak, python_growth_threshold_bytes=-1)

    def test_stability_analysis_rejects_malformed_report(self):
        with self.assertRaises(StabilityAnalysisError):
            analyze_soak_report({"report_schema": "wrong", "samples": []})

    def test_cross_device_comparison_requires_same_workload(self):
        old = run_soak(CIRCUIT, iterations=3, warmup=0, max_work_units=1000)
        new = run_soak({**CIRCUIT, "shots": 5}, iterations=3, warmup=0, max_work_units=1000)
        with self.assertRaises(DeviceCompareError):
            compare_soak_reports(old, new)

    def test_cross_device_comparison_reports_resource_deltas(self):
        old = run_soak(CIRCUIT, iterations=4, warmup=0, max_work_units=1000)
        new = copy.deepcopy(old)
        new["runtime"] = dict(old["runtime"])
        new["runtime"]["machine_architecture"] = "test-device"
        for sample in new["samples"]:
            sample["duration_seconds"] *= 1.5
            sample["python_tracemalloc_current_bytes_after_cleanup"] += 128
        comparison = compare_soak_reports(old, new)
        self.assertEqual(comparison["report_schema"], "qwp777-device-comparison-1")
        self.assertTrue(comparison["summary"]["cross_host_comparison"])
        self.assertAlmostEqual(comparison["median_duration_seconds"]["change_percent"], 50.0)
        self.assertIn("maximum_sampled_rss_bytes", comparison)

if __name__ == "__main__":
    unittest.main()
