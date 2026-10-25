# Migration: QWP-777 v1.0.0 → v1.1.0

- Core `run_circuit` and CLI entry points remain available.
- API version advances to `1.1`; result schema remains `qwp777-experiment-1`.
- New optional public functions: `summarize_counts`, `statevector_probabilities`, `validate_probability_distribution`, and `compare_counts_to_reference`.
- Reference circuits must be unitary-only: remove all MEASURE operations before calling `statevector_probabilities` or `compare_counts_to_reference`.
- The reference backend is capped at 12 qubits.
