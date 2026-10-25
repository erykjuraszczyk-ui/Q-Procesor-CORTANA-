# QWP-777 v2.0.0 release checklist

- [x] Release metadata set to `2.0.0`, API contract set to `2.0`.
- [x] Frozen current API snapshot created without modifying the historical v1.6.0 contract.
- [x] Historical and current fixed-seed regression baselines included with checksums.
- [x] Migration guide and API versioning policy included.
- [ ] Maintainer follow-up: run tests on target Termux/Android, Linux, and Windows environments.
- [ ] Maintainer follow-up: run optional comparison against an independently installed simulator such as Qiskit Aer.

Checks above apply only to the locally built package. They do not imply physical-hardware testing, formal verification, or independent scientific validation.
