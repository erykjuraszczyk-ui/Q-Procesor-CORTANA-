# Known Limitations — QWP-777 v1.1.0

1. The stabilizer tableau is a prototype and has not been independently validated for all gate sequences.
2. The supported Clifford gate set is H, S, X, Z, CX, CZ, and computational-basis MEASURE.
3. The statevector reference is limited to 12 qubits due to exponential memory/time growth.
4. The reference oracle is part of this same project, not an independent third-party simulator.
5. The statevector reference helper computes ideal probabilities for unitary circuits only; remove measurement operations before calling it.
6. No dynamic circuits, mid-circuit measurements, arbitrary non-Clifford gate simulation, physical hardware, or physical noise model are provided.
7. Shannon entropy is calculated from empirical measurement frequencies; it is descriptive and not a direct physical entropy measurement.
8. A 777-qubit tableau allocation test verifies data-structure capacity only, not universal simulation accuracy or performance.
9. Local tests do not constitute cross-platform qualification or scientific certification.


## v1.2.0 additions and limits
- The optional Qiskit Aer adapter requires separate compatible `qiskit` and `qiskit-aer` installs.
- The built-in bit-flip option post-processes measurement strings and is not a calibrated physical noise model.
- The optional adapter is intended for small circuits; its 30-qubit guard is not a promise that any 30-qubit circuit will fit in memory.

## v1.3.0 comparison caveats
- Distribution comparison is statistical only and cannot prove correctness or equivalence for all possible circuits.
- Results should only be compared when the circuit and measured-qubit order are equivalent.

## v1.4.0 statistical caveats
- Outcome-wise intervals are not simultaneous family-wise intervals. Difference intervals use a normal approximation.
- Intervals quantify sampling uncertainty only; systematic errors and circuit mismatch are outside the model.

## v1.5.0 significance-analysis caveats
- Pearson chi-square p-values use an asymptotic approximation and are withheld when any expected cell count is below 5.
- The significance test is not adjusted for multiple comparisons.
- A non-significant result is not proof of equivalence; detected differences do not prove a backend is incorrect.
- Built-in conformance cases are limited regression checks, not exhaustive verification or physical-hardware certification.

## v1.6.0 regression, backend, and archive caveats
- Fixed-seed regression detects changes against a small saved baseline; it is not exhaustive verification.
- Qiskit Aer is optional and is a classical simulator. If it is not installed, no external-backend comparison has been performed.
- Backend samples use different random streams; small distribution differences are expected.
- Archive SHA-256 checksums verify byte identity, not correctness or scientific validity.

## v1.7.0 security and compatibility caveats
- HMAC-SHA256 is symmetric authentication, not public-key signing; verification requires the same secret.
- Unsigned archives may be created for convenience unless `--require-signature` is used; signature verification rejects unsigned archives.
- API compatibility is source-level (exports, selected callable signatures, and result schema), not exhaustive semantic verification.
- A baseline refresh creates a new versioned artifact; human review is still required before using it as an authoritative release gate.

## v1.8.0 statistical and signing caveats
- Cross-release empirical distribution changes do not automatically establish a regression; inspect seeds, shot counts, and intentional algorithm changes.
- Regression report comparison is limited to cases present in reports and cannot prove equivalence outside those cases.
- Ed25519 signing requires the optional `cryptography` package and secure handling of the private key.
- Trust in Ed25519 verification depends on obtaining the correct public key through a trusted channel. A valid signature does not prove scientific correctness.
- HMAC-SHA256 remains symmetric authentication and requires a shared secret.

## v1.9.0 release-audit caveats
- The release audit covers selected tests, public API contracts, and finite regression baselines; it is not formal verification.
- Signature self-tests check implementation behavior using temporary keys. Real release authenticity depends on trusted key distribution.
- Qiskit Aer execution remains optional and is not asserted unless the backend actually ran.


## v2.2.0 performance and memory
- The memory estimator covers Python list containers for the tableau and phase vector only; it is not a process-RSS estimator.
- The per-shot temporary tableau copy is skipped by the experiment runner, but the simulator still allocates its O(n²) X/Z tables for each shot.
- The benchmark uses a specific GHZ-style Clifford circuit and bounded workloads; its values do not generalize to arbitrary circuits or other hardware.
- Target-device measurements on Android/Termux and Linux remain necessary.

## v2.3.0 stability and memory diagnostics
- `qwp777_soak.py` uses a bounded work proxy, not a guaranteed runtime or energy estimate.
- RSS sampling reads `VmRSS` from `/proc/self/status` where available; it can be unavailable on non-procfs systems and is host-specific.
- A short soak run does not prove the absence of memory leaks. Inspect repeated reports over longer durations and on every supported target device.
- Profile comparison rejects different workload identity fields, but thermal state, system load, battery/power mode and other environmental effects can still confound results.
- Actual Android/Termux compatibility remains unverified until the package is run on a physical target device.
