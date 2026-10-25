"""Compare experiment counts against a small exact statevector reference."""
from __future__ import annotations
from qwp777_metrics import total_variation_distance, hellinger_distance
from qwp777_reference import statevector_probabilities, ReferenceError
from qwp777_statistics import summarize_counts, StatisticsError

class DifferentialValidationError(ValueError):
    pass

def compare_counts_to_reference(num_qubits, unitary_gates, counts):
    """Compare observed counts with ideal reference probabilities.

    `unitary_gates` must exclude measurement operations. `counts` uses output
    bit strings in the same displayed qubit order as the reference distribution.
    Intended only for circuits of up to 12 qubits.
    """
    try:
        reference = statevector_probabilities(num_qubits, unitary_gates)
        observed = summarize_counts(counts)["probabilities"]
    except (ReferenceError, StatisticsError) as exc:
        raise DifferentialValidationError(str(exc)) from exc
    return {
        "reference_backend": "qwp777-small-statevector-oracle",
        "num_qubits": num_qubits,
        "observed_shots": sum(counts.values()),
        "reference_probabilities": reference,
        "observed_probabilities": observed,
        "total_variation_distance": total_variation_distance(observed, reference),
        "hellinger_distance": hellinger_distance(observed, reference)
    }
