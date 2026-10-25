# Migration guide: v2.8.0 → v2.9.0

No breaking public Python API changes are introduced. The result schema remains `qwp777-experiment-1`; the frozen API contract moves to API 2.9.

New release workflows should generate and verify the SBOM before generating the release manifest:

```bash
python src/qwp777_sbom.py generate --root . --output docs/SBOM.cdx.json
python src/qwp777_sbom.py verify --root . --sbom docs/SBOM.cdx.json
python src/qwp777_dependency_audit.py --root . --sbom docs/SBOM.cdx.json -o docs/DEPENDENCY_AUDIT.json
python -m unittest discover -s tests -v
python src/qwp777_release_audit.py -o docs/RELEASE_AUDIT.json
```

The audit is offline and static. It identifies undeclared imports and verifies SBOM declaration coverage; it does not report whether components are free of vulnerabilities. A separate live advisory scan and a lockfile would be required for a fuller supply-chain assessment.
