# QWP-777 v3.1.0 — CI and release automation

## Workflow stages

`.github/workflows/release.yml` performs two stages:

1. **Validate and package** on pushes to `main` / `master`, pull requests, version tags, and manual dispatch. It runs the local fail-fast release pipeline and uploads a named artifact bundle.
2. **Publish tagged release** only when `github.ref` begins with `refs/tags/v`. This job has the extra write permissions it needs, downloads the already-validated bundle, verifies the ZIP SHA-256 sidecar a second time, requests a GitHub/Sigstore artifact attestation, and publishes the release assets.

The publish job is conditional, not available to pull-request builds. The tag guard requires the tag to match `v` plus the exact semantic version in `VERSION`. For example, `VERSION=3.1.0` accepts only `v3.1.0`, not `v3.1.1`, `v3.1.0-rc1`, or `3.1.0`.

## Run locally

```bash
bash scripts/ci_release.sh
```

Pass a destination if needed:

```bash
bash scripts/ci_release.sh /tmp/qwp777-dist
```

The script uses `VERSION` to name the ZIP and output directory, and gates the release on compilation, unit tests, API compatibility, deterministic regression, CycloneDX SBOM verification, offline dependency audit, release audit, provenance verification, manifest verification, and archive integrity.

The tag helper can be tested directly:

```bash
python scripts/check_release_tag.py --tag v3.1.0
```

## Published assets and attestation

On a matching version tag, the workflow publishes the ZIP, SHA-256 sidecar, release manifest, SBOM, dependency audit, provenance JSON, release audit, test reports, and regression report. It then requests a Sigstore-backed GitHub artifact attestation for the ZIP. Verify it with:

```bash
gh attestation verify Qwantum-Processor-777-v3.1.0.zip --repo OWNER/REPOSITORY
```

Use the actual owner/repository slug and a GitHub CLI version that supports artifact attestations. Attestation availability depends on the repository visibility and GitHub plan. A repository owner must inspect the resulting Actions run and Release page; the workflow has not been executed remotely as part of this local build.

## Signing and trust boundary

The local Ed25519 helper in `src/qwp777_release_signing.py` remains available for organizations that want to use their own protected publisher key. Do not put private keys in the repository, ZIP, or untrusted pull-request environment. GitHub/Sigstore attestations use the GitHub workflow identity; an independently generated local public key beside a signature does not prove publisher identity unless its fingerprint is trusted through another channel.

## Limits

- The dependency audit is static/offline and does not query CVE/OSV/vendor advisories.
- A successful local pipeline is not evidence that GitHub-hosted Actions, GitHub Release publishing, or Termux/Android has been tested.
- Passing tests do not establish formal simulator correctness or physical quantum-hardware equivalence.
