# Release signing and verification

QWP-777 signs the exact byte sequence in `docs/RELEASE_MANIFEST.json` using Ed25519. The detached signature envelope records the manifest SHA-256, size, release, algorithm, and SHA-256 fingerprint of the raw public key. The signature is external to the ZIP to avoid self-reference; the manifest itself is inside the ZIP and covers all regular project files except itself.

## Key generation

Install the optional dependency:

```bash
python -m pip install cryptography
```

Generate keys once, using a passphrase stored in an environment variable:

```bash
export QWP777_RELEASE_KEY_PASSPHRASE='use-a-unique-long-passphrase'
python src/qwp777_release_signing.py keygen \
  --private-key "$HOME/.config/qwp777/release-private.pem" \
  --public-key "$HOME/.config/qwp777/release-public.pem" \
  --passphrase-env QWP777_RELEASE_KEY_PASSPHRASE
```

Never add the private key or its passphrase to the repository, ZIP, shell history, or logs. The key generator refuses to overwrite existing key files.

## Sign after packaging

Build the ZIP first. Then sign the exact manifest included inside it:

```bash
python src/qwp777_release_signing.py sign \
  --manifest docs/RELEASE_MANIFEST.json \
  --private-key "$HOME/.config/qwp777/release-private.pem" \
  --password-env QWP777_RELEASE_KEY_PASSPHRASE \
  --output ../Qwantum-Processor-777-v3.1.0.manifest.sig.json
```

## Verify a downloaded release

After downloading the ZIP, its `.sha256` sidecar, the detached signature JSON and the PEM public key:

```bash
sha256sum -c Qwantum-Processor-777-v3.1.0.zip.sha256
unzip Qwantum-Processor-777-v3.1.0.zip
cd QWP-777-v3.1.0
python src/qwp777_release_package.py verify --root .
python src/qwp777_provenance.py verify --root .
python src/qwp777_release_signing.py verify \
  --manifest docs/RELEASE_MANIFEST.json \
  --signature ../Qwantum-Processor-777-v3.1.0.manifest.sig.json \
  --public-key ../Qwantum-Processor-777-v2.8.0.public.pem
```

Compare the public key fingerprint using a separately trusted channel before treating the signature as publisher authentication. A public key distributed beside a ZIP is not, by itself, an independent trust anchor.
