import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qwp777_api import __version__, API_VERSION, run_circuit, validate_result, ResultContractError
from qwp777_experiment import ExperimentError

class StableReleaseTests(unittest.TestCase):
    def test_release_metadata(self):
        self.assertEqual(__version__, "3.1.0")
        self.assertEqual(API_VERSION, "3.0")

    def test_minimal_api_config(self):
        result = run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]}], "shots": 5})
        self.assertTrue(validate_result(result))
        self.assertEqual(result["shots"], 5)
        self.assertEqual(result["release"], "3.1.0")

    def test_api_defaults(self):
        result = run_circuit({"num_qubits": 1, "gates": [{"gate":"X","qubits":[0]},{"gate":"MEASURE","qubits":[0]}]})
        self.assertEqual(result["shots"], 1000)
        self.assertEqual(result["counts"], {"1": 1000})

    def test_unknown_config_field_rejected(self):
        with self.assertRaises(ValueError):
            run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]}], "shot": 3})

    def test_measurement_must_be_terminal(self):
        with self.assertRaises(ExperimentError):
            run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]},{"gate":"X","qubits":[0]}]})

    def test_each_qubit_measured_once(self):
        with self.assertRaises(ExperimentError):
            run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]},{"gate":"MEASURE","qubits":[0]}]})

    def test_result_count_invariant(self):
        result = run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]}], "shots": 4})
        invalid = copy.deepcopy(result)
        invalid["counts"] = {"0": 1}
        with self.assertRaises(ResultContractError):
            validate_result(invalid)


    def test_result_rejects_malformed_measured_indices(self):
        result = run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]}], "shots": 4})
        invalid = copy.deepcopy(result)
        invalid["measured_qubits"] = [[]]
        with self.assertRaises(ResultContractError):
            validate_result(invalid)

    def test_result_probability_invariant(self):
        result = run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]}], "shots": 4})
        invalid = copy.deepcopy(result)
        invalid["probabilities"] = {"0": 0.5}
        with self.assertRaises(ResultContractError):
            validate_result(invalid)

    def test_result_outcome_shape(self):
        result = run_circuit({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]}], "shots": 4})
        invalid = copy.deepcopy(result)
        invalid["counts"] = {"00": 4}
        invalid["probabilities"] = {"00": 1.0}
        with self.assertRaises(ResultContractError):
            validate_result(invalid)

if __name__ == "__main__":
    unittest.main()
