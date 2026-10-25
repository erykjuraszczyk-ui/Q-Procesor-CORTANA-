"""Compare the built-in simulator with the optional Qiskit Aer backend."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path
from qwp777_experiment import run_experiment
from qwp777_qiskit_adapter import run_with_qiskit, OptionalBackendUnavailable
from qwp777_noise import apply_bit_flip_noise
from qwp777_conformance import compare_backend_counts, ConformanceError
from qwp777_version import __version__

def compare_backends(payload, noise_probability=0.0):
    if not isinstance(payload, dict):
        raise ValueError("circuit input must be a JSON object")
    for field in ("num_qubits", "gates"):
        if field not in payload:
            raise ValueError(f"circuit input requires {field}")
    shots = payload.get("shots", 1000)
    seed = payload.get("seed", 7)
    if isinstance(noise_probability, bool) or not isinstance(noise_probability, (int, float)) or not 0 <= noise_probability <= 1:
        raise ValueError("noise_probability must be a number in [0, 1]")
    base = {
        "report_schema": "qwp777-backend-comparison-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software_release": __version__,
        "circuit": {
            "num_qubits": payload["num_qubits"], "gates": payload["gates"],
            "shots": shots, "seed": seed, "synthetic_noise_probability": float(noise_probability)
        },
        "notes": [
            "Both backends run on classical computing hardware; Qiskit Aer is not a physical QPU.",
            "Random streams differ across backends; sampled counts need not match exactly.",
            "A successful statistical comparison does not prove universal backend equivalence."
        ]
    }
    internal = run_experiment(payload["num_qubits"], payload["gates"], shots, seed, noise_probability)
    base["internal_backend"] = {
        "name": internal["backend"], "counts": internal["counts"], "probabilities": internal["probabilities"]
    }
    try:
        external = run_with_qiskit(payload["num_qubits"], payload["gates"], shots, seed)
    except OptionalBackendUnavailable as exc:
        base["status"] = "optional_backend_unavailable"
        base["external_backend"] = {"name": "qiskit-aer-optional", "available": False, "reason": str(exc)}
        return base
    external_counts = external["counts"]
    if noise_probability > 0:
        external_counts = apply_bit_flip_noise(external_counts, float(noise_probability), seed=(seed ^ 0x5A17))
    comparison = compare_backend_counts(internal["counts"], external_counts)
    base["external_backend"] = {
        "name": external["backend"], "available": True, "counts": external_counts,
        "probabilities": {key: value/shots for key, value in external_counts.items()}
    }
    base["comparison"] = comparison
    base["status"] = "compared"
    return base

def main(argv=None):
    parser = argparse.ArgumentParser(description="Compare QWP-777 with the optional Qiskit Aer backend.")
    parser.add_argument("circuit", help="JSON file with num_qubits, gates, optional shots and seed")
    parser.add_argument("--noise-probability", type=float, default=0.0,
                        help="apply same synthetic measurement bit-flip probability to both count samples")
    parser.add_argument("-o", "--output", help="write report JSON to this path")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(Path(args.circuit).read_text(encoding="utf-8"))
        report = compare_backends(payload, args.noise_probability)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, json.JSONDecodeError, ValueError, ConformanceError, TypeError, KeyError) as exc:
        print(f"qwp777-backend-compare: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
