# Migration guide — v2.7.0 → v2.8.0

## Runtime/API

- The public `qwp777_api` export names and callable signatures are unchanged.
- The release identifier advances to `2.8.0`, and the API identifier advances to `2.8`.
- The result schema remains `qwp777-experiment-1`.
- Historical contracts and regression baselines are retained. A new frozen contract and fixed-seed regression baseline are supplied for v2.8.0.

## New release-integrity workflow

1. Run the full unit tests and unified release audit.
2. Generate `docs/PROVENANCE.json` using `qwp777_provenance.py create` after `docs/RELEASE_AUDIT.json` and `docs/TEST_REPORT.json` exist.
3. Build the manifest and ZIP with `qwp777_release_package.py build`.
4. Sign the exact `docs/RELEASE_MANIFEST.json` bytes using `qwp777_release_signing.py sign`. Keep the private key outside the project and distribute the detached signature and public key separately from the ZIP.
5. On receipt, check the ZIP `.sha256`, extract the archive, verify the manifest, verify provenance, and verify the Ed25519 signature with the public key whose fingerprint has been independently trusted.

## Trust/security limits

A ZIP SHA-256 sidecar detects byte changes only if the expected digest itself is obtained from a trusted source. An Ed25519 signature validates the exact manifest bytes against a public/private key pair; it does not establish the publisher's identity without an independently trusted fingerprint. Provenance is a structured build summary, not an SLSA/in-toto attestation, code-signing certificate, or reproducible-build proof.
