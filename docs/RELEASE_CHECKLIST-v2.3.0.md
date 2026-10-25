# QWP-777 v2.3.0 release checklist

- [x] Unit tests pass from the source tree and unpacked ZIP.
- [x] API compatibility is checked against `compatibility/api-v1.6.0.json` and `compatibility/api-v2.3.0.json`.
- [x] Historical regression baseline v1.5.0 and current baseline v2.3.0 pass.
- [x] SHA-256 sidecar for v2.3.0 baseline verifies.
- [x] Release comparison against v2.2.0 is clean.
- [x] Profile, memory estimate, scale benchmark and soak-smoke tests pass in the unified audit.
- [x] HMAC signature roundtrip passes; Ed25519 passes or is marked as unavailable if its optional dependency is absent.
- [x] ZIP integrity and ZIP SHA-256 were checked after packaging; unpacked tests and audit pass.
- [ ] Device-specific Android/Termux soak test is run separately before making device-specific claims.
