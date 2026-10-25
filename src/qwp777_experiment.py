"""Repeated-shot runner for QWP-777's Clifford stabilizer prototype."""
from __future__ import annotations
import argparse, json, sys
from collections import Counter
from pathlib import Path
from qwp777_stabilizer import StabilizerSimulator, StabilizerError
from qwp777_validation import validate_gates, CircuitSchemaError
from qwp777_metrics import total_variation_distance, hellinger_distance
from qwp777_version import __version__, API_VERSION, RESULT_SCHEMA_VERSION
from qwp777_noise import apply_bit_flip_noise, NoiseModelError

class ExperimentError(ValueError): pass

def run_experiment(num_qubits, gates, shots=1000, seed=7, noise_probability=0.0):
    """Run a circuit from a fresh |0...0> state for each shot.

    The circuit must contain explicit MEASURE gates. Optional noise is synthetic
    post-processing, not a calibrated physical-device model.
    """
    validate_gates(gates, num_qubits)
    if isinstance(shots, bool) or not isinstance(shots, int) or not 1 <= shots <= 1_000_000:
        raise ExperimentError("shots must be an integer in 1..1000000")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32-1:
        raise ExperimentError("seed must be an integer in 0..4294967295")
    measured_qubits = []
    measurement_started = False
    for index, item in enumerate(gates):
        gate = item["gate"].upper()
        if gate == "MEASURE":
            measurement_started = True
            q = item["qubits"][0]
            if q in measured_qubits:
                raise ExperimentError(f"qubit {q} is measured more than once; v1.0.0 supports one terminal measurement per qubit")
            measured_qubits.append(q)
        elif measurement_started:
            raise ExperimentError(f"gate {index} appears after measurement started; dynamic circuits are not supported")
    if not measured_qubits:
        raise ExperimentError("circuit must contain at least one MEASURE gate")
    # Each shot gets a deterministic but distinct seed derived from the root seed.
    counts = Counter()
    for shot in range(shots):
        sim = StabilizerSimulator(num_qubits, seed=(seed + shot) % (2**32))
        # The runner only needs measurements; avoid allocating a second O(n^2) tableau copy per shot.
        result = sim.run(gates, include_tableau=False)
        # Keys follow the measurement-gate first-appearance order.
        key = "".join(str(result.measurements[q]) for q in measured_qubits)
        counts[key] += 1
    ideal_sampled = dict(sorted(counts.items()))
    if isinstance(noise_probability, bool) or not isinstance(noise_probability, (int, float)) or not 0.0 <= noise_probability <= 1.0:
        raise ExperimentError("noise_probability must be a number in [0, 1]")
    ordered = apply_bit_flip_noise(ideal_sampled, float(noise_probability), seed=(seed ^ 0x5A17)) if noise_probability > 0 else ideal_sampled
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "release": __version__,
        "api_version": API_VERSION,
        "backend": "qwp777-stabilizer-prototype",
        "num_qubits": num_qubits,
        "shots": shots,
        "seed": seed,
        "noise_model": {"type": "synthetic-independent-bit-flip", "probability": float(noise_probability)},
        "measured_qubits": measured_qubits,
        "counts": ordered,
        "probabilities": {k: v/shots for k, v in ordered.items()},
        "notes": [
            "Software prototype; not a physical quantum processor.",
            "Optional noise is synthetic post-processing, not calibrated device noise.",
            "Stabilizer backend is intended for Clifford circuits."
        ]
    }

def compare_distributions(observed, reference):
    return {
        "total_variation_distance": total_variation_distance(observed, reference),
        "hellinger_distance": hellinger_distance(observed, reference)
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a QWP-777 Clifford circuit experiment from JSON.")
    parser.add_argument("circuit", help="JSON file with num_qubits, gates, optional shots and seed")
    parser.add_argument("--noise-probability", type=float, default=0.0,
                        help="synthetic measurement bit-flip probability in [0, 1] (default: 0)")
    parser.add_argument("-o", "--output", help="write result JSON to this path")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.circuit).read_text(encoding="utf-8"))
        result = run_experiment(payload["num_qubits"], payload["gates"],
                                payload.get("shots", 1000), payload.get("seed", 7),
                                args.noise_probability)
        rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, CircuitSchemaError, StabilizerError, ExperimentError, NoiseModelError) as exc:
        print(f"qwp777-experiment: error: {exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
