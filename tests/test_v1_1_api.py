import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import qwp777_api

class V11ApiTests(unittest.TestCase):
    def test_version(self):
        self.assertEqual(qwp777_api.__version__, "3.1.0")
        self.assertEqual(qwp777_api.API_VERSION, "3.0")

    def test_new_public_functions(self):
        for name in ("summarize_counts", "statevector_probabilities",
                     "validate_probability_distribution", "compare_counts_to_reference"):
            self.assertTrue(callable(getattr(qwp777_api, name)))

    def test_entropy_api(self):
        stats = qwp777_api.summarize_counts({"0": 5, "1": 5})
        self.assertAlmostEqual(stats["shannon_entropy_bits"], 1.0)

if __name__ == "__main__":
    unittest.main()
