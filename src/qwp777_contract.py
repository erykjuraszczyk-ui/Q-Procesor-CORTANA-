"""Validation utilities for QWP-777 result payloads."""
from __future__ import annotations
import math
from qwp777_version import RESULT_SCHEMA_VERSION

class ResultContractError(ValueError):
    """Raised when a result payload violates the documented JSON contract."""

_REQUIRED = {
    "schema_version", "release", "api_version", "backend", "num_qubits",
    "shots", "seed", "measured_qubits", "counts", "probabilities", "notes"
}

def validate_result(result):
    """Validate basic shape and arithmetic invariants for a runner result.

    Returns True when valid; raises ResultContractError otherwise.
    """
    if not isinstance(result, dict):
        raise ResultContractError("result must be an object")
    missing = _REQUIRED - result.keys()
    if missing:
        raise ResultContractError("missing result fields: " + ", ".join(sorted(missing)))
    if result["schema_version"] != RESULT_SCHEMA_VERSION:
        raise ResultContractError("unsupported result schema_version")
    if not isinstance(result["release"], str) or not result["release"]:
        raise ResultContractError("release must be a non-empty string")
    if result["api_version"] not in {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9", "2.0", "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "3.0"}:
        raise ResultContractError("unsupported api_version")
    n, shots, seed = result["num_qubits"], result["shots"], result["seed"]
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 777:
        raise ResultContractError("num_qubits must be an integer in 1..777")
    if isinstance(shots, bool) or not isinstance(shots, int) or shots < 1:
        raise ResultContractError("shots must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32-1:
        raise ResultContractError("seed is out of range")
    measured = result["measured_qubits"]
    if not isinstance(measured, list) or not measured:
        raise ResultContractError("measured_qubits must be a non-empty list")
    if any(isinstance(q, bool) or not isinstance(q, int) or not 0 <= q < n for q in measured):
        raise ResultContractError("measured_qubits contains an invalid index")
    if len(set(measured)) != len(measured):
        raise ResultContractError("measured_qubits must not contain duplicates")
    if not isinstance(result["backend"], str) or not result["backend"]:
        raise ResultContractError("backend must be a non-empty string")
    counts, probs = result["counts"], result["probabilities"]
    if not isinstance(counts, dict) or not counts:
        raise ResultContractError("counts must be a non-empty object")
    if not isinstance(probs, dict) or set(probs) != set(counts):
        raise ResultContractError("probabilities keys must match counts keys")
    total = 0
    for key, count in counts.items():
        if not isinstance(key, str) or len(key) != len(measured) or any(c not in "01" for c in key):
            raise ResultContractError("each outcome key must be a bit string matching measured_qubits length")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ResultContractError("each count must be a positive integer")
        total += count
        p = probs[key]
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or p < 0 or p > 1:
            raise ResultContractError("each probability must be finite and in [0, 1]")
        if not math.isclose(p, count / shots, rel_tol=1e-9, abs_tol=1e-9):
            raise ResultContractError("probability does not match count / shots")
    if total != shots:
        raise ResultContractError("sum(counts) must equal shots")
    if not isinstance(result["notes"], list) or any(not isinstance(note, str) for note in result["notes"]):
        raise ResultContractError("notes must be a list of strings")
    return True
