import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_experiment import run_experiment, ExperimentError, compare_distributions
from qwp777_metrics import total_variation_distance, hellinger_distance, MetricsError

class ExperimentTests(unittest.TestCase):
    def test_x_is_deterministic(self):
        r = run_experiment(1, [{"gate":"X","qubits":[0]},{"gate":"MEASURE","qubits":[0]}], shots=20, seed=2)
        self.assertEqual(r["counts"], {"1":20})
        self.assertEqual(r["probabilities"], {"1":1.0})

    def test_bell_correlations(self):
        r = run_experiment(2, [
            {"gate":"H","qubits":[0]}, {"gate":"CX","qubits":[0,1]},
            {"gate":"MEASURE","qubits":[0]}, {"gate":"MEASURE","qubits":[1]}
        ], shots=100, seed=9)
        self.assertEqual(set(r["counts"]).issubset({"00","11"}), True)
        self.assertEqual(sum(r["counts"].values()), 100)

    def test_repeatable_seed(self):
        gates = [{"gate":"H","qubits":[0]},{"gate":"MEASURE","qubits":[0]}]
        self.assertEqual(run_experiment(1,gates,shots=25,seed=17)["counts"],
                         run_experiment(1,gates,shots=25,seed=17)["counts"])

    def test_measurement_required(self):
        with self.assertRaises(ExperimentError):
            run_experiment(1,[{"gate":"H","qubits":[0]}],shots=1)

    def test_shot_range(self):
        with self.assertRaises(ExperimentError):
            run_experiment(1,[{"gate":"MEASURE","qubits":[0]}],shots=0)

    def test_tvd(self):
        self.assertAlmostEqual(total_variation_distance({"0":1,"1":1},{"0":1}), 0.5)
        self.assertAlmostEqual(total_variation_distance({"0":2},{"0":5}), 0.0)

    def test_hellinger(self):
        self.assertAlmostEqual(hellinger_distance({"0":1},{"1":1}), 1.0)
        self.assertAlmostEqual(hellinger_distance({"0":1},{"0":1}), 0.0)

    def test_metric_rejects_invalid(self):
        with self.assertRaises(MetricsError):
            total_variation_distance({"0":-1},{"0":1})

    def test_compare(self):
        result = compare_distributions({"00":8,"11":2},{"00":5,"11":5})
        self.assertAlmostEqual(result["total_variation_distance"], 0.3)
        self.assertIn("hellinger_distance", result)

if __name__ == "__main__":
    unittest.main()
