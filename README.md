# QWP-777 — Qwantum Processor 777

**Release:** v3.1.0  
**API contract:** 3.0  
**Result schema:** `qwp777-experiment-1`

QWP-777 is a software prototype for simulating stabilizer/Clifford quantum circuits and conducting reproducible experiments. It is **not** a physical quantum processor and is not a universal simulator for arbitrary circuits at 777 qubits.

## Release package

The v3.1.0 ZIP was built and tested locally:
- Unit tests: 195/195 passed.
- Release audit: 21/21 checks passed.
- Manifest: 236/236 packaged files matched.
- Archive, SBOM, provenance and detached manifest signature verification passed.

These are local results; GitHub Actions has not yet been confirmed running on this repository.

## Import the full source package

The full ZIP is currently attached to the ChatGPT conversation, not published as a public GitHub Release asset. To add all project files, download the ZIP from the conversation to your device and follow the steps below.

### Termux / Android

1. Download `Qwantum-Processor-777-v3.1.0.zip` into **Download**.
2. Run:

```bash
pkg update
pkg install git unzip
termux-setup-storage
cd ~/storage/shared/Download
unzip Qwantum-Processor-777-v3.1.0.zip
git clone https://github.com/erykjuraszczyk-ui/Q-Procesor-CORTANA-.git
cd Q-Procesor-CORTANA-
cp -a ../QWP-777-v3.1.0/. .
git status --short
git add .
git commit -m "feat: import QWP-777 v3.1.0"
git push origin main
```

Review `git status --short` before committing. Do not force-push or overwrite repository history. If the extracted directory has a different name, adjust the `cp` source path accordingly. GitHub may prompt for authentication; use an approved credential method, never paste a token into this README or a public file.

## Verification

Check the ZIP hash before extracting:

```bash
sha256sum Qwantum-Processor-777-v3.1.0.zip
```

Expected SHA-256:

```
e73b1f9b65faa991b32a0d29ed39f68a6bff57bd985eca6c9c817d0bebdf69b7
```

A detached signature verifies the manifest against the supplied public key; it does not independently establish publisher identity. Verify the public-key fingerprint through an independent trusted channel.

## Scope and limitations

- No claim of execution on real quantum hardware.
- Dependency vulnerability status has not been assessed against live CVE/OSV databases.
- Android/Termux testing and remote GitHub Actions execution remain unverified.
