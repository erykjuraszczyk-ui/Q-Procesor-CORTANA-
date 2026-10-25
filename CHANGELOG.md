# Changelog — QWP-777 v3.1.0

## v3.1.0 — CI publishing and artifact provenance

- Split GitHub Actions into a read-only validation/package job and a tag-only publishing job with separate permissions.
- Added strict release-tag guard: only `v<VERSION>` is accepted for publication.
- Added a second checksum verification before publishing the release archive.
- Added GitHub/Sigstore artifact provenance attestation for the ZIP on tag releases.
- Automated GitHub Release asset publication with ZIP, SHA-256 sidecar, manifest, SBOM, dependency audit, provenance, audit report, test report, and regression report.
- Made the local build pipeline derive archive/report paths from the `VERSION` file.
- Added unit coverage for matching/mismatching tags and validated package metadata for v3.1.0.
- Kept API 3.0 public signatures and the `qwp777-experiment-1` result schema unchanged.

## v3.0.0 — CI/release pipeline baseline

- Added the fail-fast local CI/release script and GitHub Actions artifact packaging workflow.
- Added API contract, fixed-seed regression, CycloneDX SBOM, offline dependency audit, release audit, and provenance checks.
- Added an external Ed25519 manifest-signing utility; signing keys remain outside the ZIP.
