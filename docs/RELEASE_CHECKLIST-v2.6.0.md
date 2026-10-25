# Release checklist — QWP-777 v2.6.0

- [x] API version and release metadata advanced to 2.6 / 2.6.0.
- [x] New immutable API contract snapshot created.
- [x] New versioned regression baseline and SHA-256 sidecar created.
- [x] Historical API contracts and regression baselines preserved.
- [x] Multi-release series tool and unit tests added.
- [x] Release audit includes the multi-release smoke check.
- [x] Public `qwp777_api` export names/signatures preserved.
- [x] Result schema remains `qwp777-experiment-1`.
- [ ] Run tests on a physical Android/Termux device before claiming Android-specific validation.
- [ ] Run Qiskit Aer comparisons separately if the optional backend is desired.
