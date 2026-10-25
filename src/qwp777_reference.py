"""Small statevector reference utilities for differential validation.

The reference oracle is exponential and intentionally limited to 12 qubits.
This module computes a theoretical computational-basis probability distribution
for circuits with gates supported by qwp777_differential, excluding measurements.
"""
from __future__ import annotations
import math
from qwp777_differential import run_statevector, OracleError

class ReferenceError(ValueError):
    pass

def statevector_probabilities(num_qubits, gates):
    """Return all basis-state probabilities as zero-padded bit strings.

    Gates must not contain MEASURE; this computes the pre-measurement distribution.
    Qubit q maps to bit position q in the oracle's integer basis index, while the
    returned key is formatted in conventional big-endian display order.
    """
    if any(not isinstance(g, dict) or str(g.get("gate", "")).upper() == "MEASURE" for g in gates):
        raise ReferenceError("reference distribution accepts unitary gates only; remove MEASURE")
    try:
        _, state = run_statevector(num_qubits, gates, seed=7)
    except (OracleError, KeyError, TypeError, IndexError) as exc:
        raise ReferenceError(str(exc)) from exc
    result = {}
    for index, amplitude in enumerate(state):
        probability = float(abs(amplitude) ** 2)
        if probability > 1e-15:
            result[format(index, f"0{num_qubits}b")] = probability
    total = sum(result.values())
    if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ReferenceError(f"reference state is not normalized (sum={total})")
    return result

def validate_probability_distribution(distribution, tolerance=1e-9):
    """Validate finite probabilities in [0,1] summing to one."""
    if not isinstance(distribution, dict) or not distribution:
        raise ReferenceError("distribution must be a non-empty mapping")
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance < 0:
        raise ReferenceError("tolerance must be a finite non-negative number")
    total = 0.0
    for outcome, probability in distribution.items():
        if not isinstance(outcome, str) or not outcome or any(bit not in "01" for bit in outcome):
            raise ReferenceError("outcome keys must be non-empty bit strings")
        if isinstance(probability, bool) or not isinstance(probability, (int, float)) or not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ReferenceError("probabilities must be finite numbers in [0,1]")
        total += probability
    if not math.isclose(total, 1.0, rel_tol=tolerance, abs_tol=tolerance):
        raise ReferenceError(f"probabilities must sum to 1 (got {total})")
    return True
