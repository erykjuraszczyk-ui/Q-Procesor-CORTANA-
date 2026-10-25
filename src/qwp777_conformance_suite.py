"""Built-in golden-circuit conformance suite for the QWP-777 prototype."""
from __future__ import annotations
from qwp777_experiment import run_experiment

def run_conformance_suite(shots=512, seed=1777):
    """Run deterministic and structural checks against known circuit properties."""
    if isinstance(shots, bool) or not isinstance(shots, int) or not 64 <= shots <= 100000:
        raise ValueError("shots must be an integer in 64..100000")
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32-1:
        raise ValueError("seed must be an integer in 0..4294967295")

    def circuit(n, gates):
        return run_experiment(n, gates, shots=shots, seed=seed)

    cases = []
    def add_case(name, result, checks):
        evaluated = []
        for description, passed, detail in checks:
            evaluated.append({"check": description, "passed": bool(passed), "detail": detail})
        cases.append({
            "name": name, "passed": all(c["passed"] for c in evaluated),
            "checks": evaluated, "observed_counts": result["counts"],
            "shots": result["shots"]
        })

    zero = circuit(1, [{"gate":"MEASURE","qubits":[0]}])
    add_case("zero-state", zero, [
        ("all outcomes are zero", set(zero["counts"]) == {"0"}, list(zero["counts"])),
        ("shot total is preserved", sum(zero["counts"].values()) == shots, sum(zero["counts"].values()))
    ])

    xstate = circuit(1, [{"gate":"X","qubits":[0]}, {"gate":"MEASURE","qubits":[0]}])
    add_case("pauli-x-deterministic", xstate, [
        ("all outcomes are one", set(xstate["counts"]) == {"1"}, list(xstate["counts"])),
        ("shot total is preserved", sum(xstate["counts"].values()) == shots, sum(xstate["counts"].values()))
    ])

    bell_gates = [
        {"gate":"H","qubits":[0]}, {"gate":"CX","qubits":[0,1]},
        {"gate":"MEASURE","qubits":[0]}, {"gate":"MEASURE","qubits":[1]}
    ]
    bell = circuit(2, bell_gates)
    bell_values = list(bell["counts"].values())
    add_case("bell-state-correlation", bell, [
        ("only correlated outcomes 00 and 11 occur", set(bell["counts"]).issubset({"00","11"}), sorted(bell["counts"])),
        ("both correlated outcomes are sampled", set(bell["counts"]) == {"00","11"}, sorted(bell["counts"])),
        ("neither correlated outcome is vanishingly rare", all(v >= shots * 0.10 for v in bell_values), bell["counts"])
    ])

    ghz_gates = [
        {"gate":"H","qubits":[0]}, {"gate":"CX","qubits":[0,1]}, {"gate":"CX","qubits":[0,2]},
        {"gate":"MEASURE","qubits":[0]}, {"gate":"MEASURE","qubits":[1]}, {"gate":"MEASURE","qubits":[2]}
    ]
    ghz = circuit(3, ghz_gates)
    ghz_values = list(ghz["counts"].values())
    add_case("ghz-three-qubit-correlation", ghz, [
        ("only 000 and 111 occur", set(ghz["counts"]).issubset({"000","111"}), sorted(ghz["counts"])),
        ("both expected outcomes are sampled", set(ghz["counts"]) == {"000","111"}, sorted(ghz["counts"])),
        ("neither expected outcome is vanishingly rare", all(v >= shots * 0.10 for v in ghz_values), ghz["counts"])
    ])

    hstate = circuit(1, [{"gate":"H","qubits":[0]}, {"gate":"MEASURE","qubits":[0]}])
    p_one = hstate["counts"].get("1", 0) / shots
    add_case("hadamard-balanced-sampling", hstate, [
        ("only 0 and 1 occur", set(hstate["counts"]).issubset({"0","1"}), sorted(hstate["counts"])),
        ("empirical probability of 1 is within broad 0.35..0.65 band", 0.35 <= p_one <= 0.65, p_one)
    ])

    # Separate direct call with p=1 makes every sampled bit flip.
    noisy = run_experiment(1, [{"gate":"MEASURE","qubits":[0]}], shots=shots,
                           seed=seed, noise_probability=1.0)
    add_case("synthetic-noise-endpoint", noisy, [
        ("p=1 flips every zero outcome to one", set(noisy["counts"]) == {"1"}, noisy["counts"]),
        ("shot total is preserved", sum(noisy["counts"].values()) == shots, sum(noisy["counts"].values()))
    ])

    passed = sum(1 for case in cases if case["passed"])
    return {
        "suite_schema": "qwp777-conformance-suite-1",
        "release": "1.5.0",
        "shots_per_case": shots,
        "seed": seed,
        "summary": {"cases_total": len(cases), "cases_passed": passed,
                    "cases_failed": len(cases)-passed, "passed": passed == len(cases)},
        "cases": cases,
        "notes": [
            "This is a small built-in software conformance suite, not a certification.",
            "Sampling checks use fixed seeds and broad tolerances.",
            "No physical quantum hardware is tested."
        ]
    }
