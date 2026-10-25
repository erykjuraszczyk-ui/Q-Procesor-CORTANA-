# QWP-777 v2.2.0 release checklist

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Verify current API snapshot `compatibility/api-v2.2.0.json`.
- [ ] Run v1.5.0 historical and v2.2.0 current regression baselines.
- [ ] Verify current baseline SHA-256 sidecar.
- [ ] Compare against the v2.1.0 regression report.
- [ ] Check HMAC-SHA256 and Ed25519 self-tests (Ed25519 may report optional dependency unavailable).
- [ ] Check memory-estimator and benchmark smoke gates.
- [ ] Review benchmark workload budget before long runs.
- [ ] Regenerate `docs/RELEASE_AUDIT.json` and `docs/TEST_REPORT.md`.
- [ ] Validate the final ZIP after extraction and generate its SHA-256 sidecar.
- [ ] Collect independent performance/memory measurements on Android/Termux and Linux target devices before making hardware-specific claims.
