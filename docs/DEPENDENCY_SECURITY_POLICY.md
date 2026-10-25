# Dependency and SBOM policy — v2.9.0

## Dependency model
- Required runtime dependencies: none beyond Python standard library for core simulator operation.
- Optional `cryptography`: Ed25519 release-manifest signing/verification.
- Optional `qiskit` and `qiskit-aer`: external comparison/simulation adapter.
- Versions are intentionally reported as unlocked; observed build versions are contextual, not resolved install constraints.

## SBOM
`docs/SBOM.cdx.json` uses CycloneDX 1.6. The SBOM inventories the QWP-777 application and declared optional integrations. The dependency policy file is hashed into SBOM metadata and compared during verification.

## Static dependency audit
`src/qwp777_dependency_audit.py` extracts source imports, filters Python standard-library and in-project modules, checks that external imports are declared, verifies SBOM completeness, and records which optional dependencies are installed in the build environment.

## Vulnerability scan status
The utility deliberately makes no network calls. It does not query CVE, OSV, GitHub Advisory Database, OS vendor data, malware lists, or license data. `vulnerability_status` is `not_assessed`. A passing report means only that the documented static checks passed.

## Release order
1. Review `DEPENDENCIES.json` when imports or integrations change.
2. Generate `docs/SBOM.cdx.json`.
3. Run dependency audit and review `docs/DEPENDENCY_AUDIT.json`.
4. Run unit tests, regression, release audit and manifest/signature steps.
5. Verify the final ZIP and detached SHA-256 after packaging.
