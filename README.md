# QWP-777 — Qwantum Processor 777

**Release:** v3.1.0  
**API contract:** 3.0  
**Result schema:** `qwp777-experiment-1`

QWP-777 is a software prototype for simulating stabilizer/Clifford quantum circuits and conducting reproducible experiments. It is **not** a physical quantum processor and should not be described as a universal simulator for arbitrary circuits at 777 qubits.

## Release package

The v3.1.0 ZIP package was built and tested locally. The reported local checks were:
- Unit tests: 195/195 passed.
- Release audit: 21/21 checks passed.
- Manifest: 236/236 packaged files matched.
- Archive, SBOM, provenance and detached manifest signature verification passed.

These are local results; they do not mean GitHub Actions has run on this repository.

## Import the full source package

The full v3.1.0 ZIP is currently available as a ChatGPT conversation attachment, not as a public GitHub asset. To populate this repository with all source files, download that ZIP to your computer or Android device, extract it, then copy the extracted project contents into this repository and push the commit.

### Termux / Android

1. Download `Qwantum-Processor-777-v3.1.0.zip` from the conversation into **Download**.
2. Run:

```bash
pkg update
pkg install git unzip
termux-setup-storage
cd ~/storage/shared/Download
unzip Qwantum-Processor-777-v3.1.0.zip
cd QWP-777-v3.1.0
git init
git branch -M main
git remote add origin https://github.com/erykjuraszczyk-ui/Q-Procesor-CORTANA-.git
git add .
git commit -m "feat: import QWP-777 v3.1.0"
git push -u origin main
```

If this repository already has commits or a remote configured, do not run `git init` or overwrite history. Instead clone the repository and copy the extracted files into the clone, then commit and push.

## Verification

Check the ZIP hash before extracting:

```bash
sha256sum Qwantum-Processor-777-v3.1.0.zip
```

Expected SHA-256:

```
e73b1f9b65faa991b32a0d29ed39f68a6bff57bd985eca6c9c817d0bebdf69b7
```

The signature verifies a manifest against the supplied public key; it does not independently establish publisher identity. Verify the public-key fingerprint through a trusted, independent channel.

## Scope and limitations

- No claim of execution on real quantum hardware.
- Dependency vulnerability status has not been assessed against live CVE/OSV databases.
- Android/Termux testing and remote GitHub Actions execution remain unverified.
