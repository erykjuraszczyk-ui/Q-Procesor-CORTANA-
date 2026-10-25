"""Optional adapter for running a small QWP-777 gate list with Qiskit Aer.

Qiskit is an optional dependency. This adapter does not implement 777-qubit
universal simulation; practical limits depend on the chosen backend and circuit.
"""
from __future__ import annotations

class OptionalBackendUnavailable(RuntimeError):
    pass

def run_with_qiskit(num_qubits, gates, shots=1000, seed=7):
    """Run supported H, X, Z, CX, CZ and terminal MEASURE operations via Aer."""
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        raise OptionalBackendUnavailable(
            "Optional backend unavailable. Install compatible 'qiskit' and 'qiskit-aer' packages."
        ) from exc
    if isinstance(num_qubits, bool) or not isinstance(num_qubits, int) or not 1 <= num_qubits <= 30:
        raise ValueError("num_qubits must be an integer in 1..30 for this adapter")
    if isinstance(shots, bool) or not isinstance(shots, int) or not 1 <= shots <= 1_000_000:
        raise ValueError("shots must be an integer in 1..1000000")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32-1:
        raise ValueError("seed must be an integer in 0..4294967295")
    circuit = QuantumCircuit(num_qubits, num_qubits)
    measured, started = [], False
    for idx, item in enumerate(gates):
        gate = item["gate"].upper()
        qs = item["qubits"]
        if gate == "MEASURE":
            started = True
            q = qs[0]
            if q in measured:
                raise ValueError(f"qubit {q} measured more than once")
            measured.append(q)
            circuit.measure(q, q)
            continue
        if started:
            raise ValueError(f"gate {idx} appears after measurement started")
        if gate in ("H", "X", "Z") and len(qs) == 1:
            getattr(circuit, gate.lower())(qs[0])
        elif gate in ("CX", "CZ") and len(qs) == 2:
            getattr(circuit, gate.lower())(qs[0], qs[1])
        else:
            raise ValueError(f"unsupported gate or arity: {gate}")
    if not measured:
        raise ValueError("circuit must contain at least one MEASURE gate")
    backend = AerSimulator()
    compiled = transpile(circuit, backend, seed_transpiler=seed)
    result = backend.run(compiled, shots=shots, seed_simulator=seed).result()
    raw = result.get_counts()
    # Qiskit bitstrings are printed highest classical bit first; map only the
    # measured qubits in MEASURE first-appearance order to QWP's key convention.
    counts = {}
    for qiskit_bits, count in raw.items():
        classical = qiskit_bits.replace(" ", "")[::-1]
        key = "".join(classical[q] for q in measured)
        counts[key] = counts.get(key, 0) + count
    counts = dict(sorted(counts.items()))
    return {
        "schema_version": "qwp777-experiment-1",
        "backend": "qiskit-aer-optional",
        "num_qubits": num_qubits,
        "shots": shots,
        "seed": seed,
        "measured_qubits": measured,
        "counts": counts,
        "probabilities": {k: v/shots for k, v in counts.items()},
        "notes": ["External Qiskit Aer backend; not physical hardware.",
                  "No device-calibrated noise is configured."]
    }
