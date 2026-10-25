# QWP-777 v2.1.0 release checklist

- [x] Release metadata set to `2.1.0`, API version to `2.1`.
- [x] Current API snapshot created; v1.6.0 and v2.0.0 contracts preserved.
- [x] Added platform-portable timing and traced-allocation profiler.
- [x] Added best-effort runtime metadata collector.
- [x] Added profiling/runtime smoke check to unified release audit.
- [x] New fixed-seed regression baseline with SHA-256 sidecar.
- [ ] Maintainer follow-up: run tests on actual Android/Termux, Linux, and Windows targets.
- [ ] Maintainer follow-up: run optional Qiskit Aer comparison where installed.

Passing local tests does not imply target-device testing, formal verification, physical hardware validation, or universal 777-qubit simulation.
