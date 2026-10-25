"""Stable public API surface for QWP-777."""
from __future__ import annotations
from qwp777_version import __version__, API_VERSION
from qwp777_experiment import run_experiment, compare_distributions, ExperimentError
from qwp777_contract import validate_result, ResultContractError
from qwp777_validation import validate_gates, CircuitSchemaError
from qwp777_statistics import summarize_counts, StatisticsError
from qwp777_reference import statevector_probabilities, validate_probability_distribution, ReferenceError
from qwp777_differential_validation import compare_counts_to_reference, DifferentialValidationError

def run_circuit(config):
    """Run a circuit from a config mapping.

    Required: num_qubits, gates. Optional: shots (1000), seed (7).
    Returns a JSON-serializable result mapping.
    """
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    allowed = {"num_qubits", "gates", "shots", "seed"}
    unknown = set(config) - allowed
    if unknown:
        raise ValueError("unsupported config fields: " + ", ".join(sorted(unknown)))
    if "num_qubits" not in config or "gates" not in config:
        raise ValueError("config requires num_qubits and gates")
    result = run_experiment(
        config["num_qubits"], config["gates"],
        config.get("shots", 1000), config.get("seed", 7)
    )
    validate_result(result)
    return result

__all__ = [
    "__version__", "API_VERSION", "run_circuit", "run_experiment",
    "compare_distributions", "validate_gates", "validate_result",
    "ExperimentError", "CircuitSchemaError", "ResultContractError",
    "summarize_counts", "StatisticsError", "statevector_probabilities",
    "validate_probability_distribution", "ReferenceError",
    "compare_counts_to_reference", "DifferentialValidationError"
]
