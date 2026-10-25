# Qwantum Processor 777 — QWP-777 v3.1.0

QWP-777 is a software-based stabilizer / Clifford-circuit simulator and validation toolkit. It is not physical quantum hardware, and 777 is the product target/name rather than a claim that arbitrary 777-qubit circuits can be efficiently simulated.

**Software release:** 3.1.0 · **API:** 3.0 (compatible) · **Result schema:** `qwp777-experiment-1`

## What's new in v3.1.0

- GitHub Actions now separates read-only validation from tag-only publishing.
- A release tag must match `VERSION` exactly (for example, `v3.1.0`) or publication stops.
- Tagged releases are built from validated artifacts, their SHA-256 sidecar is checked again, and the workflow publishes a GitHub Release.
- The workflow requests GitHub/Sigstore artifact provenance for the release ZIP.
- The local release pipeline derives its archive and report filenames from `VERSION`, so new versions no longer require editing every hard-coded output path.
- New tests cover exact tag/version matching and reject mismatched or malformed tags.
- Public API signatures and `qwp777-experiment-1` remain unchanged.

## Quick start

Requires Python 3.12+ (the CI workflow is configured for Python 3.12).

```bash
python -m unittest discover -s tests -v
python src/qwp777_api.py --help
python src/qwp777_release_audit.py -o docs/RELEASE_AUDIT.json
```

## Build a release package locally

```bash
bash scripts/ci_release.sh
```

The pipeline runs compilation, the full unit suite, API compatibility, fixed-seed regression, SBOM verification, offline dependency audit, release audit, provenance checks, manifest verification, and ZIP integrity checks. Artifacts are written to `../dist-v3.1.0` by default, or to the output path supplied as the first argument.

## Release tagging

Before creating a tag, commit the desired source and `VERSION` together. For this release, the tag must be exactly `v3.1.0`. On GitHub, the workflow runs validation first; only a matching `v*` tag can proceed to the publication job. The publishing job downloads only the validated artifact bundle, rechecks the ZIP checksum, attests the archive, and creates the GitHub Release.

## Verifying downloads

```bash
sha256sum -c Qwantum-Processor-777-v3.1.0.zip.sha256
unzip Qwantum-Processor-777-v3.1.0.zip
cd QWP-777-v3.1.0
python src/qwp777_release_package.py verify --root .
python src/qwp777_provenance.py verify --root .
```

To verify a GitHub artifact attestation, use GitHub CLI with the release archive and repository identity, for example:

```bash
gh attestation verify Qwantum-Processor-777-v3.1.0.zip --repo OWNER/REPOSITORY
```

Replace `OWNER/REPOSITORY` with the actual GitHub repository path. This attestation step is only created when the workflow runs in a supported GitHub repository with the required permissions.

## Security and scientific limitations

- The dependency audit is static and offline; it does not query CVE, OSV, or vendor advisory databases.
- Local testing does not prove the GitHub-hosted workflow itself succeeded. A release run must be confirmed in the repository's Actions tab.
- GitHub/Sigstore attestation authenticates workflow provenance when supported and verified; it is not a proof of scientific correctness.
- Passing simulation tests is not proof of general-purpose quantum hardware equivalence.
