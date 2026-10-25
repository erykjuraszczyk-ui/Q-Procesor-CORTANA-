"""Backend/result conformance comparison helpers."""
from __future__ import annotations
import math
from qwp777_metrics import total_variation_distance, hellinger_distance

class ConformanceError(ValueError):
    pass

def _validate_counts(counts, label):
    if not isinstance(counts, dict) or not counts:
        raise ConformanceError(f"{label} counts must be a non-empty dictionary")
    for key, value in counts.items():
        if not isinstance(key, str) or not key or any(c not in "01" for c in key):
            raise ConformanceError(f"{label} contains an invalid bitstring key")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ConformanceError(f"{label} counts must be non-negative integers")
    total = sum(counts.values())
    if total <= 0:
        raise ConformanceError(f"{label} counts must sum to a positive number")
    lengths = {len(k) for k in counts}
    if len(lengths) != 1:
        raise ConformanceError(f"{label} bitstrings must have equal lengths")
    return total

def compare_backend_counts(left, right):
    """Compare two count dictionaries without assuming equal shot totals.

    Returns TVD, Hellinger distance, per-outcome probability deltas and totals.
    The result is statistical comparison, not proof that either backend is correct.
    """
    left_total = _validate_counts(left, "left")
    right_total = _validate_counts(right, "right")
    left_lengths = {len(k) for k in left}
    right_lengths = {len(k) for k in right}
    if left_lengths != right_lengths:
        raise ConformanceError("backend bitstring widths do not match")
    lp = {k: v / left_total for k, v in left.items()}
    rp = {k: v / right_total for k, v in right.items()}
    outcomes = sorted(set(lp) | set(rp))
    left_full = {k: lp.get(k, 0.0) for k in outcomes}
    right_full = {k: rp.get(k, 0.0) for k in outcomes}
    deltas = {k: right_full[k] - left_full[k] for k in outcomes}
    return {
        "comparison_schema": "qwp777-conformance-1",
        "left_shots": left_total,
        "right_shots": right_total,
        "total_variation_distance": total_variation_distance(left_full, right_full),
        "hellinger_distance": hellinger_distance(left_full, right_full),
        "outcomes": outcomes,
        "left_probabilities": left_full,
        "right_probabilities": right_full,
        "probability_delta_right_minus_left": deltas,
        "notes": ["Statistical comparison only; not proof of backend correctness.",
                  "Different shot totals are normalized before comparison."]
    }

def compare_result_payloads(left_result, right_result):
    if not isinstance(left_result, dict) or not isinstance(right_result, dict):
        raise ConformanceError("both results must be JSON objects")
    for field in ("counts", "num_qubits", "measured_qubits"):
        if field not in left_result or field not in right_result:
            raise ConformanceError(f"both results must include {field}")
    if left_result["num_qubits"] != right_result["num_qubits"]:
        raise ConformanceError("num_qubits does not match")
    if left_result["measured_qubits"] != right_result["measured_qubits"]:
        raise ConformanceError("measured_qubits order does not match")
    return compare_backend_counts(left_result["counts"], right_result["counts"])
